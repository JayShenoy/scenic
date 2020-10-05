param map = localPath('../../tests/formats/opendrive/maps/CARLA/Town10HD.xodr')
param carla_map = 'Town10HD'
model scenic.domains.driving.model

TRAFFIC_SPEED = 10
EGO_SPEED = 8
DISTANCE_THRESHOLD = 60
BRAKE_ACTION = Range(0.4, 0.6)

behavior WaitTurnBehavior(speed, intersection_lane):
	brake_intensity = resample(BRAKE_ACTION)
	try:
		do FollowLaneBehavior(speed, desired_maneuver=ManeuverType.LEFT_TURN)

	interrupt when network.laneAt(self) == intersection_lane and distanceToAnyObjs(self, DISTANCE_THRESHOLD):
		take SetBrakeAction(brake_intensity)


def createPlatoonAt(car, numCars, model=None, dist=Range(2, 8), shift=Range(-0.5, 0.5), wiggle=0):
	lastCar = car 
	for i in range(numCars-1):
		center = follow roadDirection from (front of lastCar) for resample(dist)
		pos = OrientedPoint right of center by shift, facing resample(wiggle) relative to roadDirection
		lastCar = Car ahead of pos, with behavior FollowLaneBehavior(TRAFFIC_SPEED)

def carAheadOfCar(car, gap, offsetX=0, wiggle=0):
	pos = OrientedPoint at (front of car) offset by (offsetX @ gap),
		facing resample(wiggle) relative to roadDirection
	return Car ahead of pos, with behavior FollowLaneBehavior(TRAFFIC_SPEED)

depth = 6
laneGap = 3.5
carGap = Range(4, 6)
laneShift = Range(-2, 2)
wiggle = Range(-2 deg, 2 deg)

def createLaneAt(car):
	createPlatoonAt(car, depth, dist=carGap, wiggle=wiggle)

inter_lanes = []
connecting_lanes = []
inter_opposite_lane_groups = []
for intersection in network.intersections:
	for incomingLane in intersection.incomingLanes:
		# Keep lane if it has left turn at the intersection
		has_left_turn = False
		has_straight = False
		for maneuver in incomingLane.maneuvers:
			if maneuver.type == ManeuverType.LEFT_TURN:
				has_left_turn = True
				connecting_lane = maneuver.connectingLane
			if maneuver.type == ManeuverType.STRAIGHT:
				has_straight = True
				end_lane = maneuver.endLane
				if not end_lane.road.is1Way:
					opposite_lane_group = end_lane.group.opposite

		if has_left_turn and has_straight:
			inter_lanes.append(incomingLane)
			connecting_lanes.append(connecting_lane)
			inter_opposite_lane_groups.append(opposite_lane_group)

lane_sec = inter_lanes[0].sections[0]
connecting_lane = connecting_lanes[0]
opposite_lane_secs = [lane.sections[0] for lane in inter_opposite_lane_groups[0].lanes]

ego = Car on lane_sec.centerline, with behavior WaitTurnBehavior(EGO_SPEED, connecting_lane)

for opposite_lane_sec in opposite_lane_secs:
	other = Car on opposite_lane_sec.centerline, with behavior FollowLaneBehavior(TRAFFIC_SPEED)
	createLaneAt(other)

Pedestrian on crosswalk