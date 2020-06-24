from scenic.simulators.webots.road.world import setLocalWorld
setLocalWorld(__file__, '../road/southside2.wbt')

from scenic.simulators.webots.road.model import *
from scenic.simulators.webots.mars.model import *

ego = Rover at 0 @ -2
c2 = Rover at 1 @ -1
require abs((relative heading of c2) - 90 deg) <= 10 deg


# Some junk 
Pipe
BigRock
Rock