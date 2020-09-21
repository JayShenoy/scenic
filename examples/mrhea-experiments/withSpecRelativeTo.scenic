from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

ego = Car with roll 50 deg 

c2 = Car with roll 20 deg relative to ego