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
	class CBufferingPolygons : public IPSTAlgo
	{
	public:
		std::vector<uint32_t> PolygonCountPerCategory;
		std::vector<uint32_t> PolygonData;
		std::vector<double2> Coordinates;
		std::unique_ptr<CRaster> RangesRaster;
		std::unique_ptr<CRaster> GradientRaster;
	};

	/*
	template <class T>
	struct LineSegment
	{
		TVec2<T> p0;
		TVec2<T> p1;
	};

	template <class T>
	struct LineSegmentWithValues
	{
		TVec2<T> p0;
		TVec2<T> p1;
		float value0;
		float value1;
	};

	void MergeLineSets(
		const LineSegment<double>* lines0, 
		const float* values0, 
		uint32_t lineCount0, 
		const LineSegment<double>* lines1, 
		const float* values1, 
		uint32_t lineCount1,
		float padding,
		CRectd& out_bb,
		std::vector<LineSegmentWithValues<float>>& out_lines)
	{
		out_bb = CRectd::Union(
			CRectd::BBFromPoints((const double2*)lines0, lineCount0 * 2),
			CRectd::BBFromPoints((const double2*)lines1, lineCount1 * 2)).Inflated(padding);;

		const auto origin = out_bb.m_Min;

		out_lines.clear();
		out_lines.reserve(lineCount0 + lineCount1);
		for (uint32_t i = 0; i < lineCount0; ++i)
		{
			LineSegmentWithValues<float> l;
			l.p0 = float2(lines0[i].p0 - origin);
			l.p1 = float2(lines0[i].p1 - origin);
			l.value0 = values0[i];
			l.value1 = std::numeric_limits<float>::quiet_NaN();
			out_lines.push_back(l);
		}
		for (uint32_t i = 0; i < lineCount1; ++i)
		{
			LineSegmentWithValues<float> l;
			l.p0 = float2(lines1[i].p0 - origin);
			l.p1 = float2(lines1[i].p1 - origin);
			l.value0 = std::numeric_limits<float>::quiet_NaN();
			l.value1 = values1[i];
			out_lines.push_back(l);
		}

		std::sort(out_lines.begin(), out_lines.end(), [](const auto& a, const auto& b) -> bool
		{
			const auto cmp = memcmp(&a, &b, 4 * sizeof(float));
			return (0 == cmp) ? (int)isnan(a.value0) < (int)isnan(b.value0) : cmp < 0;
		});

		{
			size_t n = std::min(out_lines.size(), (size_t)1);
			for (size_t i = 1; i < out_lines.size(); ++i)
			{
				if (memcmp(&out_lines[n - 1].p0, &out_lines[i].p0, 4 * sizeof(float)) == 0)
				{
					out_lines[n - 1].value1 = out_lines[i].value1;
				}
				else
				{
					out_lines[n++] = out_lines[i];
				}
			}
			out_lines.resize(n);
		}
	}
	*/

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

	// Coordinates are expected to be relative to CENTER of upper left pixel in image.
	static void RasterCapsulesToPatch(Arr2dView<float>& img, const array_view<std::pair<float2, float2>> lines, float radius, const array_view<float> scores)
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
			RasterCapsulesToPatch(
				img.sub_view(patch_bb.m_Min.x, patch_bb.m_Min.y, patch_bb.Width(), patch_bb.Height()),
				make_array_view(lines_per_patch.data() + first_line_index, line_count),
				radius,
				make_array_view(scores_per_patch.data() + first_line_index, line_count));
		});
	}

	std::unique_ptr<CBufferingPolygons> CreateBufferingPolygons(SCreateBufferPolygonsDesc& desc, IProgressCallback& progress)
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

		// Calculate bounding box
		auto bb = CRectd::BBFromPoints((const double2*)desc.LineCoords1, desc.LineCount1 * 2);
		if (desc.LineCoords2)
		{
			const auto bb2 = CRectd::BBFromPoints((const double2*)desc.LineCoords2, desc.LineCount2 * 2);
			bb.GrowToIncludeRect(bb2);
		}
		bb.Inflate(desc.BufferSize * SIGMA_RANGE);
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

		typedef std::pair<double2, double2> line_t;

		const bool use_decay = true;
		if (use_decay)
		{
			auto raster_lines = [&](const line_t* lines, const float* intensities, size_t count, float multiplier)
			{
				for (size_t line_index = 0; line_index < count; ++line_index)
				{
					float2 p0(lines[line_index].first - pixel_origin);
					float2 p1(lines[line_index].second - pixel_origin);
					RasterLine(sdf_view, p0 * invPixelSizeMeters, p1 * invPixelSizeMeters, intensities[line_index] * multiplier);
				}
			};

			raster_lines((line_t*)desc.LineCoords1, desc.Values1, desc.LineCount1, -1.f);
			if (desc.LineCoords2)
			{
				raster_lines((line_t*)desc.LineCoords2, desc.Values2, desc.LineCount2, 1.f);
			}
			else
			{
				raster_lines((line_t*)desc.LineCoords1, desc.Values2, desc.LineCount1, 1.f);
			}

			GaussianBlur(sdf_view, desc.BufferSize * invPixelSizeMeters);
		}
		else
		{
			std::vector<std::pair<float2, float2>> lines;
			lines.reserve(std::max(desc.LineCount1, desc.LineCount2));

			const auto radiusInPixels = invPixelSizeMeters * desc.BufferSize;

			auto raster_pills = [&](Arr2dView<float> raster_view, const array_view<line_t> dlines, const array_view<float> intensities)
			{
				lines.resize(dlines.size());
				for (size_t line_index = 0; line_index < dlines.size(); ++line_index)
				{
					lines[line_index].first = float2(dlines[line_index].first - pixel_origin) * invPixelSizeMeters;
					lines[line_index].second = float2(dlines[line_index].second - pixel_origin) * invPixelSizeMeters;
				}
				RasterCapsules(raster_view, make_array_view(lines.data(), lines.size()), radiusInPixels, intensities);
			};

			// Before
			CRaster raster_before(sdf_raster->Width(), sdf_raster->Height(), sdf_raster->Format());
			auto raster_before_view = (Arr2dView<float>)raster_before;
			raster_before_view.Clear(0);
			raster_pills(raster_before_view, make_array_view((line_t*)desc.LineCoords1, desc.LineCount1), make_array_view(desc.Values1, desc.LineCount1));
			
			// After
			if (desc.LineCoords2)
			{
				raster_pills(sdf_view, make_array_view((line_t*)desc.LineCoords2, desc.LineCount2), make_array_view(desc.Values2, desc.LineCount2));
			}
			else
			{
				raster_pills(sdf_view, make_array_view((line_t*)desc.LineCoords1, desc.LineCount1), make_array_view(desc.Values2, desc.LineCount1));
			}

			// After - Before
			sdf_view.for_each_coords([&](uint32_t x, uint32_t y, float& pixel)
			{
				pixel -= raster_before_view.at(x, y);
			});


			// Before Only
			//raster_pills(sdf_view, make_array_view((line_t*)desc.LineCoords1, desc.LineCount1), make_array_view(desc.Values1, desc.LineCount1));

			// After only
			//raster_pills(sdf_view, make_array_view((line_t*)desc.LineCoords2, desc.LineCount2), make_array_view(desc.Values2, desc.LineCount2));
		}

		// Normalize value range [-1..1]
		{
			float min = std::numeric_limits<float>::max(), max = std::numeric_limits<float>::lowest();
			sdf_view.for_each([&](auto& value)
			{
				min = std::min(min, value);
				max = std::max(max, value);
			});
			const auto max_range = std::max(abs(min), abs(max));
			const auto inv_max_range = 1.f / max_range;
			sdf_view.for_each([&](auto& value)
			{
				value *= inv_max_range;
			});
		}

		auto result = std::make_unique<CBufferingPolygons>();
		result->PolygonData.reserve(1024);
		result->Coordinates.reserve(1024);

		if (desc.CreateRangesPolygons)
		{
			for (size_t range_index = 0; range_index < sizeof(RANGES) / sizeof(RANGES[0]); ++range_index)
			{
				const auto& range = RANGES[range_index];
				const auto polygons = PolygonsFromSdfGrid(sdf_view, range.first, range.second);

				// Calculate and reserve space
				size_t polygonDataSize = 0;
				size_t polygonPointCount = 0;
				for (const auto& polygon : polygons)
				{
					polygonDataSize += 1 + polygon.Rings.size();
					for (const auto& ring : polygon.Rings)
					{
						polygonPointCount += ring.size();
					}
				}
				result->PolygonData.reserve(result->PolygonData.size() + polygonDataSize);
				result->Coordinates.reserve(result->Coordinates.size() + polygonPointCount);

				for (const auto& polygon : polygons)
				{
					result->PolygonData.push_back((uint32_t)polygon.Rings.size());
					for (const auto& ring : polygon.Rings)
					{
						result->PolygonData.push_back((uint32_t)ring.size());
						for (const auto& pt : ring)
						{
							result->Coordinates.push_back(pixel_origin + (double2(pt) * desc.Resolution));
						}
					}
				}

				result->PolygonCountPerCategory.push_back((uint32_t)polygons.size());
			}
		}

		if (desc.CreateRangesRaster || desc.CreateGradientRaster)
		{
			sdf_view.FlipY();
		}

		if (desc.CreateRangesRaster)
		{
			auto ranges_raster = std::make_unique<CRaster>(
				sdf_raster->Width(),
				sdf_raster->Height(),
				RasterFormat_Byte);
			ranges_raster->SetBB(sdf_raster->BB());

			auto ranges_raster_view = (Arr2dView<uint8_t>)*ranges_raster;
			ranges_raster_view.Clear(0);

			for (uint32_t y = 0; y < sdf_view.Height(); ++y)
			{
				for (uint32_t x = 0; x < sdf_view.Width(); ++x)
				{
					const auto value = sdf_view.at(x, y);
					for (size_t range_index = 0; range_index < sizeof(RANGES) / sizeof(RANGES[0]); ++range_index)
					{
						const auto& range = RANGES[range_index];
						if (value >= range.first && value <= range.second)
						{
							ranges_raster_view.at(x, y) = (uint8_t)range_index + 1;
							break;
						}
					}
				}
			}

			result->RangesRaster = std::move(ranges_raster);
		}

		if (desc.CreateGradientRaster)
		{
			result->GradientRaster = std::move(sdf_raster);
		}

		desc.OutCategoryCount = (uint32_t)result->PolygonCountPerCategory.size();
		desc.OutPolygonCountPerCategory = result->PolygonCountPerCategory.empty() ? nullptr : result->PolygonCountPerCategory.data();
		desc.OutPolygonData = result->PolygonData.empty() ? nullptr : result->PolygonData.data();
		desc.OutPolygonCoords = result->Coordinates.empty() ? nullptr : (double*)result->Coordinates.data();
		desc.OutRangesRaster = result->RangesRaster.get();
		desc.OutGradientRaster = result->GradientRaster.get();

		return result;
	}
}

PSTADllExport psta_handle_t PSTACreateBufferPolygons(SCreateBufferPolygonsDesc* desc)
{
	try {
		VerifyStructVersion(*desc);

		CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

		return psta::CreateBufferingPolygons(*desc, progress).release();
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
	return nullptr;
}