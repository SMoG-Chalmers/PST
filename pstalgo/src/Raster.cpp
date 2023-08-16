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

#include <stdexcept>
#include <pstalgo/Debug.h>
#include <pstalgo/Raster.h>
#include <pstalgo/analyses/Common.h>

namespace psta
{
	CRaster::CRaster()
	{
		m_BB.SetEmpty();
	}

	CRaster::CRaster(uint32_t width, uint32_t height, RasterFormat format)
		: m_Width(width)
		, m_Height(height)
		, m_Pitch(width * RasterFormatPixelSize(format))
		, m_Format(format)
	{
		m_Bits = malloc(m_Pitch * m_Height);
		m_BB.SetEmpty();
	}

	CRaster::~CRaster()
	{
		free(m_Bits);
	}

	uint8_t RasterFormatPixelSize(RasterFormat format)
	{
		switch (format)
		{
		case RasterFormat_Byte:
			return 1;
		case RasterFormat_Float:
			return 4;
		}
		throw std::runtime_error("Unsupported raster data type");
	}
}

PSTADllExport psta_result_t PSTAGetRasterData(psta_raster_handle_t handle, SRasterData* ret_data)
{
	try {
		VerifyStructVersion(*ret_data);
		auto& raster = *(psta::CRaster*)handle;
		ret_data->BBMinX = raster.BB().m_Min.x;
		ret_data->BBMinY = raster.BB().m_Min.y;
		ret_data->BBMaxX = raster.BB().m_Max.x;
		ret_data->BBMaxY = raster.BB().m_Max.y;
		ret_data->Width  = raster.Width();
		ret_data->Height = raster.Height();
		ret_data->Pitch  = raster.Pitch();
		ret_data->Format = raster.Format();
		ret_data->Bits   = raster.Data();
		return PSTA_RESULT_OK;
	}
	catch (const std::exception& e) {
		LOG_ERROR(e.what());
	}
	catch (...) {
		LOG_ERROR("Unknown exception");
	}
	return PSTA_RESULT_ERROR;
}