# armature.py

from bpy.types import Object
from bpy.path import clean_name

from collections import OrderedDict

from .util import get_uuid
from .math import MAT4_ROT_X_PI2


def export_bones(bone_list):
    """export a list of bones in the Three.js format
    """
    out = []
    for bone in bone_list:
        out_bone = OrderedDict()
        out_bone["name"] = clean_name(bone.name)
        if bone.parent in bone_list:
            parent_matrix = bone.parent.matrix_local
            bone_matrix = bone.matrix_local
            bone_matrix = parent_matrix.inverted() * bone_matrix
            pos, rot, scl = bone_matrix.decompose()
            out_bone["pos"] = [pos.x, pos.z, -pos.y]
            out_bone["parent"] = bone_list.index(bone.parent)
        else:
            bone_matrix = bone.matrix_local
            pos, rot, scl = bone_matrix.decompose()
            out_bone["pos"] = [pos.x, pos.z, -pos.y]
            out_bone["parent"] = -1
        out_bone["rotq"] = [rot.x, rot.z, -rot.y, rot.w]
        if any(s != 1.0 for s in scl):
            out_bone["scl"] = [scl.x, scl.z, scl.y]
        out.append(out_bone)
    return out


def export_armature_object(ob, exporter=None):
    """exports a Blender ARM Object as a dictionary representing a
    THREE.Group instance

    Note: Armature bones are included as userData and must be handled manually
    in app code!


    :returns (dict): A dictionary representing a THREE.Group instance
    """

    assert isinstance(ob, Object) and \
        ob.type == "ARMATURE", \
        "encode_armature_object() expects a " \
        "`bpy.types.Object(type='ARMATURE')` arg"

    # create object dict
    out = OrderedDict()
    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)
    out["type"] = "Group"

    if exporter is not None:
        # add bones to userData for now
        # should prbably check if there is exatcly one child mesh or not
        # and apply the bones there instead
        arm = exporter._arm_map.get(ob)
        if arm:
            userData = out["userData"] = OrderedDict()
            userData["bones"] = export_bones(exporter._bone_map[arm])

    return out
