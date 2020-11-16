"""Scenic vectors and vector fields."""

from __future__ import annotations

import math
from math import sin, cos
import random
import collections
import itertools

import shapely.geometry
import wrapt

from scenic.core.distributions import (Samplable, Distribution, MethodDistribution,
    needsSampling, makeOperatorHandler, distributionMethod, distributionFunction,
	RejectionException, smt_add, smt_subtract, smt_multiply, smt_divide, smt_and, 
	smt_equal, smt_mod, smt_assert, findVariableName,
	checkAndEncodeSMT, writeSMTtoFile, cacheVarName, smt_lessThan, smt_lessThanEq, smt_ite, normalizeAngle_SMT, vector_operation_smt)
from scenic.core.lazy_eval import valueInContext, needsLazyEvaluation, makeDelayedFunctionCall
import scenic.core.utils as utils
from scenic.core.geometry import normalizeAngle

class VectorDistribution(Distribution):
	"""A distribution over Vectors."""
	defaultValueType = None		# will be set after Vector is defined

	def toVector(self):
		return self

class CustomVectorDistribution(VectorDistribution):
	"""Distribution with a custom sampler given by an arbitrary function."""
	def __init__(self, sampler, *dependencies, name='CustomVectorDistribution', evaluator=None):
		super().__init__(*dependencies)
		self.sampler = sampler
		self.name = name
		self.evaluator = evaluator

	def sampleGiven(self, value):
		return self.sampler(value)

	def evaluateInner(self, context):
		if self.evaluator is None:
			raise NotImplementedError('evaluateIn() not supported by this distribution')
		return self.evaluator(self, context)

	def __str__(self):
		deps = utils.argsToString(self.dependencies)
		return f'{self.name}{deps}'

class VectorOperatorDistribution(VectorDistribution):
	"""Vector version of OperatorDistribution."""
	def __init__(self, operator, obj, operands):
		super().__init__(obj, *operands)
		self.operator = operator
		self.object = obj
		self.operands = operands

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		# if not isinstance(obj, Samplable):
		# 	obj = self

		if debug:
			writeSMTtoFile(smt_file_path, "VectorOperatorDistribution")

		if self in cached_variables.keys():
			if debug:
				writeSMTtoFile(smt_file_path, "Already In cached_variables")
			return cached_variables[self]

		## encode Samplable attributes:
		for op in self.operands:
			if isinstance(op, Samplable):
				print("operand: ", op)
				op.encodeToSMT(smt_file_path, cached_variables, debug = debug)

		## handle VectorOperatorDist object
		vector = self.object.encodeToSMT(smt_file_path, cached_variables, obj = self, debug = debug)
		return cacheVarName(cached_variables, self, vector)

	def sampleGiven(self, value):
		first = value[self.object]
		rest = (value[child] for child in self.operands)
		op = getattr(first, self.operator)
		return op(*rest)

	def evaluateInner(self, context):
		obj = valueInContext(self.object, context)
		operands = tuple(valueInContext(arg, context) for arg in self.operands)
		return VectorOperatorDistribution(self.operator, obj, operands)

	def __str__(self):
		ops = utils.argsToString(self.operands)
		return f'{self.object}.{self.operator}{ops}'

class VectorMethodDistribution(VectorDistribution):
	"""Vector version of MethodDistribution."""
	def __init__(self, method, obj, args, kwargs):
		super().__init__(*args, *kwargs.values())
		self.method = method
		self.object = obj
		self.arguments = args
		self.kwargs = kwargs

	def sampleGiven(self, value):
		args = (value[arg] for arg in self.arguments)
		kwargs = { name: value[arg] for name, arg in self.kwargs.items() }
		return self.method(self.object, *args, **kwargs)

	def evaluateInner(self, context):
		obj = valueInContext(self.object, context)
		arguments = tuple(valueInContext(arg, context) for arg in self.arguments)
		kwargs = { name: valueInContext(arg, context) for name, arg in self.kwargs.items() }
		return VectorMethodDistribution(self.method, obj, arguments, kwargs)

	def __str__(self):
		args = utils.argsToString(itertools.chain(self.arguments, self.kwargs.values()))
		return f'{self.object}.{self.method.__name__}{args}'

def scalarOperator(method):
	"""Decorator for vector operators that yield scalars."""
	op = method.__name__
	setattr(VectorDistribution, op, makeOperatorHandler(op))

	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		if any(needsSampling(arg) for arg in itertools.chain(args, kwargs.values())):
			return MethodDistribution(method, instance, args, kwargs)
		else:
			return wrapped(*args, **kwargs)
	return wrapper(method)

def makeVectorOperatorHandler(op):
	def handler(self, *args):
		return VectorOperatorDistribution(op, self, args)
	return handler
def vectorOperator(method):
	"""Decorator for vector operators that yield vectors."""
	op = method.__name__
	setattr(VectorDistribution, op, makeVectorOperatorHandler(op))

	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		def helper(*args):
			if needsSampling(instance):
				return VectorOperatorDistribution(op, instance, args)
			elif any(needsSampling(arg) for arg in args):
				return VectorMethodDistribution(method, instance, args, {})
			elif any(needsLazyEvaluation(arg) for arg in args):
				# see analogous comment in distributionFunction
				return makeDelayedFunctionCall(helper, args, {})
			else:
				return wrapped(*args)
		return helper(*args)
	return wrapper(method)

def vectorDistributionMethod(method):
	"""Decorator for methods that produce vectors. See distributionMethod."""
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		def helper(*args, **kwargs):
			if any(needsSampling(arg) for arg in itertools.chain(args, kwargs.values())):
				return VectorMethodDistribution(method, instance, args, kwargs)
			elif any(needsLazyEvaluation(arg)
			         for arg in itertools.chain(args, kwargs.values())):
				# see analogous comment in distributionFunction
				return makeDelayedFunctionCall(helper, args, kwargs)
			else:
				return wrapped(*args, **kwargs)
		return helper(*args, **kwargs)
	return wrapper(method)

class Vector(Samplable, collections.abc.Sequence):
	"""A 2D vector, whose coordinates can be distributions."""
	def __init__(self, x, y):
		self.coordinates = (x, y)
		super().__init__(self.coordinates)

	@property
	def x(self) -> float:
		return self.coordinates[0]

	@property
	def y(self) -> float:
		return self.coordinates[1]


	def encodeRotatedBy_SMT(self, cached_variables, smt_file_path, angle, x, y, debug=False):
		""" encodes rotatedBy function to a SMT formula 
		type: angle, x, y := class objects """
		if debug:
			writeSMTtoFile(smt_file_path, "encode RotatedBy()")

		angle = checkAndEncodeSMT(smt_file_path, cached_variables, angle)

		if not isinstance(x, str):
			x = checkAndEncodeSMT(smt_file_path, cached_variables, x)
		if not isinstance(y, str):
			y = checkAndEncodeSMT(smt_file_path, cached_variables, y)

		cos = "(cos "+angle+")"
		sin = "(sin "+angle+")"

		cos_mul_x = smt_multiply(cos, x)
		sin_mul_y = smt_multiply(sin, y)
		cos_mul_y = smt_multiply(cos, y)
		sin_mul_x = smt_multiply(sin, x)

		x_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
		y_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')

		x_smt_encoding = smt_assert("equal", x_name, smt_subtract(cos_mul_x, sin_mul_y))
		y_smt_encoding = smt_assert("equal", y_name, smt_add(sin_mul_x, cos_mul_y))

		writeSMTtoFile(smt_file_path, x_smt_encoding)
		writeSMTtoFile(smt_file_path, y_smt_encoding)

		return (x_name, y_name)

	def encodeOffsetRotated_SMT(self, cached_variables, smt_file_path, heading, offset, debug=False):
		if debug:
			writeSMTtoFile(smt_file_path, "encode OffsetRotated()")

		offset_smt = self.encodeRotatedBy_SMT(cached_variables, smt_file_path, heading, offset.x, offset.y)
		x_smt_var = offset_smt[0]
		y_smt_var = offset_smt[1]

		if not isinstance(self.x, str):
			self_x = checkAndEncodeSMT(smt_file_path, cached_variables, self.x)
		else: 
			self_x = self.x
		if not isinstance(self.y, str):
			self_y = checkAndEncodeSMT(smt_file_path, cached_variables, self.y)
		else:
			self_y = self.y

		x_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
		y_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')
		x_smt_encoding = smt_assert("equal", x_name, smt_add(x_smt_var, self_x))
		y_smt_encoding = smt_assert("equal", y_name, smt_add(y_smt_var, self_y))

		writeSMTtoFile(smt_file_path, x_smt_encoding)
		writeSMTtoFile(smt_file_path, y_smt_encoding)
		return (x_name, y_name)

	def encodeToSMT(self, smt_file_path, cached_variables, obj=None, debug=False):
		if debug:
			writeSMTtoFile(smt_file_path, "Vector")

		if not isinstance(obj, Samplable):
			obj = self

		if obj in cached_variables.keys():
			if debug:
				writeSMTtoFile(smt_file_path, "in Vector class, "+str(obj)+" exists in cached_variables dict")
			return cached_variables[obj]			

		if isinstance(obj, Vector):
			if debug:
				writeSMTtoFile(smt_file_path, "in Vector class, input obj is Vector class")
			x = checkAndEncodeSMT(smt_file_path, cached_variables, obj.x, debug = debug)
			y = checkAndEncodeSMT(smt_file_path, cached_variables, obj.y, debug = debug)
			return cacheVarName(cached_variables, obj, (x,y))

		elif isinstance(obj, VectorOperatorDistribution):
			if debug:
				writeSMTtoFile(smt_file_path, "in Vector class, input obj is VectorOperatorDistribution class")
			operator = obj.operator
			ob = obj.object
			operands = obj.operands

			### Make sure object and operands are smt encoded
			ob.encodeToSMT(smt_file_path, cached_variables, debug=debug)
			for op in operands:
				if isinstance(op, Samplable):
					op.encodeToSMT(smt_file_path, cached_variables, debug=debug)

			if operator == 'rotatedBy':
				if debug:
					writeSMTtoFile(smt_file_path, "rotatedBy")
				angle = operands[0]
				output_vector = self.encodeRotatedBy_SMT(cached_variables, smt_file_path, angle, self.x, self.y, debug=False)
				return cacheVarName(cached_variables, obj, output_vector)

			elif operator == 'offsetRotated':
				if debug:
					writeSMTtoFile(smt_file_path, "offsetRotated")
				heading = operands[0]
				offset = operands[1]
				output_vector = self.encodeOffsetRotated_SMT(cached_variables, smt_file_path, heading, offset, debug=False)
				return cacheVarName(cached_variables, obj, output_vector)

			elif operator == 'offsetRadially':
				if debug:
					writeSMTtoFile(smt_file_path, "offsetRadially")
				radius = operands[0]
				heading = operands[1]
				offset = Vector(0, radius)
				output_vector = self.encodeOffsetRotated_SMT(cached_variables, smt_file_path, heading, offset, debug=False)
				return cacheVarName(cached_variables, obj, output_vector)

			elif operator == 'distanceTo':
				if debug:
					writeSMTtoFile(smt_file_path, "distanceTo")

				other = operands[0]
				if not isinstance(other, Vector):
					other.encodeToSMT(smt_file_path, cached_variables, debug=debug)
				# y * y = (x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2)
				(other_x, other_y) = cached_variables[other]
				(x, y) = cached_variables[self]

				x1_x2 = smt_subtract(x, other_x)
				sq_x1_x2 = smt_multiply(x1_x2, x1_x2)
				y1_y2 = smt_subtract(y, other_y)
				sq_y1_y2 = smt_multiply(y1_y2, y1_y2)
				summation = smt_add(sq_x1_x2, sq_y1_y2)

				var_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'distance')
				sq_var_name = smt_multiply(var_name, var_name)
				smt_encoding = smt_assert("equal", sq_var_name, summation)
				writeSMTtoFile(smt_file_path, smt_encoding)
				return cacheVarName(cached_variables, obj, (var_name))

			elif operator == 'angleWith':
				if debug:
					writeSMTtoFile(smt_file_path, "angleWith")
				other = operands[0]
				(other_x, other_y) = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				(vec_x, vec_y) = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				smt_atan_other = "(arctan (div "+smt_divide(other_y, other_x)+")" 
				smt_atan_vec   = "(arctan (div "+smt_divide(vec_y, vec_x)+")" 
				subtraction = smt_subtract(smt_atan_other, smt_atan_vec)
				theta = normalizeAngle_SMT(subtraction)
				return cacheVarName(cached_variables, obj, (theta))

			elif operator == 'angleTo':
				if debug:
					writeSMTtoFile(smt_file_path, "angleTo")
				other = operands[0]
				(other_x, other_y) = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				(vec_x, vec_y) = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				dx = smt_assert("subtract", other_x, vec_x)
				dy = smt_assert("subtract", other_y, vec_y)
				smt_atan = "(arctan "+smt_divide(dy, dx)+")" 
				subtraction = smt_subtract(smt_atan, smt_divide('3.1416','2'))
				theta = normalizeAngle_SMT(subtraction)
				return cacheVarName(cached_variables, obj, (theta))

			elif operator == 'norm':
				if debug:
					writeSMTtoFile(smt_file_path, "norm")
				(vec_x, vec_y) = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				square_x = smt_multiply(vec_x, vec_x)
				square_y = smt_multiply(vec_y, vec_y)
				summation = smt_add(square_x, square_y)
				norm_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'vec_norm')
				sq_norm_var = smt_multiply(norm_var, norm_var)
				smt_encoding = smt_assert("equal", sq_norm_var, summation)
				writeSMTtoFile(smt_file_path, smt_encoding)
				return cacheVarName(cached_variables, obj, (norm_var))

			elif operator == 'normalized':
				if debug:
					writeSMTtoFile(smt_file_path, "normalized")
				(vec_x, vec_y) = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				square_x = smt_multiply(vec_x, vec_x)
				square_y = smt_multiply(vec_y, vec_y) 
				summation = smt_add(square_x, square_y)
				norm_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'vec_norm')
				sq_norm_var = "(* "+norm_var+" "+norm_var+")"
				norm_smt_encoding = smt_assert("equal", sq_norm_var, summation)
				x = smt_divide(vec_x, norm_var)
				y = smt_divide(vec_y, norm_var)
				x_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
				y_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')
				smt_x = smt_assert("equal", x_var, x)
				smt_y = smt_assert("equal", y_var, y)
				writeSMTtoFile(smt_file_path, norm_smt_encoding)
				writeSMTtoFile(smt_file_path, smt_x)
				writeSMTtoFile(smt_file_path, smt_y)
				return cacheVarName(cached_variables, obj, (x_var, y_var))

			elif operator == '__add__' or '__radd__':
				if debug:
					writeSMTtoFile(smt_file_path, "add or radd")
				other = operands[0]

				# variable can be a constant or Vector
				variable = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				self_vector = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				summation_vector = vector_operation_smt(self_vector, "add", variable)

				x_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
				y_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')

				(x, y) = vector_operation_smt((x_var, y_var), "equal", summation_vector)
				writeSMTtoFile(smt_file_path, smt_assert(None, x))
				writeSMTtoFile(smt_file_path, smt_assert(None, y))
				return cacheVarName(cached_variables, obj, self_vector)

			elif operator == '__sub__':
				if debug:
					writeSMTtoFile(smt_file_path, "subtract")
				other = operands[0]
				# variable can be a constant or Vector
				variable = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				self_vector = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				subtraction_vector = vector_operation_smt(self_vector, "subtract", variable)

				x_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
				y_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')

				(x, y) = vector_operation_smt((x_var, y_var), "equal", subtraction_vector)
				writeSMTtoFile(smt_file_path, smt_assert(None, x))
				writeSMTtoFile(smt_file_path, smt_assert(None, y))
				return cacheVarName(cached_variables, obj, (x,y))

			elif operator == '__rsub__':
				if debug:
					writeSMTtoFile(smt_file_path, "rsubtract")
				other = operands[0]
				variable = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				self_vector = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				subtraction_vector = vector_operation_smt(variable, "subtract", self_vector)

				x_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
				y_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')

				(x, y) = vector_operation_smt((x_var, y_var), "equal", subtraction_vector)
				writeSMTtoFile(smt_file_path, smt_assert(None, x))
				writeSMTtoFile(smt_file_path, smt_assert(None, y))
				return cacheVarName(cached_variables, obj, (x, y))

			elif operator == '__mul__' or '__rmul__':
				if debug:
					writeSMTtoFile(smt_file_path, "multiply or rmultiply")
				other = operands[0]
				scalar = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				(vec_x, vec_y) = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				mul_x = smt_multiply(scalar, vec_x)
				mul_y = smt_multiply(scalar, vec_y)
				x_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
				y_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')
				x_smt_encoding = smt_assert("equal", x_var, mul_x)
				y_smt_encoding = smt_assert("equal", y_var, mul_y)
				writeSMTtoFile(smt_file_path, x_smt_encoding)
				writeSMTtoFile(smt_file_path, y_smt_encoding)
				return cacheVarName(cached_variables, obj, (x_var, y_var))

			elif operator == '__truediv__':
				if debug:
					writeSMTtoFile(smt_file_path, "division")
				other = operands[0]
				scalar = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				(vec_x, vec_y) = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				div_x = smt_divide(scalar, vec_x)
				div_y = smt_divide(scalar, vec_y)
				x_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'x')
				y_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'y')
				x_smt_encoding = smt_assert("equal", x_var, div_x)
				y_smt_encoding = smt_assert("equal", y_var, div_y)
				writeSMTtoFile(smt_file_path, x_smt_encoding)
				writeSMTtoFile(smt_file_path, y_smt_encoding)
				return cacheVarName(cached_variables, obj, (x_var, y_var))

			elif operator == '__len__':
				if debug:
					writeSMTtoFile(smt_file_path, "length")
				length_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'vec_length')
				smt_encoding = smt_assert("equal", length_var, str(len(self.coordinates)))
				writeSMTtoFile(smt_file_path, smt_encoding)
				return cacheVarName(cached_variables, obj, (length_var))

			elif operator == '__getitem__':
				if debug:
					writeSMTtoFile(smt_file_path, "getitem")
				index = operands[0]
				index = checkAndEncodeSMT(smt_file_path, cached_variables, index)
				vec = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				element = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'vec_element')

				## TODO: Encode Array!
				smt_encoding = smt_assert("equal", element, vec[index])
				writeSMTtoFile(smt_file_path, smt_encoding)
				return cacheVarName(cached_variables, obj, (element))

			elif operator == '__eq__':
				if debug:
					writeSMTtoFile(smt_file_path, "equal")
				other = operands[0]
				(vec_x, vec_y) = checkAndEncodeSMT(smt_file_path, cached_variables, self)
				if isinstance(other, Vector):
					(other_x, other_y) = checkAndEncodeSMT(smt_file_path, cached_variables, other)
				elif isinstance(other, (list, tuple)):
					if len(other) == 2: 
						other_x = checkAndEncodeSMT(smt_file_path, cached_variables, other[0])
						other_y = checkAndEncodeSMT(smt_file_path, cached_variables, other[1])
					else:
						print("ERROR: COMPARING VECTOR TO LIST/TUPLE WITH LENGTH > or < 2 NotImplemented")
						raise NotImplementedError
				else:
					print("ERROR: COMPARING VECTOR TO OTHER THAN VECTOR, LIST, TUPLE NOT ALLOWED")
					raise NotImplementedError

				x_eq = smt_equal(vec_x, other_x)
				y_eq = smt_equal(vec_y, other_y)
				eq_smt = smt_and(x_eq, y_eq)
				eq_var = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], "eq_bool", class_type = "Bool")
				smt_encoding = smt_assert("equal", eq_var, eq_smt)

				writeSMTtoFile(smt_file_path, smt_encoding)
				return cacheVarName(cached_variables, obj, (eq_var))

		else:
			print("ERROR: UNIDENTIFIED OPERATOR DETECTED IN VECTOR()")
			raise NotImplementedError

		return None

	def toVector(self) -> Vector:
		return self

	def sampleGiven(self, value):
		return Vector(*(value[coord] for coord in self.coordinates))

	def evaluateInner(self, context):
		return Vector(*(valueInContext(coord, context) for coord in self.coordinates))

	@vectorOperator
	def rotatedBy(self, angle) -> Vector:
		"""Return a vector equal to this one rotated counterclockwise by the given angle."""
		x, y = self.x, self.y
		c, s = cos(angle), sin(angle)
		return Vector((c * x) - (s * y), (s * x) + (c * y))

	@vectorOperator
	def offsetRotated(self, heading, offset) -> Vector:
		ro = offset.rotatedBy(heading)
		return self + ro

	@vectorOperator
	def offsetRadially(self, radius, heading) -> Vector:
		return self.offsetRotated(heading, Vector(0, radius))

	@scalarOperator
	def distanceTo(self, other) -> float:
		if not isinstance(other, Vector):
			return other.distanceTo(self)
		dx, dy = other.toVector() - self
		return math.hypot(dx, dy)

	@scalarOperator
	def angleTo(self, other) -> float:
		dx, dy = other.toVector() - self
		return normalizeAngle(math.atan2(dy, dx) - (math.pi / 2))

	@scalarOperator
	def angleWith(self, other) -> float:
		"""Compute the signed angle between self and other.

		The angle is positive if other is counterclockwise of self (considering
		the smallest possible rotation to align them).
		"""
		x, y = self.x, self.y
		ox, oy = other.x, other.y
		return normalizeAngle(math.atan2(oy, ox) - math.atan2(y, x))

	@scalarOperator
	def norm(self) -> float:
		return math.hypot(*self.coordinates)

	@vectorOperator
	def normalized(self) -> Vector:
		l = math.hypot(*self.coordinates)
		return Vector(*(coord/l for coord in self.coordinates))

	@vectorOperator
	def __add__(self, other) -> Vector:
		return Vector(self[0] + other[0], self[1] + other[1])

	@vectorOperator
	def __radd__(self, other) -> Vector:
		return Vector(self[0] + other[0], self[1] + other[1])

	@vectorOperator
	def __sub__(self, other) -> Vector:
		return Vector(self[0] - other[0], self[1] - other[1])

	@vectorOperator
	def __rsub__(self, other) -> Vector:
		return Vector(other[0] - self[0], other[1] - self[1])

	@vectorOperator
	def __mul__(self, other) -> Vector:
		return Vector(*(coord*other for coord in self.coordinates))

	def __rmul__(self, other) -> Vector:
		return self.__mul__(other)

	@vectorOperator
	def __truediv__(self, other) -> Vector:
		return Vector(*(coord/other for coord in self.coordinates))

	def __len__(self):
		return len(self.coordinates)

	def __getitem__(self, index):
		return self.coordinates[index]

	def __repr__(self):
		return f'({self.x} @ {self.y})'

	def __eq__(self, other):
		if isinstance(other, Vector):
			return other.coordinates == self.coordinates
		elif isinstance(other, (tuple, list)):
			return tuple(other) == self.coordinates
		else:
			return NotImplemented

	def __hash__(self):
		return hash(self.coordinates)

VectorDistribution.defaultValueType = Vector

class OrientedVector(Vector):
	def __init__(self, x, y, heading):
		super().__init__(x, y)
		self.heading = heading

	@staticmethod
	@distributionFunction
	def make(position, heading) -> OrientedVector:
		return OrientedVector(*position, heading)

	def toHeading(self):
		return self.heading

	def __eq__(self, other):
		if type(other) is not OrientedVector:
			return NotImplemented
		return (other.coordinates == self.coordinates
		    and other.heading == self.heading)

	def __hash__(self):
		return hash((self.coordinates, self.heading))

class VectorField:
	"""A vector field, providing a heading at every point.

	Arguments:
		name (str): name for debugging.
		value: function computing the heading at the given `Vector`.
		minSteps (int): Minimum number of steps for `followFrom`; default 4.
		defaultStepSize (float): Default step size for `followFrom`; default 5.
	"""
	def __init__(self, name, value, minSteps=4, defaultStepSize=5):
		self.name = name
		self.value = value
		self.valueType = float
		self.minSteps = minSteps
		self.defaultStepSize = defaultStepSize

	def encodeToSMT(self, smt_file_path, cached_variables, obj, debug=False):
		if debug:
			writeSMTtoFile(smt_file_path, "VectorField")
			writeSMTtoFile(smt_file_path, "VectorField obj = "+str(obj))
			writeSMTtoFile(smt_file_path, "VectorField type(obj) = "+str(type(obj)))

		if not isinstance(obj, Samplable):
			obj = self

		if obj in cached_variables.keys():
			return cached_variables[obj]

		if isinstance(obj, VectorMethodDistribution) or isinstance(obj, MethodDistribution):
			if debug:
				writeSMTtoFile(smt_file_path, "in VectorField, obj is VectorMethodDistribution or MethodDistribution")
			method = obj.method
			arguments = obj.arguments
		else:
			print("NotImplemented")
			raise NotImplementedError

		var_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'vectorField')

		if method == VectorField.__getitem__:
			""" 
			TODOs : need to handle cases when pos is a distribution
			In such case, this should return an interval of heading instead
			"""
			pos = obj.arguments[0]._conditioned
			heading = self.__getitem__(pos)
			smt_encoding = smt_assert("equal", var_name, str(heading))
			writeSMTtoFile(smt_file_path, smt_encoding)
			if debug:
				writeSMTtoFile(smt_file_path, "in VectorField, method = __getitem__")
				writeSMTtoFile(smt_file_path, "VectorField heading = "+ str(heading))
			return cacheVarName(cached_variables, obj, (var_name))

		# TODOs: followFrom 
		
		return var_name

	@distributionMethod
	def __getitem__(self, pos) -> float:
		return self.value(pos)

	@vectorDistributionMethod
	def followFrom(self, pos, dist, steps=None, stepSize=None):
		"""Follow the field from a point for a given distance.

		Uses the forward Euler approximation, covering the given distance with
		equal-size steps. The number of steps can be given manually, or computed
		automatically from a desired step size.

		Arguments:
			pos (`Vector`): point to start from.
			dist (float): distance to travel.
			steps (int): number of steps to take, or :obj:`None` to compute the number of
				steps based on the distance (default :obj:`None`).
			stepSize (float): length used to compute how many steps to take, or
				:obj:`None` to use the field's default step size.
		"""
		if steps is None:
			steps = self.minSteps
			stepSize = self.defaultStepSize if stepSize is None else stepSize
			if stepSize is not None:
				steps = max(steps, math.ceil(dist / stepSize))

		step = dist / steps
		for i in range(steps):
			pos = pos.offsetRadially(step, self[pos])
		return pos

	@staticmethod
	def forUnionOf(regions):
		"""Creates a `PiecewiseVectorField` from the union of the given regions.

		If none of the regions have an orientation, returns :obj:`None` instead.
		"""
		if any(reg.orientation for reg in regions):
			return PiecewiseVectorField('Union', regions)
		else:
			return None

	def __str__(self):
		return f'<{type(self).__name__} {self.name}>'

class PolygonalVectorField(VectorField):
	"""A piecewise-constant vector field defined over polygonal cells.

	Arguments:
		name (str): name for debugging.
		cells: a sequence of cells, with each cell being a pair consisting of a Shapely
			geometry and a heading. If the heading is :obj:`None`, we call the given
			**headingFunction** for points in the cell instead.
		headingFunction: function computing the heading for points in cells without
			specified headings, if any (default :obj:`None`).
		defaultHeading: heading for points not contained in any cell (default
			:obj:`None`, meaning reject such points).
	"""
	def __init__(self, name, cells, headingFunction=None, defaultHeading=None):
		self.cells = tuple(cells)
		if headingFunction is None and defaultHeading is not None:
			headingFunction = lambda pos: defaultHeading
		self.headingFunction = headingFunction
		for cell, heading in self.cells:
			if heading is None and headingFunction is None and defaultHeading is None:
				raise RuntimeError(f'missing heading for cell of PolygonalVectorField')
		self.defaultHeading = defaultHeading
		super().__init__(name, self.valueAt)

	def valueAt(self, pos):
		point = shapely.geometry.Point(pos)
		for cell, heading in self.cells:
			if cell.intersects(point):
				return self.headingFunction(pos) if heading is None else heading
		if self.defaultHeading is not None:
			return self.defaultHeading
		raise RejectionException(f'evaluated PolygonalVectorField at undefined point')

class PiecewiseVectorField(VectorField):
	"""A vector field defined by patching together several regions.

	The heading at a point is determined by checking each region in turn to see if it has
	an orientation and contains the point, returning the corresponding heading if so. If
	we get through all the regions, then we return the **defaultHeading**, if any, and
	otherwise reject the scene.

	Arguments:
		name (str): name for debugging.
		regions (sequence of `Region` objects): the regions making up the field.
		defaultHeading (float): the heading for points not in any region with an
			orientation (default :obj:`None`, meaning reject such points).
	"""
	def __init__(self, name, regions, defaultHeading=None):
		self.regions = tuple(regions)
		self.defaultHeading = defaultHeading
		super().__init__(name, self.valueAt)

	def valueAt(self, point):
		for region in self.regions:
			if region.containsPoint(point) and region.orientation:
				return region.orientation[point]
		if self.defaultHeading is not None:
			return self.defaultHeading
		raise RejectionException(f'evaluated PiecewiseVectorField at undefined point')








