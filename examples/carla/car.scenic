#SET MODEL (i.e. definitions of all referenceable vehicle types, road library, etc)
model scenic.domains.driving.model

param time = Range(10, 16) * 60
param weather = Uniform('RAIN', 'THUNDER')

ego = Car on road
spot = OrientedPoint on visible curb
badAngle = Uniform(-1, 1) * Range(10, 20) deg

badlyParkedCar = Car left of spot by 0.5,
					facing badAngle relative to roadDirection