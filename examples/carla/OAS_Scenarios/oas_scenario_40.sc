
import scenic.simulators.carla.actions as actions
import time
from shapely.geometry import LineString
from scenic.core.regions import regionFromShapelyObject
from scenic.simulators.domains.driving.network import loadNetwork
from scenic.simulators.domains.driving.roads import ManeuverType
loadNetwork('/home/carla_challenge/Desktop/Carla/Dynamic-Scenic/CARLA_0.9.9/Unreal/CarlaUE4/Content/Carla/Maps/OpenDrive/Town03.xodr')

from scenic.simulators.carla.model import *
from scenic.simulators.carla.behaviors import *

simulator = CarlaSimulator('Town03')

twoLane_roads = []
for r in network.roads:
	if len(r.lanes) == 2:
		twoLane_roads.append(r)

# twoLane_roads = filter(lambda i: len(i.lanes) == 2, network.roads)
selected_road = Uniform(*twoLane_roads)
# possible_lanes = filter(lambda i: len(i.lanes), network.roads)
lane = Uniform(*selected_road.lanes)

ego = Car at lane.centerline[0]
biker = Bicycle ahead of ego by (5, 10),
		with behavior FollowLaneBehavior(target_speed = 10, network = network)