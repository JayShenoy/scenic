
### Top-level functionality of the scenic package as a script:
### load a scenario and generate scenes in an infinite loop.

import sys
import time
import argparse
import random
import os
import csv
from pathlib import Path

import scenic.syntax.translator as translator
from scenic.simulators import SimulationCreationError

parser = argparse.ArgumentParser(prog='scenic',
                                 usage='scenic [-h] [options] scenario',
                                 description='Interactively sample from a Scenic scenario.')

# Options
parser.add_argument('-d', '--delay', help='loop automatically with this delay (in seconds)',
                    type=float)
parser.add_argument('-z', '--zoom', help='zoom expansion factor', type=float, default=2)
parser.add_argument('-s', '--seed', help='random seed', type=int)
parser.add_argument('-v', '--verbosity', help='verbosity level (default 1)',
                    type=int, choices=(0, 1, 2, 3), default=1)

# Simulation options
simOpts = parser.add_argument_group('simulation options')
simOpts.add_argument('-S', '--simulate', help='run simulations from scenes', action='store_true')
simOpts.add_argument('--time', help='time bound for simulations (default none)',
                     type=int, default=None)
simOpts.add_argument('--count', help='number of simulations to run (default infinity)',
                     type=int, default=0)
simOpts.add_argument('--log-trajectory', type=str, help='store trajectory to the following directory', default=None)

# Debugging options
debugOpts = parser.add_argument_group('debugging options')
debugOpts.add_argument('-b', '--full-backtrace', help='show full internal backtraces',
                       action='store_true')
debugOpts.add_argument('--dump-initial-python', help='dump initial translated Python',
                       action='store_true')
debugOpts.add_argument('--dump-ast', help='dump final AST', action='store_true')
debugOpts.add_argument('--dump-python', help='dump Python equivalent of final AST',
                       action='store_true')
debugOpts.add_argument('--no-pruning', help='disable pruning', action='store_true')
debugOpts.add_argument('--gather-stats', help='collect statistics over this many scenes',
                       type=int, metavar='N')

# Positional arguments
parser.add_argument('scenario', help='a Scenic file to run')

# Parse arguments and set up configuration
args = parser.parse_args()
delay = args.delay
translator.showInternalBacktrace = args.full_backtrace
translator.dumpTranslatedPython = args.dump_initial_python
translator.dumpFinalAST = args.dump_ast
translator.dumpASTPython = args.dump_python
translator.verbosity = args.verbosity
translator.usePruning = not args.no_pruning
if args.seed is not None:
    print(f'Using random seed = {args.seed}')
    random.seed(args.seed)

# Load scenario from file
print('Beginning scenario construction...')
startTime = time.time()
scenario = translator.scenarioFromFile(args.scenario)
totalTime = time.time() - startTime
print(f'Scenario constructed in {totalTime:.2f} seconds.')

def logTrajectory(path, index, info, trajectory):
    logname = os.path.join(path, f"simulation-{index}.csv")
    with open(logname, 'w') as file:
        writer = csv.writer(file, delimiter='&')
        writer.writerow(info)
        for state in trajectory:
            writer.writerow(state)

def prepareLogTrajectory(path_str):
    path = Path(path_str)
    if not path.exists():
        raise ValueError(f"Log output path '{path_str}' should exist")
    if not path.is_dir():
        raise ValueError(f"Log output path '{path_str}' should be directory")
    logDirStr = os.path.join(path_str, time.strftime("%Y%m%d-%H%M%S")) 
    logDirPath = Path(logDirStr)
    logDirPath.mkdir(parents=False, exist_ok=False)   
    return logDirStr

def generateScene():
    startTime = time.time()
    scene, iterations = scenario.generate(verbosity=args.verbosity)
    if args.verbosity >= 1:
        totalTime = time.time() - startTime
        print(f'  Generated scene in {iterations} iterations, {totalTime:.4g} seconds.')
    return scene, iterations

def runSimulation(scene, index, loggingPath):
    startTime = time.time()
    if args.verbosity >= 1:
        print('  Beginning simulation...')
    try:
        trajectory, trajectoryInfo = scene.simulate(maxSteps=args.time, verbosity=args.verbosity)
    except SimulationCreationError as e:
        if args.verbosity >= 1:
            print(f'  Failed to create simulation: {e}')
        return
    if args.verbosity >= 1:
        totalTime = time.time() - startTime
        print(f'  Ran simulation in {totalTime:.4g} seconds.')
    if loggingPath is not None:
        logTrajectory(loggingPath, index, trajectoryInfo, trajectory)





if args.gather_stats is None:   # Generate scenes interactively until killed
    import matplotlib.pyplot as plt
    if args.log_trajectory is not None:
        loggingPath = prepareLogTrajectory(args.log_trajectory)
    else:
        loggingPath = None
    i = 0
    while True:
        scene, _ = generateScene()
        i += 1
        if args.simulate:
            runSimulation(scene, i, loggingPath)
            if 0 < args.count <= i:
                break
        else:
            if delay is None:
                scene.show(zoom=args.zoom)
            else:
                scene.show(zoom=args.zoom, block=False)
                plt.pause(delay)
                plt.clf()
else:   # Gather statistics over the specified number of scenes
    its = []
    startTime = time.time()
    while len(its) < args.gather_stats:
        scene, iterations = generateScene()
        its.append(iterations)
    totalTime = time.time() - startTime
    count = len(its)
    print(f'Sampled {len(its)} scenes in {totalTime:.2f} seconds.')
    print(f'Average iterations/scene: {sum(its)/count}')
    print(f'Average time/scene: {totalTime/count:.2f} seconds.')
