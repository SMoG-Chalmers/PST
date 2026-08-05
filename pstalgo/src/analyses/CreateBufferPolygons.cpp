/*
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. The GNU Lesser General Public License
is intended to guarantee your freedom to share and change all versions
of a program--to make sure it remains free software for all its users.

PST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with PST. If not, see <http://www.gnu.org/licenses/>.
*/

#include <algorithm>
#include <memory>
#include <stdexcept>
#include <vector>
#include <pstalgo/analyses/CreateBufferPolygons.h>
#include <pstalgo/Debug.h>
#include <pstalgo/geometry/Geometry.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/geometry/SignedDistanceField.h>
#include <pstalgo/gfx/Blur.h>
#include <pstalgo/utils/Arr2d.h>
#include <pstalgo/utils/Concurrency.h>
#include <pstalgo/Raster.h>
#include <pstalgo/Vec2.h>
#include <pstalgo/experimental/ArrayView.h>
#include <pstalgo/maths.h>
#include "../ProgressUtil.h"

namespace psta
{
	class CCompareResults : public IPSTAlgo
	{
	public:
		std::unique_ptr<CRaster> Raster;
	};

	static void RasterLine(Arr2dView<float>& img, const float2& p0, const float2& p1, float intensity)
	{
		const auto vLine = p1 - p0;
		const auto lineLength = vLine.getLength();
		const auto vTangent = vLine * (1.0f / lineLength);
		const int sampleCount = (int)ceil(lineLength * 2.f);
		const float sampleLength = lineLength / sampleCount;
		const float2 vStep = vTangent * sampleLength;
		const float sampleIntensity = sampleLength * intensity;

		auto checkCoords = [&](int x, int y) -> bool
		{
			return (x >= 0) & (x < (int)img.Width()) & (y >= 0) & (y < (int)img.Height());
		};

		auto samplePos = p0 + vStep * .5f;
		float sampleSum = 0;
		for (int sampleIndex = 0; sampleIndex < sampleCount; ++sampleIndex, samplePos += vStep)
		{
			const int x = (int)samplePos.x;
			const int y = (int)samplePos.y;
			const float dx = samplePos.x - (float)x;
			const float dy = samplePos.y - (float)y;
			if (checkCoords(x, y))
				img.at(x, y) += (1.f - dx) * (1.f - dy) * sampleIntensity;
			if (checkCoords(x + 1, y))
				img.at(x + 1, y) += dx * (1.f - dy) * sampleIntensity;
			if (checkCoords(x, y + 1))
				img.at(x, y + 1) += (1.f - dx) * dy * sampleIntensity;
			if (checkCoords(x + 1, y + 1))
				img.at(x + 1, y + 1) += dx * dy * sampleIntensity;
		}
	}

	static void RasterPoint(Arr2dView<float>& img, const float2& p, float intensity)
	{
		auto checkCoords = [&](int x, int y) -> bool
		{
			return (x >= 0) & (x < (int)img.Width()) & (y >= 0) & (y < (int)img.Height());
		};

		const int x = (int)p.x;
		const int y = (int)p.y;
		const float dx = p.x - (float)x;
		const float dy = p.y - (float)y;
		if (checkCoords(x, y))
			img.at(x, y) += (1.f - dx) * (1.f - dy) * intensity;
		if (checkCoords(x + 1, y))
			img.at(x + 1, y) += dx * (1.f - dy) * intensity;
		if (checkCoords(x, y + 1))
			img.at(x, y + 1) += (1.f - dx) * dy * intensity;
		if (checkCoords(x + 1, y + 1))
			img.at(x + 1, y + 1) += dx * dy * intensity;
	}

	// Deposits intensity * covered_cell_fraction into each cell, so that the total
	// deposited mass equals intensity * polygon_area (in pixel units). Coverage is
	// estimated with SSxSS supersampling per cell, even-odd fill rule (holes work
	// with any ring orientation). Vertices are expected in pixel space, relative to
	// CENTER of upper left pixel (same convention as RasterLine/RasterPoint).
	static void RasterPolygon(Arr2dView<float>& img, const float2* vertices, const unsigned int* ringPointCounts, unsigned int ringCount, float intensity)
	{
		const int SS = 4;  // Supersamples per pixel axis
		const float sampleWeight = 1.f / (SS * SS);

		unsigned int totalPointCount = 0;
		for (unsigned int r = 0; r < ringCount; ++r)
			totalPointCount += ringPointCounts[r];
		if (totalPointCount < 3)
			return;

		// Signed area (shoelace) for the sub-pixel fallback below
		float signedArea2 = 0;
		{
			const float2* v = vertices;
			for (unsigned int r = 0; r < ringCount; ++r)
			{
				const unsigned int n = ringPointCounts[r];
				for (unsigned int k = 0; k < n; ++k)
				{
					const auto& p0 = v[k];
					const auto& p1 = v[(k + 1) % n];
					signedArea2 += p0.x * p1.y - p1.x * p0.y;
				}
				v += n;
			}
		}

		const auto bb = CRectf::BBFromPoints(vertices, totalPointCount);

		// Sub-pixel polygons: scanline coverage quantizes to whole supersamples,
		// which is disproportionately coarse for tiny footprints. Deposit the exact
		// mass as a point instead.
		const float area = .5f * abs(signedArea2);
		if (area < 4.f * sampleWeight)
		{
			if (area > 0)
				RasterPoint(img, bb.Center(), intensity * area);
			return;
		}

		// Subsample row centers are at ((j + .5) / SS) - .5; pixel row = j / SS
		const int jMin = std::max(0, (int)ceil((bb.m_Min.y + .5f) * SS - .5f));
		const int jMax = std::min((int)img.Height() * SS - 1, (int)floor((bb.m_Max.y + .5f) * SS - .5f));

		std::vector<float> crossings;
		size_t coveredSampleCount = 0;
		for (int j = jMin; j <= jMax; ++j)
		{
			const float ys = ((j + .5f) / SS) - .5f;

			crossings.clear();
			const float2* v = vertices;
			for (unsigned int r = 0; r < ringCount; ++r)
			{
				const unsigned int n = ringPointCounts[r];
				for (unsigned int k = 0; k < n; ++k)
				{
					const auto& p0 = v[k];
					const auto& p1 = v[(k + 1) % n];
					if ((p0.y <= ys) != (p1.y <= ys))
						crossings.push_back(p0.x + (ys - p0.y) / (p1.y - p0.y) * (p1.x - p0.x));
				}
				v += n;
			}
			std::sort(crossings.begin(), crossings.end());

			const int y = j / SS;
			for (size_t s = 0; s + 1 < crossings.size(); s += 2)
			{
				const int kMin = std::max(0, (int)ceil((crossings[s] + .5f) * SS - .5f));
				const int kMax = std::min((int)img.Width() * SS - 1, (int)floor((crossings[s + 1] + .5f) * SS - .5f));
				for (int k = kMin; k <= kMax; ++k)
				{
					img.at(k / SS, y) += intensity * sampleWeight;
					++coveredSampleCount;
				}
			}
		}

		// Safety net for thin slivers with area above the threshold but too narrow
		// to catch any supersample: deposit the full mass as a point instead of
		// dropping the object silently.
		if (0 == coveredSampleCount)
			RasterPoint(img, bb.Center(), intensity * area);
	}

	static void RasterGeometry(Arr2dView<float>& img, SCompareResultsDesc::EGeometryType geometryType, const double2* coords, const unsigned int* polygonData, const float* values, size_t objectCount, float multiplier, const double2& pixelOrigin, float invPixelSize)
	{
		switch (geometryType)
		{
		case SCompareResultsDesc::Lines:
			for (size_t i = 0; i < objectCount; ++i)
			{
				const float2 p0(coords[i * 2] - pixelOrigin);
				const float2 p1(coords[i * 2 + 1] - pixelOrigin);
				RasterLine(img, p0 * invPixelSize, p1 * invPixelSize, values[i] * multiplier);
			}
			break;
		case SCompareResultsDesc::Points:
			for (size_t i = 0; i < objectCount; ++i)
			{
				const float2 p(coords[i] - pixelOrigin);
				RasterPoint(img, p * invPixelSize, values[i] * multiplier);
			}
			break;
		case SCompareResultsDesc::Polygons:
		{
			if (nullptr == polygonData)
				throw std::runtime_error("CompareResults: polygon data missing");
			std::vector<float2> vertices;
			std::vector<unsigned int> ringPointCounts;
			const unsigned int* pd = polygonData;
			const double2* v = coords;
			for (size_t i = 0; i < objectCount; ++i)
			{
				const unsigned int ringCount = *pd++;
				ringPointCounts.assign(pd, pd + ringCount);
				pd += ringCount;
				unsigned int pointCount = 0;
				for (unsigned int r = 0; r < ringCount; ++r)
					pointCount += ringPointCounts[r];
				vertices.clear();
				vertices.reserve(pointCount);
				for (unsigned int k = 0; k < pointCount; ++k, ++v)
					vertices.push_back(float2(*v - pixelOrigin) * invPixelSize);
				RasterPolygon(img, vertices.data(), ringPointCounts.data(), ringCount, values[i] * multiplier);
			}
			break;
		}
		default:
			throw std::runtime_error("CompareResults: unsupported geometry type");
		}
	}

	static size_t PolygonTotalPointCount(const unsigned int* polygonData, size_t polygonCount)
	{
		size_t pointCount = 0;
		const unsigned int* pd = polygonData;
		for (size_t i = 0; i < polygonCount; ++i)
		{
			const unsigned int ringCount = *pd++;
			for (unsigned int r = 0; r < ringCount; ++r)
				pointCount += *pd++;
		}
		return pointCount;
	}

	// Coordinates are expected to be relative to CENTER of upper left pixel in image.
	static void RasterCapsulesToPatch(Arr2dView<float> img, const array_view<std::pair<float2, float2>> lines, float radius, const array_view<float> scores)
	{
		const auto radius_sqrd = radius * radius;
		for (size_t i = 0; i < lines.size(); ++i)
		{
			const auto& line = lines[i];
			const auto v = (line.second - line.first);
			const float line_length = v.getLength();
			const auto tangent = v * (1.f / line_length);
			const auto score = scores[i];
			img.for_each_coords([&](auto x, auto y, auto& intensity)
			{
				const auto d_sqrd = DistanceFromPointToLineSegmentSqrd(float2((float)x, (float)y), line, line_length, tangent);
				intensity = std::max(intensity, (float)(d_sqrd <= radius_sqrd) * score);
			});
		}
	}

	// Coordinates are expected to be relative to CENTER of upper left pixel in image.
	static void RasterCapsules(Arr2dView<float>& img, const array_view<std::pair<float2, float2>> lines, float radius, const array_view<float> scores)
	{
		const int PATCH_DIM_MULTIPLE = 16;          // Patch size will be a multiple of this many pixels
		const int PATCH_MIN_RADIUS_MULTIPLIER = 2;  // Patch size will be at least as big as this many times the radius

		const int patch_dim = std::max(1, (int)ceil((radius * PATCH_MIN_RADIUS_MULTIPLIER) / PATCH_DIM_MULTIPLE)) * PATCH_DIM_MULTIPLE;
		const float inv_patch_dim = 1.f / patch_dim;
		const int patch_count_x = (img.Width()  + PATCH_DIM_MULTIPLE - 1) / PATCH_DIM_MULTIPLE;
		const int patch_count_y = (img.Height() + PATCH_DIM_MULTIPLE - 1) / PATCH_DIM_MULTIPLE;
		
		auto bb_from_patch = [&](int px, int py) -> CRecti
		{
			CRecti patch_bb;
			patch_bb.m_Min.x = px * patch_dim;
			patch_bb.m_Min.y = py * patch_dim;
			patch_bb.m_Max.x = std::min(patch_bb.m_Min.x + patch_dim, (int)img.Width());
			patch_bb.m_Max.y = std::min(patch_bb.m_Min.y + patch_dim, (int)img.Height());
			return patch_bb;
		};

		// For each patch, create a list of lines that intersect it
		std::vector<std::pair<float2, float2>> lines_per_patch;
		std::vector<float> scores_per_patch;
		auto patches = Arr2d<uint32_t>(patch_count_x, patch_count_y);
		patches.Clear(0);
		for (int twice = 0; twice < 2; ++twice)
		{
			for (const auto& line : lines)
			{
				auto bb = CRectf::BBFromPoints(&line.first, 2);
				bb.Inflate(radius);
				int px0 = clamp((int)(bb.m_Min.x * inv_patch_dim), 0, (int)patches.Width() - 1);
				int py0 = clamp((int)(bb.m_Min.y * inv_patch_dim), 0, (int)patches.Height() - 1);
				int px1 = clamp((int)ceil(bb.m_Max.x * inv_patch_dim), 0, (int)patches.Width());
				int py1 = clamp((int)ceil(bb.m_Max.y * inv_patch_dim), 0, (int)patches.Height());
				for (int py = py0; py < py1; ++py)
				{
					for (int px = px0; px < px1; ++px)
					{
						const auto patch_bb = (CRectf)bb_from_patch(px, py);
						if (TestAABBCapsuleOverlap(patch_bb, line.first, line.second, radius))
						{
							if (0 == twice)
							{
								++patches.at(px, py);
							}
							else
							{
								const float2 patch_offset((float)(px * patch_dim), (float)(py * patch_dim));
								auto index = --patches.at(px, py);
								lines_per_patch[index] = std::make_pair(line.first - patch_offset, line.second - patch_offset);
								scores_per_patch[index] = scores[&line - lines.data()];
							}
						}
					}
				}

			}
			if (1 == twice)
			{
				break;
			}
			uint32_t n = 0;
			patches.for_each([&](auto& patch)
			{
				n += patch;
				patch = n;
			});
			lines_per_patch.resize(n);
			scores_per_patch.resize(n);
		}

		parallel_for((uint32_t)patches.size(), [&](uint32_t patch_index)
		{
			const uint32_t py = patch_index / patches.Width();
			const uint32_t px = patch_index % patches.Width();

			const auto patch_bb = (CRecti)bb_from_patch(px, py);
			const uint32_t first_line_index = patches.at(px, py);
			const uint32_t last_line_index = (px == patches.Width() - 1 && py == patches.Height() - 1) ? (uint32_t)lines_per_patch.size() : *(&patches.at(px, py) + 1);
			const auto line_count = last_line_index - first_line_index;
			if (line_count == 0)
			{
				return;
			}
			//(Arr2dView<float>& img, const array_view<std::pair<float2, float2>> lines, float radius, const array_view<float> scores)
			RasterCapsulesToPatch(
				img.sub_view(patch_bb.m_Min.x, patch_bb.m_Min.y, patch_bb.Width(), patch_bb.Height()),
				make_array_view(lines_per_patch.data() + first_line_index, line_count),
				radius,
				make_array_view(scores_per_patch.data() + first_line_index, line_count));
		});
	}

	std::unique_ptr<CCompareResults> CompareResults(SCompareResultsDesc& desc, IProgressCallback& progress)
	{
		const std::pair<float, float> RANGES[] = {
			{std::numeric_limits<float>::lowest(), -0.50f},
			{-0.50f, -0.25f},
			{-0.25f, -0.10f},
			{-0.10f, -0.01f},
			{ 0.01f,  0.10f},
			{ 0.10f,  0.25f},
			{ 0.25f,  0.50f},
			{ 0.50f,  std::numeric_limits<float>::max()},
		};

		const float SIGMA_RANGE = 3.0f;

		const float pixelSizeMeters = desc.Resolution;
		const float invPixelSizeMeters = 1.0f / desc.Resolution;

		auto pointCountOf = [&](unsigned int objectCount, const unsigned int* polygonData) -> size_t
		{
			switch (desc.GeometryType)
			{
			case SCompareResultsDesc::Lines:    return objectCount * 2;
			case SCompareResultsDesc::Points:   return objectCount;
			case SCompareResultsDesc::Polygons:
				if (nullptr == polygonData)
					throw std::runtime_error("CompareResults: polygon data missing");
				return PolygonTotalPointCount(polygonData, objectCount);
			}
			throw std::runtime_error("CompareResults: unsupported geometry type");
		};

		// Calculate bounding box
		auto bb = CRectd::BBFromPoints((const double2*)desc.LineCoords1, (unsigned int)pointCountOf(desc.LineCount1, desc.PolygonData1));
		if (desc.LineCoords2)
		{
			const auto bb2 = CRectd::BBFromPoints((const double2*)desc.LineCoords2, (unsigned int)pointCountOf(desc.LineCount2, desc.PolygonData2));
			bb.GrowToIncludeRect(bb2);
		}
		bb.Inflate(desc.BlurRadius * SIGMA_RANGE);
		bb.m_Min.x = floor(bb.m_Min.x * invPixelSizeMeters) * pixelSizeMeters;
		bb.m_Min.y = floor(bb.m_Min.y * invPixelSizeMeters) * pixelSizeMeters;
		bb.m_Max.x = ceil(bb.m_Max.x  * invPixelSizeMeters) * pixelSizeMeters;
		bb.m_Max.y = ceil(bb.m_Max.y  * invPixelSizeMeters) * pixelSizeMeters;

		auto sdf_raster = std::make_unique<CRaster>(
			(uint32_t)round(invPixelSizeMeters * bb.Width()),
			(uint32_t)round(invPixelSizeMeters * bb.Height()),
			RasterFormat_Float);
		sdf_raster->SetBB(bb);

		auto sdf_view = (Arr2dView<float>)*sdf_raster;
		sdf_view.Clear(0);

		const double2 pixel_origin = bb.m_Min + double2(.5f, .5f) * pixelSizeMeters;

		if (SCompareResultsDesc::Normalized == desc.Mode)
		{
			{
				RasterGeometry(sdf_view, desc.GeometryType, (const double2*)desc.LineCoords1, desc.PolygonData1, desc.Values1, desc.LineCount1, -1.f, pixel_origin, invPixelSizeMeters);
				if (desc.LineCoords2)
				{
					RasterGeometry(sdf_view, desc.GeometryType, (const double2*)desc.LineCoords2, desc.PolygonData2, desc.Values2, desc.LineCount2, 1.f, pixel_origin, invPixelSizeMeters);
				}
				else
				{
					RasterGeometry(sdf_view, desc.GeometryType, (const double2*)desc.LineCoords1, desc.PolygonData1, desc.Values2, desc.LineCount1, 1.f, pixel_origin, invPixelSizeMeters);
				}

				GaussianBlur(sdf_view, desc.BlurRadius * invPixelSizeMeters);
			}

			// Normalize value range [-1..1]
			{
				float min = std::numeric_limits<float>::max(), max = std::numeric_limits<float>::lowest();
				sdf_view.for_each([&](auto& value)
				{
					min = std::min(min, value);
					max = std::max(max, value);
				});
				desc.OutMin = min;
				desc.OutMax = max;
				const auto max_range = std::max(abs(min), abs(max));
				const auto inv_max_range = 1.f / max_range;
				sdf_view.for_each([&](auto& value)
				{
					value *= inv_max_range;
				});
			}
		}
		else if (SCompareResultsDesc::RelativePercent == desc.Mode)
		{
			{
				CRaster before_raster(sdf_raster->Width(), sdf_raster->Height(), RasterFormat_Float);
				before_raster.SetBB(sdf_raster->BB());
				auto before_view = (Arr2dView<float>)before_raster;
				before_view.Clear(0);

				// Before
				RasterGeometry(before_view, desc.GeometryType, (const double2*)desc.LineCoords1, desc.PolygonData1, desc.Values1, desc.LineCount1, 1.f, pixel_origin, invPixelSizeMeters);
				GaussianBlur(before_view, desc.BlurRadius * invPixelSizeMeters);

				// After
				if (desc.LineCoords2)
				{
					RasterGeometry(sdf_view, desc.GeometryType, (const double2*)desc.LineCoords2, desc.PolygonData2, desc.Values2, desc.LineCount2, 1.f, pixel_origin, invPixelSizeMeters);
				}
				else
				{
					RasterGeometry(sdf_view, desc.GeometryType, (const double2*)desc.LineCoords1, desc.PolygonData1, desc.Values2, desc.LineCount1, 1.f, pixel_origin, invPixelSizeMeters);
				}
				GaussianBlur(sdf_view, desc.BlurRadius * invPixelSizeMeters);

				// Calculate difference
				for (uint32_t y = 0; y < sdf_view.Height(); ++y)
				{
					auto* before = &before_view.at(0, y);
					auto* after  = &sdf_view.at(0, y);
					for (uint32_t x = 0; x < sdf_view.Width(); ++x)
					{
						after[x] = 100.f * (std::max(after[x], desc.M) / std::max(before[x], desc.M) - 1.f);
					}
				}
			}

			// Calculate min and max
			{
				float min = std::numeric_limits<float>::max(), max = std::numeric_limits<float>::lowest();
				sdf_view.for_each([&](auto& value)
					{
						min = std::min(min, value);
						max = std::max(max, value);
					});
				desc.OutMin = min;
				desc.OutMax = max;
			}
		}

		sdf_view.FlipY();

		auto result = std::make_unique<CCompareResults>();

		result->Raster = std::move(sdf_raster);

		desc.OutRaster = result->Raster.get();

		return result;
	}
}

PSTADllExport psta_handle_t PSTACompareResults(SCompareResultsDesc* desc)
{
	try {
		VerifyStructVersion(*desc);

		CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

		return psta::CompareResults(*desc, progress).release();
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
	return nullptr;
}