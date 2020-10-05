""" Scenario Description
Voyage OAS Scenario Unique ID: 2-2-XX-CF-STR-CAR:Pa>E:03
The lead car suddenly stops and then resumes moving forward
"""

param map = localPath('../../tests/formats/opendrive/maps/CARLA/Town10HD.xodr')  # or other CARLA map that definitely works
param carla_map = 'Town10HD'
model scenic.domains.driving.model

roads = network.roads
select_road = Uniform(*roads)
select_lane = Uniform(*select_road.lanes)

ego = Car on select_lane.centerline,
		with behavior FollowLaneBehavior()