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

#pragma once

#include <vector>
#include <pstalgo/pstalgo.h>
#include "Progress.h"

class CPSTAlgoProgressCallback: public IProgressCallback
{
public:
	CPSTAlgoProgressCallback(FPSTAProgressCallback cbfunc, void* user_data, int min_progress_interval_ms = 100);

	// IProgressCallback Interface
	void ReportProgress(float progress) override;
	void ReportStatus(const char* text) override;
	bool GetCancel() override;

private:
	bool TestFrequencyFilter();
	void ResetFrequencyFilter();

	FPSTAProgressCallback m_CBFunc;
	void*                 m_UserData;
	float                 m_Progress;
	bool                  m_Cancel;
	const unsigned int    m_MinFilterIntervalMSec;
	unsigned int          m_LastFilterTimestamp;
};


class CPSTMultiTaskProgressCallback : public IProgressCallback
{
public:
	CPSTMultiTaskProgressCallback(IProgressCallback& parent_progress);

	void AddTask(unsigned int id, float weight, const char* text);

	void SetCurrentTask(unsigned int id);

	// IProgressCallback Interface
	void ReportProgress(float progress) override;
	void ReportStatus(const char* text) override;
	bool GetCancel() override;

private:
	IProgressCallback& m_ParentProgress;
	float m_CurrTaskWeight;
	float m_FinishedWeight;
	float m_TotalWeightInv;
	
	struct STask
	{
		unsigned int m_Id;
		float m_Weight;
		const char* m_Text;
	};
	std::vector<STask> m_Tasks;
};


