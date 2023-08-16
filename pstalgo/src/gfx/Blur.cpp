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

#include <future>
#include <vector>
#include <pstalgo/math/Gaussian.h>
#include <pstalgo/utils/Arr2d.h>

namespace psta
{
	void GaussianBlur(Arr2dView<float>& img, float sigma_range)
	{
		using namespace std;

		const int radius = (int)ceil(sigma_range * 3);

		auto* blur_kernel = (float*)alloca((radius + 1) * sizeof(float));
		GenerateGaussianKernel((float)radius / sigma_range, radius + 1, blur_kernel);

		psta::Arr2d<float> tmp(img.Width(), img.Height());
		tmp.Clear(0);

		auto vertical_pass = [&](int y_beg, int y_end)
		{
			for (int y = y_beg; y < y_end; ++y)
			{
				const int y_min = -std::min(y, radius);
				const int y_max = min((int)img.Height() - y - 1, radius);
				for (int x = 0; x < (int)img.Width(); ++x)
				{
					float s = 0.0f;
					for (int i = y_min; i <= y_max; ++i)
					{
						s += blur_kernel[abs(i)] * img.at(x, y + i);
					}
					tmp.at(x, y) = s;
				}
			}
		};

		auto horizontal_pass = [&](int y_beg, int y_end)
		{
			for (int y = y_beg; y < y_end; ++y)
			{
				for (int x = 0; x < (int)img.Width(); ++x)
				{
					const int x_min = -std::min(x, radius);
					const int x_max = std::min((int)img.Width() - x - 1, radius);
					float s = 0.0f;
					for (int i = x_min; i <= x_max; ++i)
					{
						s += blur_kernel[abs(i)] * tmp.at(x + i, y);
					}
					img.at(x, y) = s;
				}
			}
		};

		const auto max_thread_count = std::max(std::thread::hardware_concurrency(), 1u);
		const auto max_rows_per_thread = (uint32_t)(img.Height() + max_thread_count - 1) / max_thread_count;
			
		std::vector<std::future<void>> tasks;
		tasks.reserve(max_thread_count);

		for (size_t pass_index = 0; pass_index < 2; ++pass_index)
		{
			for (unsigned int thread_index = 0; thread_index < max_thread_count; ++thread_index)
			{
				const int y_beg = max_rows_per_thread * thread_index;
				const int y_end = std::min(y_beg + max_rows_per_thread, img.Height());
				if (y_end <= y_beg)
					break;
				if (pass_index == 0)
					tasks.push_back(std::async(std::launch::async, vertical_pass, y_beg, y_end));
				else
					tasks.push_back(std::async(std::launch::async, horizontal_pass, y_beg, y_end));
			}
			for (auto& task : tasks)
			{
				task.wait();
			}
			tasks.clear();
		}
	}
}