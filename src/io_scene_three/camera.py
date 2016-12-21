# camera.py

from math import degrees, atan, tan

from bpy.types import Object
from bpy.path import clean_name

from collections import OrderedDict

from .util import get_uuid


def export_persp_camera_object(ob, scene):
    """

    """

    assert isinstance(ob, Object) and \
        ob.type == "CAMERA" and \
        ob.data.type == "PERSP", \
        "export_persp_camera_object() expects a " \
        "`bpy.types.Object(type=\"LAMP\").data(type=\"PERSP\")` arg"

    out = OrderedDict()

    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)
    out["type"] = "PerspectiveCamera"
    aspect = out["aspect"] = (scene.render.resolution_x /
                              scene.render.resolution_y)
    out["fov"] = degrees(2 * atan(tan(ob.data.angle / 2) / aspect))
    out["near"] = ob.data.clip_start
    out["far"] = ob.data.clip_end

    return out


def export_camera_object(ob, scene):
    """exports a Blender CAMERA Object as a dict representing a
    THREE.*Camera instance

    :arg ob:(bpy.types.Object(type="CAMERA")): Blender CAMERA Object
    :arg [scene] (bpy.types.Scene): Blender scene (needed to calculate
                                    camera aspect)

    :returns (dict): A dictionary representing a THREE.*Camera instance

    :raises (TypeError): On unsupported camera types
    """

    assert isinstance(ob, Object) and ob.type == "CAMERA", \
        "encode_camera_object() expects a `bpy.types.Object` arg"

    if ob.data.type == "PERSP":
        return export_persp_camera_object(ob, scene)

    # TODO: elif: ob.data.type == "ORTHO":
    #       return export_ortho_camera_object(ob)

    else:
        raise TypeError(
            "CAMERA type '%s' is not supported yet" % (ob.data.type))
