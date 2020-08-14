import math

import carla

from scenic.domains.driving.actions import *
import scenic.simulators.carla.utils.utils as utils
import scenic.simulators.carla.model as carlaModel

################################################
# Actions available to all carla.Actor objects #
################################################

class OffsetAction(Action):
	"""Teleports actor forward (in direction of its heading) by some offset."""
	
	def __init__(self, offset):
		super().__init__()
		self.offset = offset

	def applyTo(self, obj, carlaActor, sim):
		pos = obj.position.offsetRotated(obj.heading, self.offset)
		loc = utils.scenicToCarlaLocation(pos, z=obj.elevation)
		carlaActor.set_location(loc)


class SetLocationAction(Action):
	def __init__(self, pos):
		super().__init__()
		self.pos = pos  # NOTE: Must translate to Carla coords

	def applyTo(self, obj, carlaActor, sim):
		loc = utils.scenicToCarlaLocation(self.pos, z=obj.elevation)
		carlaActor.set_location(loc)


class SetVelocityAction(Action):
	def __init__(self, xVel, yVel, zVel=0):
		super().__init__()
		self.xVel = xVel
		self.yVel = yVel
		self.zVel = zVel

	def applyTo(self, obj, carlaActor, sim):
		newVel = utils.scalarToCarlaVector3D(xVel, yVel, zVel)
		carlaActor.set_velocity(newVel) 


class SetSpeedAction(Action):
	def __init__(self, speed):
		super().__init__()
		self.speed = speed

	def applyTo(self, obj, carlaActor, sim):
		newVel = utils.scenicSpeedToCarlaVelocity(speed, carlaActor.heading)
		carlaActor.set_velocity(newVel)


class SetAngularVelocityAction(Action):
	def __init__(self, angularVel):
		self.angularVel = angularVel

	def applyTo(self, obj, sim):
		xAngularVel = self.angularVel * math.cos(obj.heading)
		yAngularVel = self.angularVel * math.sin(obj.heading)
		newAngularVel = utils.scalarToCarlaVector3D(xAngularVel, yAngularVel)
		obj.carlaActor.set_angular_velocity(newAngularVel)

class SetTransformAction(Action):	# TODO eliminate
	def __init__(self, pos, heading):
		self.pos = pos
		self.heading = heading

	def applyTo(self, obj, sim):
		loc = utils.scenicToCarlaLocation(pos, z=obj.elevation)
		rot = utils.scenicToCarlaRotation(heading)
		transform = carla.Transform(loc, rot)
		obj.carlaActor.set_transform(transform)


#############################################
# Actions specific to carla.Vehicle objects #
#############################################

class VehicleAction(Action):
	def canBeTakenBy(self, agent):
		return isinstance(agent, carlaModel.Vehicle)

class SetManualGearShiftAction(VehicleAction):
	def __init__(self, manualGearShift):
		if not isinstance(manualGearShift, bool):
			raise RuntimeError('Manual gear shift must be a boolean.')
		self.manualGearShift = manualGearShift

	def applyTo(self, obj, sim):
		vehicle = obj.carlaActor
		ctrl = vehicle.get_control()
		ctrl.manual_gear_shift = self.manualGearShift
		vehicle.apply_control(ctrl)


class SetGearAction(VehicleAction):
	def __init__(self, gear):
		if not isinstance(gear, int):
			raise RuntimeError('Gear must be an int.')
		self.gear = gear

	def applyTo(self, obj, sim):
		vehicle = obj.carlaActor
		ctrl = vehicle.get_control()
		ctrl.gear = self.gear
		vehicle.apply_control(ctrl)


class SetManualFirstGearShiftAction(VehicleAction):	# TODO eliminate
	def applyTo(self, obj, sim):
		ctrl = carla.VehicleControl(manual_gear_shift=True, gear=1)
		obj.carlaActor.apply_control(ctrl)


#################################################
# Actions available to all carla.Walker objects #
#################################################

class PedestrianAction(Action):
	def canBeTakenBy(self, agent):
		return isinstance(agent, carlaModel.Pedestrian)
class SetRelativeDirectionAction(PedestrianAction):
	'''Offsets direction counterclockwise relative to walker's forward vector.'''

	def __init__(self, offset, degrees=False):
		super().__init__()
		self.offset = math.radians(offset) if degrees else offset

	def applyTo(self, obj, walker, sim):
		ctrl = walker.get_control()
		currDir = ctrl.direction
		sinOffset, cosOffset = math.cos(self.offset), math.sin(self.offset)
		newX = currDir.x * cosOffset - currDir.y * sinOffset
		newY = currDir.x * sinOffset + currDir.y * cosOffset
		ctrl.direction = utils.scalarToCarlaVector3D(newX, newY, currDir.z)
		walker.apply_control(ctrl)


class SetSpeedAction(PedestrianAction):
	def __init__(self, speed):
		assert speed >= 0.0, \
			'Speed must be a non-negative float.'
		super().__init__()
		self.speed = speed  # float

	def applyTo(self, obj, walker, sim):
		ctrl = walker.get_control()
		ctrl.speed = self.speed
		walker.apply_control(ctrl)


class SetJumpAction(PedestrianAction):
	def __init__(self, jump):
		if not isinstance(jump, bool):
			raise RuntimeError('Jump must be a boolean.')
		self.jump = jump

	def applyTo(self, obj, sim):
		walker = obj.carlaActor
		ctrl = walker.get_control()
		ctrl.jump = self.jump
		walker.apply_control(ctrl)
