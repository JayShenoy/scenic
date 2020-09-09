from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

spot = OrientedPoint on curb, with roll 20 deg

ego = Car at spot