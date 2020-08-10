from scenic.simulators.domains.driving.network import loadNetwork
loadNetwork('/home/carla_challenge/Desktop/Carla/Dynamic-Scenic/CARLA_0.9.9/Unreal/CarlaUE4/Content/Carla/Maps/OpenDrive/Town01.xodr')
from scenic.simulators.carla.behaviors import *
from scenic.simulators.carla.model import *
import scenic.simulators.carla.actions as actions

simulator = CarlaSimulator('Town01')

"""
Ego-vehicle performs a lane changing to evade a
leading vehicle, which is moving too slowly.
Based on 2019 Carla Challenge Traffic Scenario 05.
"""

EGO_SPEED = 10
SLOW_CAR_SPEED = 6
EGO_TO_SLOWCAR = (15,20)
DIST_THRESHOLD = 15

behavior WalkForward():
	
	for i in range(10):
		wait

	while True:
		actions.SetSpeedAction(speed=5)

#PLACEMENT
select_road = Uniform(*network.roads)
possible_lanes = select_road.lanes
select_lane = Uniform(*possible_lanes)

ego = Car on select_lane

other = Pedestrian on visible road,
		with behavior WalkForward(),
		with regionContainedIn None

# for testing speed : town1 396.34527587890625 @ -164.07579040527344
# require not (ego in intersection)

