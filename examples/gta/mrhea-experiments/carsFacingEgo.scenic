from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../map.npz')

from scenic.simulators.gta.model import *

ego = Car with viewAngle(360 deg), with visibleDistance 60

c2 = Car offset by (0,0) @ (10,20), with viewAngle(20 deg)

pos = back left of ego
c3 = Car at pos, with viewAngle(60 deg)

require c2 can see ego
# require c3 can see ego