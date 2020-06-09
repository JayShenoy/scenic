"""Stub to allow changing the LGSVL map without changing the model."""

import os.path

#: Name of LGSVL scene in WebUI (e.g. 'BorregasAve')
sceneName = None

#: Path to OpenDRIVE file for the desired map
mapPath = None

#: Name of Apollo HD map (in Dreamview), if any
apolloMapName = None

def setMap(module, relpath, scene, apolloMap=None):
    global sceneName, mapPath, apolloMapName
    base = os.path.dirname(module)
    mapPath = os.path.join(base, relpath)
    sceneName = scene
    apolloMapName = apolloMap
