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

#include <pstalgo/math/Gaussian.h>
#include <pstalgo/math/Integral.h>

namespace psta
{
	void GenerateGaussianKernel(float sigma_range, unsigned int num_values, float* ret_values)
	{
		const unsigned int INTEGRAL_STEPS = 10;

		if (0 == num_values)
			return;

		const unsigned int radius = num_values - 1;

		const float step = sigma_range / (0.5f + radius);

		float x = 0.5f * step;
		ret_values[0] = 2.0f * IntegralApprox(GaussianFunc, 0.0f, x, INTEGRAL_STEPS);

		for (unsigned int i = 1; i < num_values; ++i, x += step)
			ret_values[i] = IntegralApprox(GaussianFunc, x, x + step, INTEGRAL_STEPS);

		// Normalize
		float sum = 0.5f * ret_values[0];
		for (unsigned int i = 1; i < num_values; ++i)
			sum += ret_values[i];
		const float normalize_multiplier = 0.5f / sum;
		for (unsigned int i = 0; i < num_values; ++i)
			ret_values[i] *= normalize_multiplier;
	}
}