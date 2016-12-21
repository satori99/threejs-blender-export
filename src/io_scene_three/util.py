# io_scene_three - util.py
from uuid import uuid5, NAMESPACE_DNS
from collections import OrderedDict
from mathutils import Matrix, Color
from idprop.types import IDPropertyArray


def traverse_visible_objects(scene, start_ob=None, selected_only=False):
    """yields each visible scene graph object, optionally starting from the
    specified object

    :arg scene (bpy.types.Scene): Blender scene to traverse
    :arg [start_ob] (bpy.types.ID): Optional Blender object to start from
    :arg [selected_only] (bool): only traverse selected objects

    :yields (bpy.types.ID): Each visible object in the scene
    """
    if start_ob is not None:
        if start_ob.is_visible(scene):
            if selected_only:
                if start_ob.select is True:
                    yield start_ob
            else:
                yield start_ob
        for child in start_ob.children:
            yield from traverse_visible_objects(scene,
                                                start_ob=child,
                                                selected_only=selected_only)
    else:
        for child in iter(o for o in scene.objects if o.parent is None):
            yield from traverse_visible_objects(scene,
                                                start_ob=child,
                                                selected_only=selected_only)


def get_uuid(ob):
    """Creates a determinsitic uuid based on an objects name and type

    NOTE: Any two objects with the same name and type will return the same UUID

    :arg ob (bpy.types.ID): Blender object

    :returns (str): A UUID string
    """
    return str(uuid5(NAMESPACE_DNS, str(ob)))


def get_custom_props(ob):
    """returns a dictionary of custom three_* properties for the specified object

    :arg ob (bpy.types.ID): Blender object

    :returns (dict): Dictionary containing any prefixed custom properties
    """
    prefix = "three_"
    out = OrderedDict()
    for k, v in ob.items():
        if k.startswith(prefix) and k.find(".") == -1:
            k = k.replace(prefix, "")
            if isinstance(v, IDPropertyArray):
                v = v.to_list()
            # return int 0 or 1 as bool
            elif (v == 1 or v == 0):
                v = bool(v)
            out[k] = v
    return out
