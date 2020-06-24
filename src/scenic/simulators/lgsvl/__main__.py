"""Example script for running driving scenarios in LGSVL."""

import sys
import time
import argparse
import random

try:
    import lgsvl
except ImportError as e:
    raise RuntimeError('This script requires the LGSVL Python API to be installed') from e

import scenic
import scenic.simulators.lgsvl.simulator

parser = argparse.ArgumentParser(
    prog='scenic.simulators.lgsvl',
    usage='python -m scenic.simulators.lgsvl [options] scenario',
    description='Sample from a Scenic scenario and run simulations in LGSVL.'
)

# Options
parser.add_argument('-d', '--duration', help='duration of simulations (in seconds)',
                    type=float, default=30)

parser.add_argument('-H', '--host', help='host for LGSVL connection',
                    type=str, default='localhost')
parser.add_argument('-p', '--port', help='port for LGSVL connection', type=int, default=8181)
parser.add_argument('-r', '--reload', help='always reload LGSVL scene', action='store_true')

# Positional arguments
parser.add_argument('scenario', help='a Scenic file to run')

args = parser.parse_args()

# Load scenario from file
print('Beginning scenario construction...')
startTime = time.time()
scenario = scenic.scenarioFromFile(args.scenario)
totalTime = time.time() - startTime
print(f'Scenario constructed in {totalTime:.2f} seconds.')

lgsvl_scene = scenario.params.get('lgsvl_scene')
if lgsvl_scene is None:
    raise RuntimeError('This scenario does not appear to use the LGSVL world model.')
if scenic.core.distributions.needsSampling(lgsvl_scene):
    raise RuntimeError('The LGSVL scene must be fixed (not a distribution)')

# Connect to LGSVL
client = lgsvl.Simulator(address=args.host, port=args.port)
if args.reload or client.current_scene != lgsvl_scene:
    client.load(scene=lgsvl_scene)

# Sample scenes and run simulations
while True:
    scene, _ = scenario.generate()

    simulation = scenic.simulators.lgsvl.simulator.LGSVLSimulation(scene, client)

    simulation.run(args.duration)
