"""Scenic script for testing purposes only."""

import matplotlib.pyplot as plt
param map = localPath('../OpenDrive/Town10HD.xodr')
param carla_map = 'Town10HD'
model scenic.domains.driving.model

roads = network.roads
select_road = Uniform(*roads)
select_lane = Uniform(*select_road.lanes)

ego = Car on select_lane.centerline

spot = OrientedPoint on visible curb
badAngle = Uniform(-1,1) * (10,20) deg
other = Car left of (spot offset by 1.5 @ 0),
	facing badAngle relative to ego.heading,
	with regionContainedIn None

require ((angle to other) - ego.heading) < 10 deg
require (distance to other) < 20