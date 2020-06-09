
from scenic.simulators.lgsvl.map import setMap
setMap(__file__, 'maps/borregasave.xodr', 'BorregasAve', 'BorregasAve')
from scenic.simulators.lgsvl.model import *

start = Point on road
end = Point following roadDirection from start for 20

ego = EgoCar at start, with destination end
