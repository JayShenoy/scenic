#SET MODEL (i.e. definitions of all referenceable vehicle types, road library, etc)
model scenic.domains.driving.model

lane = Uniform(*network.lanes)

ego = Car on lane

leadCar1 = Car on visible lane.group
leadCar2 = Car on visible lane.group

require (10 < distance from ego to leadCar1) < 20
require (10 < distance from ego to leadCar2) < 20