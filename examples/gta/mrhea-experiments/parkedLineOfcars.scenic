from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../map.npz')

from scenic.simulators.gta.model import *

param time = (4 * 60, 12 * 60) # 0400 to 1200 hours 
param weather = 'BLIZZARD'

dist = (2,4)

spot = OrientedPoint on curb 
#parkedCar = Car left of spot

# ego = Car at parkedCar offset by (-20, 0) @ (-30,30), with viewAngle(100 deg)

ego = Car at spot

numCars = 10
createPlatoonAt(ego, numCars)

