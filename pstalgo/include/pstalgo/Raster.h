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

#pragma once

#include <cstdint>
#include <stdexcept>
#include <type_traits>
#include <pstalgo/pstalgo.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/geometry/Rect.h>
#include <pstalgo/utils/Arr2d.h>

typedef psta_handle_t psta_raster_handle_t;

enum RasterFormat : uint8_t {
	RasterFormat_Undefined = 0,
	RasterFormat_Byte = 1,
	RasterFormat_Float = 2,
};

namespace psta
{
	class CRaster;

	template <typename T>
	inline Arr2dView<T> Arr2dViewFromRaster(CRaster& raster);

	template <typename T>
	inline Arr2dView<const T> Arr2dViewFromRaster(const CRaster& raster);

	class CRaster : public IPSTAlgo
	{
	public:
		CRaster();
		CRaster(uint32_t width, uint32_t height, RasterFormat format);
		~CRaster();

		template <typename T>
		inline operator Arr2dView<T>() { return Arr2dViewFromRaster<T>(*this); }

		template <typename T>
		inline operator Arr2dView<const T>() const { return Arr2dViewFromRaster<const T>(const_cast<CRaster&>(*this)); }

		void SetBB(const CRectd& bb) { m_BB = bb; }
		const CRectd& BB() const { return m_BB; }
		inline uint32_t Width() const { return m_Width; }
		inline uint32_t Height() const { return m_Height; }
		inline uint32_t Pitch() const { return m_Pitch; }
		inline RasterFormat Format() const { return m_Format; }
		inline void* Data() { return m_Bits; }
		inline const void* Data() const { return m_Bits; }

		double2 PixelSize() const { return double2(m_BB.Width() / m_Width, m_BB.Height() / m_Height); }

	private:
		uint32_t m_Width = 0;
		uint32_t m_Height = 0;
		uint32_t m_Pitch = 0;
		RasterFormat m_Format = RasterFormat_Undefined;
		void* m_Bits = nullptr;
		CRectd m_BB;
	};

	template <typename T> inline RasterFormat RasterFormatForType() { throw std::runtime_error("Unsupported raster data type"); }
	template <> inline RasterFormat RasterFormatForType<uint8_t>()  { return RasterFormat_Byte; }
	template <> inline RasterFormat RasterFormatForType<float>()    { return RasterFormat_Float; }

	template <typename T>
	inline Arr2dView<T> Arr2dViewFromRaster(CRaster& raster)
	{
		if (RasterFormatForType<std::remove_const_t<T>>() != raster.Format())
		{
			throw std::runtime_error("Raster data type mismatch");
		}
		return Arr2dView<T>((T*)raster.Data(), raster.Width(), raster.Height(), raster.Pitch() / sizeof(T));
	}

	uint8_t RasterFormatPixelSize(RasterFormat format);
}

struct SRasterData
{
	SRasterData() : m_Version(VERSION) {}

	// Version
	static const uint32_t VERSION = 1;
	uint32_t m_Version;
	
	double BBMinX;
	double BBMinY;
	double BBMaxX;
	double BBMaxY;

	uint32_t Width;
	uint32_t Height;
	uint32_t Pitch;
	RasterFormat Format;
	void* Bits;
};

PSTADllExport psta_result_t PSTAGetRasterData(psta_raster_handle_t handle, SRasterData* ret_data);