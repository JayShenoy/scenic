from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../map.npz')

from scenic.simulators.gta.model import *

carGap = (10,40)
wiggle = (-2 deg, 2 deg)
laneGap = 2.0

def unevenLineOfCars(car, gap, offsetX=0, wiggle=0):
    pos = OrientedPoint at (front of car) offset by (offsetX @ resample(gap)),
        facing resample(wiggle) relative to roadDirection
    return Car ahead of pos

ego = Car with visibleDistance 150

numCars = 4
lastCar = ego
for i in range(numCars-1):
    newCar = unevenLineOfCars(lastCar, carGap, offsetX=-laneGap, wiggle=wiggle)
    lastCar = newCar


