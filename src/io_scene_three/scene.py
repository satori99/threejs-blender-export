# scene.py

from bpy.types import Scene
from bpy.path import clean_name

from collections import OrderedDict

from .util import get_uuid, get_custom_props
from .lamp import export_ambient_light


def export_fog(scene):
    """Exports Blender Scene fog properties as a dictionary representing a
    three.js Fog type.

    NOTE: `None` is returned if use mist setting is not checked.

    :arg scene (bpy.types.Scene): Blender Scene

    :returns (dict): A Dictionary representing three.js Fog type or None if
                     the scene has no mist settings
    """

    out = None

    if scene.world and scene.world.mist_settings.use_mist:

        out = OrderedDict()
        # TODO FogExp2 - just normal fog for now.
        out["type"] = "Fog"
        out["color"] = scene.world.horizon_color
        out["near"] = scene.world.mist_settings.start
        out["far"] = scene.world.mist_settings.start + \
            scene.world.mist_settings.depth

    return out


def export_scene(scene, exporter=None):
    """Encodes a Blender Scene instance into a dictionary representing a
    three.js Scene type

    :arg scene (bpy.types.Scene): Blender Scene object to be encoded.

    :returns (dict): Dictionary representing a three.js Scene type
    """

    assert isinstance(scene, Scene), \
        "export_scene() expects a `bpy.types.Scene` arg"

    print("-> THREE.Scene(\"%s\")" % scene.name)

    # create scene dict
    out = OrderedDict()
    out["uuid"] = get_uuid(scene)
    out["name"] = clean_name(scene.name)
    out["type"] = "Scene"
    # out["background"] = scene.world.horizon_color
    out["fog"] = export_fog(scene)

    # add custom properties
    out.update(get_custom_props(scene))

    # add scene children
    if exporter is not None:
        out["children"] = [o for o in exporter.objects
                           if o.parent not in exporter.objects]

    # add ambient light
    ambient = export_ambient_light(scene)
    if ambient:
        out["children"].append(ambient)

    # done
    return out
