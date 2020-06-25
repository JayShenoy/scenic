
import pytest

from tests.utils import compileScenic

def test_basic(loadLocalScenario):
    scenario = loadLocalScenario('basic.scenic')
    scenario.generate(maxIterations=1000)

def test_bumper_to_bumper(loadLocalScenario):
    scenario = loadLocalScenario('bumperToBumper.scenic')
    scenario.generate(maxIterations=1000)

def test_mutate():
    scenario = compileScenic(
        'from scenic.simulators.gta.map import setLocalMap\n'
        f'setLocalMap("{__file__}", "map.npz")\n'
        'from scenic.simulators.gta.model import *\n'
        'ego = EgoCar with color CarColor(0, 0, 1)\n'
        'mutate'
    )
    scene, _ = scenario.generate(maxIterations=50)
    assert tuple(scene.egoObject.color) != (0, 0, 1)
