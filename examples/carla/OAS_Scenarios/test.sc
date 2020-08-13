from scenic.simulators.domains.driving.network import loadNetwork
loadNetwork('/home/carla_challenge/Desktop/Carla/Dynamic-Scenic/CARLA_0.9.9/Unreal/CarlaUE4/Content/Carla/Maps/OpenDrive/Town03.xodr')
from scenic.simulators.carla.behaviors import *
from scenic.simulators.carla.model import *
import scenic.simulators.carla.actions as actions
import math
from scenic.core.vectors import Vector

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
SIMULATION_RATE = 10 # TICKS/SEC

behavior WalkForward():
	
	current_sidewalk = network.sidewalkAt(self.position)
	end_point = Uniform(*current_sidewalk.centerline.points)
	end_vec = end_point[0] @ end_point[1]
	normal_vec = Vector.normalized(end_vec)
	take actions.WalkTowardsAction(goal_position=normal_vec)
	take actions.SetSpeedAction(speed=1)


behavior EgoBehavior():
	
	try:
		FollowLaneBehavior()
	interrupt when simulation().currentTime > 5 * SIMULATION_RATE and simulation().currentTime < 10 * SIMULATION_RATE:
		print("LANE SWITCH TRIGGERED!")
		current_lane = network.laneAt(self)
		adjacent_lanes = current_lane.adjacentLanes
		print("adjacent_lanes: ", adjacent_lanes)
		select_laneToSwitch = Uniform(*adjacent_lanes)
		LaneChangeBehavior(select_laneToSwitch, 10)

#PLACEMENT
select_road = Uniform(*network.roads)
possible_lanes = select_road.lanes
select_lane = Uniform(*possible_lanes)


ego = Motorcycle on select_lane,
		with behavior EgoBehavior()

# other = Pedestrian on visible select_lane.group.sidewalk.centerline, 
# 		facing ego.heading,
# 		with behavior WalkForward(),
# 		with regionContainedIn None,
# 		with blueprint 'walker.pedestrian.0004'

