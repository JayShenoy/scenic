#SET MODEL (i.e. definitions of all referenceable vehicle types, road library, etc)
model scenic.domains.driving.model

lane = Uniform(*network.lanes)

ego = Car on lane

leadCar = Car on visible ego.lane

require (5 < distance from ego to leadCar) < 20
require ego can see leadCar