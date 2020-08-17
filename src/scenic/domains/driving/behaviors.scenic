
import scenic.domains.driving.controllers as controllers
from scenic.domains.driving.actions import *

def concatenateCenterlines(centerlines=[]):
    return PolylineRegion.unionAll(centerlines)

def distance(pos1, pos2):
    """ pos1, pos2 = (x,y) """
    return math.sqrt(math.pow(pos1[0]-pos2[0],2) + math.pow(pos1[1]-pos2[1],2))

def distanceToAnyObjs(vehicle, thresholdDistance):
    """ checks whether there exists any obj
    (1) in front of the vehicle, (2) within thresholdDistance """
    objects = simulation().objects
    for obj in objects:
        if not (vehicle can see obj):
            continue
        if distance(vehicle.position, obj.position) < 0.1:
            # this means obj==vehicle
            pass
        elif distance(vehicle.position, obj.position) < thresholdDistance:
            return True
    return False

behavior WalkForwardBehavior():
    current_sidewalk = network.sidewalkAt(self.position)
    end_point = Uniform(*current_sidewalk.centerline.points)
    end_vec = end_point[0] @ end_point[1]
    normal_vec = Vector.normalized(end_vec)
    take WalkTowardsAction(goal_position=normal_vec), SetSpeedAction(speed=1)

behavior ConstantThrottleBehavior(x):
    while True:
        take SetThrottleAction(x), SetReverseAction(False), SetHandBrakeAction(False)

behavior FollowLaneBehavior(target_speed = 25):

    # instantiate longitudinal and latitudinal pid controllers
    dt = simulation().timestep
    _lon_controller = controllers.PIDLongitudinalController(dt=dt)
    _lat_controller = controllers.PIDLateralController(dt=dt)
    past_steer_angle = 0

    while True:
        cte = self.lane.centerline.signedDistanceTo(self.position)
        speed_error = target_speed - self.speed

        # compute throttle : Longitudinal Control
        throttle = _lon_controller.run_step(speed_error)

        # compute steering : Latitudinal Control
        current_steer_angle = _lat_controller.run_step(cte)

        take FollowLaneAction(throttle=throttle,
                              current_steer=current_steer_angle,
                              past_steer=past_steer_angle)
        past_steer_angle = current_steer_angle


behavior FollowTrajectoryBehavior(target_speed = 25, trajectory = None):
    assert trajectory is not None

    trajectory_line = PolylineRegion.unionAll(trajectory)

    # instantiate longitudinal and latitudinal pid controllers
    dt = simulation().timestep
    _lon_controller = controllers.PIDLongitudinalController(dt=dt)
    _lat_controller = controllers.PIDLateralController(dt=dt)
    past_steer_angle = 0

    while True:
        cte = trajectory_line.signedDistanceTo(self.position)
        speed_error = target_speed - self.speed

        # compute throttle : Longitudinal Control
        throttle = _lon_controller.run_step(speed_error)

        # compute steering : Latitudinal Control
        current_steer_angle = _lat_controller.run_step(cte)

        take FollowLaneAction(throttle=throttle,
                              current_steer=current_steer_angle,
                              past_steer=past_steer_angle)
        past_steer_angle = current_steer_angle
