"""Interface from Scenic to LGSVL."""

import lgsvl

import scenic.simulators.lgsvl.utils as utils

class LGSVLSimulation:
    """Class for running an LGSVL simulation from a scene."""
    def __init__(self, scene, client):
        self.client = client
        self.apolloHDMap = scene.params['apolloHDMap']
        self.objects = scene.objects
        self.apolloCar = None

        # Reset simulator (deletes all existing objects)
        self.client.reset()

        # Create LGSVL objects corresponding to Scenic objects
        self.lgsvlObjects = {}
        for obj in self.objects:
            # Figure out what type of LGSVL object this is
            if not hasattr(obj, 'lgsvlObject'):
                continue    # not an LGSVL object
            if not hasattr(obj, 'lgsvlName'):
                raise RuntimeError(f'object {obj} does not have an lgsvlName property')
            if not hasattr(obj, 'lgsvlAgentType'):
                raise RuntimeError(f'object {obj} does not have an lgsvlAgentType property')
            name = obj.lgsvlName
            agentType = obj.lgsvlAgentType

            # Set up position and orientation
            state = lgsvl.AgentState()
            if obj.elevation is None:
                obj.elevation = self.groundElevationAt(obj.position)
            state.transform.position = utils.scenicToLGSVLPosition(obj.position, obj.elevation)
            state.transform.rotation = utils.scenicToLGSVLRotation(obj.heading)

            # Create LGSVL object
            lgsvlObj = self.client.add_agent(name, agentType, state)
            obj.lgsvlObject = lgsvlObj
            
            # Initialize Apollo if needed
            if hasattr(obj, 'apolloVehicle'):
                self.initApolloFor(obj, lgsvlObj)

    def groundElevationAt(self, pos):
        """Get the ground elevation at a given Scenic position."""
        origin = utils.scenicToLGSVLPosition(pos, 100000)
        result = self.client.raycast(origin, lgsvl.Vector(0, -1, 0), 1)
        if result is None:
            print(f'WARNING: no ground at position {pos}')
            return 0
        return result.point.y

    def initApolloFor(self, obj, lgsvlObj):
        """Initialize Apollo for an ego vehicle.

        Uses LG's interface which injects packets into Dreamview.
        """
        try:
            import dreamview
        except ImportError as e:
            raise RuntimeError('using Apollo requires the "dreamview" Python package') from e

        if self.apolloCar:
            raise RuntimeError('can only use one Apollo vehicle')
        self.apolloCar = lgsvlObj

        # connect bridge from LGSVL to Apollo
        lgsvlObj.connect_bridge(obj.bridgeHost, obj.bridgePort)

        # set up connection and map/vehicle configuration
        dv = dreamview.Connection(self.client, lgsvlObj)
        obj.dreamview = dv
        waitToStabilize = False
        if dv.getCurrentMap() != self.apolloHDMap:
            dv.setHDMap(self.apolloHDMap)
            waitToStabilize = True
        if dv.getCurrentVehicle() != obj.apolloVehicle:
            dv.setVehicle(obj.apolloVehicle)
            waitToStabilize = True
        
        print('Initializing Apollo...')

        # stop the car to cancel buffered speed from previous simulations
        cntrl = lgsvl.VehicleControl()
        cntrl.throttle = 0.0
        lgsvlObj.apply_control(cntrl, True)
        # start modules
        dv.disableModule('Control')
        ready = dv.getModuleStatus()
        for module in obj.apolloModules:
            if not ready[module]:
                dv.enableModule(module)
                print('Module', module, 'is not ready...')
                waitToStabilize = True
        while True:
            ready = dv.getModuleStatus()
            if all(ready[module] for module in obj.apolloModules):
                break

        # wait for Apollo to stabilize, if needed
        if waitToStabilize:
            delay = 25
            print(f'Waiting {delay} seconds for Apollo to stabilize...')
            self.client.run(delay)
        dv.enableModule('Control')
        delay = 15
        print(f'Waiting {delay} seconds for Control module to come up...')
        self.client.run(delay)
        print('Initialized Apollo.')

        if obj.destination is not None:
            print('Setting destination for Apollo.')
            dest = obj.destination.toVector()
            z = self.groundElevationAt(dest)
            dv.setDestination(dest.x, dest.y, z, coordType=dreamview.CoordType.Unity)

    def makeLGSVLWaypoints(self, waypoints):
        """Convert a sequence of Scenic Points/OrientedPoints into LGSVL waypoints."""
        waypoints = tuple(waypoints)
        if isinstance(waypoints[0], lgsvl.DriveWaypoint):
            return waypoints

        pts = []
        for wp in self.waypoints:
            elev = self.groundElevationAt(wp)
            pos = utils.scenicToLGSVLPosition(wp, y=elev)
            h = getattr(wp, 'heading', 0)
            rot = utils.scenicToLGSVLRotation(h)
            pt = lgsvl.DriveWaypoint(pos, wp.speed, rot)
            pts.append(pt)
        return tuple(pts)

    def run(self, duration):
        """Run simulation for the given duration."""
        if self.apolloCar and duration > 1:
            # push vehicle for 1 second to start
            cntrl = lgsvl.VehicleControl()
            cntrl.throttle = 0.5
            self.apolloCar.apply_control(cntrl, True)

            self.client.run(time_limit=1)

            self.apolloCar.apply_control(cntrl, False)

            self.client.run(time_limit=duration-1)
        else:
            self.client.run(time_limit=duration)
