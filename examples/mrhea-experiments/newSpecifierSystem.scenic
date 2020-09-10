from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

ego = Car

c2 = Car offset by 1@2, on road