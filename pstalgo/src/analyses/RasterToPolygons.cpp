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
#include <pstalgo/analyses/RasterToPolygons.h>
#include <pstalgo/Debug.h>
#include <pstalgo/geometry/Geometry.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/geometry/SignedDistanceField.h>
#include <pstalgo/gfx/Blur.h>
#include <pstalgo/utils/Arr2d.h>
#include <pstalgo/utils/Span.h>
#include <pstalgo/Raster.h>
#include <pstalgo/Vec2.h>
#include <pstalgo/experimental/ArrayView.h>
#include <pstalgo/maths.h>
#include "../ProgressUtil.h"

namespace psta
{
	class COutputPolygons : public IPSTAlgo
	{
	public:
		std::vector<uint32_t> PolygonCountPerCategory;
		std::vector<uint32_t> PolygonData;
		std::vector<double2> Coordinates;
	};

	std::unique_ptr<COutputPolygons> RasterToPolygons(const CRaster& raster, const psta::span<std::pair<float,float>>& ranges, IProgressCallback& progress)
	{
		const auto& bb = raster.BB();
		const auto pixel_size = double2(raster.PixelSize().x, -raster.PixelSize().y);
		const auto pixel_origin = double2(raster.BB().m_Left + pixel_size.x * .5, raster.BB().m_Bottom + pixel_size.y * .5);

		auto result = std::make_unique<COutputPolygons>();
		result->PolygonData.reserve(1024);
		result->Coordinates.reserve(1024);

		{
			const auto raster_view = (Arr2dView<const float>)raster;

			for (const auto& range : ranges)
			{
				const auto polygons = PolygonsFromSdfGrid(raster_view, range.first, range.second);

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
							result->Coordinates.push_back(pixel_origin + (double2(pt) * pixel_size));
						}
					}
				}

				result->PolygonCountPerCategory.push_back((uint32_t)polygons.size());
			}
		}

		return result;
	}
}

PSTADllExport psta_handle_t PSTARasterToPolygons(SRasterToPolygonsDesc* desc)
{
	try {
		VerifyStructVersion(*desc);

		const auto ranges = psta::make_span(reinterpret_cast<const std::pair<float, float>*>(desc->Ranges), desc->RangeCount);

		CPSTAlgoProgressCallback progress(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

		auto result = psta::RasterToPolygons(*(const psta::CRaster*)desc->Raster, ranges, progress);
		
		desc->OutPolygonCountPerRange = result->PolygonCountPerCategory.empty() ? nullptr : result->PolygonCountPerCategory.data();
		desc->OutPolygonData = result->PolygonData.empty() ? nullptr : result->PolygonData.data();
		desc->OutPolygonCoords = result->Coordinates.empty() ? nullptr : (double*)result->Coordinates.data();

		return result.release();
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
	return nullptr;
}