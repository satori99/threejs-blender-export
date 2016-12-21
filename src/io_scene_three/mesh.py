# mesh.py

import bmesh

from bpy.types import Object, Material, Mesh
from bpy.path import clean_name

from collections import OrderedDict, namedtuple
from mathutils import Vector

from .util import get_uuid, get_custom_props
from .math import MAT4_ROT_X_PI2, COLOR_WHITE
from .material import UV_MAPS, UV2_MAPS

DEFAULT_UV = (0.0, 0.0)

# bmesh constants
MOD_TRIANGULATE_NGON_BEAUTY = 0
MOD_TRIANGULATE_QUAD_FIXED = 1

# named tuple to represent MESH objects with active modifiers. These objects
# data can't be shared, and needs a ref. to the object when encoding mesh data,
# so they are wrapped with this named tuple to differentiate them when
# exporting
ModifiedMesh = namedtuple("ModifiedMesh", "name object")


def export_mesh_object(ob, exporter=None):
    """Encodes a Blender MESH object into a dict representing a `THREE.Mesh`
    instance.

    :arg ob (bpy.types.Object(type="MESH")): Blender MESH object

    :returns (dict): A dictionary representing a `THREE.Mesh` instance
    """

    assert isinstance(ob, Object) and ob.type == "MESH", \
        "export_mesh_object() expects a`bpy.types.Object(type=\"MESH\")` arg"

    is_skinned = exporter is not None and ob in exporter._arm_map

    out = OrderedDict()
    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)

    # out["type"] = "SkinnedMesh" if is_skinned else "Mesh"
    out["type"] = "Mesh"

    if exporter is not None:
        geom = exporter._geom_map.get(ob)
        if geom:
            out["geometry"] = get_uuid(geom)
            mat = exporter._mat_map.get(ob)
            if mat:
                out["material"] = get_uuid(mat)
                if isinstance(mat, Material):
                    out["castShadow"] = mat.use_cast_shadows
                    out["receiveShadow"] = mat.use_shadows
                else:
                    out["castShadow"] = any(m.use_cast_shadows
                                            for m in mat.materials)
                    out["receiveShadow"] = any(m.use_shadows
                                               for m in mat.materials)

    return out


def export_mesh(ob_or_mesh, exporter=None):
    """Encodes a Blender MESH type into a dictionary representing a
    THREE.BufferGeometry instance

    :arg ob_or_mesh (.mesh.ModifiedMesh|bpy.types.Mesh):

    :returns (dict):
    """

    assert isinstance(ob_or_mesh, (Mesh, ModifiedMesh)), \
        "export_mesh() expects a `bpy.types.Mesh or ModifiedMesh` arg"

    def _parse_arg():
        if isinstance(ob_or_mesh, ModifiedMesh):
            return ob_or_mesh.object, ob_or_mesh.object.data
        else:
            return None, ob_or_mesh

    def _get_export_armature():
        arm, bone_map, vgroup_map = None, None, None
        if ob is not None and exporter is not None:
            if ob in exporter._arm_map:
                arm_ob = ob.find_armature()
                if arm_ob and len(ob.vertex_groups) > 0:
                    arm = arm_ob.data
            if arm is not None:
                # map export bones names to their index
                bone_map = dict()
                for index, bone in enumerate(exporter._bone_map[arm]):
                    bone_map[bone.name] = index
                # map vertex group names to bone index
                vgroup_map = dict()
                for name, index in iter((g.name, bone_map[g.name])
                                        for index, g in
                                        enumerate(ob.vertex_groups)
                                        if g.name in bone_map):
                    vgroup_map[name] = index
        return arm, bone_map, vgroup_map

    def _create_attribute(size):
        attr = OrderedDict()
        attr["type"] = "Float32Array"
        attr["itemSize"] = size
        attr["array"] = None
        return attr

    def _create_export_attributes():

        attrs = OrderedDict()
        attrs["position"] = _create_attribute(3)
        attrs["normal"] = _create_attribute(3)

        for mat in mesh.materials:

            if mat is None:
                continue

            if exporter is not None:

                textures = exporter._tex_map.get(mat, None)
                if textures is not None:

                    if 'uv' not in attrs and any(
                            True for m in UV_MAPS
                            for n, t in textures.items()
                            if t is not None and m == n):

                        attrs["uv"] = _create_attribute(2)

                    if 'uv2' not in attrs and any(
                            True for m in UV2_MAPS
                            for n, t in textures.items()
                            if t is not None and m == n):

                        attrs["uv2"] = _create_attribute(2)

            if 'color' not in attrs and mat.use_vertex_color_paint:
                attrs["color"] = _create_attribute(3)

        if arm is not None:
            attrs["skinIndex"] = _create_attribute(4)
            attrs["skinWeight"] = _create_attribute(4)

        return attrs

    def _create_index_attribute():
        attr = OrderedDict()
        attr["type"] = "Uint32Array"
        attr["itemSize"] = 1
        attr["array"] = []
        return attr

    def _create_bmesh():
        bm = bmesh.new()
        if ob is not None:
            bm.from_object(ob,
                           exporter.scene,
                           deform=True,
                           render=False,
                           face_normals=True)
        else:
            bm.from_mesh(mesh, face_normals=True)
        bm.transform(MAT4_ROT_X_PI2)
        bmesh.ops.split_edges(
            bm, edges=list(set(a for b in [
                           f.edges for f in bm.faces if not f.smooth
                           ] for a in b)))
        bmesh.ops.triangulate(bm,
                              faces=bm.faces,
                              quad_method=MOD_TRIANGULATE_QUAD_FIXED,
                              ngon_method=MOD_TRIANGULATE_NGON_BEAUTY)
        bm.verts.index_update()
        bm.verts.ensure_lookup_table()
        bm.faces.sort(key=lambda f: f.material_index)
        bm.faces.index_update()
        bm.faces.ensure_lookup_table()
        return bm

    def _get_uv_layer(mesh, bm, texs, uv2=False):

        if texs is None:
            return None

        uv_maps = UV2_MAPS if uv2 is True else UV_MAPS

        uv_name = next((v[1] for k, v in texs.items()
                       if v is not None and k in uv_maps), "")

        uv_layer = next((i for i, t in enumerate(mesh.uv_textures)
                        if t.name == uv_name), mesh.uv_textures.active_index)

        return bm.loops.layers.uv[uv_layer] if uv_layer > -1 else None

    def _update_bounds(co):
        min_vertex.x = min(min_vertex.x, co.x)
        min_vertex.y = min(min_vertex.y, co.y)
        min_vertex.z = min(min_vertex.z, co.z)
        max_vertex.x = max(max_vertex.x, co.x)
        max_vertex.y = max(max_vertex.y, co.y)
        max_vertex.z = max(max_vertex.z, co.z)

    def _create_group(start, count, mat_index):
        group = OrderedDict()
        group["start"] = start
        group["count"] = count
        group["materialIndex"] = mat_index
        return group

    def _get_vertex_data_iter(offset):
        # returns a flattened iterator for vertex data
        return iter(a for b in (v[offset] for v in vertex_map) for a in b)

    def _set_vertex_data_array(name, index):
        # set attribute array
        attributes[name]["array"] = _get_vertex_data_iter(index)

    def _set_vertex_data_arrays():
        # set geometry attribute arrays
        _set_vertex_data_array("position", 0)
        _set_vertex_data_array("normal", 1)
        if "uv" in attributes:
            _set_vertex_data_array("uv", 2)
        if "uv2" in attributes:
            _set_vertex_data_array("uv2", 3)
        if "color" in attributes:
            _set_vertex_data_array("color", 4)
        if "skinIndex" in attributes:
            _set_vertex_data_array("skinIndex", 5)
        if "skinWeight" in attributes:
            _set_vertex_data_array("skinWeight", 6)

    # parse input arg
    ob, mesh = _parse_arg()

    # get export armature, bones and vgroup map, in any
    arm, bones, vgroup_map = _get_export_armature()

    if arm is not None:

        # save original pose position and force REST pose
        pose_position = arm.pose_position
        if pose_position == "POSE":
            arm.pose_position = "REST"
            exporter.scene.update()

    # track spherical geometry bounds
    min_vertex, max_vertex = Vector(), Vector()

    # map unique vertices attribute tuples to their indices
    vertex_map = OrderedDict()

    # create indexed THREE.BufferGeometry dict
    out = OrderedDict()

    out["uuid"] = get_uuid(ob_or_mesh)
    out["name"] = clean_name(ob_or_mesh.name)
    out["type"] = "BufferGeometry"

    data = out["data"] = OrderedDict()

    attributes = data["attributes"] = _create_export_attributes()

    data["index"] = _create_index_attribute()
    index_array = data["index"]["array"]

    groups = data["groups"] = []
    bounding_sphere = data["boundingSphere"] = OrderedDict()

    # create bmesh instance
    bm = _create_bmesh()

    # process mesh by face material ...
    for mat_index, mat in enumerate(mesh.materials or [None]):

        # each material starts a new geometry group
        group_start = len(index_array)

        # get attr layers for this material
        texs = exporter._tex_map.get(mat)
        uv_layer = _get_uv_layer(mesh, bm, texs, uv2=False)
        uv2_layer = _get_uv_layer(mesh, bm, texs, uv2=True)
        color_layer = bm.loops.layers.color.active
        deform_layer = bm.verts.layers.deform.active

        # process eack mesh material face loop ...
        for face in iter(f for f in bm.faces if f.material_index == mat_index):
            for loop in face.loops:
                vert = loop.vert

                # update spherical bounds
                _update_bounds(vert.co)

                # create vertex data tuple
                position = vert.co.to_tuple()
                normal = vert.normal.to_tuple()

                uv, uv2, color, skin_index, skin_weight = \
                    None, None, None, None, None

                if "uv" in attributes:

                    if uv_layer is not None:

                        uv = loop[uv_layer].uv.to_tuple()

                    else:

                        uv = DEFAULT_UV

                if "uv2" in attributes:

                    if uv2_layer is not None:

                        uv2 = loop[uv2_layer].uv.to_tuple()

                    else:

                        uv2 = DEFAULT_UV

                if "color" in attributes:

                    if color_layer is not None:

                        color = tuple(loop[color_layer])

                    else:

                        color = COLOR_WHITE

                if "skinIndex" in attributes:

                    if deform_layer is not None:

                        deform_vert = vert[deform_layer]

                        vgroup_data = [
                            (vgroup_map[g.name], deform_vert.get(i, 0.0))
                            for i, g in enumerate(ob.vertex_groups)
                            if g.name in vgroup_map]

                        vgroup_data.sort(key=lambda x: x[1], reverse=True)

                        del vgroup_data[4:]

                        vgroup_data += [(0, 0.0)] * (4 - len(vgroup_data))

                        skin_index = tuple(w[0] for w in vgroup_data)
                        skin_weight = tuple(w[1] for w in vgroup_data)

                    else:

                        # default skin values
                        skin_index = (0, 0, 0, 0)
                        skin_weight = (0.0, 0.0, 0.0, 0.0)

                # map vertex data tuple
                vertex_data = (
                    position, normal, uv, uv2, color, skin_index, skin_weight)
                if vertex_data in vertex_map:
                    vertex_index = vertex_map[vertex_data]
                else:
                    vertex_index = len(vertex_map)
                    vertex_map[vertex_data] = vertex_index
                index_array.append(vertex_index)

        # create geometry group
        groups.append(_create_group(group_start,
                                    len(index_array) - group_start,
                                    mat_index))

    # free bmesh
    bm.free()

    # set geometry attribute arrays
    _set_vertex_data_arrays()

    # set bounding sphere data
    center = Vector(((min_vertex.x + max_vertex.x) / 2,
                    (min_vertex.y + max_vertex.y) / 2,
                    (min_vertex.z + max_vertex.z) / 2))
    bounding_sphere["center"] = list(center.to_tuple())
    bounding_sphere["radius"] = (max_vertex - center).length

    # add custom/override properties
    out.update(get_custom_props(mesh))

    # restore original pose position
    if arm is not None:
        arm.pose_position = pose_position
        exporter.scene.update()

    # done
    return out
