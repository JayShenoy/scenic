
import scenic.simulators.carla.actions as actions
import time

from scenic.simulators.domains.driving.network import loadNetwork
loadNetwork('/home/carla_challenge/Downloads/Town03.xodr')

from scenic.simulators.carla.model import *
from scenic.simulators.carla.behaviors import *

simulator = CarlaSimulator('Town03')

"""
Ego-vehicle performs a lane changing to evade a
leading vehicle, which is moving too slowly.
Based on 2019 Carla Challenge Traffic Scenario 05.
"""

EGO_SPEED = 10
SLOW_CAR_SPEED = 6
EGO_TO_SLOWCAR = (15,20)
DIST_THRESHOLD = 15

#EGO BEHAVIOR
behavior EgoBehavior(origpath=[],leftpath=[]):
    try:
        FollowLaneBehavior(EGO_SPEED,network)
    interrupt when ((distance to slowCar) < DIST_THRESHOLD):
        print('THRESHOLD PASSED: CHANGING LANES')
        FollowTrajectoryBehavior(EGO_SPEED,leftpath)

#OTHER BEHAVIOR
behavior SlowCarBehavior():
    FollowLaneBehavior(SLOW_CAR_SPEED, network)

#GEOMETRY
laneSecsWithLeftLane = []
for lane in network.lanes:
    for laneSec in lane.sections:
        if laneSec.laneToLeft is not None:
            laneSecsWithLeftLane.append(laneSec)
assert len(laneSecsWithLeftLane) > 0, \
    'No lane sections with adjacent left lane in network.'

# initLaneSec = Uniform(*laneSecsWithLeftLane)
initLaneSec = laneSecsWithLeftLane[10]
leftLaneSec = initLaneSec.laneToLeft

#PLACEMENT
spawnPt = OrientedPoint on initLaneSec.centerline
ego = Car ahead of spawnPt by 10,
    with behavior EgoBehavior([initLaneSec.centerline], [leftLaneSec.centerline]),
    with blueprint 'vehicle.tesla.model3'

slowCar = Car following roadDirection from ego by EGO_TO_SLOWCAR,
    with behavior SlowCarBehavior()
