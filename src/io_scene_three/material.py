# material.py

from bpy.types import Material
from bpy.path import clean_name

from collections import namedtuple, OrderedDict

from .util import get_uuid, get_custom_props
from .math import COLOR_WHITE


# name tuple to wrap Multi-Materials.
MultiMaterial = namedtuple("MultiMaterial", "name materials")


UV_MAPS = ("map",
           "alphaMap",
           "normalMap",
           "emissiveMap",
           "bumpMap",
           "displacementMap",
           "roughnessMap",
           "metalnessMap",
           )

UV2_MAPS = ("lightMap",
            "aoMap",
            )


# default material for unassigned faces
_DEFAULT_MATERIAL = OrderedDict()
_DEFAULT_MATERIAL["name"] = "DEFAULT_MATERIAL"
_DEFAULT_MATERIAL["type"] = "MeshStandardMaterial"
_DEFAULT_MATERIAL["color"] = COLOR_WHITE
_DEFAULT_MATERIAL["roughness"] = 0.5


def export_material(mat, exporter=None, _export_uuid=True):
    """

    """

    assert isinstance(mat, (Material, MultiMaterial, type(None))), \
        "export_material expects a `bpy.types.Material` arg"

    # use default material
    if mat is None:
        return _DEFAULT_MATERIAL

    # create material dict
    out = OrderedDict()
    out["uuid"] = get_uuid(mat) if _export_uuid else None
    out["name"] = clean_name(mat.name)

    if isinstance(mat, MultiMaterial):

        # create THREE.MultiMaterial
        out["type"] = "MultiMaterial"
        out["materials"] = iter(export_material(
            m, exporter=exporter, _export_uuid=False) for m in mat.materials)

    else:

        # create THREE.MeshStandardMaterial
        out["type"] = "MeshStandardMaterial"
        out["color"] = mat.diffuse_color * mat.diffuse_intensity
        if mat.roughness != 1.0:
            out["roughness"] = mat.roughness

        # transparency properties
        if mat.use_transparency:
            out["transparent"] = mat.use_transparency
            if mat.alpha > 0:
                out["opacity"] = 1.0 - mat.alpha
            # out["opacity"] = mat.alpha

        # use vertex colors
        if mat.use_vertex_color_paint:
            out["vertexColors"] = True

        # fog disabled?
        if not mat.use_mist:
            out["fog"] = False

        if exporter is not None:
            # add export texture maps
            texs = exporter._tex_map.get(mat)
            if texs:
                for n, v in texs.items():
                    if v is not None:
                        out[n] = get_uuid(v[0])

        # add custom/override properties
        out.update(get_custom_props(mat))

    return out
