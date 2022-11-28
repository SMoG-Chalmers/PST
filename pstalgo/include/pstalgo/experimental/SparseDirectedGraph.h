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

/**
 *  Sparse directed graph that can store user data for each node and edge.
 *  Memory layout is optimized for fast graph traversal.
 */
#pragma once

#include <new>
#include <vector>

#ifdef _MSC_VER
	#include <intrin.h>  // for _BitScanReverse
	#if _MSC_VER <= 1800
		#define alignof __alignof
	#endif
#endif

#include <pstalgo/system/System.h>
#include <pstalgo/utils/Bit.h>
#include <pstalgo/Debug.h>

namespace psta
{
	class CSparseDirectedGraphBase
	{
	public:
		typedef unsigned int HNode;

		CSparseDirectedGraphBase();
		CSparseDirectedGraphBase(const CSparseDirectedGraphBase&) = delete;
		CSparseDirectedGraphBase(CSparseDirectedGraphBase&&);

		~CSparseDirectedGraphBase();

		void Clear();

		void operator=(const CSparseDirectedGraphBase&) = delete;
		void operator=(CSparseDirectedGraphBase&&);

		void ReserveNodeCount(size_t node_count);

		unsigned int NodeCount() const { return m_NodeCount; }

		HNode NodeHandleFromIndex(size_t index) const { return m_NodeHandles[index]; }

		void Copy(const CSparseDirectedGraphBase& other);

	protected:
		char* Alloc(unsigned int size);

		void NeedCapacity(unsigned int capacity);

		char*        m_Data = nullptr;
		unsigned int m_Size = 0;
		unsigned int m_Capacity = 0;
		unsigned int m_NodeCount = 0;
		std::vector<HNode> m_NodeHandles;
	};

	// Variation with UNTYPED node and edge data
	// WARNING: Node data and edge data is currently 4-byte aligned!
	class CSparseDirectedGraph : public CSparseDirectedGraphBase
	{
	public:
		typedef unsigned int index_t;

		static const HNode INVALID_HANDLE  = (HNode)-1;
		static const index_t INVALID_INDEX = (index_t)-1;

		// 8 bytes
		struct SNode
		{
			SNode(index_t index, unsigned int edge_count) : m_Index(index), m_EdgeCount(edge_count) {}
			index_t      Index() const { return m_Index; }
			unsigned int EdgeCount() const { return m_EdgeCount; }
			void*        Data() { return this + 1; }
			const void*  Data() const { return (SNode*)this + 1; }
		private:
			index_t      m_Index;
			unsigned int m_EdgeCount;
		};

		// 8 bytes
		struct SEdge
		{
			void        SetTarget(HNode handle, index_t index) { m_TargetHandle = handle; m_TargetIndex = index; }
			HNode       TargetHandle() const { return m_TargetHandle; }
			index_t     TargetIndex()  const { return m_TargetIndex; }
			void*       Data() { return this + 1; }
			const void* Data() const { return (SEdge*)this + 1; }
		private:
			HNode   m_TargetHandle = INVALID_HANDLE;
			index_t m_TargetIndex  = INVALID_INDEX;
		};

		CSparseDirectedGraph(unsigned int node_data_size, unsigned int edge_data_size)
			: m_NodeSize((unsigned int)align_up(sizeof(SNode) + node_data_size, alignof(SNode)))
			, m_EdgeSize((unsigned int)align_up(sizeof(SEdge) + edge_data_size, alignof(SEdge)))
		{}

		unsigned int NodeDataSize() const { return m_NodeSize - sizeof(SNode); }

		unsigned int EdgeDataSize() const { return m_EdgeSize - sizeof(SEdge); }

		void ReserveNodeCount(size_t node_count);

		HNode NewNode(unsigned int edge_count)
		{
			auto* node = (SNode*)Alloc(NodeSize(edge_count));
			new (node)SNode(m_NodeCount++, edge_count);
			ForEachEdge(*node, [](SEdge& e) { new (&e)SEdge(); });
			const auto handle = (HNode)((char*)node - m_Data);
			m_NodeHandles.push_back(handle);
			return handle;
		}

		SNode& Node(HNode handle)
		{
			ASSERT(handle < m_Capacity);
			return *(SNode*)(m_Data + handle);
		}

		const SNode& Node(HNode handle) const
		{
			ASSERT(handle < m_Capacity);
			return *(SNode*)(m_Data + handle);
		}

		template <class TLambda> void ForEachEdge(const SNode& node, TLambda&& lmbd)       { char* e = (char*)&node + m_NodeSize; auto* e_end = e + node.EdgeCount() * m_EdgeSize; for (; e < e_end; e += m_EdgeSize) lmbd(*(SEdge*)e); }
		template <class TLambda> void ForEachEdge(const SNode& node, TLambda&& lmbd) const { char* e = (char*)&node + m_NodeSize; auto* e_end = e + node.EdgeCount() * m_EdgeSize; for (; e < e_end; e += m_EdgeSize) lmbd(*(const SEdge*)e); }

	private:
		unsigned int NodeSize(unsigned int edge_count) const
		{
			return m_NodeSize + m_EdgeSize * edge_count;
		}

		unsigned int m_NodeSize;
		unsigned int m_EdgeSize;
	};


	struct SEmpty {};

	// Variation with TYPED node and edge data
	template <class TNodeData = SEmpty, class TEdgeData = SEmpty>
	class TSparseDirectedGraph : public CSparseDirectedGraphBase
	{
	public:
		typedef unsigned int index_t;

		static const HNode INVALID_HANDLE = (HNode)-1;
		static const index_t INVALID_INDEX = (index_t)-1;

		// 8 bytes (+ data)
		class CEdge : public TEdgeData
		{
		public:
			HNode   TargetHandle() const { return m_TargetHandle; }
			index_t TargetIndex() const  { return m_TargetIndex; }

			void SetTarget(HNode handle, index_t index) { m_TargetHandle = handle; m_TargetIndex = index; }

		private:
			HNode   m_TargetHandle = INVALID_HANDLE;
			index_t m_TargetIndex = INVALID_INDEX;
		};

		// 4 bytes (+ data)
		class CNode : public TNodeData
		{
		public:
			CNode(index_t index, unsigned int edge_count)
				: m_Index(index | edge_count << 24) {}

			index_t      Index() const { return m_Index & 0x00FFFFFF; }
			unsigned int EdgeCount() const { return m_Index >> 24; }
			CEdge&       Edge(unsigned int index) { return reinterpret_cast<CEdge*>(this + 1)[index]; }
			const CEdge& Edge(unsigned int index) const { return const_cast<CNode*>(this)->Edge(index); }

			template <class TLambda> void ForEachEdge(TLambda&& lmbd)       { for (unsigned int i = 0; i < EdgeCount(); ++i) lmbd(Edge(i)); }
			template <class TLambda> void ForEachEdge(TLambda&& lmbd) const { for (unsigned int i = 0; i < EdgeCount(); ++i) lmbd(Edge(i)); }

		private:
			index_t m_Index;
		};

		TSparseDirectedGraph() {}
		TSparseDirectedGraph(const TSparseDirectedGraph&) = delete;
		TSparseDirectedGraph(TSparseDirectedGraph&& other) : CSparseDirectedGraphBase(std::forward<TSparseDirectedGraph>(other)) {}

		void operator=(const TSparseDirectedGraph&) = delete;
		void operator=(TSparseDirectedGraph&& rhs) { CSparseDirectedGraphBase::operator=(std::forward<TSparseDirectedGraph>(rhs)); }

		void ReserveNodeCount(size_t node_count)
		{
			CSparseDirectedGraphBase::ReserveNodeCount(node_count);
			NeedCapacity(node_count * (sizeof(CNode) + sizeof(CEdge)));  // Assume on avarage one edge per node
		}

		HNode NewNode(unsigned int edge_count)
		{
			char* ptr = Alloc(NodeSize(edge_count));
			auto* node = new (ptr)CNode(m_NodeCount++, edge_count);
			for (unsigned int i = 0; i < edge_count; ++i)
				new (&node->Edge(i)) CEdge;
			const auto handle = (HNode)(ptr - m_Data);
			m_NodeHandles.push_back(handle);
			return handle;
		}

		CNode& Node(HNode handle)
		{
			ASSERT(handle < m_Capacity);
			return *(CNode*)(m_Data + handle);
		}

		const CNode& Node(HNode handle) const { return const_cast<TSparseDirectedGraph*>(this)->Node(handle); }

		index_t TargetIndex(const CEdge& edge) const { return edge.TargetIndex(); }

	private:
		static unsigned int NodeSize(unsigned int edge_count)
		{
			return (unsigned int)(sizeof(CNode) + edge_count * sizeof(CEdge));
		}
	};
}
