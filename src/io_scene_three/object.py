# object.py

from bpy.types import Object
from bpy.path import clean_name

from collections import OrderedDict

from .util import get_uuid, get_custom_props
from .math import MAT4_IDENTITY
from .mesh import export_mesh_object
from .lamp import export_lamp_object
from .camera import export_camera_object
from .armature import export_armature_object


def export_empty_object(ob):
    """

    """

    assert isinstance(ob, Object) and ob.type == "EMPTY", \
        "export_empty_object() expects a `bpy.types.Object(type='EMPTY')` arg"

    out = OrderedDict()

    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)
    out["type"] = "Object3D"

    return out


def export_object(ob, exporter=None):
    """exports a Blender Object (`bpy.types.Object`) as a dictionary
    representing a three.js type

    Currently EMPTY, MESH, LAMP, CAMERA, and ARMATURE Object types
    are supported.

    :returns (dict): A dictionary representing a Three.js scene-graph
                     object type

    :raises (TypeError): On unsupported Blender Object types
    """

    assert isinstance(ob, Object), \
        "export_object() expects a `bpy.types.Object` arg"

    if ob.type == "EMPTY":
        out = export_empty_object(ob)

    elif ob.type == "MESH":
        out = export_mesh_object(ob, exporter=exporter)

    elif ob.type == "LAMP":
        out = export_lamp_object(ob)

    elif ob.type == "CAMERA":
        out = export_camera_object(ob, exporter.scene)

    elif ob.type == "ARMATURE":
        out = export_armature_object(ob, exporter=exporter)

    else:
        raise TypeError("type '%s' is not supported yet" % (ob.type))

    # add matrix
    if exporter is not None:
        matrix = exporter._ob_map[ob][1]
    else:
        matrix = ob.matrix_local
    if matrix != MAT4_IDENTITY:
        out["matrix"] = matrix

    # add children
    if exporter is not None:
        out["children"] = [o for (o, (p, _))
                           in exporter._ob_map.items()
                           if p == ob]

    # userData
    if "userData" not in out:
        out["userData"] = OrderedDict()
    out["userData"].update(get_custom_props(ob, prefix="userData_"))

    # add custom/override properties
    out.update(get_custom_props(ob))

    return out
