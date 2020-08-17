
import scenic.simulators.carla.actions as actions
import time
from shapely.geometry import LineString
from scenic.core.regions import regionFromShapelyObject
from scenic.simulators.domains.driving.network import loadNetwork
from scenic.simulators.domains.driving.roads import ManeuverType
loadNetwork('/home/carla_challenge/Desktop/Carla/Dynamic-Scenic/CARLA_0.9.9/Unreal/CarlaUE4/Content/Carla/Maps/OpenDrive/Town10HD.xodr') 

from scenic.simulators.carla.model import *
from scenic.simulators.carla.behaviors import *

simulator = CarlaSimulator('Town10HD')

MAX_BREAK_THRESHOLD = 1
TERMINATE_TIME = 20


behavior EgoBehavior(target_speed=10, trajectory = None):
	assert trajectory is not None
	brakeIntensity = 0.7

	try: 
		FollowTrajectoryBehavior(target_speed=10, trajectory=trajectory)

	interrupt when distanceToAnyCars(car=self, thresholdDistance=10):
		take actions.SetBrakeAction(brakeIntensity)


threeWayIntersections = filter(lambda i: i.is3Way, network.intersections)
intersection = Uniform(*threeWayIntersections)
# print("intersection: ", threeWayIntersections.index(intersection))

straight_maneuvers = filter(lambda m: m.type == ManeuverType.STRAIGHT, intersection.maneuvers)
straight_maneuver = Uniform(*straight_maneuvers)
# print("straight_maneuver: ", straight_maneuvers.index(straight_maneuver))


startLane = straight_maneuver.startLane
connectingLane = straight_maneuver.connectingLane
endLane = straight_maneuver.endLane
centerlines = [startLane.centerline, connectingLane.centerline, endLane.centerline]
print("centerlines: ", centerlines)


conflicting_lefts = filter(lambda m: m.type == ManeuverType.LEFT_TURN, straight_maneuver.conflictingManeuvers)
leftTurn_maneuver = Uniform(*conflicting_lefts)
# print("conflicting_lefts: ", conflicting_lefts.index(leftTurn_maneuver))

L_startLane = leftTurn_maneuver.startLane
L_connectingLane = leftTurn_maneuver.connectingLane
L_endLane = leftTurn_maneuver.endLane
L_centerlines = [L_startLane.centerline, L_connectingLane.centerline, L_endLane.centerline]

# other = Car on startLane.centerline,
# 		with behavior EgoBehavior(target_speed=10, trajectory=centerlines)


ego = Car on L_startLane.centerline,
		with behavior FollowTrajectoryBehavior(target_speed=10, trajectory=L_centerlines)

# require that other car reaches the intersection before the ego car