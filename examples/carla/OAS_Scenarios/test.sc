import matplotlib.pyplot as plt
param map = localPath('../OpenDrive/Town01.xodr')
param carla_map = 'Town01'
model scenic.domains.driving.model

MAX_BREAK_THRESHOLD = 1
SAFETY_DISTANCE = 8
PARKING_SIDEWALK_OFFSET_RANGE = -0.5
CUT_IN_TRIGGER_DISTANCE = Uniform(10, 12)

behavior CutInBehavior(laneToFollow):
	print("OTHER LOCATION: ", self.position)
	while (distance from self to ego) > CUT_IN_TRIGGER_DISTANCE:
		wait

	FollowLaneBehavior(laneToFollow = laneToFollow)

behavior CollisionAvoidance():
	while distanceToAnyObjs(self, SAFETY_DISTANCE):
		take SetBrakeAction(MAX_BREAK_THRESHOLD)


behavior EgoBehavior():

	print("EGO LOCATION: ", self.position)

	try: 
		FollowLaneBehavior()

	interrupt when distanceToAnyObjs(self, SAFETY_DISTANCE):
		CollisionAvoidance()


roads = network.roads
select_road = Uniform(*roads)
lane = Uniform(*select_road.lanes)

ego = Car
		# with behavior EgoBehavior(),
		# with regionContainedIn None
Trash on visible ego.laneGroup.rightEdge,
	with regionContainedIn None
		
# spot = OrientedPoint on visible curb
# parkedHeadingAngle = Uniform(-1,1) * (10, 20) deg

# other = Bicycle following roadDirection from ego by (5, 10),
# 			# with behavior CutInBehavior(ego_lane),
# 			with regionContainedIn None

# require (angle from ego to other) - ego.heading < 0 deg
# require (distance from ego to other) > 10 and (distance from ego to other) < 20