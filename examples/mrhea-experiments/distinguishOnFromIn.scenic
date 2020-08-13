from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

spot = OrientedPoint on curb

ego = Car at spot
c2 = Car offset by ((-10,10), (20, 40))