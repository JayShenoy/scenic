"""Utility functions for geometric computation."""

import math
import itertools
import warnings

import numpy as np
import shapely.geometry
import shapely.ops

from scenic.core.distributions import (needsSampling, distributionFunction,
                                       monotonicDistributionFunction)
from scenic.core.lazy_eval import needsLazyEvaluation
from scenic.core.utils import cached_property

@distributionFunction
def sin(x):
	return math.sin(x)

@distributionFunction
def cos(x):
	return math.cos(x)

@monotonicDistributionFunction
def hypot(x, y):
	return math.hypot(x, y)

@monotonicDistributionFunction
def max(*args):
	return __builtins__['max'](*args)

@monotonicDistributionFunction
def min(*args):
	return __builtins__['min'](*args)

def normalizeAngle(angle):
	while angle > math.pi:
		angle -= math.tau
	while angle < -math.pi:
		angle += math.tau
	assert -math.pi <= angle <= math.pi
	return angle

def dotProduct(a, b):
	return ((a.x * b.x) + (a.y * b.y) + (a.z * b.z))

def norm(a):
	return math.sqrt(math.pow(a.x, 2) + math.pow(a.y, 2) + math.pow(a.z, 2)) 

def addVectors(a, b):
	ax, ay = a[0], a[1]
	bx, by = b[0], b[1]
	return (ax + bx, ay + by)

def subtractVectors(a, b):
	ax, ay = a[0], a[1]
	bx, by = b[0], b[1]
	return (ax - bx, ay - by)

def averageVectors(a, b, weight=0.5):
	ax, ay = a[0], a[1]
	bx, by = b[0], b[1]
	aw, bw = 1.0 - weight, weight
	return (ax * aw + bx * bw, ay * aw + by * bw)

def rotateVector(vector, angle):
	x, y = vector
	c, s = cos(angle), sin(angle)
	return ((c * x) - (s * y), (s * x) + (c * y))

def findMinMax(iterable):
	minv = float('inf')
	maxv = float('-inf')
	for val in iterable:
		if val < minv:
			minv = val
		if val > maxv:
			maxv = val
	return (minv, maxv)

def radialToCartesian(point, radius, heading):
	angle = heading + (math.pi / 2.0)
	rx, ry = radius * cos(angle), radius * sin(angle)
	return (point[0] + rx, point[1] + ry)

def positionRelativeToPoint(point, heading, offset):
	ro = rotateVector(offset, heading)
	return addVectors(point, ro)

def headingOfSegment(pointA, pointB):
	# TODO: @pytest Update to 3D. Requires orientation
	ax, ay, az = pointA
	bx, by, bz = pointB
	return math.atan2(by - ay, bx - ax) - (math.pi / 2.0)

# TODO: @pytest Update to 3D view angle. Requires orientation
def viewAngleToPoint(point, base, heading):
	x, y, z = base
	ox, oy, oz = point
	a = math.atan2(oy - y, ox - x) - (heading + (math.pi / 2.0))
	if a < -math.pi:
		a += math.tau
	elif a > math.pi:
		a -= math.tau
	assert -math.pi <= a and a <= math.pi
	return a

def apparentHeadingAtPoint(point, heading, base):
	# TODO: @pytest Update to 3D. Requires orientation
	x, y, z = base
	ox, oy, oz = point
	a = (heading + (math.pi / 2.0)) - math.atan2(oy - y, ox - x)
	if a < -math.pi:
		a += math.tau
	elif a > math.pi:
		a -= math.tau
	assert -math.pi <= a and a <= math.pi
	return a

def circumcircleOfAnnulus(center, heading, angle, minDist, maxDist):
	m = (minDist + maxDist) / 2.0
	g = (maxDist - minDist) / 2.0
	h = m * math.sin(angle / 2.0)
	h2 = h * h
	d = math.sqrt(h2 + (m * m))
	r = math.sqrt(h2 + (g * g))
	return radialToCartesian(center, d, heading), r

def pointIsInCone(point, base, heading, angle):
	va = viewAngleToPoint(point, base, heading)
	return (abs(va) <= angle / 2.0)

def polygonUnion(polys, tolerance=0.05, holeTolerance=0.002):
	union = shapely.ops.unary_union(list(polys))
	assert union.is_valid, union
	if tolerance > 0:
		if isinstance(union, shapely.geometry.MultiPolygon):
			polys = [cleanPolygon(poly, tolerance, holeTolerance) for poly in union]
			union = shapely.ops.unary_union(polys)
		else:
			union = cleanPolygon(union, tolerance, holeTolerance)
	assert union.is_valid, union
	return union

def cleanPolygon(poly, tolerance, holeTolerance):
	exterior = cleanChain(poly.exterior.coords, tolerance)
	assert len(exterior) >= 3
	ints = []
	for interior in poly.interiors:
		interior = cleanChain(interior.coords, tolerance)
		if len(interior) >= 3:
			hole = shapely.geometry.Polygon(interior)
			if hole.area > holeTolerance:
				ints.append(interior)
	newPoly = shapely.geometry.Polygon(exterior, ints)
	assert newPoly.is_valid, newPoly
	return newPoly

def cleanChain(chain, tolerance, angleTolerance=0.008):
	if len(chain) <= 2:
		return chain
	closed = (tuple(chain[0]) == tuple(chain[-1]))
	tol2 = tolerance * tolerance
	# collapse hooks
	chain = np.array(chain)
	a, b = chain[-1], chain[0]
	newChain = []
	for c in chain[1:]:
		dx, dy = c[0] - a[0], c[1] - a[1]
		if (dx * dx) + (dy * dy) > tol2:
			newChain.append(b)
			a = b
			b = c
		else:
			b = c
	if len(newChain) == 0:
		return newChain
	newChain.append(newChain[0] if closed else c)
	return newChain

class TriangulationError(RuntimeError):
	"""Signals that the installed triangulation libraries are insufficient.

	Specifically, raised when pypoly2tri hits the recursion limit trying to
	triangulate a large polygon.
	"""
	pass

def triangulatePolygon(polygon):
	"""Triangulate the given Shapely polygon.

	Note that we can't use ``shapely.ops.triangulate`` since it triangulates
	point sets, not polygons (i.e., it doesn't respect edges). We need an
	algorithm for triangulation of polygons with holes (it doesn't need to be a
	Delaunay triangulation).

	We use ``mapbox_earcut`` by default. If it is not installed, we allow fallback to
	``pypoly2tri`` for historical reasons (we originally used the GPC library, which is
	not free for commercial use, falling back to ``pypoly2tri`` if not installed).

	Args:
		polygon (shapely.geometry.Polygon): Polygon to triangulate.

	Returns:
		A list of disjoint (except for edges) triangles whose union is the
		original polygon.
	"""
	try:
		return triangulatePolygon_mapbox(polygon)
	except ImportError:
		pass
	try:
		return triangulatePolygon_pypoly2tri(polygon)
	except ImportError:
		pass
	raise RuntimeError('no triangulation libraries installed '
	                   '(did you uninstall mapbox_earcut?)')

def triangulatePolygon_pypoly2tri(polygon):
	import pypoly2tri
	polyline = []
	for c in polygon.exterior.coords[:-1]:
		polyline.append(pypoly2tri.shapes.Point(c[0],c[1]))
	cdt = pypoly2tri.cdt.CDT(polyline)
	for i in polygon.interiors:
		polyline = []
		for c in i.coords[:-1]:
			polyline.append(pypoly2tri.shapes.Point(c[0],c[1]))
		cdt.AddHole(polyline)
	try:
		cdt.Triangulate()
	except RecursionError:		# polygon too big for pypoly2tri
		raise TriangulationError('pypoly2tri unable to triangulate large polygon; for '
		                         'non-commercial use, try "pip install Polygon3"')

	triangles = list()
	for t in cdt.GetTriangles():
		triangles.append(shapely.geometry.Polygon([
			t.GetPoint(0).toTuple(),
			t.GetPoint(1).toTuple(),
			t.GetPoint(2).toTuple()
		]))
	return triangles

def triangulatePolygon_mapbox(polygon):
	import mapbox_earcut
	vertices, rings = [], []
	ring = polygon.exterior.coords[:-1]		# despite 'ring' name, actually need a chain
	vertices.extend(ring)
	rings.append(len(vertices))
	for interior in polygon.interiors:
		ring = interior.coords[:-1]
		vertices.extend(ring)
		rings.append(len(vertices))
	vertices = np.array(vertices, dtype=np.float64)
	rings = np.array(rings)
	result = mapbox_earcut.triangulate_float64(vertices, rings)

	triangles = []
	points = vertices[result]
	its = [iter(points)] * 3
	for triple in zip(*its):
		triangles.append(shapely.geometry.Polygon(triple))
	return triangles

def plotPolygon(polygon, plt, style='r-'):
	def plotRing(ring):
		x, y = ring.xy
		plt.plot(x, y, style)
	if isinstance(polygon, shapely.geometry.MultiPolygon):
		polygons = polygon
	else:
		polygons = [polygon]
	for polygon in polygons:
		plotRing(polygon.exterior)
		for ring in polygon.interiors:
			plotRing(ring)

class RotatedRectangle:
	"""mixin providing collision detection for rectangular objects and regions"""
	# TODO: @pytest Update to 3D
	def containsPoint(self, point):
		pt = shapely.geometry.Point(point)
		return self.polygon.intersects(pt)

	def intersects(self, rect):
		return self.polygon.intersects(rect.polygon)

	@cached_property
	def polygon(self):
		position, heading, hw, hh = self.position, self.heading, self.hw, self.hh
		if any(needsSampling(c) or needsLazyEvaluation(c)
		       for c in (position, heading, hw, hh)):
			return None		# can only convert fixed Regions to Polygons
		corners = RotatedRectangle.makeCorners(position.x, position.y, heading, hw, hh)
		return shapely.geometry.Polygon(corners)

	@staticmethod
	def makeCorners(px, py, heading, hw, hh):
		s, c = sin(heading), cos(heading)
		s_hw, c_hw = s*hw, c*hw
		s_hh, c_hh = s*hh, c*hh
		corners = (
			(px + c_hw - s_hh, py + s_hw + c_hh),
			(px - c_hw - s_hh, py - s_hw + c_hh),
			(px - c_hw + s_hh, py - s_hw - c_hh),
			(px + c_hw + s_hh, py + s_hw - c_hh)
		)
		return corners
