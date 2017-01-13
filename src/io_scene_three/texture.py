# texture.py

from bpy.types import Texture
from bpy.path import clean_name

from collections import OrderedDict

from .util import get_uuid, get_custom_props


THREE_UVMapping = 300
THREE_CubeReflectionMapping = 301

THREE_RepeatWrapping = 1000
THREE_MirroredRepeatWrapping = 1002

THREE_NearestFilter = 1003
THREE_NearestMipmapNearestFilter = 1004
THREE_NearestMipmapLinearFilter = 1005
THREE_LinearFilter = 1006
THREE_LinearMipmapNearestFilter = 1007


def export_texture(tex):
    """exports a Blender texture as a dictionary representing a
    THREE.Texture instance

    :arg tex (bpy.types.Texture): Blender Texture

    :returns (dict): A dictionary representing a THREE.texture instance
    """

    assert isinstance(tex, Texture), \
        "export_texture expects a `bpy.types.Texture` arg"

    # create THREE.Texture dict
    out = OrderedDict()
    out["uuid"] = get_uuid(tex)
    out["name"] = clean_name(tex.name)

    if tex.type == "ENVIRONMENT_MAP":

        out["type"] = "CubeTexture"
        out["mapping"] = THREE_CubeReflectionMapping

    else:

        out["type"] = "Texture"
        # out["mapping"] = THREE_UVMapping
        if tex.repeat_x != 1 or tex.repeat_y != 1:
            out["repeat"] = [tex.repeat_x, tex.repeat_y]
        # out["offset"] = [0, 0]

        # wrap
        if tex.extension == "CHECKER":
            out["wrap"] = [THREE_MirroredRepeatWrapping,
                           THREE_MirroredRepeatWrapping]
        elif tex.extension == "REPEAT":
            out["wrap"] = [THREE_RepeatWrapping,
                           THREE_RepeatWrapping]

        # filter
        if not tex.use_interpolation:
            out["magFilter"] = THREE_NearestFilter
            if not tex.use_mipmap:
                out["minFilter"] = THREE_NearestFilter
            else:
                if not tex.use_mipmap_gauss:
                    out["minFilter"] = THREE_NearestMipmapNearestFilter
                else:
                    out["minFilter"] = THREE_NearestMipmapLinearFilter
        else:
            if not tex.use_mipmap:
                out["magFilter"] = THREE_LinearFilter
            elif not tex.use_mipmap_gauss:
                out["minFilter"] = THREE_LinearMipmapNearestFilter

    out["anisotropy"] = 16

    out["image"] = get_uuid(tex.image)

    return out
