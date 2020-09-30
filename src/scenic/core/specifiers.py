"""Specifiers and associated objects."""

import itertools

from scenic.core.lazy_eval import (DelayedArgument, toDelayedArgument, requiredProperties,
                                   needsLazyEvaluation)
from scenic.core.distributions import toDistribution
from scenic.core.utils import RuntimeParseError

## Specifiers themselves

class Specifier:
	"""Specifier providing a value for a property given dependencies.

	Any optionally-specified properties are evaluated as attributes of the primary value.
	"""
	def __init__(self, priorities, value, deps=None):
		self.priorities = priorities
		self.value = toDelayedArgument(value)
		self.modifying = dict()
		if deps is None:
			deps = set()
		deps |= requiredProperties(value)
		for p in priorities:
			if p in deps: 
				raise RuntimeParseError(f'specifier for property {p} depends on itself')
		self.requiredProperties = deps

	def applyTo(self, obj, modifying):
		"""Apply specifier to an object, including the specified optional properties."""
		val = self.value.evaluateIn(obj, modifying)
		if isinstance(val, dict):
			for v in val: 
				distV = toDistribution(val[v])
				assert not needsLazyEvaluation(distV)
				setattr(obj, v, distV)
		else:
			val = toDistribution(val)
			assert not needsLazyEvaluation(val)
			if not isinstance(self.priorities, dict):
				self.priorities = {self.priorities: -1}
			for prop in self.priorities: 
				setattr(obj, prop, val)
				
	def __str__(self):
		return f'<Specifier of {self.priorities}>'

class ModifyingSpecifier(Specifier):
	def __init__(self, priorities, value, deps=None):
		super().__init__(priorities, value, deps)

## Support for property defaults

class PropertyDefault:
	"""A default value, possibly with dependencies."""
	def __init__(self, requiredProperties, attributes, value):
		self.requiredProperties = requiredProperties
		self.value = value

		def enabled(thing, default):
			if thing in attributes:
				attributes.remove(thing)
				return True
			else:
				return default
		self.isAdditive = enabled('additive', False)
		for attr in attributes:
			raise RuntimeParseError(f'unknown property attribute "{attr}"')

	@staticmethod
	def forValue(value):
		if isinstance(value, PropertyDefault):
			return value
		else:
			return PropertyDefault(set(), set(), lambda self, specifier: value)

	def resolveFor(self, prop, overriddenDefs):
		"""Create a Specifier for a property from this default and any superclass defaults."""
		if self.isAdditive:
			allReqs = self.requiredProperties
			for other in overriddenDefs:
				allReqs |= other.requiredProperties
			def concatenator(context, specifier):
				allVals = [self.value(context, specifier)]
				for other in overriddenDefs:
					allVals.append(other.value(context, specifier))
				return tuple(allVals)
			val = DelayedArgument(allReqs, concatenator) # TODO: @Matthew Change to dicts 
		else:
			val = DelayedArgument(self.requiredProperties, self.value)
		return Specifier(prop, val) # TODO: @Matthew Change to dict for prop 
