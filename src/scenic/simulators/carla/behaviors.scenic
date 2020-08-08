
import scenic.simulators.carla.actions as actions
from scenic.simulators.carla.model import roadDirection
from scenic.simulators.domains.driving.roads import ManeuverType
from scenic.core.regions import regionFromShapelyObject
from shapely.geometry import LineString
import math

from scenic.simulators.domains.driving.network import loadNetwork
loadNetwork('/home/carla_challenge/Downloads/Town03.xodr')
from scenic.simulators.carla.model import *

def concatenateCenterlines(centerlines=[]):
	return PolylineRegion.unionAll(centerlines)

def distance(pos1, pos2):
	""" pos1, pos2 = (x,y) """
	return math.sqrt(math.pow(pos1[0]-pos2[0],2) + math.pow(pos1[1]-pos2[1],2))

def distanceToAnyCars(car, thresholdDistance):
	""" returns boolean """
	objects = simulation().objects
	for obj in objects:
		if distance(car.position, obj.position) < 0.1:
			# this means obj==car
			pass
		elif distance(car.position, obj.position) < thresholdDistance:
			return True
	return False

behavior AccelerateForwardBehavior():
	take actions.SetReverseAction(False)
	take actions.SetHandBrakeAction(False)
	take actions.SetThrottleAction(0.5)

behavior WalkForwardBehavior():
	take actions.SetSpeedAction(0.5)

behavior ConstantThrottleBehavior(x):
    take actions.SetThrottleAction(x)


behavior FollowLaneBehavior(target_speed = 10, network = None):
	assert network is not None

	# instantiate longitudinal and latitudinal pid controllers
	_lon_controller = actions.PIDLongitudinalController(self)
	_lat_controller = actions.PIDLateralController(self)
	past_steer_angle = 0
	past_speed = 0 # making an assumption here that the agent starts from zero speed
	current_lane = network.laneAt(self)
	current_centerline = current_lane.centerline
	in_turning_lane = False # assumption that the agent is not instantiated within a connecting lane
	entering_intersection = False # assumption that the agent is not instantiated within an intersection
	end_lane = None

	while True:

		if self.speed is not None:
			current_speed = self.speed
		else:
			current_speed = past_speed

		if not entering_intersection and (distance from self.position to current_centerline[-1]) < 20 :
			entering_intersection = True
			select_maneuver = Uniform(*current_lane.maneuvers)

			# assumption: there always will be a maneuver
			current_centerline = concatenateCenterlines([current_centerline, select_maneuver.connectingLane.centerline, \
				select_maneuver.endLane.centerline])

			current_lane = select_maneuver.endLane
			end_lane = current_lane

			if select_maneuver.type != ManeuverType.STRAIGHT:
				in_turning_lane = True

		if (end_lane is not None) and (self.position in end_lane):
			in_turning_lane = False
			entering_intersection = False 
			
		nearest_line_points = current_centerline.nearestSegmentTo(self.position)
		nearest_line_segment = PolylineRegion(nearest_line_points)
		cte = nearest_line_segment.signedDistanceTo(self.position)

		speed_error = target_speed - current_speed

		# compute throttle : Longitudinal Control
		throttle = _lon_controller.run_step(speed_error)
		if in_turning_lane:
			throttle = min(0.4, throttle)

		# compute steering : Latitudinal Control
		current_steer_angle = _lat_controller.run_step(cte)
		past_steer_angle = current_steer_angle
		past_speed = current_speed

		take actions.FollowLaneAction(throttle=throttle, current_steer=current_steer_angle, past_steer=past_steer_angle)

	

behavior FollowTrajectoryBehavior(target_speed = 10, trajectory = None):
	assert trajectory is not None

	trajectory_line = concatenateCenterlines(trajectory)

	# instantiate longitudinal and latitudinal pid controllers
	_lon_controller = actions.PIDLongitudinalController(self)
	_lat_controller = actions.PIDLateralController(self)
	past_steer_angle = 0

	while True:
		if self.speed is not None:
			current_speed = self.speed
		else:
			current_speed = 0

		cte = trajectory_line.signedDistanceTo(self.position)
		speed_error = target_speed - current_speed

		# compute throttle : Longitudinal Control
		throttle = _lon_controller.run_step(speed_error)

		# compute steering : Latitudinal Control
		current_steer_angle = _lat_controller.run_step(cte)

		take actions.FollowLaneAction(throttle=throttle, current_steer=current_steer_angle, past_steer=past_steer_angle)
		past_steer_angle = current_steer_angle
