"""io_mesh_threejs_object.export

Blender Three.js Object Exporter Addon - Export
"""

# The MIT License (MIT)
#
# Copyright (c) 2014 satori99
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import time
import uuid

from collections import (OrderedDict,
                         defaultdict,
                         namedtuple,
                         )
from mathutils import Matrix

import bpy
import bmesh

MOD_TRIANGULATE_QUAD_FIXED = 1
MOD_TRIANGULATE_NGON_BEAUTY = 0
DEL_FACES = 5

ROTATE_X_PI2 = Matrix([[1,  0,  0,  0],
                       [0,  0,  1,  0],
                       [0, -1,  0,  0],
                       [0,  0,  0,  1]])

from . import threejs
from . import json


# #############################################################################
# Global dictionaries.
# #############################################################################


# dict of THREE.Material dictionaries keyed by Blender material
_g_materials = dict()

# map of THREE.BufferGeometry dictionaries keyed by mesh name
_g_geometries = defaultdict(OrderedDict)

# A dict of shared THREE.BufferGeometry dictionaries keyed by mesh.data name
_g_shared_geometries = dict()

# map of THREE object dictionaries keyed by blender object
_g_objects = dict()

# global root object
_g_root_object = threejs.create_object3d("root")


def _clear_globals():
    """
    """
    for g in [_g_materials,
              _g_geometries,
              _g_shared_geometries,
              _g_objects,
              _g_root_object["children"]]:
        g.clear()


def _flatten_list(l):
    """
    """
    return [a for b in l for a in b]


def _map_seq_indices(seq):
    '''
    maps a sequence of values into a dict of unique
    keys and the indexes they were found at.
    '''
    map = defaultdict(list)
    for index, obj in enumerate(seq):
        map[obj].append(index)

    return map


def _color_to_int(color, intensity=1.0):
    '''
    Converts a blender color object to an integer value
    '''
    return int(color.r * intensity * 255) << 16 ^ \
        int(color.g * intensity * 255) << 8 ^ \
        int(color.b * intensity * 255)


def _select_objects(obs):
    """
    Deselects all objects, before selecting objects in the specified list
    """
    bpy.ops.object.select_all(action="DESELECT")
    for ob in obs:
        ob.select = True


def _get_descendants(ob):
    """
    Generator for object descendants, depth first recursively.
    """
    for c in ob.children:
        yield c
        for d in _get_object_descendants(c):
            yield d


def _get_uv_layers(uv_layers):
    """
    """
    uv_layer = uv_layers.active

    uv2_layer = None

    if len(uv_layers) > 1:
        if uv_layers[0] == uv_layer:
            uv2_layer = uv_layers[1]
        else:
            uv2_layer = uv_layers[0]

    return uv_layer, uv2_layer


def _flip_matrix(m):
    """
    Flips a blender matrix to the Three.js coord system, and flattens it
    into a row-major 1D list
    """
    return [
        m[0][0], m[2][0], -m[1][0], m[3][0],
        m[0][2], m[2][2], m[2][1], m[3][1],
        -m[0][1], m[1][2], m[1][1], m[3][2],
        m[0][3], m[2][3], -m[1][3], m[3][3]
    ]


def _get_matrix(ob, **props):
    """
    returns a objects matrix and the parent it is relative to.
    """
    uniform_scale = props["uniform_scale"]

    def _scale_matrix_position(m):

        m[0][3] *= uniform_scale
        m[1][3] *= uniform_scale
        m[2][3] *= uniform_scale

        return m

    # get the parent instance, if it exists ...
    if ob.parent in _g_objects:
        matrix = _scale_matrix_position(ob.matrix_local.copy())
        parent = _g_objects[ob.parent]

    # ...otherwise, use the root object as the parent
    else:
        matrix = _scale_matrix_position(ob.matrix_world.copy())
        parent = _g_root_object

    return _flip_matrix(matrix), parent


def _get_geometry(mesh,
                  scene,
                  apply_mesh_modifiers=True,
                  mesh_modifier_mode="RENDER",
                  uniform_scale=1.0,
                  split_by_material=True,
                  **props
                  ):
    """
    Generator for mesh geometry
    """
    # temp bmesh
    bm = bmesh.new()

    try:

        # fill the bmesh with modified vertex data
        if apply_mesh_modifiers:
            render = mesh_modifier_mode == 'RENDER'
            bm.from_object(mesh, scene, render=render, face_normals=False)

        # fill the bmesh with edit mesh data
        else:
            bm.from_mesh(mesh.data, face_normals=False)

        # transform bmesh verts to three.js coords, and scale
        bm.transform(ROTATE_X_PI2 * Matrix.Scale(uniform_scale, 4))

        # bake flat faces into mesh
        flat_edges = set()
        for face in bm.faces:
            if not face.smooth:
                flat_edges.update(face.edges)
        bmesh.ops.split_edges(bm, edges=list(flat_edges))

        # triangulate
        bm.calc_tessface()  # gets rid of ngons?
        bmesh.ops.triangulate(bm,
                              faces=bm.faces,
                              quad_method=MOD_TRIANGULATE_QUAD_FIXED,
                              ngon_method=MOD_TRIANGULATE_NGON_BEAUTY)
        bm.normal_update()

        # determine if the mesh should be split by material.
        if not split_by_material or not mesh.data.materials:
            mat = mesh.data.materials[0] if mesh.data.materials else None

            # yield mesh data
            yield mat, bm

        # loop through unique materials ...
        else:
            for mat, index_list in \
                    _map_seq_indices(mesh.data.materials).items():

                # temp material mesh
                mat_bm = bm.copy()
                try:

                    # delete non-material faces
                    geom = [f for f in mat_bm.faces
                            if f.material_index not in index_list]
                    bmesh.ops.delete(mat_bm, geom=geom, context=DEL_FACES)

                    # yield mesh data
                    if len(mat_bm.faces) > 0:
                        yield mat, mat_bm

                # always free temp material mesh
                finally:
                    mat_bm.free()

    # always free temp mesh
    finally:
        bm.free()


def _export_objects(context, **props):
    """
    Generator for export objects
    """
    types = props["object_types"]
    selected_only = props["selected_only"]
    include_descendents = props["include_descendants"]

    # filter selected objects by type
    if selected_only:
        for ob in [o for o in context.selected_objects
                   if not o.hide and o.type in types]:
            yield ob

            # select all visible descendent types
            if include_descendents:
                for d in _get_descendants(ob):
                    if not d.hide and d.type in types:
                        yield d

    # filter all scene objects by type
    else:
        for ob in [o for o in context.scene.objects
                   if not o.hide and o.type in types]:
            yield ob


def _export_material(mat):
    """
    parses a blender material object into an OrderedDict representing a
    Three.js material instance
    """
    # ignore null materials
    if not mat:
        return None

    # create three material instance
    obj = threejs.create_material(mat.name)

    # common material properties
    obj["vertexColors"] = mat.use_vertex_color_paint
    obj["transparent"] = mat.use_transparency
    obj["opacity"] = mat.alpha if mat.use_transparency else 1.0
    obj["color"] = _color_to_int(mat.diffuse_color,
                                 mat.diffuse_intensity)

    # if 'shadeless' is checked, save this material
    # as a Three.js MeshBasicMaterial type.
    if mat.use_shadeless:
        obj["type"] = "MeshBasicMaterial"

    # Lambert/Phong common properties
    else:
        obj["ambient"] = _color_to_int(mat.diffuse_color, mat.ambient)
        obj["emissive"] = _color_to_int(mat.diffuse_color, mat.emit)

        # if material has no specular component, save it as a
        # Three.js MeshLambertMaterial type.
        if mat.specular_intensity == 0:
            obj["type"] = "MeshLambertMaterial"

        # Phong properties
        else:
            obj["type"] = "MeshPhongMaterial"
            obj["shininess"] = int(mat.specular_hardness / 3)
            obj["specular"] = _color_to_int(mat.specular_color,
                                            mat.specular_intensity)

    # done
    threejs.print_object(obj)

    return obj


def _export_animation(mesh, scene, morphs, **props):
    """
    morph_animations=
    {
        <Material.000>: {
            "FlagAction_000": [ verts, ... ],
            "FlagAction_000": [ verts, ... ],
            "FlagAction_000": [ verts, ... ],
        },
        <Material.000>: {
            "FlagAction_000": [ verts, ... ],
            "FlagAction_000": [ verts, ... ],
            "FlagAction_000": [ verts, ... ],
        }
    }
    """

    action = mesh.animation_data.action

    morph_data = dict()

    print("Exporting morph_animations:", action.name)

    for index, frame in enumerate(range(scene.frame_start,
                                        scene.frame_end,
                                        scene.frame_step)):

        name = "%s_%03d" % (action.name, index)

        # print("%s (%s)" % (name, frame))

        scene.frame_set(frame)

        for mat, bm in _get_geometry(mesh, scene, **props):

            morph_indices = morphs[mat]

            # print("Processing %d indices ... " % (len(morph_indices)))

            if mat in morph_data:
                # print("Getting existing morph targets ... ")
                morph_targets = morph_data[mat]
            else:
                # print("Creating morph targets %s ... ")
                morph_targets = morph_data[mat] = OrderedDict()

            morph_verts = morph_targets[name] = list()

            for i in morph_indices:

                vert = bm.verts[i].co.to_tuple()

                morph_verts += vert

    return morph_data


def _export_geometry(mesh, scene, **props):
    """
    Generator for mesh geometries

    yields a material and a THREE.BufferGeometry dictionary for each sub-mesh
    """
    apply_mesh_modifiers = props["apply_mesh_modifiers"]
    morph_animations = props["morph_animations"]
    export_uvs = props["export_uvs"]
    export_uv2s = props["export_uv2s"]
    export_colors = props["export_colors"]
    export_index = props["export_index"]

    morph_animations = morph_animations and mesh.animation_data

    # only check for, and re-use matching shared geometry if this mesh
    # has no modifiers or we are not applying them ...
    use_shared = not morph_animations and (
        not mesh.modifiers or not apply_mesh_modifiers)

    # yield the uuid's for each shared geometry ...
    if use_shared and mesh.data.name in _g_shared_geometries:
        for mat, geom in _g_shared_geometries[mesh.data.name].items():
            # mat_id = _g_materials[mat]["uuid"] if mat else None
            # geom_id = geom["uuid"]
            yield mat, geom

    # otherwise, create the geometry for this mesh object.
    else:
        geoms = dict()
        if morph_animations:
            morphs = dict()
        for mat, bm in _get_geometry(mesh, scene, **props):

            # parse material
            if mat not in _g_materials:
                _g_materials[mat] = _export_material(mat)

            # get uv layers
            if export_uvs:
                uv_layer, uv2_layer = _get_uv_layers(bm.loops.layers.uv)
                export_uvs = export_uvs and uv_layer
                export_uv2s = export_uvs and export_uv2s and uv2_layer

            # get color layer
            if export_colors:
                color_layer = bm.loops.layers.color.active
                export_colors = export_colors and color_layer

            # create vertex data->index map
            if export_index:
                vertex_map = dict()

            if morph_animations:
                morph_data = morphs[mat] = list()

            # create vertex data arrays
            data = defaultdict(list)

            # append data to the vertex data arrays
            def appendVertex(vertex):
                data["position"] += vertex["position"]
                data["normal"] += vertex["normal"]
                if export_uvs:
                    data["uv"] += vertex["uv"]
                    if export_uv2s:
                        data["uv2"] += vertex["uv2"]
                if export_colors:
                    data["color"] += vertex["color"]

            # populate vertex data arrays
            for face in bm.faces:
                for loop in face.loops:

                    # create vertex data
                    vertex = OrderedDict()
                    vertex["position"] = loop.vert.co.to_tuple()
                    vertex["normal"] = loop.vert.normal.to_tuple()

                    if export_uvs:
                        vertex["uv"] = loop[uv_layer].uv.to_tuple()
                        if export_uv2s:
                            vertex["uv2"] = loop[uv2_layer].uv.to_tuple()

                    if export_colors:
                        color = loop[color_layer]
                        vertex["color"] = (color.r, color.g, color.b)

                    # Indexed BufferGeometry
                    if export_index:
                        # Get existing vertex index ...
                        key = tuple(vertex.values())
                        if key in vertex_map:
                            index = vertex_map[key]

                        # ... or map a new vertex
                        else:
                            index = len(vertex_map)
                            vertex_map[key] = index

                            # append vertex data
                            appendVertex(vertex)
                            if morph_animations:
                                morph_data.append(loop.vert.index)

                        # append index
                        data["index"].append(index)

                    # Non-indexed BufferGeometry
                    else:
                        appendVertex(vertex)
                        if morph_animations:
                            morph_data.append(loop.vert.index)

            # print("positions", int(len(data["position"]) / 3))

            # create buffergeometry
            name = "%s:%s" % (mesh.data.name, mat.name if mat else None)
            geom = threejs.create_buffergeometry(name, data)
            geoms[mat] = geom
            # yield mat, geom

        # export morph animation
        if morph_animations:

            m_data = _export_animation(mesh, scene, morphs, **props)

            for mat, targets in m_data.items():
                print(mat)
                for target_name, positions in targets.items():
                    print("\t", target_name, len(positions))

            for mat, data in m_data.items():
                geom = geoms[mat]
                morph_targets = geom["data"]["morphTargets"]
                positions = geom["data"]["attributes"]["position"]["array"]
                for name, verts in data.items():
                    assert(len(verts) == len(positions))
                    target = OrderedDict()
                    target["name"] = name
                    target["vertices"] = verts
                    morph_targets.append(target)

        # store mesh geomtries
        _g_geometries[mesh.name] = geoms
        if use_shared:
            _g_shared_geometries[mesh.data.name] = geoms

        for mat, geom in geoms.items():
            threejs.print_object(geom)
            yield mat, geom


def _export_mesh(mesh, scene, **props):
    """
    """
    morphs_in_userdata = props["morphs_in_userdata"]

    # create mesh parent object
    matrix, parent = _get_matrix(mesh, **props)
    obj = threejs.create_object3d(mesh.name, matrix=matrix)
    children = obj["children"]

    # create a new sub-mesh for each mesh geometry
    for mat, geom in _export_geometry(mesh, scene, **props):
        name = "%s:%s" % (mesh.name, mat.name if mat else None)
        child_mesh = threejs.create_mesh(name,
                                         geom=geom["uuid"],
                                         mat=_g_materials[mat]["uuid"]
                                         if mat else None
                                         )

        # move animation to userData
        geom_data = geom["data"]
        geom_morphtargets = geom_data["morphTargets"]
        if geom_morphtargets and morphs_in_userdata:
            child_mesh["userData"]["morphTargets"] = geom_morphtargets
            del geom_data["morphTargets"]

        # append child mesh
        children.append(child_mesh)

    # promote first child object if it is the only child
    if len(children) == 1:
        child = children[0]
        child["matrix"] = obj["matrix"]
        child["userData"] = obj["userData"]
        obj = child

    # append mesh objects
    parent["children"].append(obj)

    _g_objects[mesh] = obj

    threejs.print_object(obj)


def _export_lamp(lamp, scene, **props):
    """
    """
    matrix, parent = _get_matrix(lamp, **props)

    data = lamp.data

    if data.type == 'SUN':

        location = [1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                    matrix[12], matrix[13], matrix[14], 1]

        obj = threejs.create_light(lamp.name,
                                   "DirectionalLight",
                                   matrix=location,
                                   color=_color_to_int(data.color),
                                   intensity=data.energy,
                                   )

    elif data.type == 'HEMI':

        location = [1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                    matrix[12], matrix[13], matrix[14], 1]

        obj = threejs.create_light(lamp.name,
                                   "HemisphereLight",
                                   matrix=location,
                                   color=_color_to_int(data.color),
                                   groundColor=_color_to_int(data.color),
                                   intensity=data.energy,
                                   )

    elif data.type == 'POINT':
        obj = threejs.create_light(lamp.name,
                                   "PointLight",
                                   matrix=matrix,
                                   color=_color_to_int(data.color),
                                   intensity=data.energy,
                                   distance=data.distance,
                                   )

    elif data.type == 'SPOT':
        castShadow = data.shadow_method != "NOSHADOW"
        onlyShadow = castShadow and data.use_only_shadow
        obj = threejs.create_light(lamp.name,
                                   "SpotLight",
                                   matrix=matrix,
                                   color=_color_to_int(data.color),
                                   intensity=data.energy,
                                   distance=data.distance,
                                   angle=data.spot_size,
                                   exponent=data.spot_blend,
                                   castShadow=castShadow,
                                   onlyShadow=onlyShadow,
                                   )

    else:

        raise NotImplementedError('TODO: Parse light type:', data.type)

    parent["children"].append(obj)

    _g_objects[lamp] = obj

    threejs.print_object(obj)


def _export_ambient(scene, **props):
    """
    """

    print('scene.world.ambient_color', scene.world.ambient_color)

    ambient = threejs.create_light(
        "Ambient",
        "AmbientLight",
        color=_color_to_int(scene.world.ambient_color)
        )

    # ambient["_hex"] = hex(ambient["color"])

    threejs.print_object(ambient)
    _g_root_object["children"].append(ambient)


# Export


def export(context, **props):
    """
    """

    float_precision = props["float_precision"]
    filepath = props["filepath"]
    object_types = props["object_types"]
    export_ambient = props["export_ambient"]

    start = time.time()
    scene = context.scene

    # set object mode
    if scene.objects.active:
        bpy.ops.object.mode_set(mode="OBJECT")

    # get current selected objects
    sel_obs = context.selected_objects[:]

    # get current frome number
    sel_frame = scene.frame_current

    try:

        # export each scene object
        for ob in _export_objects(context, **props):
            print("\nExporting %s: %s\n" % (ob.type, ob.name))
            if ob.type == "MESH":
                _export_mesh(ob, scene, **props)
            elif ob.type == "LAMP":
                _export_lamp(ob, scene, **props)
            else:
                print("\n!TODO: Parse %s objects!\n" % (ob.type))

        # export ambient light
        if "LAMP" in object_types and export_ambient:
            print("\nExporting %s: %s\n" % (ob.type, ob.name))
            _export_ambient(scene, **props)

        # create output content
        content = threejs.create_output(
            _g_root_object,
            list(_g_materials.values()),
            _flatten_list([g.values() for g in
                           _g_geometries.values()])
            )

        # export has completed
        duration = time.time() - start
        print("\nParsed scene objects in %.2fs." % (duration))

        # write to file...
        print("\nWriting %s ... " % (filepath), end="")
        file = open(filepath, "w+", encoding="utf8", newline="\n")

        # ... using custom JSON writer.
        json.dump(content, file, props["float_precision"])

        # finished exporting
        file.close()
        print("done.")

    finally:

        # always clear globals
        _clear_globals()

        # always restore initial object selection
        _select_objects(sel_obs)

        # always restore initial selected frome
        scene.frame_set(sel_frame)

    # export has completed
    duration = time.time() - start
    print("\nCompleted in %.2fs." % (duration))


# END OF FILE
