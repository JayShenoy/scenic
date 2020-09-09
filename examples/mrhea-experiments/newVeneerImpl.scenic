from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

ego = Car on road

c2 = Car ahead of ego

require(distance from ego to c2) > 10
