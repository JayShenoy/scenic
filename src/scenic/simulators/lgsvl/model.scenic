"""Scenic world model for LGSVL."""

import math
import time

try:
    import lgsvl
except ImportError as e:
    raise RuntimeError('This scenario requires the LGSVL Python API to be installed')

from scenic.simulators.lgsvl.map import mapPath, sceneName, apolloMapName
from scenic.simulators.lgsvl.workspace import LGSVLWorkspace

# Load map and set up various useful regions, etc.

if mapPath is None:
    raise RuntimeError('No map file specified: did you call setMap before importing the model?')
if sceneName is None:
    raise RuntimeError('No LGSVL scene specified: did you call setMap before importing the model?')

param lgsvl_scene = sceneName
param apolloHDMap = apolloMapName

workspace = LGSVLWorkspace(mapPath)

roadDirection = workspace.road_direction
road = workspace.drivable_region
sidewalk = workspace.sidewalk_region

## LGSVL objects

class LGSVLObject:
    lgsvlObject: None   # LGSVL Python API object corresponding to this Scenic object
    elevation: None

# TODO: Get vehicle models, dimensions from LGSVL
class Car(LGSVLObject):
    regionContainedIn: road
    position: Point on road
    heading: (roadDirection at self.position) + self.roadDeviation
    roadDeviation: 0
    viewAngle: 90 deg
    width: 2.5
    height: 5
    requireVisible: False
    lgsvlName: 'Sedan'
    lgsvlAgentType: lgsvl.AgentType.NPC

class EgoCar(Car):
    lgsvlName: 'Lincoln2017MKZ (Apollo 5.0)'
    lgsvlAgentType: lgsvl.AgentType.EGO
    apolloVehicle: 'Lincoln2017MKZ'
    apolloModules: ['Localization', 'Perception', 'Transform', 'Routing',
                    'Prediction', 'Planning', 'Camera']
    dreamview: None     # connection to Dreamview (set at runtime)
    bridgeHost: 'localhost'
    bridgePort: 9090
    destination: None   # position to drive to, if any

class Pedestrian(LGSVLObject):
    regionContainedIn: sidewalk
    position: Point on sidewalk
    heading: (0, 360) deg
    width: 0.5
    height: 0.5
    lgsvlName: 'Bob'
    lgsvlAgentType: lgsvl.AgentType.PEDESTRIAN

## Utility classes

class Waypoint(OrientedPoint):
    heading: roadDirection at self.position
    speed: 10
