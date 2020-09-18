""" Scenario Description
Based on CARLA Challenge Scenario 6: https://carlachallenge.org/challenge/nhtsa/
Ego-vehicle must go around a blocking object
using the opposite lane, yielding to oncoming traffic.
"""

param map = localPath('../../../tests/formats/opendrive/maps/CARLA/Town07.xodr')  # or other CARLA map that definitely works
param carla_map = 'Town07'
model scenic.domains.driving.model


#CONSTANTS
ONCOMING_THROTTLE = 0.6
EGO_SPEED = 7
ONCOMING_CAR_SPEED = 10
DIST_THRESHOLD = 13
YIELD_THRESHOLD = 5
BLOCKING_CAR_DIST = Range(15, 20)
BREAK_INTENSITY = 0.8
BYPASS_DIST = 5
DIST_BTW_BLOCKING_ONCOMING_CARS = 10
DIST_TO_INTERSECTION = 15

#EGO BEHAVIOR
behavior EgoBehavior(path):
	current_lane = network.laneAt(self)
	laneChangeCompleted = False
	bypassed = False

	try:
		do FollowLaneBehavior(EGO_SPEED, laneToFollow=current_lane)

	interrupt when (distance to blockingCar) < DIST_THRESHOLD and not laneChangeCompleted:
		if ego can see oncomingCar:
			take SetBrakeAction(BREAK_INTENSITY)
		elif (distance to oncomingCar) > YIELD_THRESHOLD:
			do LaneChangeBehavior(path, is_oppositeTraffic=True, target_speed=EGO_SPEED)
			do FollowLaneBehavior(EGO_SPEED, is_oppositeTraffic=True) until (distance to blockingCar) > BYPASS_DIST
			laneChangeCompleted = True
		else:
			wait

	interrupt when (blockingCar can see ego) and (distance to blockingCar) > BYPASS_DIST and not bypassed:
		current_laneSection = network.laneSectionAt(self)
		rightLaneSec = current_laneSection._laneToLeft
		do LaneChangeBehavior(rightLaneSec, is_oppositeTraffic=False, target_speed=EGO_SPEED)
		bypassed = True


#OTHER BEHAVIORS
behavior OncomingCarBehavior(path = []):
	try: 
		do FollowLaneBehavior(ONCOMING_CAR_SPEED) 

	interrupt when (distance to ego) < 1:
		wait

#GEOMETRY


#behavior WalkAcrossRoadBehavior():
#    """Walk forward behavior for pedestrians.
#
#    It will uniformly randomly choose either end of the sidewalk that the pedestrian is on, and have the pedestrian walk towards the endpoint.
#    """
#    current_sidewalk = _model.network.sidewalkAt(self.position)
#    end_point = Uniform(*current_sidewalk.centerline.points)
#    end_vec = end_point[0] @ end_point[1]
#    normal_vec = Vector.normalized(end_vec)
#    take WalkTowardsAction(goal_position=normal_vec), SetSpeedAction(speed=1)


#Find lanes that have a lane to their left in the opposite direction
laneSecsWithLeftLane = []
for lane in network.lanes:
	for laneSec in lane.sections:
		if laneSec._laneToLeft is not None:
			if laneSec._laneToLeft.isForward is not laneSec.isForward:
				laneSecsWithLeftLane.append(laneSec)

assert len(laneSecsWithLeftLane) > 0, \
	'No lane sections with adjacent left lane with opposing \
	traffic direction in network.'

initLaneSec = Uniform(*laneSecsWithLeftLane)
leftLaneSec = initLaneSec._laneToLeft

spawnPt = OrientedPoint on initLaneSec.centerline

#PLACEMENT
# 
#Pedstrian on network.laneGroupAt(self).curb 
#     facing 90 deg relative to roadDirection
# Goal = Point ahead of Pedestrain by 8
#oncomingCar = Pedestrian on leftLaneSec.centerline,
oncomingCar = Pedstrian on network.laneGroupAt(self).curb,
	with behavior OncomingCarBehavior(),
	with regionContainedIn None

ego = Car at spawnPt,
	with behavior EgoBehavior(leftLaneSec)
	
blockingCar = Truck following roadDirection from ego for BLOCKING_CAR_DIST,
				with viewAngle 90 deg, 
				with blueprint "vehicle.tesla.cybertruck"

#Make sure the oncoming Car is at a visible section of the lane
require blockingCar can see oncomingCar
require (distance from blockingCar to oncomingCar) < DIST_BTW_BLOCKING_ONCOMING_CARS
require (distance from blockingCar to intersection) > DIST_TO_INTERSECTION

## Car left of spot by 0.5,
##    with model CarModel.models['BUS']