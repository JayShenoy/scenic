# Scenic

[![Documentation Status](https://readthedocs.org/projects/scenic-lang/badge/?version=latest)](https://scenic-lang.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/License-BSD%203--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

A compiler and scene generator for the Scenic scenario description language.
Please see the [documentation](https://scenic-lang.readthedocs.io/) for installation instructions, as well as tutorials and other information about the Scenic language, its implementation, and its interfaces to various simulators.

For a description of the language and some of its applications, see [our PLDI 2019 paper](https://arxiv.org/abs/1809.09310) (*note:* the syntax of Scenic has changed slightly since then).
Scenic was designed and implemented by Daniel J. Fremont, Tommaso Dreossi, Shromona Ghosh, Edward Kim, Xiangyu Yue, Alberto L. Sangiovanni-Vincentelli, and Sanjit A. Seshia.

If you have any problems using Scenic, please submit an issue to [our GitHub repository](https://github.com/BerkeleyLearnVerify/Scenic) or contact Daniel at <dfremont@ucsc.edu>.

The repository is organized as follows:

* the _src/scenic_ directory contains the package proper;
* the _examples_ directory has many examples of Scenic programs;
* the _docs_ directory contains the sources for the documentation;
* the _tests_ directory contains tests for the Scenic compiler.

# Scenic Data Generation Platform

## Setup

### Installing CARLA
* Download the latest release of CARLA. As of 10/6/20, this is located [here](https://github.com/carla-simulator/carla/releases/tag/0.9.10.1)
    * Other releases can be found [here](https://github.com/carla-simulator/carla/releases)
    * First, download “CARLA_0.9.10.1.tar.gz”. Unzip the contents of this folder into a directory of your choice. In this setup guide, we’ll unzip it into “~/carla”
    * Download “AdditionalMaps_0.9.10.1.tar.gz”. Do not unzip this file. Rather, navigate to “~/carla” (the directory you unzipped CARLA into in the previous step), and place “AdditionalMaps_0.9.10.1.tar.gz” in the “Import” subdirectory.
* In the command line, cd into “~/carla” and run `./ImportAssets.sh`
* Try running `./CarlaUE4.sh -fps=15` from the “~/carla” directory. You should see a window pop up containing a 3D scene.
* The CARLA release contains a Python package for the API. To use this, you need to add the package to your terminal’s PYTHONPATH variable as follows:
    * First, copy down the filepath of the Python package. The package should be located in “~/carla/PythonAPI/carla/dist”. Its name should be something like “carla-0.9.10-py3.7-linux-x86_64.egg”
    * Open your “~/.bashrc” file in an editor. Create a new line with the following export statement: “export PYTHONPATH=/path/to/egg/file”
    * Save and exit “~/.bashrc” and restart the terminal for the changes to take effect. To confirm that the package is on the PYTHONPATH, try the command “echo $PYTHONPATH”

### Installing Scenic
* Clone the current repository.
* In the command line, enter the repository and switch to the branch “dynamics2-recording”
* Run `poetry install` followed by `poetry shell`
* You’re now ready to run dynamic Scenic scripts! Here’s an example: `python -m scenic -S --time 200 --count 3 -m scenic.simulators.carla.model /path/to/scenic/script`
    * This creates 3 simulations of the specified Scenic script, each of which runs for 200 time steps. Some example Scenic scripts are located in “examples/carla”
