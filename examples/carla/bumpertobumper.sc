# import scenic.simulators.carla.actions as actions

# from scenic.core.geometry import subtractVectors

# from scenic.simulators.domains.driving.network import loadNetwork
# loadNetwork('/home/carla_challenge/Desktop/Carla/Dynamic-Scenic/CARLA_0.9.9/Unreal/CarlaUE4/Content/Carla/Maps/OpenDrive/Town03.xodr')

# param map = localPath('../OpenDrive/Town03.xodr')
# param carla_map = 'Town03'

# from scenic.simulators.carla.model import *
# from scenic.simulators.carla.behaviors import *

# simulator = CarlaSimulator('Town03')

param map = localPath('../../tests/formats/opendrive/maps/CARLA/Town10HD.xodr')
param carla_map = 'Town10HD'
model scenic.domains.driving.model

"""
Dynamic version of bumper-to-bumper scenario from https://arxiv.org/pdf/1809.09310.pdf
"""

TRAFFIC_SPEED = 10
EGO_SPEED = 8
DISTANCE_THRESHOLD = 6
BRAKE_ACTION = Range(0.8, 1.0)

behavior FollowTrafficBehavior(speed):
	brake_intensity = resample(BRAKE_ACTION)
	try:
		do FollowLaneBehavior(speed)

	interrupt when distanceToAnyObjs(self, DISTANCE_THRESHOLD):
		take SetBrakeAction(brake_intensity)


def createPlatoonAt(car, numCars, model=None, dist=Range(2, 8), shift=Range(-0.5, 0.5), wiggle=0):
	lastCar = car 
	for i in range(numCars-1):
		center = follow roadDirection from (front of lastCar) for resample(dist)
		pos = OrientedPoint right of center by shift, facing resample(wiggle) relative to roadDirection
		lastCar = Car ahead of pos, with behavior FollowTrafficBehavior(TRAFFIC_SPEED)

def carAheadOfCar(car, gap, offsetX=0, wiggle=0):
	pos = OrientedPoint at (front of car) offset by (offsetX @ gap),
		facing resample(wiggle) relative to roadDirection
	return Car ahead of pos, with behavior FollowTrafficBehavior(TRAFFIC_SPEED)

depth = 4
laneGap = 3.5
carGap = Range(1, 3)
laneShift = Range(-2, 2)
wiggle = Range(-5 deg, 5 deg)

def createLaneAt(car):
	createPlatoonAt(car, depth, dist=carGap, wiggle=wiggle)

laneSecsWithLeftLane = []
for lane in network.lanes:
	for laneSec in lane.sections:
		if laneSec._laneToLeft is not None:
			laneSecsWithLeftLane.append(laneSec)

assert len(laneSecsWithLeftLane) > 0, \
	'No lane sections with adjacent left lane in network.'

initLaneSec = laneSecsWithLeftLane[4]


ego = Car on initLaneSec.centerline, with behavior FollowTrafficBehavior(EGO_SPEED)
leftCar = carAheadOfCar(ego, laneShift + carGap, offsetX=-laneGap, wiggle=wiggle)
createLaneAt(leftCar)

midCar = carAheadOfCar(ego, resample(carGap), wiggle=wiggle)
createLaneAt(midCar)

#rightCar = carAheadOfCar(ego, resample(laneShift) + resample(carGap), offsetX=laneGap, wiggle=wiggle)
#createLaneAt(rightCar)	