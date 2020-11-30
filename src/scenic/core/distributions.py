"""Objects representing distributions that can be sampled from."""

import collections
import itertools
import random
import math
import typing
import warnings

import numpy
import wrapt

from scenic.core.lazy_eval import (LazilyEvaluable,
    requiredProperties, needsLazyEvaluation, valueInContext, makeDelayedFunctionCall)
from scenic.core.utils import argsToString, areEquivalent, cached, sqrt2
from scenic.core.errors import RuntimeParseError

def smt_add(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(+ "+var1+" "+var2+")"

def smt_subtract(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(- "+var1+" "+var2+")"

def smt_multiply(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(* "+var1+" "+var2+")"

def smt_divide(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(div "+var1+" "+var2+")"

def smt_and(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(and "+var1+" "+var2+")"

def smt_or(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(or "+var1+" "+var2+")"

def smt_equal(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(= "+var1+" "+var2+")"

def smt_mod(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(mod "+var1+" "+var2+")"

def smt_lessThan(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(< "+var1+" "+var2+")"

def smt_lessThanEq(var1, var2):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str))
	return "(<= "+var1+" "+var2+")"

def smt_ite(predicate, output1, output2):
	assert(isinstance(predicate, str))
	assert(isinstance(output1, str))
	assert(isinstance(output2, str))
	return "(ite "+predicate+" "+output1+" "+output2+")"

def smt_assert(operation_type, var1, var2=None):
	assert(isinstance(var1, str))
	assert(isinstance(var2, str) or var2==None)

	if operation_type == "add":
		op_encoding = smt_add(var1, var2)
	elif operation_type == "subtract":
		op_encoding = smt_subtract(var1, var2)
	elif operation_type == "multiply":
		op_encoding = smt_multiply(var1, var2)
	elif operation_type == "divide":
		op_encoding = smt_divide(var1, var2)
	elif operation_type == "equal":
		op_encoding = smt_equal(var1, var2)
	elif operation_type == "and":
		op_encoding = smt_and(var1, var2)
	elif operation_type == "mod":
		op_encoding = smt_mod(var1, var2)
	elif operation_type == "<=":
		op_encoding = smt_lessThanEq(var1, var2)
	elif operation_type == "<":
		op_encoding = smt_lessThan(var1, var2)
	elif operation_type == None:
		op_encoding = var1
	else:
		print("SMT_ASSERT() UNIDENTIFIED OPERATION")
		raise NotImplementedError

	return "(assert "+ op_encoding +")"

def vector_operation_smt(vector1, operation, vector2):
	""" vector1, vector2 := (x, y) from triangle := shapely.geometry.polygon.Polygon
	x, y are floats"""
	
	x1 = str(vector1[0])
	y1 = str(vector1[1])

	if isinstance(vector2, tuple):
		x2 = str(vector2[0])
		y2 = str(vector2[1])
	else: # scalar operation to a vector case
		assert(isinstance(vector2, str))
		x2 = y2 = vector2

	if operation == "add":	
		x = smt_add(x1, x2)
		y = smt_add(y1, y2)
	elif operation == "subtract":
		x = smt_subtract(x1, x2)
		y = smt_subtract(y1, y2)
	elif operation == "multiply":
		x = smt_multiply(x1, x2)
		y = smt_multiply(y1, y2) 
	elif operation == "equal":
		x = smt_equal(x1, x2)
		y = smt_equal(y1, y2)
	else:
		print("vector_operation_smt() UNIDENTIFIED OPERATION")
		raise NotImplementedError

	return (x, y)

def normalizeAngle_SMT(original_angle):
	angle = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'angle')
	ite1 = smt_assert("equal", angle , smt_ite(smt_lessThan("0", original_angle), \
		smt_mod(original_angle, "6.2832"), original_angle))
	ite2 = smt_assert("equal", angle , smt_ite(smt_lessThan(original_angle, "0"), \
		smt_mod(original_angle, "-6.2832"), original_angle))

	writeSMTtoFile(smt_file_path, ite1)
	writeSMTtoFile(smt_file_path, ite2)

	theta = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'theta')
	theta_encoding = smt_assert("equal", theta, angle)
	angleTo_encoding1 = smt_assert("equal", theta, smt_ite(smt_lessThanEq("3.1416",angle), smt_subtract(angle,"6.2832"), angle))
	angleTo_encoding2 = smt_assert("equal", theta, smt_ite(smt_lessThanEq(angle, "-3.1416"), smt_add(angle,"6.2832"), angle))

	writeSMTtoFile(smt_file_path, theta_encoding)
	writeSMTtoFile(smt_file_path, angleTo_encoding1)
	writeSMTtoFile(smt_file_path, angleTo_encoding2)
	return theta

def findVariableName(cached_variables, smt_file_path, variable_list, class_name, class_type=None):
	""" for smt encoding, to avoid duplicate naming, add a number at then end for differentiation 
		returns the next available name """

	cached_var = [variable for variable in variable_list if variable.startswith(class_name)]
	var_name = class_name+str(len(cached_var)+1) 

	if class_type == None:
		declare_var= "(declare-fun "+var_name+" () Real)\n"
	else:
		declare_var= "(declare-fun "+var_name+" () "+class_type+"\n)"

	writeSMTtoFile(smt_file_path, declare_var)
	cached_variables['variables'].append(var_name)
	return var_name

def checkAndEncodeSMT(smt_file_path, cached_variables, obj, debug=False):
	if isinstance(obj, Samplable):
		# print("checkAndEncodeSMT obj: ", obj)
		print("obj type: ", type(obj))
		return obj.encodeToSMT(smt_file_path, cached_variables, debug=debug)
	elif isinstance(obj, int) or isinstance(obj, float):
		return str(obj)
	elif isinstance(obj, str):
		# this covers case in regions.py, PointInRegionDist's encodeToSMT where
		# a Vector is instantiated with string variable names
		return obj
	else:
		print("checkAndEncodeSMT UNIDENTIFIED CASE DETECTED")
		raise NotImplementedError
	return None

def writeSMTtoFile(smt_file_path, smt_encoding):
	if isinstance(smt_encoding, str):
		with open(smt_file_path, "a+") as smt_file:
			smt_file.write(smt_encoding+"\n")

	elif isinstance(smt_encoding, tuple) and len(smt_encoding) == 2:
		with open(smt_file_path, "a+") as smt_file:
			smt_file.write(smt_encoding[0]+"\n")
			smt_file.write(smt_encoding[1]+"\n")
	else :
		raise NotImplementedError

	return None

def cacheVarName(cached_variables, obj, var_names):
	""" caches variable names.
	type : var_names := tuple """

	# if obj in cached_variables.keys():
	# 	return cached_variables[obj]
	if not isinstance(var_names, tuple):
		var_names = (var_names)

	key_exists = False
	for key in list(cached_variables.keys()):
		if obj is key:
			key_exists = True

	if key_exists:
		return cached_variables[obj]

	for var in var_names:
		if var not in cached_variables['variables']:
			cached_variables['variables'].append(var)

	if len(var_names) == 1:
		var_names = var_names[0]
	cached_variables[obj] = var_names
	# cached_variables.update({obj: var_names})
	return var_names

def isNotConditioned(obj):
	return obj == obj._conditioned

def dependencies(thing):
	"""Dependencies which must be sampled before this value."""
	return getattr(thing, '_dependencies', ())

def needsSampling(thing):
	"""Whether this value requires sampling."""
	return isinstance(thing, Distribution) or dependencies(thing)

def supportInterval(thing):
	"""Lower and upper bounds on this value, if known."""
	if hasattr(thing, 'supportInterval'):
		return thing.supportInterval()
	elif isinstance(thing, (int, float)):
		return thing, thing
	else:
		return None, None

def underlyingFunction(thing):
	"""Original function underlying a distribution wrapper."""
	func = getattr(thing, '__wrapped__', thing)
	return getattr(func, '__func__', func)

def canUnpackDistributions(func):
	"""Whether the function supports iterable unpacking of distributions."""
	return getattr(func, '_canUnpackDistributions', False)

def unpacksDistributions(func):
	"""Decorator indicating the function supports iterable unpacking of distributions."""
	func._canUnpackDistributions = True
	return func

class RejectionException(Exception):
	"""Exception used to signal that the sample currently being generated must be rejected."""
	pass

## Abstract distributions

class DefaultIdentityDict:
	"""Dictionary which is the identity map by default.

	The map works on all objects, even unhashable ones, but doesn't support all
	of the standard mapping operations.
	"""
	def __init__(self):
		self.storage = {}

	def __getitem__(self, key):
		return self.storage.get(id(key), key)

	def __setitem__(self, key, value):
		self.storage[id(key)] = value

	def __contains__(self, key):
		return id(key) in self.storage

class Samplable(LazilyEvaluable):
	"""Abstract class for values which can be sampled, possibly depending on other values.

	Samplables may specify a proxy object 'self._conditioned' which must have the same
	distribution as the original after conditioning on the scenario's requirements. This
	allows transparent conditioning without modifying Samplable fields of immutable objects.
	"""
	def __init__(self, dependencies):
		deps = []
		props = set()
		for dep in dependencies:
			if needsSampling(dep) or needsLazyEvaluation(dep):
				deps.append(dep)
				props.update(requiredProperties(dep))
		super().__init__(props)
		self._dependencies = tuple(deps)	# fixed order for reproducibility
		self._conditioned = self	# version (partially) conditioned on requirements

	@staticmethod
	def sampleAll(quantities):
		"""Sample all the given Samplables, which may have dependencies in common.

		Reproducibility note: the order in which the quantities are given can affect the
		order in which calls to random are made, affecting the final result.
		"""
		subsamples = DefaultIdentityDict()
		for q in quantities:
			if q not in subsamples:
				subsamples[q] = q.sample(subsamples) if isinstance(q, Samplable) else q
		return subsamples

	def sample(self, subsamples=None):
		"""Sample this value, optionally given some values already sampled."""
		if subsamples is None:
			subsamples = DefaultIdentityDict()
		for child in self._conditioned._dependencies:
			if child not in subsamples:
				subsamples[child] = child.sample(subsamples)
		return self._conditioned.sampleGiven(subsamples)

	def translateToSMT(parent, subsamples=None):
		if subsamples in None:
			subsamples = DefaultIdentityDict()
		for child in parent._conditioned._dependencies:
			if child not in subsamples:
				subsamples[child] = translateToSMT(child, subsamples)
		return parent._conditioned.sampleGiven(subsamples)

	def sampleGiven(self, value):
		"""Sample this value, given values for all its dependencies.

		The default implementation simply returns a dictionary of dependency values.
		Subclasses must override this method to specify how actual sampling is done.
		"""
		return DefaultIdentityDict({ dep: value[dep] for dep in self._dependencies })

	def conditionTo(self, value):
		"""Condition this value to another value with the same conditional distribution."""
		assert isinstance(value, Samplable)
		self._conditioned = value

	def evaluateIn(self, context):
		"""See LazilyEvaluable.evaluateIn."""
		value = super().evaluateIn(context)
		# Check that all dependencies have been evaluated
		assert all(not needsLazyEvaluation(dep) for dep in value._dependencies)
		return value

	def dependencyTree(self):
		"""Debugging method to print the dependency tree of a Samplable."""
		l = [str(self)]
		for dep in dependencies(self):
			for line in dep.dependencyTree():
				l.append('  ' + line)
		return l

class Distribution(Samplable):
	"""Abstract class for distributions."""

	defaultValueType = object

	def __new__(cls, *args, **kwargs):
		dist = super().__new__(cls)
		# at runtime, return a sample from the distribution immediately
		import scenic.syntax.veneer as veneer
		if veneer.simulationInProgress():
			dist.__init__(*args, **kwargs)
			return dist.sample()
		else:
			return dist

	def __init__(self, *dependencies, valueType=None):
		super().__init__(dependencies)
		if valueType is None:
			valueType = self.defaultValueType
		self.valueType = valueType

	def clone(self):
		"""Construct an independent copy of this Distribution."""
		raise NotImplementedError('clone() not supported by this distribution')

	@property
	@cached
	def isPrimitive(self):
		"""Whether this is a primitive Distribution."""
		try:
			self.clone()
			return True
		except NotImplementedError:
			return False

	def bucket(self, buckets=None):
		"""Construct a bucketed approximation of this Distribution.

		This function factors a given Distribution into a discrete distribution over
		buckets together with a distribution for each bucket. The argument *buckets*
		controls how many buckets the domain of the original Distribution is split into.
		Since the result is an independent distribution, the original must support
		clone().
		"""
		raise NotImplementedError('bucket() not supported by this distribution')

	def supportInterval(self):
		"""Compute lower and upper bounds on the value of this Distribution."""
		return None, None

	def __getattr__(self, name):
		if name.startswith('__') and name.endswith('__'):	# ignore special attributes
			return object.__getattribute__(self, name)
		return AttributeDistribution(name, self)

	def __call__(self, *args):
		return OperatorDistribution('__call__', self, args)

	def __iter__(self):
		raise TypeError(f'distribution {self} is not iterable')

	def _comparisonError(self, other):
		raise RuntimeParseError('random values cannot be compared '
		                        '(and control flow cannot depend on them)')

	__lt__ = _comparisonError
	__le__ = _comparisonError
	__gt__ = _comparisonError
	__ge__ = _comparisonError
	__eq__ = _comparisonError
	__ne__ = _comparisonError

	def __hash__(self):		# need to explicitly define since we overrode __eq__
		return id(self)

	def __len__(self):
		raise RuntimeParseError('cannot take the len of a random value')

	def __bool__(self):
		raise RuntimeParseError('control flow cannot depend on a random value')

## Derived distributions

class CustomDistribution(Distribution):
	"""Distribution with a custom sampler given by an arbitrary function"""
	def __init__(self, sampler, *dependencies, name='CustomDistribution', evaluator=None):
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

	def isEquivalentTo(self, other):
		if not type(other) is CustomDistribution:
			return False
		return (self.sampler == other.sampler
			and self.name == other.name
			and self.evaluator == other.evaluator)

	def __str__(self):
		return f'{self.name}{argsToString(self.dependencies)}'

class TupleDistribution(Distribution, collections.abc.Sequence):
	"""Distributions over tuples (or namedtuples, or lists)."""
	def __init__(self, *coordinates, builder=tuple):
		super().__init__(*coordinates)
		self.coordinates = coordinates
		self.builder = builder

	def __len__(self):
		return len(self.coordinates)

	def __getitem__(self, index):
		return self.coordinates[index]

	def __iter__(self):
		yield from self.coordinates

	def sampleGiven(self, value):
		return self.builder(value[coordinate] for coordinate in self.coordinates)

	def evaluateInner(self, context):
		coordinates = (valueInContext(coord, context) for coord in self.coordinates)
		return TupleDistribution(*coordinates, builder=self.builder)

	def isEquivalentTo(self, other):
		if not type(other) is TupleDistribution:
			return False
		return (areEquivalent(self.coordinates, other.coordinates)
			and self.builder == other.builder)

	def __str__(self):
		coords = ', '.join(str(c) for c in self.coordinates)
		return f'({coords}, builder={self.builder})'

def toDistribution(val):
	"""Wrap Python data types with Distributions, if necessary.

	For example, tuples containing Samplables need to be converted into TupleDistributions
	in order to keep track of dependencies properly.
	"""
	if isinstance(val, (tuple, list)):
		coords = [toDistribution(c) for c in val]
		if any(needsSampling(c) or needsLazyEvaluation(c) for c in coords):
			if isinstance(val, tuple) and hasattr(val, '_fields'):		# namedtuple
				builder = type(val)._make
			else:
				builder = type(val)
			return TupleDistribution(*coords, builder=builder)
	return val

class FunctionDistribution(Distribution):
	"""Distribution resulting from passing distributions to a function"""
	def __init__(self, func, args, kwargs, support=None, valueType=None):
		args = tuple(toDistribution(arg) for arg in args)
		kwargs = { name: toDistribution(arg) for name, arg in kwargs.items() }
		if valueType is None:
			valueType = typing.get_type_hints(func).get('return')
		super().__init__(*args, *kwargs.values(), valueType=valueType)
		self.function = func
		self.arguments = args
		self.kwargs = kwargs
		self.support = support

	def conditionforSMT(self, condition, conditioned_bool):
		for arg in self.arguments:
			if isinstance(arg, Samplable) and isNotConditioned(arg):
				arg.conditionforSMT(condition, conditioned_bool)
		for kwarg in self.kwargs:
			if isinstance(kwarg, Samplable) and isNotConditioned(kwarg):
				kwarg.conditionforSMT(condition, conditioned_bool)
		for support in self.support:
			if isinstance(support, Samplable) and isNotConditioned(support):
				support.conditionforSMT(condition, conditioned_bool)
		return None

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		"""to avoid duplicate variable names, check for variable existence in cached_variables dict:
		   cached_variables : key = obj, value = variable_name / key = 'variables', value = list(cached variables so far)
		   encodeToSMT() must return 'cached_variables' dictionary
		"""
		# import scenic.core.geometry as geometry
		raise NotImplementedError

		if debug:
			writeSMTtoFile(smt_file_path, "FunctionDistribution")

		if self in cached_variables.keys():
			if debug:
				writeSMTtoFile(smt_file_path, "FunctionDistribution already exists in cached_variables dict")
			return cached_variables[obj]

		for arg in self.arguments:
			if isinstance(arg, Samplable):
				arg.encodeToSMT(smt_file_path, cached_variables, debug=debug)
		for kwarg in self.kwargs:
			if isinstance(kwarg, Samplable):
				kwarg.encodeToSMT(smt_file_path, cached_variables, debug=debug)

		# cached_variables = self.object.encodeToSMT(smt_file_path, cached_variables, self)

		return cached_variables

	def sampleGiven(self, value):
		args = []
		for arg in self.arguments:
			if isinstance(arg, StarredDistribution):
				val = value[arg]
				try:
					iter(val)
				except TypeError:	# TODO improve backtrace
					raise TypeError(f"'{type(val).__name__}' object on line {arg.lineno} "
					                "is not iterable") from None
				args.extend(val)
			else:
				args.append(value[arg])
		kwargs = { name: value[arg] for name, arg in self.kwargs.items() }
		return self.function(*args, **kwargs)

	def evaluateInner(self, context):
		function = valueInContext(self.function, context)
		arguments = tuple(valueInContext(arg, context) for arg in self.arguments)
		kwargs = { name: valueInContext(arg, context) for name, arg in self.kwargs.items() }
		return FunctionDistribution(function, arguments, kwargs)

	def supportInterval(self):
		if self.support is None:
			return None, None
		subsupports = (supportInterval(arg) for arg in self.arguments)
		kwss = { name: supportInterval(arg) for name, arg in self.kwargs.items() }
		return self.support(*subsupports, **kwss)

	def isEquivalentTo(self, other):
		if not type(other) is FunctionDistribution:
			return False
		return (self.function == other.function
			and areEquivalent(self.arguments, other.arguments)
			and areEquivalent(self.kwargs, other.kwargs)
			and self.support == other.support)

	def __str__(self):
		args = argsToString(itertools.chain(self.arguments, self.kwargs.items()))
		return f'{self.function.__name__}{args}'

def distributionFunction(wrapped=None, *, support=None, valueType=None):
	"""Decorator for wrapping a function so that it can take distributions as arguments."""
	if wrapped is None:		# written without arguments as @distributionFunction
		return lambda wrapped: distributionFunction(wrapped,
		                                            support=support, valueType=valueType)

	@unpacksDistributions
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		def helper(*args, **kwargs):
			args = tuple(toDistribution(arg) for arg in args)
			kwargs = { name: toDistribution(arg) for name, arg in kwargs.items() }
			if any(needsSampling(arg) for arg in itertools.chain(args, kwargs.values())):
				return FunctionDistribution(wrapped, args, kwargs, support, valueType)
			elif any(needsLazyEvaluation(arg)
			         for arg in itertools.chain(args, kwargs.values())):
				# recursively call this helper (not the original function), since the
				# delayed arguments may evaluate to distributions, in which case we'll
				# have to make a FunctionDistribution
				return makeDelayedFunctionCall(helper, args, kwargs)
			else:
				return wrapped(*args, **kwargs)
		return helper(*args, **kwargs)
	return wrapper(wrapped)

def monotonicDistributionFunction(method, valueType=None):
	"""Like distributionFunction, but additionally specifies that the function is monotonic."""
	def support(*subsupports, **kwss):
		mins, maxes = zip(*subsupports)
		kwmins = { name: interval[0] for name, interval in kwss.items() }
		kwmaxes = { name: interval[1] for name, interval in kwss.items() }
		l = None if None in mins or None in kwmins else method(*mins, **kwmins)
		r = None if None in maxes or None in kwmaxes else method(*maxes, **kwmaxes)
		return l, r
	return distributionFunction(method, support=support, valueType=valueType)

class StarredDistribution(Distribution):
	"""A placeholder for the iterable unpacking operator * applied to a distribution."""
	def __init__(self, value, lineno):
		assert isinstance(value, Distribution)
		self.value = value
		self.lineno = lineno	# for error handling when unpacking fails
		super().__init__(value, valueType=value.valueType)

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		raise NotImplementedError

	def conditionforSMT(self, condition, conditioned_bool):
		raise NotImplementedError

	def sampleGiven(self, value):
		return value[self.value]

	def evaluateInner(self, context):
		return StarredDistribution(valueInContext(self.value, context))

	def __str__(self):
		return f'*{self.value}'

class MethodDistribution(Distribution):
	"""Distribution resulting from passing distributions to a method of a fixed object"""
	def __init__(self, method, obj, args, kwargs, valueType=None):
		args = tuple(toDistribution(arg) for arg in args)
		kwargs = { name: toDistribution(arg) for name, arg in kwargs.items() }
		if valueType is None:
			valueType = typing.get_type_hints(method).get('return')
		super().__init__(*args, *kwargs.values(), valueType=valueType)
		self.method = method
		self.object = obj
		self.arguments = args
		self.kwargs = kwargs

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		"""to avoid duplicate variable names, check for variable existence in cached_variables dict:
		   cached_variables : key = obj, value = variable_name / key = 'variables', value = list(cached variables so far)
		   encodeToSMT() must return 'cached_variables' dictionary
		"""
		# import scenic.core.geometry as geometry
		if debug:
			writeSMTtoFile(smt_file_path, "MethodDistribution")
			writeSMTtoFile(smt_file_path, "method: "+str(self.method))
			writeSMTtoFile(smt_file_path, "type(method): "+str(type(self.method)))
			# writeSMTtoFile(smt_file_path, "object: "+str(self.object))
			writeSMTtoFile(smt_file_path, "type(object): "+str(type(self.object)))
			# writeSMTtoFile(smt_file_path, "arguments: "+str(self.arguments))
			for arg in self.arguments:
				writeSMTtoFile(smt_file_path, "type(argument): "+str(type(arg)))
			writeSMTtoFile(smt_file_path, "self.kwargs: "+str(self.kwargs))

		if self in cached_variables.keys():
			if debug:
				writeSMTtoFile(smt_file_path, "MethodDistribution already exists in cached_variables dict")
			return cached_variables[self]
		
		for arg in self.arguments:
			if isinstance(arg, Samplable):
				arg.encodeToSMT(smt_file_path, cached_variables, debug=debug)
		
		for kwarg in self.kwargs:
			if isinstance(kwarg, Samplable):
				kwarg.encodeToSMT(smt_file_path, cached_variables, debug=debug)

		# create cached_variables[self]
		output = self.object.encodeToSMT(smt_file_path, cached_variables, self, debug=debug)
		return cacheVarName(cached_variables, self, output)

	def conditionforSMT(self, condition, conditioned_bool):
		if isinstance(self.object, Samplable) and isNotConditioned(self.object):
			self.object.conditionforSMT(condition, conditioned_bool)
		for arg in self.arguments:
			if isinstance(arg, Samplable) and isNotConditioned(arg):
				arg.conditionforSMT(condition, conditioned_bool)
		for kwarg in self.kwargs:
			if isinstance(kwarg, Samplable) and isNotConditioned(kwarg):
				kwarg.conditionforSMT(condition, conditioned_bool)
		return None

	def sampleGiven(self, value):
		args = []
		for arg in self.arguments:
			if isinstance(arg, StarredDistribution):
				args.extend(value[arg.value])
			else:
				args.append(value[arg])
		kwargs = { name: value[arg] for name, arg in self.kwargs.items() }
		return self.method(self.object, *args, **kwargs)

	def evaluateInner(self, context):
		obj = valueInContext(self.object, context)
		arguments = tuple(valueInContext(arg, context) for arg in self.arguments)
		kwargs = { name: valueInContext(arg, context) for name, arg in self.kwargs.items() }
		return MethodDistribution(self.method, obj, arguments, kwargs)

	def isEquivalentTo(self, other):
		if not type(other) is MethodDistribution:
			return False
		return (self.method == other.method
			and areEquivalent(self.object, other.object)
			and areEquivalent(self.arguments, other.arguments)
			and areEquivalent(self.kwargs, other.kwargs))

	def __str__(self):
		args = argsToString(itertools.chain(self.arguments, self.kwargs.items()))
		return f'{self.object}.{self.method.__name__}{args}'

def distributionMethod(method):
	"""Decorator for wrapping a method so that it can take distributions as arguments."""
	@unpacksDistributions
	@wrapt.decorator
	def wrapper(wrapped, instance, args, kwargs):
		def helper(*args, **kwargs):
			args = tuple(toDistribution(arg) for arg in args)
			kwargs = { name: toDistribution(arg) for name, arg in kwargs.items() }
			if any(needsSampling(arg) for arg in itertools.chain(args, kwargs.values())):
				return MethodDistribution(method, instance, args, kwargs)
			elif any(needsLazyEvaluation(arg)
			         for arg in itertools.chain(args, kwargs.values())):
				# see analogous comment in distributionFunction
				return makeDelayedFunctionCall(helper, args, kwargs)
			else:
				return wrapped(*args, **kwargs)
		return helper(*args, **kwargs)
	return wrapper(method)

class AttributeDistribution(Distribution):
	"""Distribution resulting from accessing an attribute of a distribution"""
	def __init__(self, attribute, obj):
		super().__init__(obj)
		self.attribute = attribute
		self.object = obj

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		if debug:
			writeSMTtoFile(smt_file_path, "AttributeDistribution")
			writeSMTtoFile(smt_file_path, "attribute: " + str(self.attribute))
			writeSMTtoFile(smt_file_path, "type(attribute): " + str(type(self.attribute)))
			# writeSMTtoFile(smt_file_path, "object: " + str(self.object))
			writeSMTtoFile(smt_file_path, "type(object): " + str(type(self.object)))

		if self in cached_variables.keys():
			if debug:
				writeSMTtoFile(smt_file_path, "AttributeDistribution exists in cached_variables dict")
			return cached_variables[self]

		import scenic.core.vectors as vectors
		import scenic.core.type_support as type_support
		if debug:
			print("AttributeDistribution's type(object): ", type(self.object))


		if isinstance(self.object, vectors.VectorOperatorDistribution):
			(x,y) = self.object.encodeToSMT(smt_file_path, cached_variables, debug = debug)
			if self.attribute == 'x':
				return cacheVarName(cached_variables, self, x)
			elif self.attribute == 'y':
				return cacheVarName(cached_variables, self, y)
			else:
				raise NotImplementedError

		elif isinstance(self.object, type_support.TypecheckedDistribution):
			distribution = self.object.dist
			if debug:
				writeSMTtoFile(smt_file_path, "distribution: " + str(distribution))
				writeSMTtoFile(smt_file_path, "type(distribution): " + str(type(distribution)))

			output = distribution.encodeToSMT(smt_file_path, cached_variables, debug=debug)
			if self.attribute == 'intersect':
				return cacheVarName(cached_variables, self, output)
			else:
				raise NotImplementedError

		elif isinstance(self.object, Options):
			output = self.object.encodeToSMT(smt_file_path, cached_variables, debug=debug)
			return cacheVarName(cached_variables, self, output)

		else:
			print("AttributeDistribution's type(object): ", type(self.object))
			raise NotImplementedError

		return None

	def conditionforSMT(self, condition, conditioned_bool):
		if isinstance(self.object, Samplable) and isNotConditioned(self.object):
			self.object.conditionforSMT(condition, conditioned_bool)
		return None

	def sampleGiven(self, value):
		obj = value[self.object]
		return getattr(obj, self.attribute)

	def evaluateInner(self, context):
		obj = valueInContext(self.object, context)
		return AttributeDistribution(self.attribute, obj)

	def supportInterval(self):
		obj = self.object
		if isinstance(obj, Options):
			attrs = (getattr(opt, self.attribute) for opt in obj.options)
			mins, maxes = zip(*(supportInterval(attr) for attr in attrs))
			l = None if any(sl is None for sl in mins) else min(mins)
			r = None if any(sr is None for sr in maxes) else max(maxes)
			return l, r
		return None, None

	def isEquivalentTo(self, other):
		if not type(other) is AttributeDistribution:
			return False
		return (self.attribute == other.attribute
			and areEquivalent(self.object, other.object))

	def __call__(self, *args):
		vty = self.object.valueType
		if vty is not object and (func := getattr(vty, self.attribute, None)):
			if isinstance(func, property):
				func = func.fget
			retTy = typing.get_type_hints(func).get('return')
		else:
			retTy = None
		return OperatorDistribution('__call__', self, args, valueType=retTy)

	def __str__(self):
		return f'{self.object}.{self.attribute}'

class OperatorDistribution(Distribution):
	"""Distribution resulting from applying an operator to one or more distributions"""
	def __init__(self, operator, obj, operands, valueType=None):
		operands = tuple(toDistribution(arg) for arg in operands)
		if valueType is None:
			valueType = self.inferType(obj, operator)
		super().__init__(obj, *operands, valueType=valueType)
		self.operator = operator
		self.object = obj
		self.operands = operands

	def conditionforSMT(self, condition, conditioned_bool):
		if isinstance(self.object, Samplable) and isNotConditioned(self.object):
			self.object.conditionforSMT(condition, conditioned_bool)
		for op in self.operands:
			if isinstance(op, Samplable) and isNotConditioned(op):
				op.conditionforSMT(condition, conditioned_bool)
		return None

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		"""to avoid duplicate variable names, check for variable existence in cached_variables dict:
		   cached_variables : key = obj, value = variable_name / key = 'variables', value = list(cached variables so far)
		   encodeToSMT() must return 'cached_variables' dictionary
		"""
		if debug:
			writeSMTtoFile(smt_file_path, "OperatorDistribution")
			writeSMTtoFile(smt_file_path, "operator: "+str(self.operator))
			writeSMTtoFile(smt_file_path, "type(operator): "+str(type(self.operator)))
			# writeSMTtoFile(smt_file_path, "object: "+str(self.object))
			writeSMTtoFile(smt_file_path, "type(object): "+str(type(self.object)))
			# writeSMTtoFile(smt_file_path, "operands: "+str(self.operands))
			for op in self.operands:
				writeSMTtoFile(smt_file_path, "type(operand): "+str(type(op)))

		if self in cached_variables.keys():
			if debug:
				writeSMTtoFile(smt_file_path, "OperatorDistribution already exists in cached_variables dict")
			return cached_variables[self]

		var_name = self.object.encodeToSMT(smt_file_path, cached_variables, debug=debug)

		assert(len(self.operands) < 2)
		operand = self.operands[0]._conditioned
		if isinstance(operand, Samplable):
			operand_smt = operand.encodeToSMT(smt_file_path, cached_variables, debug=debug)
		elif isinstance(operand, int) or isinstance(operand, float):
			operand_smt = str(self.operands[0])
		else:
			raise NotImplementedError

		if self.operator in ['__add__', '__radd__' , '__sub__', '__rsub__', '__truediv__', '__rtruediv__', '__mul__', '__rmul__',\
			'__floordiv__', '__rfloordiv__','__mod__', '__rmod__','__divmod__', '__rdivmod__','__pow__', '__rpow__']:

			var_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'opdist')

			if self.operator == '__add__' or self.operator == '__radd__':
				summation = smt_add(cached_variables[self.object], operand_smt)
				smt_encoding = smt_assert("equal", var_name, summation)

			elif self.operator == '__mul__' or self.operator == '__rmul__':
				multiplication = smt_multiply(cached_variables[self.object], operand_smt)
				smt_encoding = smt_assert("equal", var_name, multiplication)

			elif self.operator == '__sub__':
				subtraction = smt_subtract(cached_variables[self.object], operand_smt)
				smt_encoding = smt_assert("equal", var_name, subtraction)

			elif self.operator == '__rsub__':
				subtraction = smt_subtract(cached_variables[self.operands[0]], operand_smt)
				smt_encoding = smt_assert("equal", var_name, subtraction)

			elif self.operator == '__truediv__':
				truediv = smt_divide(cached_variables[self.object], operand_smt)
				smt_encoding = smt_assert("equal", var_name, truediv)

			elif self.operator == '__rtruediv__':
				division = smt_divide(cached_variables[self.operands[0]], operand_smt)
				smt_encoding = smt_assert("equal", var_name, division)

			elif self.operator == '__mod__':
				modular = smt_mod(cached_variables[self.object], operand_smt)
				smt_encoding = smt_assert("equal", var_name, modular)

			elif self.operator == '__rmod__':
				modular = smt_mod(cached_variables[self.operands[0]], operand_smt)
				smt_encoding = smt_assert("equal", var_name, modular)

			else:
				raise NotImplementedError

			# TODO: floordiv, rfloordiv, divmod, rdivmod, pow, rpow
			writeSMTtoFile(smt_file_path, smt_encoding)

		elif self.operator == '__call__':
			if isinstance(self.object, MethodDistribution):
				methodDist = self.object
				if methodDist.attribute == 'intersect':
					return cacheVarName(cached_variables, self, var_name)

		else:
			raise NotImplementedError

		return cacheVarName(cached_variables, self, var_name)

	@staticmethod
	def inferType(obj, operator):
		if issubclass(obj.valueType, (float, int)):
			return float
		return None

	def sampleGiven(self, value):
		first = value[self.object]
		rest = [value[child] for child in self.operands]
		op = getattr(first, self.operator)
		result = op(*rest)
		# handle horrible int/float mismatch
		# TODO what is the right way to fix this???
		if result is NotImplemented and isinstance(first, int):
			first = float(first)
			op = getattr(first, self.operator)
			result = op(*rest)
		return result

	def evaluateInner(self, context):
		obj = valueInContext(self.object, context)
		operands = tuple(valueInContext(arg, context) for arg in self.operands)
		return OperatorDistribution(self.operator, obj, operands)

	def supportInterval(self):
		if self.operator in ('__add__', '__radd__', '__sub__', '__rsub__', '__truediv__'):

			assert len(self.operands) == 1
			l1, r1 = supportInterval(self.object)
			l2, r2 = supportInterval(self.operands[0])
			if l1 is None or l2 is None or r1 is None or r2 is None:
				return None, None
			if self.operator == '__add__' or self.operator == '__radd__':
				l = l1 + l2
				r = r1 + r2
			elif self.operator == '__sub__':
				l = l1 - r2
				r = r1 - l2
			elif self.operator == '__rsub__':
				l = l2 - r1
				r = r2 - l1
			elif self.operator == '__truediv__':
				if l2 > 0:
					l = l1 / r2 if l1 >= 0 else l1 / l2
					r = r1 / l2 if r1 >= 0 else r1 / r2
				else:
					l, r = None, None 	# TODO improve
			return l, r
		return None, None

	def isEquivalentTo(self, other):
		if not type(other) is OperatorDistribution:
			return False
		return (self.operator == other.operator
			and areEquivalent(self.object, other.object)
			and areEquivalent(self.operands, other.operands))

	def __str__(self):
		return f'{self.object}.{self.operator}{argsToString(self.operands)}'

# Operators which can be applied to distributions.
# Note that we deliberately do not include comparisons and __bool__,
# since Scenic does not allow control flow to depend on random variables.
allowedOperators = (
	'__neg__',
	'__pos__',
	'__abs__',
	'__add__', '__radd__',
	'__sub__', '__rsub__',
	'__mul__', '__rmul__',
	'__truediv__', '__rtruediv__',
	'__floordiv__', '__rfloordiv__',
	'__mod__', '__rmod__',
	'__divmod__', '__rdivmod__',
	'__pow__', '__rpow__',
	'__round__',
	'__getitem__',
)
def makeOperatorHandler(op):
	def handler(self, *args):
		return OperatorDistribution(op, self, args)
	return handler
for op in allowedOperators:
	setattr(Distribution, op, makeOperatorHandler(op))

import scenic.core.type_support as type_support

class MultiplexerDistribution(Distribution):
	"""Distribution selecting among values based on another distribution."""

	def __init__(self, index, options):
		self.index = index
		self.options = tuple(toDistribution(opt) for opt in options)
		assert len(self.options) > 0
		valueType = type_support.unifyingType(self.options)
		super().__init__(index, *self.options, valueType=valueType)

	def sampleGiven(self, value):
		idx = value[self.index]
		assert 0 <= idx < len(self.options), (idx, len(self.options))
		return value[self.options[idx]]

	def evaluateInner(self, context):
		return type(self)(valueInContext(self.index, context),
		                  (valueInContext(opt, context) for opt in self.options))

	def isEquivalentTo(self, other):
		if not type(other) == type(self):
			return False
		return (areEquivalent(self.index, other.index)
		        and areEquivalent(self.options, other.options))

## Simple distributions

class Range(Distribution):
	"""Uniform distribution over a range"""
	def __init__(self, low, high):
		low = type_support.toScalar(low, f'Range endpoint {low} is not a scalar')
		high = type_support.toScalar(high, f'Range endpoint {high} is not a scalar')
		super().__init__(low, high, valueType=float)
		self.low = low
		self.high = high

	def conditionforSMT(self, condition, conditioned_bool):
		if isinstance(self.low, Samplable) and isNotConditioned(self.low):
			self.low.conditionforSMT(condition, conditioned_bool)
		if isinstance(self.high, Samplable) and isNotConditioned(self.high):
			self.high.conditionforSMT(condition, conditioned_bool)
		return None

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		"""
			smt_file_path must be an absolute path, not relative to a root of non-home folder
			to avoid duplicate variable names, check for variable existence in cached_variables dict:
		   cached_variables : key = obj, value = variable_name / key = 'variables', value = list(cached variables so far)
		"""
		if debug:
			writeSMTtoFile(smt_file_path, "Range")
		
		if self in cached_variables.keys():
			if debug:
				print("Range object already exists in cached_variables dict: ", self)
				writeSMTtoFile(smt_file_path, "already exists in cached_variables dict")
			return cached_variables[self]

		low = checkAndEncodeSMT(smt_file_path, cached_variables, self.low)
		high = checkAndEncodeSMT(smt_file_path, cached_variables, self.high)

		var_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'range')

		lower_bound = smt_lessThanEq(low, var_name)
		upper_bound = smt_lessThanEq(var_name, high)
		smt_encoding = smt_assert("and", lower_bound, upper_bound)
		writeSMTtoFile(smt_file_path, smt_encoding)

		return cacheVarName(cached_variables, self, var_name)

	def __contains__(self, obj):
		return low <= obj and obj <= high

	def clone(self):
		return type(self)(self.low, self.high)

	def bucket(self, buckets=None):
		if buckets is None:
			buckets = 5
		if not isinstance(buckets, int) or buckets < 1:
			raise RuntimeError(f'Invalid buckets for Range.bucket: {buckets}')
		if not isinstance(self.low, float) or not isinstance(self.high, float):
			raise RuntimeError(f'Cannot bucket Range with non-constant endpoints')
		endpoints = numpy.linspace(self.low, self.high, buckets+1)
		ranges = []
		for i, left in enumerate(endpoints[:-1]):
			right = endpoints[i+1]
			ranges.append(Range(left, right))
		return Options(ranges)

	def sampleGiven(self, value):
		return random.uniform(value[self.low], value[self.high])

	def evaluateInner(self, context):
		low = valueInContext(self.low, context)
		high = valueInContext(self.high, context)
		return Range(low, high)

	def isEquivalentTo(self, other):
		if not type(other) is Range:
			return False
		return (areEquivalent(self.low, other.low)
			and areEquivalent(self.high, other.high))

	def __str__(self):
		return f'Range({self.low}, {self.high})'

class Normal(Distribution):
	"""Normal distribution"""
	def __init__(self, mean, stddev):
		mean = type_support.toScalar(mean, f'Normal mean {mean} is not a scalar')
		stddev = type_support.toScalar(stddev, f'Normal stddev {stddev} is not a scalar')
		super().__init__(mean, stddev, valueType=float)
		self.mean = mean
		self.stddev = stddev

	def conditionforSMT(self, condition, conditioned_bool):
		if isinstance(self.mean, Samplable) and isNotConditioned(self.mean):
			self.mean.conditionforSMT(condition, conditioned_bool)
		if isinstance(self.stddev, Samplable) and isNotConditioned(self.stddev):
			self.stddev.conditionforSMT(condition, conditioned_bool)
		return None

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		"""to avoid duplicate variable names, check for variable existence in cached_variables dict:
		   cached_variables : key = obj, value = variable_name / key = 'variables', value = list(cached variables so far)
		"""
		if debug:
			writeSMTtoFile(smt_file_path, "Normal")
		
		if self in cached_variables.keys():
			if debug:
				print("Normal object already exists in cached_variables dict: ", self)
				# writeSMTtoFile(smt_file_path, "already exists in cached_variables dict")
			return cached_variables[self]

		var_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'normal')
		return cacheVarName(cached_variables, self, var_name)

	@staticmethod
	def cdf(mean, stddev, x):
		return (1 + math.erf((x - mean) / (sqrt2 * stddev))) / 2

	@staticmethod
	def cdfinv(mean, stddev, x):
		import scipy	# slow import not often needed
		return mean + (sqrt2 * stddev * scipy.special.erfinv(2*x - 1))

	def clone(self):
		return type(self)(self.mean, self.stddev)

	def bucket(self, buckets=None):
		if not isinstance(self.stddev, float):		# TODO relax restriction?
			raise RuntimeError(f'Cannot bucket Normal with non-constant standard deviation')
		if buckets is None:
			buckets = 5
		if isinstance(buckets, int):
			if buckets < 1:
				raise RuntimeError(f'Invalid buckets for Normal.bucket: {buckets}')
			elif buckets == 1:
				endpoints = []
			elif buckets == 2:
				endpoints = [0]
			else:
				left = self.stddev * (-(buckets-3)/2 - 0.5)
				right = self.stddev * ((buckets-3)/2 + 0.5)
				endpoints = numpy.linspace(left, right, buckets-1)
		else:
			endpoints = tuple(buckets)
			for i, v in enumerate(endpoints[:-1]):
				if v >= endpoints[i+1]:
					raise RuntimeError('Non-increasing bucket endpoints for '
					                   f'Normal.bucket: {endpoints}')
		if len(endpoints) == 0:
			return Options([self.clone()])
		buckets = [(-math.inf, endpoints[0])]
		buckets.extend((v, endpoints[i+1]) for i, v in enumerate(endpoints[:-1]))
		buckets.append((endpoints[-1], math.inf))
		pieces = []
		probs = []
		for left, right in buckets:
			pieces.append(self.mean + TruncatedNormal(0, self.stddev, left, right))
			prob = (Normal.cdf(0, self.stddev, right)
			        - Normal.cdf(0, self.stddev, left))
			probs.append(prob)
		assert math.isclose(math.fsum(probs), 1), probs
		return Options(dict(zip(pieces, probs)))

	def sampleGiven(self, value):
		return random.gauss(value[self.mean], value[self.stddev])

	def evaluateInner(self, context):
		mean = valueInContext(self.mean, context)
		stddev = valueInContext(self.stddev, context)
		return Normal(mean, stddev)

	def isEquivalentTo(self, other):
		if not type(other) is Normal:
			return False
		return (areEquivalent(self.mean, other.mean)
			and areEquivalent(self.stddev, other.stddev))

	def __str__(self):
		return f'Normal({self.mean}, {self.stddev})'

class TruncatedNormal(Normal):
	"""Truncated normal distribution."""
	def __init__(self, mean, stddev, low, high):
		if (not isinstance(low, (float, int))
		    or not isinstance(high, (float, int))):	# TODO relax restriction?
			raise RuntimeError('Endpoints of TruncatedNormal must be constant')
		super().__init__(mean, stddev)
		self.low = low
		self.high = high

	def conditionforSMT(self, condition, conditioned_bool):
		if isinstance(self.low, Samplable) and isNotConditioned(self.low):
			self.low.conditionforSMT(condition, conditioned_bool)
		if isinstance(self.high, Samplable) and isNotConditioned(self.high):
			self.high.conditionforSMT(condition, conditioned_bool)
		return None

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		"""to avoid duplicate variable names, check for variable existence in cached_variables dict:
		   cached_variables : key = obj, value = variable_name / key = 'variables', value = list(cached variables so far)
		"""

		if debug:
			writeSMTtoFile(smt_file_path, "TruncatedNormal")
		
		if self in cached_variables.keys():
			if debug:
				print("TruncatedNormal object already exists in cached_variables dict: ", self)
				# writeSMTtoFile(smt_file_path, "object already exists in cached_variables dict")
			return cached_variables[self]

		low = checkAndEncodeSMT(smt_file_path, cached_variables, self.low)
		high = checkAndEncodeSMT(smt_file_path, cached_variables, self.high)

		var_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'truncated_normal')

		lower_bound = smt_lessThanEq(low, var_name)
		upper_bound = smt_lessThanEq(var_name, high)
		smt_encoding = smt_assert("and", lower_bound, upper_bound)
		writeSMTtoFile(smt_file_path, smt_encoding)

		return cacheVarName(cached_variables, self, var_name)

	def clone(self):
		return type(self)(self.mean, self.stddev, self.low, self.high)

	def bucket(self, buckets=None):
		if not isinstance(self.stddev, float):		# TODO relax restriction?
			raise RuntimeError('Cannot bucket TruncatedNormal with '
			                   'non-constant standard deviation')
		if buckets is None:
			buckets = 5
		if isinstance(buckets, int):
			if buckets < 1:
				raise RuntimeError(f'Invalid buckets for TruncatedNormal.bucket: {buckets}')
			endpoints = numpy.linspace(self.low, self.high, buckets+1)
		else:
			endpoints = tuple(buckets)
			if len(endpoints) < 2:
				raise RuntimeError('Too few bucket endpoints for '
				                   f'TruncatedNormal.bucket: {endpoints}')
			if endpoints[0] != self.low or endpoints[-1] != self.high:
				raise RuntimeError(f'TruncatedNormal.bucket endpoints {endpoints} '
				                   'do not match domain')
			for i, v in enumerate(endpoints[:-1]):
				if v >= endpoints[i+1]:
					raise RuntimeError('Non-increasing bucket endpoints for '
					                   f'TruncatedNormal.bucket: {endpoints}')
		pieces, probs = [], []
		for i, left in enumerate(endpoints[:-1]):
			right = endpoints[i+1]
			pieces.append(TruncatedNormal(self.mean, self.stddev, left, right))
			prob = (Normal.cdf(self.mean, self.stddev, right)
			        - Normal.cdf(self.mean, self.stddev, left))
			probs.append(prob)
		return Options(dict(zip(pieces, probs)))

	def sampleGiven(self, value):
		# TODO switch to method less prone to underflow?
		mean, stddev = value[self.mean], value[self.stddev]
		alpha = (self.low - mean) / stddev
		beta = (self.high - mean) / stddev
		alpha_cdf = Normal.cdf(0, 1, alpha)
		beta_cdf = Normal.cdf(0, 1, beta)
		if beta_cdf - alpha_cdf < 1e-15:
			warnings.warn('low precision when sampling TruncatedNormal')
		unif = random.random()
		p = alpha_cdf + unif * (beta_cdf - alpha_cdf)
		return mean + (stddev * Normal.cdfinv(0, 1, p))

	def evaluateInner(self, context):
		mean = valueInContext(self.mean, context)
		stddev = valueInContext(self.stddev, context)
		return TruncatedNormal(mean, stddev, self.low, self.high)

	def isEquivalentTo(self, other):
		if not type(other) is TruncatedNormal:
			return False
		return (areEquivalent(self.mean, other.mean)
			and areEquivalent(self.stddev, other.stddev)
			and self.low == other.low and self.high == other.high)

	def __str__(self):
		return f'TruncatedNormal({self.mean}, {self.stddev}, {self.low}, {self.high})'

class DiscreteRange(Distribution):
	"""Distribution over a range of integers."""
	def __init__(self, low, high, weights=None):
		if not isinstance(low, int):
			raise RuntimeError(f'DiscreteRange endpoint {low} is not a constant integer')
		if not isinstance(high, int):
			raise RuntimeError(f'DiscreteRange endpoint {high} is not a constant integer')
		if not low <= high:
			raise RuntimeError(f'DiscreteRange lower bound {low} is above upper bound {high}')
		if weights is None:
			weights = (1,) * (high - low + 1)
		else:
			weights = tuple(weights)
			assert len(weights) == high - low + 1
		super().__init__(valueType=int)
		self.low = low
		self.high = high
		self.weights = weights
		self.cumulativeWeights = tuple(itertools.accumulate(weights))
		self.options = tuple(range(low, high+1))

	def conditionforSMT(self, condition, conditioned_bool):
		if isinstance(self.low, Samplable) and isNotConditioned(self.low):
			self.low.conditionforSMT(condition, conditioned_bool)
		if isinstance(self.high, Samplable) and isNotConditioned(self.high):
			self.high.conditionforSMT(condition, conditioned_bool)
		return None

	def encodeToSMT(self, smt_file_path, cached_variables, debug=False):
		"""to avoid duplicate variable names, check for variable existence in cached_variables dict:
		   cached_variables : key = obj, value = variable_name / key = 'variables', value = list(cached variables so far)
		"""
		if debug:
			writeSMTtoFile(smt_file_path, "DiscreteRange")

		if self in cached_variables.keys():
			if debug:
				print("DiscreteRange object already exists in cached_variables dict: ", self)
				# writeSMTtoFile(smt_file_path, "already exists in cached_variables dict")
			return cached_variables[self]

		low = checkAndEncodeSMT(smt_file_path, cached_variables, self.low)
		high = checkAndEncodeSMT(smt_file_path, cached_variables, self.high)
		var_name = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], 'discrete_range', "Int")

		lower_bound = smt_lessThanEq(low, var_name)
		upper_bound = smt_lessThanEq(var_name, high)
		smt_encoding = smt_assert("and", lower_bound, upper_bound)
		writeSMTtoFile(smt_file_path, smt_encoding)
		
		return cacheVarName(cached_variables, self, var_name)

	def __contains__(self, obj):
		return low <= obj and obj <= high

	def clone(self):
		return type(self)(self.low, self.high, self.weights)

	def bucket(self, buckets=None):
		return self.clone()		# already bucketed

	def sampleGiven(self, value):
		return random.choices(self.options, cum_weights=self.cumulativeWeights)[0]

	def isEquivalentTo(self, other):
		if not type(other) is DiscreteRange:
			return False
		return (self.low == other.low and self.high == other.high
		        and self.weights == other.weights)

	def __str__(self):
		return f'DiscreteRange({self.low}, {self.high}, {self.weights})'

class Options(MultiplexerDistribution):
	"""Distribution over a finite list of options.

	Specified by a dict giving probabilities; otherwise uniform over a given iterable.
	"""
	def __init__(self, opts):
		if isinstance(opts, dict):
			options, weights = [], []
			for opt, prob in opts.items():
				if not isinstance(prob, (float, int)):
					raise RuntimeParseError(f'discrete distribution weight {prob}'
					                        ' is not a number')
				if prob < 0:
					raise RuntimeParseError(f'discrete distribution weight {prob} is negative')
				if prob == 0:
					continue
				options.append(opt)
				weights.append(prob)
			self.optWeights = dict(zip(options, weights))
		else:
			weights = None
			options = tuple(opts)
			self.optWeights = None
		if len(options) == 0:
			raise RuntimeParseError('tried to make discrete distribution over empty domain!')

		index = self.makeSelector(len(options)-1, weights)
		super().__init__(index, options)

	def encodeToSMT(self, smt_file_path, cached_variables, obj=None, debug=False):
		if debug:
			writeSMTtoFile(smt_file_path, "Options class")
			writeSMTtoFile(smt_file_path, str(self.options))
		if isinstance(obj, Samplable):
			obj = self
		if obj in cached_variables.keys():
			return cached_variables[obj]
		
		if self != self._conditioned:
			options = self._conditioned
		else:
			options = self.options

		if len(self.options!=0):
			x = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], "x")
			y = findVariableName(cached_variables, smt_file_path, cached_variables['variables'], "y")
			output = (x,y)
			for opt in options:
				point = opt.encodeToSMT(smt_file_path, cached_variables, obj=None, debug=False)
				(x_cond, y_cond) = vector_operation_smt(point, "equal", output)
				writeSMTtoFile(smt_file_path, x_cond)
				writeSMTtoFile(smt_file_path, y_cond)
		else:
			raise NotImplementedError


		return output
		# import scenic.domains.driving.roads as road_library
		# if isinstance(options[0], road_library.LinearElement):

	def conditionforSMT(self, condition, conditioned_bool):
		import scenic.domains.driving.roads as roads
		import scenic.core.vectors as vectors

		if isinstance(condition, vectors.Vector):
			# if a vector is given to condition, then search through all options of regions and 
			# condition to the one that contains 
			import scenic.core.regions as regions
			satisfying_options = []

			for opt in self.options:
				assert isinstance(opt, regions.Region)
				if opt.containsPoint(condition):
					satisfying_options.append(opt)
					conditioned_bool = True
				
				if satisfying_options != []:
					self.conditionTo(satisfying_options)
					return None

		raise NotImplementedError

	@staticmethod
	def makeSelector(n, weights):
		return DiscreteRange(0, n, weights)

	def clone(self):
		return type(self)(self.optWeights if self.optWeights else self.options)

	def bucket(self, buckets=None):
		return self.clone()		# already bucketed

	def evaluateInner(self, context):
		if self.optWeights is None:
			return type(self)(valueInContext(opt, context) for opt in self.options)
		else:
			return type(self)({valueInContext(opt, context): wt
			                  for opt, wt in self.optWeights.items() })

	def isEquivalentTo(self, other):
		if not type(other) == type(self):
			return False
		return (areEquivalent(self.index, other.index)
		        and areEquivalent(self.options, other.options))

	def __str__(self):
		if self.optWeights is not None:
			return f'{type(self).__name__}({self.optWeights})'
		else:
			return f'{type(self).__name__}{argsToString(self.options)}'

@unpacksDistributions
def Uniform(*opts):
	"""Uniform distribution over a finite list of options.

	Implemented as an instance of :obj:`Options` when the set of options is known
	statically, and an instance of `UniformDistribution` otherwise.
	"""
	if any(isinstance(opt, StarredDistribution) for opt in opts):
		return UniformDistribution(opts)
	else:
		return Options(opts)

class UniformDistribution(Distribution):
	"""Uniform distribution over a variable number of options.

	See :obj:`Options` for the more common uniform distribution over a fixed number
	of options. This class is for the special case where iterable unpacking is
	applied to a distribution, so that the number of options is unknown at
	compile time.
	"""
	def __init__(self, opts):
		self.options = opts
		valueType = type_support.unifyingType(self.options)
		super().__init__(*self.options, valueType=valueType)

	def encodeToSMT(self, smt_file_path, cached_variables, obj=None, debug=False):
		raise NotImplementedError

	def conditionforSMT(self, condition, conditioned_bool):
		raise NotImplementedError 

	def sampleGiven(self, value):
		opts = []
		for opt in self.options:
			if isinstance(opt, StarredDistribution):
				opts.extend(value[opt])
			else:
				opts.append(value[opt])
		if not opts:
			raise RejectionException('uniform distribution over empty domain')
		return random.choice(opts)

	def evaluateInner(self, context):
		opts = tuple(valueInContext(opt, context) for opt in self.options)
		return UniformDistribution(opts)

	def __str__(self):
		return f'UniformDistribution({self.options})'
