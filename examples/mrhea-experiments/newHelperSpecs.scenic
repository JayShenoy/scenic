from scenic.simulators.gta.map import setLocalMap
setLocalMap(__file__, '../gta/map.npz')

from scenic.simulators.gta.model import *

angleOffset = (8.287256822061408 deg - -359.16913666080427 deg) - 360 deg
ego = Car facing angleOffset
