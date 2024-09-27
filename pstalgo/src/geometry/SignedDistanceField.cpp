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

#include <memory>
#include <queue>
#include <pstalgo/Debug.h>
#include <pstalgo/geometry/SignedDistanceField.h>

namespace psta
{
	class CBitMatrix
	{
	public:
		CBitMatrix(uint32_t width, uint32_t height)
			: m_Width(width)
			, m_Height(height)
			, m_PatchStride((width + 7) >> 3)
		{
			m_Bits = std::make_unique<uint64_t[]>(m_PatchStride * ((height + 7) >> 3));
		}

		inline const uint32_t Width() const 
		{
			return m_Width; 
		}

		inline const uint32_t Height() const 
		{
			return m_Height; 
		}

		inline void ClearAll()
		{
			memset(m_Bits.get(), 0, m_PatchStride * ((m_Height + 7) >> 3));
		}

		inline void Set(uint32_t x, uint32_t y)
		{
			ASSERT(x < m_Width && y < m_Height);
			const uint64_t mask = 1ULL << (((y & 7) << 3) | (x & 7));
			m_Bits[(y >> 3) * m_PatchStride + (x >> 3)] |= mask;
		}

		inline bool Get(uint32_t x, uint32_t y) const
		{
			ASSERT(x < m_Width && y < m_Height);
			const uint64_t mask = 1ULL << (((y & 7) << 3) | (x & 7));
			return (m_Bits[(y >> 3) * m_PatchStride + (x >> 3)] & mask) != 0;
		}

	private:
		std::unique_ptr<uint64_t[]> m_Bits;
		uint32_t m_Width;
		uint32_t m_Height;
		uint32_t m_PatchStride;
	};

	enum EDirection
	{
		Up,
		Right,
		Down,
		Left,
	};
	/*
	static std::vector<float2> TrailRing(const Arr2dView<float>& sdf, float edgeVal, const uint2& startPos, EDirection startDirection, Arr2dView<uint8_t>& directionBits)
	{
		const float MIN_RES = 0.05f;
		const float MIN_RES_SQRD = MIN_RES * MIN_RES;

		uint2 STEP_PER_DIR[4];
		STEP_PER_DIR[Up] = uint2(0, -1);
		STEP_PER_DIR[Right] = uint2(1, 0);
		STEP_PER_DIR[Down] = uint2(0, 1);
		STEP_PER_DIR[Left] = uint2(-1, 0);

		const auto readSdfSafe = [&](const uint2& pos) -> float
		{
			return ((pos.x < sdf.Width()) & (pos.y < sdf.Height())) ? sdf.at(pos.x, pos.y) : 0; // std::numeric_limits<float>::max();
		};

		const auto testSdf = [&](uint32_t x, uint32_t y) -> bool
		{
			return ((x < sdf.Width()) & (y < sdf.Height())) && sdf.at(x, y) >= edgeVal;
		};

		std::vector<float2> pts;
		auto pos = startPos;
		auto direction = startDirection;
		do
		{
			{
				const auto step = STEP_PER_DIR[direction];
				const auto a = readSdfSafe(pos);
				const auto b = readSdfSafe(pos + step);
				const auto t = (edgeVal - a) / (b - a);
				const auto pt = float2((float)pos.x + t * (int)step.x, (float)pos.y + t * (int)step.y);
				if (pts.empty() || (pt - pts.back()).getLengthSqr() > MIN_RES_SQRD)
				{
					pts.push_back(pt);
				}
			}

			directionBits.at(pos.x, pos.y) |= (1 << direction);
			switch (direction)
			{
			case Up:

				if (testSdf(pos.x + 1, pos.y - 1))
				{
					direction = Left;
					pos.x += 1;
					pos.y -= 1;
				}
				else if (testSdf(pos.x + 1, pos.y))
				{
					direction = Up;
					pos.x += 1;
				}
				else
				{
					direction = Right;
				}
				break;
			case Right:
				if (testSdf(pos.x + 1, pos.y + 1))
				{
					direction = Up;
					pos.x += 1;
					pos.y += 1;
				}
				else if (testSdf(pos.x, pos.y + 1))
				{
					direction = Right;
					pos.y += 1;
				}
				else
				{
					direction = Down;
				}
				break;
			case Down:
				if (testSdf(pos.x - 1, pos.y + 1))
				{
					direction = Right;
					pos.x -= 1;
					pos.y += 1;
				}
				else if (testSdf(pos.x - 1, pos.y))
				{
					direction = Down;
					pos.x -= 1;
				}
				else
				{
					direction = Left;
				}
				break;
			case Left:
				if (testSdf(pos.x - 1, pos.y - 1))
				{
					direction = Down;
					pos.x -= 1;
					pos.y -= 1;
				}
				else if (testSdf(pos.x, pos.y - 1))
				{
					direction = Left;
					pos.y -= 1;
				}
				else
				{
					direction = Up;
				}
				break;
			}
		} while (direction != startDirection || pos != startPos);

		if (!pts.empty() && (pts.front() - pts.back()).getLengthSqr() < MIN_RES_SQRD)
		{
			pts.pop_back();
		}

		return pts;
	}

	std::vector<SPolygon> PolygonsFromSdfGrid(const Arr2dView<float>& sdf, float edgeVal)
	{
		const uint2 FLOOD_FILL_STEPS[] = 
		{
			uint2(-1, -1),
			uint2( 0, -1),
			uint2( 1, -1),
			uint2( 1,  0),
			uint2( 1,  1),
			uint2( 0,  1),
			uint2(-1,  1),
			uint2(-1,  0),
		};
		Arr2d<uint8_t> directionBits(sdf.Width(), sdf.Height());
		directionBits.Clear();
		CBitMatrix visitedBits(sdf.Width(), sdf.Height());
		visitedBits.ClearAll();
		std::queue<uint2> queue;

		const auto testSdf = [&](uint32_t x, uint32_t y) -> bool
		{
			return ((x < sdf.Width()) & (y < sdf.Height())) && sdf.at(x, y) >= edgeVal;
		};

		std::vector<SPolygon> polygons;

		for (uint32_t y = 0; y < sdf.Height(); ++y)
		{
			for (uint32_t x = 0; x < sdf.Width(); ++x)
			{
				if (testSdf(x, y) && !testSdf(x, y - 1) && !(directionBits.at(x, y) & (1 << Up)))
				{
					SPolygon polygon;
					polygon.Rings.emplace_back(TrailRing(sdf, edgeVal, uint2(x, y), Up, directionBits));

					// Flood-fill polygon and look for holes
					visitedBits.Set(x, y);
					queue.push(uint2(x, y));
					while (!queue.empty())
					{
						const auto at = queue.front();
						queue.pop();
						if (!(directionBits.at(at.x, at.y) & (1 << Down)) && !testSdf(at.x, at.y + 1))
						{
							// Found hole
							polygon.Rings.emplace_back(TrailRing(sdf, edgeVal, at, Down, directionBits));
						}
						// Enqueue flood-fill steps
						for (const auto& step : FLOOD_FILL_STEPS)
						{
							auto stepTo = at + step;
							if (testSdf(stepTo.x, stepTo.y) && !visitedBits.Get(stepTo.x, stepTo.y))
							{
								visitedBits.Set(stepTo.x, stepTo.y);
								queue.push(stepTo);
							}
						}
					}

					polygons.emplace_back(std::move(polygon));
				}
			}
		}

		return polygons;
	}
	*/

	static std::vector<float2> TrailRing(const Arr2dView<const float>& sdf, float range_min, float range_max, const uint2& startPos, EDirection startDirection, Arr2dView<uint8_t>& directionBits)
	{
		const float MIN_RES = 0.05f;
		const float MIN_RES_SQRD = MIN_RES * MIN_RES;

		uint2 STEP_PER_DIR[4];
		STEP_PER_DIR[Up] = uint2(0, -1);
		STEP_PER_DIR[Right] = uint2(1, 0);
		STEP_PER_DIR[Down] = uint2(0, 1);
		STEP_PER_DIR[Left] = uint2(-1, 0);

		const auto readSdfSafe = [&](const uint2& pos) -> float
		{
			return ((pos.x < sdf.Width()) & (pos.y < sdf.Height())) ? sdf.at(pos.x, pos.y) : 0; // std::numeric_limits<float>::max();
		};

		const auto testInRange = [range_min, range_max](float value)
		{
			return (value >= range_min) & (value < range_max);
		};

		const auto testSdf = [&](uint32_t x, uint32_t y) -> bool
		{
			return ((x < sdf.Width()) & (y < sdf.Height())) && testInRange(sdf.at(x, y));
		};

		std::vector<float2> pts;
		auto pos = startPos;
		auto direction = startDirection;
		do
		{
			{
				const auto step = STEP_PER_DIR[direction];
				const auto a = readSdfSafe(pos);
				const auto b = readSdfSafe(pos + step);
				const auto t = (b > a) ? (range_max - a) / (b - a) : (range_min - a) / (b - a);
				const auto pt = float2((float)pos.x + t * (int)step.x, (float)pos.y + t * (int)step.y);
				if (pts.empty() || (pt - pts.back()).getLengthSqr() > MIN_RES_SQRD)
				{
					pts.push_back(pt);
				}
			}

			directionBits.at(pos.x, pos.y) |= (1 << direction);
			switch (direction)
			{
			case Up:

				if (testSdf(pos.x + 1, pos.y - 1))
				{
					direction = Left;
					pos.x += 1;
					pos.y -= 1;
				}
				else if (testSdf(pos.x + 1, pos.y))
				{
					direction = Up;
					pos.x += 1;
				}
				else
				{
					direction = Right;
				}
				break;
			case Right:
				if (testSdf(pos.x + 1, pos.y + 1))
				{
					direction = Up;
					pos.x += 1;
					pos.y += 1;
				}
				else if (testSdf(pos.x, pos.y + 1))
				{
					direction = Right;
					pos.y += 1;
				}
				else
				{
					direction = Down;
				}
				break;
			case Down:
				if (testSdf(pos.x - 1, pos.y + 1))
				{
					direction = Right;
					pos.x -= 1;
					pos.y += 1;
				}
				else if (testSdf(pos.x - 1, pos.y))
				{
					direction = Down;
					pos.x -= 1;
				}
				else
				{
					direction = Left;
				}
				break;
			case Left:
				if (testSdf(pos.x - 1, pos.y - 1))
				{
					direction = Down;
					pos.x -= 1;
					pos.y -= 1;
				}
				else if (testSdf(pos.x, pos.y - 1))
				{
					direction = Left;
					pos.y -= 1;
				}
				else
				{
					direction = Up;
				}
				break;
			}
		} while (direction != startDirection || pos != startPos);

		if (!pts.empty() && (pts.front() - pts.back()).getLengthSqr() < MIN_RES_SQRD)
		{
			pts.pop_back();
		}

		return pts;
	}

	std::vector<SPolygon> PolygonsFromSdfGrid(const Arr2dView<const float>& sdf, float range_min, float range_max)
	{
		const uint2 FLOOD_FILL_STEPS[] =
		{
			uint2(-1, -1),
			uint2(0, -1),
			uint2(1, -1),
			uint2(1,  0),
			uint2(1,  1),
			uint2(0,  1),
			uint2(-1,  1),
			uint2(-1,  0),
		};
		Arr2d<uint8_t> directionBits(sdf.Width(), sdf.Height());
		directionBits.Clear();
		CBitMatrix visitedBits(sdf.Width(), sdf.Height());
		visitedBits.ClearAll();
		std::queue<uint2> queue;

		const auto testSdf = [&](uint32_t x, uint32_t y) -> bool
		{
			if ((x >= sdf.Width()) | (y >= sdf.Height()))
			{
				return false;
			}
			const auto value = sdf.at(x, y);
			return (sdf.at(x, y) >= range_min) & (sdf.at(x, y) < range_max);
		};

		std::vector<SPolygon> polygons;

		for (uint32_t y = 0; y < sdf.Height(); ++y)
		{
			for (uint32_t x = 0; x < sdf.Width(); ++x)
			{
				if (testSdf(x, y) && !testSdf(x, y - 1) && !(directionBits.at(x, y) & (1 << Up)))
				{
					SPolygon polygon;
					polygon.Rings.emplace_back(TrailRing(sdf, range_min, range_max, uint2(x, y), Up, directionBits));

					// Flood-fill polygon and look for holes
					visitedBits.Set(x, y);
					queue.push(uint2(x, y));
					while (!queue.empty())
					{
						const auto at = queue.front();
						queue.pop();
						if (!(directionBits.at(at.x, at.y) & (1 << Down)) && !testSdf(at.x, at.y + 1))
						{
							// Found hole
							polygon.Rings.emplace_back(TrailRing(sdf, range_min, range_max, at, Down, directionBits));
						}
						// Enqueue flood-fill steps
						for (const auto& step : FLOOD_FILL_STEPS)
						{
							auto stepTo = at + step;
							if (testSdf(stepTo.x, stepTo.y) && !visitedBits.Get(stepTo.x, stepTo.y))
							{
								visitedBits.Set(stepTo.x, stepTo.y);
								queue.push(stepTo);
							}
						}
					}

					polygons.emplace_back(std::move(polygon));
				}
			}
		}

		return polygons;
	}

	void AddLineSegmentToSdf(Arr2dView<float>& sdf, const float2& p0, const float2& p1, float maxDistance)
	{
		const auto vLine = p1 - p0;
		const auto lineLength = vLine.getLength();
		const auto vTangent = vLine * (1.0f / lineLength);

		const auto epsilon = 0.0001f;

		const float cutOff = 1.0f / (epsilon + maxDistance * maxDistance);

		CRectf bbf(p0, p0);
		bbf.GrowToIncludePoint(p1);
		bbf.Inflate(maxDistance + 1.1f);
		auto bb = (TRect<uint32_t>)CRectf::Intersection(bbf, CRectf(0, 0, (float)sdf.Width() - 1, (float)sdf.Height() - 1));
		for (uint32_t y = bb.m_Min.y; y <= bb.m_Max.y; ++y)
		{
			for (uint32_t x = bb.m_Min.x; x <= bb.m_Max.x; ++x)
			{
				const auto localPos = float2((float)x - p0.x, (float)y - p0.y);
				const auto t = dot(vTangent, localPos);
				auto d = localPos.x * vTangent.y - localPos.y * vTangent.x;
				d *= d;
				d += (float)((t < 0) | (t > lineLength)) * std::numeric_limits<float>::max();
				d = std::min(d, localPos.getLengthSqr());
				d = std::min(d, float2((float)x - p1.x, (float)y - p1.y).getLengthSqr());
				auto& sdfVal = sdf.at(x, y);
				//sdfVal += std::max(0.0f, 1.f / (epsilon + d) - cutOff);
				sdfVal = std::max(sdfVal, 1.f / (epsilon + d) - cutOff);
			}
		}
	}

	void AddLineSegmentToSdf2(Arr2dView<float>& sdf, const float2& p0, const float2& p1, float maxDistance, float resolution, float strength)
	{
		const auto vLine = p1 - p0;
		const auto lineLength = vLine.getLength();
		const auto vTangent = vLine * (1.0f / lineLength);

		const auto epsilon = 0.0001f;
		const float cutOff = 1.0f / (epsilon + maxDistance * maxDistance);

		const int sampleCount = (int)ceil(lineLength / resolution);
		const float sampleLength = lineLength / sampleCount;
		const float2 vStep = vTangent * sampleLength;

		const float sampleStrength = sampleLength * strength;

		CRectf bbf(p0, p0);
		bbf.GrowToIncludePoint(p1);
		bbf.Inflate(maxDistance + 1.1f);
		auto bb = (TRect<uint32_t>)CRectf::Intersection(bbf, CRectf(0, 0, (float)sdf.Width() - 1, (float)sdf.Height() - 1));
		for (uint32_t y = bb.m_Min.y; y <= bb.m_Max.y; ++y)
		{
			for (uint32_t x = bb.m_Min.x; x <= bb.m_Max.x; ++x)
			{
				const auto pos = float2((float)x, (float)y);
				float2 samplePos = p0 + vStep * .5f;
				float sampleSum = 0;
				for (int sampleIndex = 0; sampleIndex < sampleCount; ++sampleIndex, samplePos += vStep)
				{
					const float distSqr = (pos - samplePos).getLengthSqr();
					sampleSum += std::max(0.0f, 1.0f / (epsilon + distSqr) - cutOff);
				}
				sdf.at(x, y) += sampleSum * sampleStrength;
			}
		}
	}

}