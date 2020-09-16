"""Implementations of the built-in Scenic classes."""

import inspect
import collections
import math
import random
import pymesh

from abc import ABC, abstractmethod

from scenic.core.distributions import Samplable, needsSampling
from scenic.core.specifiers import Specifier, PropertyDefault, ModifyingSpecifier
from scenic.core.vectors import Vector, Orientation
from scenic.core.geometry import RotatedRectangle, averageVectors, hypot, min, pointIsInCone
from scenic.core.regions import CircularRegion, SectorRegion
from scenic.core.type_support import toVector, toScalar
from scenic.core.lazy_eval import needsLazyEvaluation
from scenic.core.utils import areEquivalent, cached_property, RuntimeParseError

## Abstract base class

class Constructible(Samplable):
	"""Abstract base class for Scenic objects.

	Scenic objects, which are constructed using specifiers, are implemented
	internally as instances of ordinary Python classes. This abstract class
	implements the procedure to resolve specifiers and determine values for
	the properties of an object, as well as several common methods supported
	by objects.
	"""

	def __init_subclass__(cls):
		# find all defaults provided by the class or its superclasses
		allDefs = collections.defaultdict(list)
		for sc in inspect.getmro(cls):
			if hasattr(sc, '__annotations__'):
				for prop, value in sc.__annotations__.items():
					allDefs[prop].append(PropertyDefault.forValue(value))

		# resolve conflicting defaults
		resolvedDefs = {}
		for prop, defs in allDefs.items():
			primary, rest = defs[0], defs[1:]
			spec = primary.resolveFor(prop, rest)
			resolvedDefs[prop] = spec
		cls.defaults = resolvedDefs

	@classmethod
	def withProperties(cls, props):
		assert all(reqProp in props for reqProp in cls.defaults)
		return cls(_internal=True, **props)

	def __init__(self, *args, _internal=False, **kwargs):
		if _internal:	# Object is being constructed internally; use fast path
			assert not args
			for prop, value in kwargs.items():
				assert not needsLazyEvaluation(value), (prop, value)
				object.__setattr__(self, prop, value)
			super().__init__(kwargs.values())
			self.properties = set(kwargs.keys())
			 # TODO: @Matthew Build up dict and assert at end of init
			return               # that it's len is == properties or something 
		# Validate specifiers
		name = type(self).__name__
		specifiers = list(args)
		for prop, val in kwargs.items():	# kwargs supported for internal use
			specifiers.append(Specifier({prop: 1}, val))
		properties = dict()
		modified = dict()
		priorities = dict()
		optionals = collections.defaultdict(list)
		defs = self.__class__.defaults
		'''
		For each specifier:
			* If a modifying specifier, modifying[p] = specifier
			* If a specifier, and not in properties specified, properties[p] = specifier
				- Otherwise, if property specified, check if specifier's priority is higher. 
				- If so, replace it with specifier

		Priorties are inversed: A lower priority number means semantically that it has a higher priority level
		'''
		for spec in specifiers:
			assert isinstance(spec, Specifier), (name, spec)
			props = spec.priorities
			for p in props:
				if isinstance(spec, ModifyingSpecifier):
					if p in modified:
						raise RuntimeParseError(f'property "{p}" of {name} modified twice')
					modified[p] = spec
				else:
					if p in properties:
						if spec.priorities[p] == priorities[p]:
							raise RuntimeParseError(f'property "{p}" of {name} specified twice with the same priority')
						if spec.priorities[p] < priorities[p]:
							properties[p] = spec
							priorities[p] = spec.properties[p]
							spec.modifying[p] = False
					else:
						properties[p] = spec
						priorities[p] = spec.priorities[p]
						spec.modifying[p] = False

		'''
		If a modifying specifier specifies the property with a higher priority,
		set the object's property to be specified by the modifying specifier. Otherwise,
		if the property exists and the priorities match, object needs to be specified
		by the original specifier then the resulting value is modified by the
		modifying specifier. 

		If the property is not yet being specified, the modifying specifier will 
		act as a normal specifier for that property. 
		'''
		deprecate = []
		for prop, spec in modified.items():
			if prop in properties:
				if spec.priorities[prop] < priorities[prop]:   # Higher priority level, so it specifies
					properties[prop] = spec
					priorities[prop] = spec.priorities[prop]
					spec.modifying[prop] = False
					deprecate.append(prop)
			else:                                              # Not specified, so specify it
				properties[prop] = spec
				priorities[prop] = spec.priorities[prop]
				spec.modifying[prop] = False
				deprecate.append(prop)

		# Delete all deprecated modifiers. Any remaining will modify a specified property 
		for d in deprecate:
			assert d in modified
			del modified[d]
		
		# Add any default specifiers needed
		for prop in defs:
			if prop not in properties:
				spec = defs[prop]
				specifiers.append(spec)
				properties[prop] = spec

		# Topologically sort specifiers
		order = []
		seen, done = set(), set()

		def dfs(spec):
			if spec in done:
				return
			elif spec in seen:
				raise RuntimeParseError(f'specifier for property {spec.priorities} '
										'depends on itself')
			seen.add(spec)
			for dep in spec.requiredProperties:
				child = properties.get(dep)
				if child is None:
					raise RuntimeParseError(f'property {dep} required by '
											f'specifier {spec} is not specified')
				else:
					dfs(child)
			order.append(spec)
			done.add(spec)

		for spec in specifiers:
			dfs(spec)
		assert len(order) == len(specifiers)

		for spec in specifiers:
			if isinstance(spec, ModifyingSpecifier):
				for mod in modified:
					spec.modifying[mod] = True

		# Evaluate and apply specifiers
		for spec in order:
			spec.applyTo(self, spec.modifying)

		# Set up dependencies
		deps = []
		for prop in properties:
			assert hasattr(self, prop)
			val = getattr(self, prop)
			deps.append(val)

		super().__init__(deps)
		self.properties = set(properties)
		self.modified = set(modified)

		# Possibly register this object
		self._register()

	def _register(self):
		pass	# do nothing by default; may be overridden by subclasses

	def sampleGiven(self, value):
		return self.withProperties({ prop: value[getattr(self, prop)]
								   for prop in self.properties })

	def allProperties(self):
		return { prop: getattr(self, prop) for prop in self.properties }

	def copyWith(self, **overrides):
		props = self.allProperties()
		props.update(overrides)
		return self.withProperties(props)

	def isEquivalentTo(self, other):
		if type(other) is not type(self):
			return False
		return areEquivalent(self.allProperties(), other.allProperties())

	def __str__(self):
		if hasattr(self, 'properties') and 'name' in self.properties:
			return self.name
		else:
			return super().__repr__()

	def __repr__(self):
		if hasattr(self, 'properties'):
			allProps = { prop: getattr(self, prop) for prop in self.properties }
		else:
			allProps = '<under construction>'
		return f'{type(self).__name__}({allProps})'

## Shapes

class Shape(ABC):
	"""An abstract base class for Scenic objects.

	Scenic objects have a shape property associated with them that are 
	implemented internally as meshes that describe its geometry. This 
	abstract class implements the procedure to perform mesh processing
	as well as several common methods supported by meshes that an object
	will use. 
	"""
	def __init__(self):
		pass

	@abstractmethod
	def foo(self):
		pass

## Mutators

class Mutator:
	"""An object controlling how the ``mutate`` statement affects an `Object`.

	A `Mutator` can be assigned to the ``mutator`` property of an `Object` to
	control the effect of the ``mutate`` statement. When mutation is enabled
	for such an object using that statement, the mutator's `appliedTo` method
	is called to compute a mutated version.
	"""

	def appliedTo(self, obj):
		"""Return a mutated copy of the object. Implemented by subclasses."""
		raise NotImplementedError

class PositionMutator(Mutator):
	"""Mutator adding Gaussian noise to ``position``. Used by `Point`.

	Attributes:
		stddev (float): standard deviation of noise
	"""
	def __init__(self, stddev):
		self.stddev = stddev

	def appliedTo(self, obj):
		noise = Vector(random.gauss(0, self.stddev), random.gauss(0, self.stddev))
		pos = toVector(obj.position, '"position" not a vector')
		pos = pos + noise
		return (obj.copyWith(position=pos), True)		# allow further mutation

	def __eq__(self, other):
		if type(other) is not type(self):
			return NotImplemented
		return (other.stddev == self.stddev)

	def __hash__(self):
		return hash(self.stddev)

class HeadingMutator(Mutator):
	"""Mutator adding Gaussian noise to ``heading``. Used by `OrientedPoint`.

	Attributes:
		stddev (float): standard deviation of noise
	"""
	def __init__(self, stddev):
		self.stddev = stddev

	def appliedTo(self, obj):
		noise = random.gauss(0, self.stddev)
		h = obj.heading + noise
		return (obj.copyWith(heading=h), True)		# allow further mutation

	def __eq__(self, other):
		if type(other) is not type(self):
			return NotImplemented
		return (other.stddev == self.stddev)

	def __hash__(self):
		return hash(self.stddev)

## Point

class Point(Constructible):
	"""Implementation of the Scenic class ``Point``.

	The default mutator for `Point` adds Gaussian noise to ``position`` with
	a standard deviation given by the ``positionStdDev`` property.

	Attributes:
		position (`Vector`): Position of the point. Default value is the origin.
		visibleDistance (float): Distance for ``can see`` operator. Default value 50.
		width (float): Default value zero (only provided for compatibility with
		  operators that expect an `Object`).
		length (float): Default value zero.
	"""
	position: Vector(0, 0, 0) # TODO: @Matthew Extend position to 3D.
	width: 0
	length: 0
	visibleDistance: 50

	mutationEnabled: False
	mutator: PropertyDefault({'positionStdDev'}, {'additive'},
							 lambda self, specifier: PositionMutator(self.positionStdDev))
	positionStdDev: 1

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.position = toVector(self.position, f'"position" of {self} not a vector')

	@cached_property
	def visibleRegion(self):
		return CircularRegion(self.position, self.visibleDistance)

	@cached_property
	def corners(self):
		return (self.position,)

	def toVector(self):
		return self.position.toVector()

	def canSee(self, other):	# TODO improve approximation?
		for corner in other.corners:
			if self.visibleRegion.containsPoint(corner):
				return True
		return False

	def sampleGiven(self, value):
		sample = super().sampleGiven(value)
		if self.mutationEnabled:
			for mutator in self.mutator:
				if mutator is None:
					continue
				sample, proceed = mutator.appliedTo(sample)
				if not proceed:
					break
		return sample

	# Points automatically convert to Vectors when needed
	def __getattr__(self, attr):
		if hasattr(Vector, attr):
			return getattr(self.toVector(), attr)
		else:
			raise AttributeError(f"'{type(self).__name__}' object has no attribute '{attr}'")

## OrientedPoint

class OrientedPoint(Point):
	"""Implementation of the Scenic class ``OrientedPoint``.

	The default mutator for `OrientedPoint` adds Gaussian noise to ``heading``
	with a standard deviation given by the ``headingStdDev`` property, then
	applies the mutator for `Point`.

	Attributes:
		heading (float): Heading of the `OrientedPoint`. Default value 0 (North).
		viewAngle (float): View cone angle for ``can see`` operator. Default
		  value :math:`2\\pi`.
	"""
	# TODO: @Matthew Do OrientedPoints need Orientation instead of just a scalar heading? 
	# TODO: @Matthew Heading is derived from Orientation 
	heading: 0
	viewAngle: math.tau # TODO: @Matthew Implement 2-tuple view angle for 3D views 
	pitch: 0
	roll: 0
	yaw: 0
	parentOrientation: Orientation()

	mutator: PropertyDefault({'headingStdDev'}, {'additive'},
		lambda self, specifier: HeadingMutator(self.headingStdDev))
	headingStdDev: math.radians(5)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.heading = toScalar(self.heading, f'"heading" of {self} not a scalar')
		# self.orientation = Orientation(self.roll, self.pitch, self.yaw) # TODO: @Matthew Where to place orientation? 

	@cached_property
	def visibleRegion(self):
		return SectorRegion(self.position, self.visibleDistance,
		                    self.heading, self.viewAngle)

	def relativize(self, vec):
		pos = self.relativePosition(vec)
		return OrientedPoint(position=pos, heading=self.heading)

	def relativePosition(self, vec):
		return self.position.offsetRotated(self.heading, vec)

	def toHeading(self):
		return self.heading

## Object

class Object(OrientedPoint, RotatedRectangle):
	"""Implementation of the Scenic class ``Object``.

	Attributes:
		width (float): Width of the object, i.e. extent along its X axis.
		  Default value 1.
		height (float): Height of the object, i.e. extent along its Y axis.
		  Default value 1.
		length (float): Length of the object, i.e. extent along its Z axis.
		  Default value 1. 
		allowCollisions (bool): Whether the object is allowed to intersect
		  other objects. Default value ``False``.
		requireVisible (bool): Whether the object is required to be visible
		  from the ``ego`` object. Default value ``True``.
		regionContainedIn (`Region` or ``None``): A `Region` the object is
		  required to be contained in. If ``None``, the object need only be
		  contained in the scenario's workspace.
		cameraOffset (`Vector`): Position of the camera for the ``can see``
		  operator, relative to the object's ``position``. Default ``0 @ 0``.
	"""
	width: 1
	height: 1
	length: 1 
	allowCollisions: False
	requireVisible: True
	regionContainedIn: None
	cameraOffset: Vector(0, 0)
	# shape = Shape()
	#TODO: @Matthew Object needs shape and surface mutable attributes 

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.hw = hw = self.width / 2
		self.hh = hh = self.height / 2
		self.hl = hl = self.length / 2
		self.radius = hypot(hw, hl)	# circumcircle; for collision detection
		self.inradius = min(hw, hl)	# incircle; for collision detection

		self._relations = []

	def _register(self):
		import scenic.syntax.veneer as veneer	# TODO improve?
		veneer.registerObject(self)

	@cached_property
	def left(self):
		return self.relativize(Vector(-self.hw, 0))

	@cached_property
	def right(self):
		return self.relativize(Vector(self.hw, 0))

	@cached_property
	def front(self):
		return self.relativize(Vector(0, self.hl))

	@cached_property
	def back(self):
		return self.relativize(Vector(0, -self.hl))

	@cached_property
	def frontLeft(self):
		return self.relativize(Vector(-self.hw, self.hl))

	@cached_property
	def frontRight(self):
		return self.relativize(Vector(self.hw, self.hl))

	@cached_property
	def backLeft(self):
		return self.relativize(Vector(-self.hw, -self.hl))

	@cached_property
	def backRight(self):
		return self.relativize(Vector(self.hw, -self.hl))

	@cached_property
	def top(self):
		return self.relativize(Vector(0, 0, self.hh))

	@cached_property
	def bottom(self):
		return self.relativize(Vector(0, 0, -self.hh))

	@cached_property
	def topFrontLeft(self):
		return self.relativize(Vector(-self.hw, self.hl, self.hh))

	@cached_property
	def topFrontRight(self):
		return self.relativize(Vector(self.hw, self.hl, self.hh))

	@cached_property
	def topBackLeft(self):
		return self.relativize(Vector(-self.hw, -self.hl, self.hh))

	@cached_property
	def topBackRight(self):
		return self.relativize(Vector(self.hw, -self.hl, self.hh))

	@cached_property
	def bottomFrontLeft(self):
		return self.relativize(Vector(-self.hw, self.hl, -self.hh))

	@cached_property
	def bottomFrontRight(self):
		return self.relativize(Vector(self.hw, self.hl, -self.hh))

	@cached_property
	def bottomBackLeft(self):
		return self.relativize(Vector(-self.hw, -self.hl, -self.hh))

	@cached_property
	def bottomBackRight(self):
		return self.relativize(Vector(self.hw, -self.hl, -self.hh))

	@cached_property
	def visibleRegion(self):
		camera = self.position.offsetRotated(self.heading, self.cameraOffset)
		return SectorRegion(camera, self.visibleDistance, self.heading, self.viewAngle)

	@cached_property
	def corners(self):
		hw, hl = self.hw, self.hl
		return (
			self.relativePosition(Vector(hw, hl)),
			self.relativePosition(Vector(-hw, hl)),
			self.relativePosition(Vector(-hw, -hl)),
			self.relativePosition(Vector(hw, -hl))
		)

	def show(self, workspace, plt, highlight=False):
		if needsSampling(self):
			raise RuntimeError('tried to show() symbolic Object')
		pos = self.position
		spos = workspace.scenicToSchematicCoords(pos)

		if highlight:
			# Circle around object
			rad = 1.5 * max(self.width, self.length)
			c = plt.Circle(spos, rad, color='g', fill=False)
			plt.gca().add_artist(c)
			# View cone
			ha = self.viewAngle / 2.0
			camera = self.position.offsetRotated(self.heading, self.cameraOffset)
			cpos = workspace.scenicToSchematicCoords(camera)
			for angle in (-ha, ha):
				p = camera.offsetRadially(20, self.heading + angle)
				edge = [cpos, workspace.scenicToSchematicCoords(p)]
				x, y = zip(*edge)
				plt.plot(x, y, 'b:')

		corners = [workspace.scenicToSchematicCoords(corner) for corner in self.corners]
		x, y = zip(*corners)
		color = self.color if hasattr(self, 'color') else (1, 0, 0)
		plt.fill(x, y, color=color)

		frontMid = averageVectors(corners[0], corners[1])
		baseTriangle = [frontMid, corners[2], corners[3]]
		triangle = [averageVectors(p, spos, weight=0.5) for p in baseTriangle]
		x, y = zip(*triangle)
		plt.fill(x, y, "w")
		plt.plot(x + (x[0],), y + (y[0],), color="k", linewidth=1)
