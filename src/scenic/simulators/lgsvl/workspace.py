
from scenic.simulators.formats.opendrive import OpenDriveWorkspace

class LGSVLWorkspace(OpenDriveWorkspace):
    @property
    def minimumZoomSize(self):
        return 40
