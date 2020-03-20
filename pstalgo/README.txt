Pstalgo


Overview
--------
Pstalgo is a C++ library that implements space syntax and regular
accessibility analyses. The library is also available to Python (via an
interface that connects to the library dll via ctypes).


Build Instructions
------------------

Visual C++ (Windows):
    There is a Microsoft Visual C++ 2017 project file in the 'vc'
    subdirectory that can be used for building the library on Windows.
    The project will generate intermediate files in the directory 'build',
    and output the built library files in the directory 'bin'.

CMake (Tested on Mac OS X and Ubuntu 18.04):
    - Create an empty folder called 'build'
        > mkdir build
    - Change directory to the build folder
        > cd build
    - Run cmake to generate make file
        > cmake ..
    - Build with make
        > make
    The built library will be outputted to the folder 'bin'


Testing
-------
There is a set of unit tests in the subdirectory 'test' that can be run
to verify that various aspects of Pstalgo works as expected. Note that 
the project must be built before running the tests.


Deployment
----------
There is a batch file called 'deploy.bat' that will copy the built
binaries and the python files to a separate directory. This is to
facilitate distribution of the library.


License
-------
Copyright 2019 Meta Berghauser Pont

The Pstalgo library is part of PST.

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