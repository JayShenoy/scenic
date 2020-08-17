import matplotlib.pyplot as plt

# from scenic.domains.driving.network import loadNetwork
# loadNetwork('/home/carla_challenge/Desktop/Carla/Dynamic-Scenic/CARLA_0.9.9/Unreal/CarlaUE4/Content/Carla/Maps/OpenDrive/Town10HD.xodr')

param map = localPath('../OpenDrive/Town10HD.xodr')
param carla_map = 'Town10HD'

model scenic.domains.driving.model
# from scenic.simulators.carla.model import *
	
SAFETY_DISTANCE = 10
INITIAL_DISTANCE_APART = -10

behavior CollisionAvoidance(brake_intensity=0.3):
	while distanceToAnyObjs(self, SAFETY_DISTANCE):
		take SetBrakeAction(brake_intensity)


behavior FollowLeadCarBehavior():

	try: 
		FollowLaneBehavior()

	interrupt when distanceToAnyObjs(self, SAFETY_DISTANCE):
		CollisionAvoidance()


roads = network.roads
select_road = Uniform(*roads)
select_lane = Uniform(*select_road.lanes)

other = Car on select_lane.centerline,
		with behavior FollowLaneBehavior()

ego = Car following roadDirection from other by INITIAL_DISTANCE_APART,
		with behavior FollowLeadCarBehavior()

