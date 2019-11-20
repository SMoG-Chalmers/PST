/*
Copyright 2019 Meta Berghauser Pont

This file is part of PST.

PST is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version. The GNU General Public License
is intended to guarantee your freedom to share and change all versions
of a program--to make sure it remains free software for all its users.

PST is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with PST. If not, see <http://www.gnu.org/licenses/>.
*/

#include <vector>
#include <pstalgo/Vec2.h>

template <typename TVec> bool TIsPolygonSeparatorPoint(const TVec& pt)
{
	return std::isnan(pt.x);
}

template <typename TVec>
size_t TGeneratePointsAlongPolygonEdge(const TVec* points, unsigned int point_count, decltype(points->x) interval, TVec* buffer = nullptr, size_t max_count = 0)
{
	size_t count = 0;
	if (point_count)
	{
		if (buffer)
		{
			if (count >= max_count)
				throw std::runtime_error("Buffer too small");
			buffer[count] = points[0];
		}
		++count;

		decltype(((TVec*)0)->x) t = interval;
		for (unsigned int i = 0; i < point_count; ++i)
		{
			const auto& p0 = points[i];
			auto v = points[(i + 1 < point_count) ? i + 1 : 0] - p0;
			auto len = v.getLength();
			if (len > 0)
			{
				v /= len;
				if (i == point_count - 1)
				{
					// Make sure closing gap is in range [0.5*interval, 1.5*interval]
					len -= 0.5f * interval;
				}
				for (; t < len; t += interval)
				{
					if (buffer)
					{
						if (count >= max_count)
							throw std::runtime_error("Buffer too small");
						buffer[count] = p0 + (v * t);
					}
					++count;
				}
				t -= len;
			}
		}
	}
	return count;
}

template <typename TVec>
size_t TGeneratePointsAlongRegionEdge(const TVec* points, unsigned int point_count, float interval, TVec* buffer = nullptr, size_t max_count = 0)
{
	size_t count = 0;
	unsigned int first_index = 0;
	for (unsigned int i = 0; i <= point_count; ++i)
	{
		if ((i == point_count) || TIsPolygonSeparatorPoint(points[i]))
		{
			if (i > first_index)
				count += TGeneratePointsAlongPolygonEdge(points + first_index, i - first_index, interval, buffer ? buffer + count : nullptr, max_count - count);
			first_index = i + 1;
		}
	}
	return count;
}

size_t GeneratePointsAlongRegionEdge(const float2* points, unsigned int point_count, float interval, float2* buffer, size_t max_count)
{
	return TGeneratePointsAlongRegionEdge(points, point_count, interval, buffer, max_count);
}

void GeneratePointsAlongRegionEdge(const float2* points, unsigned int point_count, float interval, std::vector<float2>& ret_points)
{
	const auto count = TGeneratePointsAlongRegionEdge(points, point_count, interval);
	ret_points.resize(count);
	TGeneratePointsAlongRegionEdge(points, point_count, interval, ret_points.data(), ret_points.size());
}

size_t GeneratePointsAlongRegionEdge(const double2* points, unsigned int point_count, float interval, double2* buffer, size_t max_count)
{
	return TGeneratePointsAlongRegionEdge(points, point_count, interval, buffer, max_count);
}

void GeneratePointsAlongRegionEdge(const double2* points, unsigned int point_count, float interval, std::vector<double2>& ret_points)
{
	const auto count = TGeneratePointsAlongRegionEdge(points, point_count, interval);
	ret_points.resize(count);
	TGeneratePointsAlongRegionEdge(points, point_count, interval, ret_points.data(), ret_points.size());
}
