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

#include <pstalgo/Debug.h>
#include <pstalgo/test/CallbackTest.h>

#include "../ProgressUtil.h"

PSTADllExport int PSTACallbackTest(const SCallbackTestDesc* desc)
{
	ASSERT(desc);

	if (desc->VERSION != desc->m_Version)
		return -1;

	CPSTAlgoProgressCallback progress_callback(desc->m_ProgressCallback, desc->m_ProgressCallbackUser);

	progress_callback.ReportProgress(desc->m_Progress);
	progress_callback.ReportStatus(desc->m_Status);

	return progress_callback.GetCancel() ? 0 : desc->m_ReturnValue;
}
