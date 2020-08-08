
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


#PLACEMENT
# possible_lanes = road.lanes
select_road = Uniform(*network.roads)
possible_lanes = select_road.lanes
select_lane = Uniform(*possible_lanes)

ego = Car on select_lane.centerline,
    with behavior FollowLaneBehavior(network = network),
    with blueprint 'vehicle.tesla.model3'

require not (ego in intersection)

