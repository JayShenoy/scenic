from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

spot = OrientedPoint at (1,2,3)

ego = Car at spot