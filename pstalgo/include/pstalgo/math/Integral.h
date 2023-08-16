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

namespace psta
{
	template <class TFunc> float IntegralApprox(TFunc&& F, float x0, float x1, unsigned int num_steps)
	{
		const float step = (x1 - x0) / num_steps;
		const float half_step = 0.5f * step;
		float sum = 0.0f;
		float x = x0 + half_step;
		for (unsigned int i = 0; i < num_steps; ++i, x += step)
			sum += F(x);
		return sum * step;
	}
}