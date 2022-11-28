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

#include <pstalgo/Debug.h>
#include "Platform.h"
#include "ProgressUtil.h"


CPSTAlgoProgressCallback::CPSTAlgoProgressCallback(FPSTAProgressCallback cbfunc, void* user_data, int min_progress_interval_ms)
	: m_CBFunc(cbfunc)
	, m_UserData(user_data)
	, m_MinFilterIntervalMSec(min_progress_interval_ms)
	, m_Progress(0)
	, m_Cancel(false)
	, m_LastFilterTimestamp(0)
{}

void CPSTAlgoProgressCallback::ReportProgress(float progress)
{
	m_Progress = progress;
	if (m_CBFunc && TestFrequencyFilter())
		m_Cancel = (0 != m_CBFunc(nullptr, m_Progress, m_UserData));
}

void CPSTAlgoProgressCallback::ReportStatus(const char* text)
{
	if (m_CBFunc)
		m_Cancel = (0 != m_CBFunc(text, m_Progress, m_UserData));
}

bool CPSTAlgoProgressCallback::GetCancel()
{
	return m_Cancel;
}

bool CPSTAlgoProgressCallback::TestFrequencyFilter()
{
	const unsigned int ts = GetTimeMSec();
	if (ts - m_LastFilterTimestamp < m_MinFilterIntervalMSec)
		return false;
	m_LastFilterTimestamp = ts;
	return true;
}

void CPSTAlgoProgressCallback::ResetFrequencyFilter()
{
	m_LastFilterTimestamp = GetTimeMSec();
}


CPSTMultiTaskProgressCallback::CPSTMultiTaskProgressCallback(IProgressCallback& parent_progress)
	: m_ParentProgress(parent_progress)
	, m_CurrTaskWeight(0)
	, m_FinishedWeight(0)
	, m_TotalWeightInv(0)
{
}

void CPSTMultiTaskProgressCallback::AddTask(unsigned int id, float weight, const char* text)
{
	STask task;
	task.m_Id = id;
	task.m_Weight = weight;
	task.m_Text = text;
	m_Tasks.push_back(task);
}

void CPSTMultiTaskProgressCallback::SetCurrentTask(unsigned int id)
{
	bool task_found = false;

	m_FinishedWeight += m_CurrTaskWeight;
	m_CurrTaskWeight = 0;

	float w = 0;
	const char* status_text = nullptr;
	for (const auto& task : m_Tasks)
	{
		if (task.m_Id == id)
		{
			status_text = task.m_Text;
			m_CurrTaskWeight = task.m_Weight;
			task_found = true;
		}
		w += task.m_Weight;
	}

	m_TotalWeightInv = (w > 0.f) ? (1.0f / w) : 0.f;

	ReportProgress(0);

	if (status_text)
		ReportStatus(status_text);

	if (!task_found)
	{
		LOG_ERROR("CPSTMultiTaskProgressCallback: Undefined task id: %d", id);
	}
}

void CPSTMultiTaskProgressCallback::ReportProgress(float progress)
{
	m_ParentProgress.ReportProgress((m_FinishedWeight + progress * m_CurrTaskWeight) * m_TotalWeightInv);
}

void CPSTMultiTaskProgressCallback::ReportStatus(const char* text)
{
	m_ParentProgress.ReportStatus(text);
}

bool CPSTMultiTaskProgressCallback::GetCancel()
{
	return m_ParentProgress.GetCancel();
}