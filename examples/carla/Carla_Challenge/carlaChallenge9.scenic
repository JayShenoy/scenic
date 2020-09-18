""" Scenario Description
Based on 2019 Carla Challenge Traffic Scenario 09.
Ego-vehicle is performing a right turn at an intersection, yielding to crossing traffic.
"""
import carla

param map = localPath('../../../tests/formats/opendrive/maps/CARLA/Town03.xodr')  # or other CARLA map that definitely works
param carla_map = 'Town03'

model scenic.simulators.carla.model

DELAY_TIME_1 = 1 # the delay time for ego
DELAY_TIME_2 = 40 # the delay time for the slow car
FOLLOWING_DISTANCE = 13 # normally 10, 40 when DELAY_TIME is 25, 50 to prevent collisions

DISTANCE_TO_INTERSECTION1 = -20
DISTANCE_TO_INTERSECTION2 = -10
SAFETY_DISTANCE = 20
BRAKE_INTENSITY = 1.0

TRAFFIC_SWITCH_DIST = Range(10,30)
CROSSING_CAR_SPEED = Range(5,12)

behavior CrossingCarBehavior(speed, trajectory):
	BRAKE_INTENSITY = 1

	try:
		do FollowTrajectoryBehavior(target_speed=speed,trajectory = trajectory)

	interrupt when (not (ego can see crossing_car)) and (distance to crossing_car) < 15:
		take SetBrakeAction(BRAKE_INTENSITY)
		print("crossing car brake")

	terminate

# behavior EgoBehavior(trajectory):
# 	try :
# 		do FollowTrajectoryBehavior(trajectory=trajectory)
# 	interrupt when withinDistanceToAnyObjs(self, SAFETY_DISTANCE):
# 		take SetBrakeAction(BRAKE_INTENSITY)

behavior EgoBehavior(destPt1, destPt2):

	# destPt must be an OrientedPoint
	spawnPt = self.position
	spawnHeading = self.heading
	take SetDestinationForAV(spawnPt, spawnHeading, destPt2, destPt2.heading)

	vehicle = self.carlaActor.vehicle
	light_set = False
	destination_set = False

	while True:
		take AutonomousAction()

		if vehicle.get_traffic_light() is not None:
			traffic_light = vehicle.get_traffic_light()

			if (distance from self to crossing_car) > TRAFFIC_SWITCH_DIST:
				traffic_light_group = traffic_light.get_group_traffic_lights()
				if len(traffic_light_group) > 1:
					for light in traffic_light_group:
						light.set_state(carla.TrafficLightState.Red)
						print("all red")
				else:
					traffic_light.set_state(carla.TrafficLightState.Red)
					print("red")

			else:
				traffic_light.set_state(carla.TrafficLightState.Green)
				print("green")

		if (distance to destPt2) < 10:
			break

	terminate


spawnAreas = []
fourWayIntersection = filter(lambda i: i.is4Way, network.intersections)
intersec = Uniform(*fourWayIntersection)

startLane_select = Uniform(*intersec.incomingLanes)
startLane_rightmostLane = startLane_select.group.lanes[0]
startLane = startLane_rightmostLane
straight_maneuvers = filter(lambda i: i.type == ManeuverType.STRAIGHT, startLane.maneuvers)
straight_maneuver = Uniform(*straight_maneuvers)
straight_trajectory = [straight_maneuver.startLane, straight_maneuver.connectingLane, straight_maneuver.endLane]


conflicting_rightTurn_maneuvers = filter(lambda i: i.type == ManeuverType.RIGHT_TURN, straight_maneuver.conflictingManeuvers)
ego_rightTurn_maneuver = Uniform(*conflicting_rightTurn_maneuvers)
ego_startLane = ego_rightTurn_maneuver.startLane

destPt1 = OrientedPoint at ego_rightTurn_maneuver.startLane.centerline[-1]
destPt2 = OrientedPoint at ego_rightTurn_maneuver.endLane.centerline[-1]

spwPt = startLane.centerline[-1]
csm_spwPt = ego_startLane.centerline[-1]

crossing_car = Car following roadDirection from spwPt for DISTANCE_TO_INTERSECTION1,
				with behavior CrossingCarBehavior(speed= CROSSING_CAR_SPEED, trajectory = straight_trajectory),
				with speed CROSSING_CAR_SPEED

ego = Truck following roadDirection from csm_spwPt for DISTANCE_TO_INTERSECTION2,
				with behavior EgoBehavior(destPt1, destPt2),
				with blueprint 'vehicle.audi.tt',
				with traffic_switch_dist TRAFFIC_SWITCH_DIST

require 50 deg < abs(crossing_car.heading - ego.heading) < 310 deg