#pragma once

#include <atomic>
#include <future>
#include <vector>

namespace psta
{
	template <class TLambda, typename TIndex>
	void parallel_for(TIndex end_index, TLambda&& lmbd)
	{
		std::atomic<TIndex> common_index_counter(0);

		auto worker = [&]()
		{
			for (;;)
			{
				const auto index = common_index_counter++;
				if (index >= end_index)
				{
					break;
				}

				lmbd(index);
			}
		};

		std::vector<std::future<void>> workers;
		for (uint32_t i = 0; i < std::thread::hardware_concurrency() - 1; ++i)
		{
			workers.push_back(std::async(std::launch::async, worker));
		}

		worker();

		for (auto& w : workers)
		{
			w.wait();
		}
	}
}