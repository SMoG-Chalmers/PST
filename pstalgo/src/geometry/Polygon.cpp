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

#include <pstalgo/geometry/Polygon.h>

// NOTE: Assumes polygon is not self-intersecting
double2 PolygonCentroid(const double2* points, uint32 point_count, double& ret_area)
{
	if (point_count < 3)
	{
		ret_area = 0;
		if (0 == point_count)
			return double2(0, 0);
		if (1 == point_count)
			return *points;
		return (points[0] + points[1]) * .5;
	}

	const auto p0_times_one_third = points[0] * (1.0 / 3);

	double poly_area_acc_times_two = 0;
	double2 poly_centroid_acc(0, 0);
	for (uint32 i = 2; i < point_count; ++i)
	{
		const auto v0 = points[i-1] - points[0];
		const auto v1 = points[i] - points[i-1];
		const auto v1_mid = (points[i] + points[i - 1]) * .5;
		const auto tri_area_times_two = crp(v0, v1);
		const auto tri_centroid = p0_times_one_third + (v1_mid * (2.0 / 3));
		poly_area_acc_times_two += tri_area_times_two;
		poly_centroid_acc += tri_centroid * tri_area_times_two;
	}

	ret_area = poly_area_acc_times_two * .5;

	return (0.0 == poly_area_acc_times_two) ? points[0] : (poly_centroid_acc / poly_area_acc_times_two);
}