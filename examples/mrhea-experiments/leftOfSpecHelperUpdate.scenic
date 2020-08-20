from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

spot = OrientedPoint on curb 

ego = Car left of spot, with roll 20 deg

spot = OrientedPoint at top front left of ego 