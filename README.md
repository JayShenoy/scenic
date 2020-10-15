# Scenic Data Generation Platform

## Synthetic Dataset

Our synthetic dataset, containing hundreds of simulations of Scenic programs, can be found [at this link](https://drive.google.com/drive/folders/18SrqL2q7PyMfaS0oKAFqoc6hVasXS20I?usp=sharing).

If you wish to generate your own datasets, please follow the setup instructions below. If you're just looking to interact with our dataset above, feel free to skip to the API section.

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
* In a new terminal window, clone the current repository.
* In the command line, enter the repository and switch to the branch “dynamics2-recording”
* Run `poetry install` followed by `poetry shell`
* You’re now ready to run dynamic Scenic scripts! Here’s an example: `python -m scenic -S --time 200 --count 3 -m scenic.simulators.carla.model /path/to/scenic/script`
    * This creates 3 simulations of the specified Scenic script, each of which runs for 200 time steps. Some example Scenic scripts are located in “examples/carla”

## Dataset Generation

To generate a synthetic dataset using Scenic, you need two things: a scenario configuration file and a sensor configuration file.

### Scenario Configuration

This file lets you configure which Scenic programs to simulate (`scripts`), how many times to simulate each program (`simulations_per_scenario`), and how many steps to run each simulation for (`time_per_simulation`), and where to output the generated data (`output_dir`).

A sample scenario configuration file, which must be saved in the JSON format, is shown below. Feel free to change the list of scripts to reference any Scenic programs on your machine.

```
{
   "output_dir": "/path/to/output/dir",
   "simulations_per_scenario": 3,
   "time_per_simulation": 300,
   "scripts": [
      "/path/to/scenario1",
      "/path/to/scenario2"
    ]
}
```

Scenic was designed and implemented by Daniel J. Fremont, Tommaso Dreossi, Shromona Ghosh, Edward Kim, Xiangyu Yue, Alberto L. Sangiovanni-Vincentelli, and Sanjit A. Seshia.
