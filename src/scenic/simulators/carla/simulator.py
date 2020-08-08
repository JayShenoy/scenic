
try:
	import carla
except ImportError as e:
	raise ModuleNotFoundError('CARLA scenarios require the "carla" Python package') from e

import pygame

import scenic.simulators as simulators
import scenic.simulators.carla.utils.utils as utils
import scenic.simulators.carla.utils.visuals as visuals
import scenic.simulators.carla.utils.bounding_boxes as bb
import time

import numpy as np
import json

class CarlaSimulator(simulators.Simulator):
	def __init__(self, carla_map, address='127.0.0.1', port=2000, timeout=10, render=True,
	             timestep=0.1):
		super().__init__()
		self.client = carla.Client(address, port)
		self.client.set_timeout(timeout)  # limits networking operations (seconds)
		self.world = self.client.load_world(carla_map)
		self.map = carla_map

		# Set to synchronous with fixed timestep
		settings = self.world.get_settings()
		settings.synchronous_mode = True
		settings.fixed_delta_seconds = timestep  # NOTE: Should not exceed 0.1
		self.world.apply_settings(settings)

		self.render = render  # visualization mode ON/OFF

	def createSimulation(self, scene):
		return CarlaSimulation(scene, self.client, self.render, self.map)


class CarlaSimulation(simulators.Simulation):
	def __init__(self, scene, client, render, map):
		super().__init__(scene)
		self.client = client
		self.client.load_world(map)
		self.world = self.client.get_world()
		self.blueprintLib = self.world.get_blueprint_library()
		
		# Reloads current world: destroys all actors, except traffic manager instances
		# self.client.reload_world()
		
		# Setup HUD
		self.render = render
		if self.render:
			self.displayDim = (1280, 720)
			self.displayClock = pygame.time.Clock()
			self.camTransform = 0
			pygame.init()
			pygame.font.init()
			self.hud = visuals.HUD(*self.displayDim)
			self.display = pygame.display.set_mode(
				self.displayDim,
				pygame.HWSURFACE | pygame.DOUBLEBUF
			)
			self.cameraManager = None

		# Create Carla actors corresponding to Scenic objects
		self.ego = None
		for obj in self.objects:
			# Extract blueprint
			# print(obj.blueprint)
			blueprint = self.blueprintLib.find(obj.blueprint)

			# Set up transform
			loc = utils.scenicToCarlaLocation(obj.position, world=self.world)
			rot = utils.scenicToCarlaRotation(obj.heading)
			# print(blueprint)
			transform = carla.Transform(loc, rot)
			
			# # Create Carla actor
			carlaActor = self.world.try_spawn_actor(blueprint, transform)
			if carlaActor is None:
				raise simulators.SimulationCreationError(
				    f'Unable to spawn object {type(obj)} at position {obj.position}, '
				    f'likely from a spawn collision. Of model {obj.blueprint} '
				)

			if isinstance(carlaActor, carla.Vehicle):
				# carlaActor.apply_control(carla.VehicleControl())  # set default controls
				carlaActor.apply_control(carla.VehicleControl(manual_gear_shift=True, gear=1))
			elif isinstance(carlaActor, carla.Walker):
				carlaActor.apply_control(carla.WalkerControl())

			# #create by batch
			# batch = []
			# equivVel = utils.scenicSpeedToCarlaVelocity(obj.speed, obj.heading)
			# print(equivVel)
			# batch.append(carla.command.SpawnActor(blueprint, transform, carlaActor).then(carla.command.ApplyVelocity(carla.command.FutureActor, equivVel)))

			obj.carlaActor = carlaActor

			# Check if ego (from carla_scenic_taks.py)
			if obj is self.objects[0]:
				self.ego = obj

				# Setup camera manager and collision sensor for ego
				if self.render:
					camIndex = 0
					camPosIndex = 0
					self.cameraManager = visuals.CameraManager(self.world, carlaActor, self.hud)
					self.cameraManager._transform_index = camPosIndex
					self.cameraManager.set_sensor(camIndex)
					self.cameraManager.set_transform(self.camTransform)

					VIEW_WIDTH = 1280.0
					VIEW_HEIGHT = 720.0
					VIEW_FOV = 90.0
					calibration = np.identity(3)
					calibration[0, 2] = VIEW_WIDTH / 2.0
					calibration[1, 2] = VIEW_HEIGHT / 2.0
					calibration[0, 0] = calibration[1, 1] = VIEW_WIDTH / (2.0 * np.tan(VIEW_FOV * np.pi / 360.0))
					self.cameraManager.sensor.calibration = calibration

					semanticCamIndex = 5
					semanticCamPosIndex = 0
					self.semanticCameraManager = visuals.CameraManager(self.world, carlaActor, self.hud)
					self.semanticCameraManager._transform_index = semanticCamPosIndex
					self.semanticCameraManager.set_sensor(semanticCamIndex)
					self.semanticCameraManager.set_transform(self.camTransform)

					lidarSensorIndex = 6
					lidarSensorPosIndex = 1
					self.lidarSensorManager = visuals.CameraManager(self.world, carlaActor, self.hud)
					self.lidarSensorManager._transform_index = lidarSensorPosIndex
					self.lidarSensorManager.set_sensor(lidarSensorIndex)
					self.lidarSensorManager.set_transform(lidarSensorPosIndex)

		self.world.tick() ## allowing manualgearshift to take effect 

		for obj in self.objects:
			if isinstance(obj.carlaActor, carla.Vehicle):
				# carlaActor.apply_control(carla.VehicleControl())  # set default controls
				obj.carlaActor.apply_control(carla.VehicleControl(manual_gear_shift=False))

		self.world.tick()

		# Set Carla actor's initial speed (if specified)
		for obj in self.objects:
			if obj.speed is not None:
				equivVel = utils.scenicSpeedToCarlaVelocity(obj.speed, obj.heading)
				obj.carlaActor.set_velocity(equivVel)

		# Initialize array of 3D bounding boxes
		self.bounding_boxes = []

	def readPropertiesFromCarla(self):
		for obj in self.objects:

			# Extract Carla properties
			carlaActor = obj.carlaActor
			currTransform = carlaActor.get_transform()
			currLoc = currTransform.location
			currRot = currTransform.rotation
			currVel = carlaActor.get_velocity()
			# print(carlaActor.get_acceleration())

			# Update Scenic object properties
			obj.position = utils.carlaToScenicPosition(currLoc)
			obj.elevation = utils.carlaToScenicElevation(currLoc)
			obj.heading = utils.carlaToScenicHeading(currRot, tolerance2D=5.0)
			obj.speed = utils.carlaVelocityToScenicSpeed(currVel)

			# NOTE: Refer to utils.carlaToScenicHeading
			if obj.heading is None:
				raise RuntimeError(f'{carlaActor} has non-planar orientation')

	def currentState(self):
		return tuple(obj.position for obj in self.objects)

	def initialState(self):
		return self.currentState()

	def step(self, actions):
		# Execute actions
		for obj, action in actions.items():
			if action:
				action.applyTo(obj, obj.carlaActor, self)

			# if obj.carlaActor.get_control().throttle > 0:
			# 	print(obj.carlaActor.get_acceleration())

		# Run simulation for one timestep
		self.world.tick()

		vehicles = self.world.get_actors().filter('vehicle.*')

		# Render simulation
		if self.render:
			# self.hud.tick(self.world, self.ego, self.displayClock)
			self.cameraManager.render(self.display)

			# Project and draw bounding boxes to display
			# if self.render_bounding_boxes:
				# bounding_boxes = bb.ClientSideBoundingBoxes.get_bounding_boxes(vehicles, self.cameraManager.sensor)
				# bb.ClientSideBoundingBoxes.draw_bounding_boxes(self.display, bounding_boxes)

			bounding_boxes_3d = bb.ClientSideBoundingBoxes.get_3d_bounding_boxes(vehicles, self.cameraManager.sensor)
			bounding_boxes_3d = [bb.tolist() for bb in bounding_boxes_3d]
			self.bounding_boxes.append(bounding_boxes_3d)

			# self.hud.render(self.display)
			pygame.display.flip()

		# Read back the results of the simulation
		self.readPropertiesFromCarla()

		return self.currentState()

	def save_videos(self, scene_name):
		self.cameraManager.save_video('{}_rgb.mp4'.format(scene_name))
		self.semanticCameraManager.save_video('{}_semantic.mp4'.format(scene_name))

		with open('{}_boxes.json'.format(scene_name), 'w') as f:
			json.dump(self.bounding_boxes, f)