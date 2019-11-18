PST for QGIS


Overview
--------
PST for QGIS is a plugin for the desktop application QGIS. It is written
in Python and implements the user interface and all communication with
QGIS. PST for QGIS is dependant on the Pstalgo library for performing its
analyses.


Deployment
----------
There is a batch file called 'deploy.bat' that will assemble a plugin
package that is ready to be used with QGIS. It will copy both Pstalgo
binaries and necessary files from the pstqgis package into a subfolder
'deploy'. Please note that Pstalgo must be built before this is done (for
instructions on how to build Pstalgo please refer to the 'readme.txt' file
in the pstalgo directory). The contents of the generated 'deploy' folder
can then be distributed/used as a regular QGIS plugin. Instructions for
how to install the plugin will be available in a file 'readme.txt' in the
generated 'deploy' directory.


License
-------
Copyright 2019 Meta Berghauser Pont

PST for QGIS is part of PST.

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


Contact
-------
Meta Berghauser Pont (copyright owner), meta.berghauserpont@chalmers.se
Martin Fitger (programmer), martin.fitger@xmnsoftware.com


Acknowledgements
----------------
PST is developed by KTH School of Architecture, Chalmers School of
Architecture (SMoG) and Spacescape AB. Alexander Ståhle, Lars Marcus, 
Daniel Koch, Martin Fitger, Ann Legeby, Gianna Stavroulaki, 
Meta Berghauser Pont, Anders Karlström, Pablo Miranda Carranza,
Tobias Nordström.