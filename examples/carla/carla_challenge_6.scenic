from scenic.simulators.carla.map import setMapPath
setMapPath(__file__, 'OpenDrive/Town01.xodr')
from scenic.simulators.carla.model import *

ego = Car 
c2 = Car at ego offset by 0 @ Range(15, 20)
c3 = Car at c2 offset by Range(-10, -2) @ Range(15,20)
require abs(relative heading of c2 from ego) <= 30 deg
require abs(relative heading of c3 from c2) >= 150 deg