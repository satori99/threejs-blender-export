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


# Three.js dict helpers


def _three_create_material(name):
    """
    """
    object = OrderedDict()

    object["name"] = name
    object["type"] = None
    object["uuid"] = str(uuid.uuid4())
    object["vertexColors"] = False
    object["transparent"] = False
    object["opacity"] = 1.0
    object["color"] = 0
    object["ambient"] = None
    object["emissive"] = None
    object["specular"] = None
    object["shininess"] = None

    def __str__():
        return "THREE.Material: %s" % (name)

    object.__str__ = __str__
    return object


def _three_create_object3d(name, matrix=None):
    '''
    returns a dict representing a THREE.Object3D instance
    '''

    if matrix:
        matrix = _flip_matrix(matrix)

    object = OrderedDict()

    object["name"] = name
    object["type"] = "Object3D"
    object["uuid"] = str(uuid.uuid4())
    object["matrix"] = matrix
    object["children"] = list()

    def __str__():
        return "THREE.Object3D: %s" % (name)

    object.__str__ = __str__
    return object


def _three_create_mesh(name, matrix=None, geom=None, mat=None):
    '''
    Returns a THREE.Mesh dict
    '''
    mesh = OrderedDict()

    mesh["name"] = name
    mesh["type"] = "Mesh"
    mesh["uuid"] = str(uuid.uuid4())
    mesh["matrix"] = matrix
    mesh["geometry"] = geom
    mesh["material"] = mat
    mesh["children"] = list()

    def __str__():
        return "THREE.Mesh: %s" % (name)

    mesh.__str__ = __str__
    return mesh


def _three_create_buffergeometry(name, data):
    """
    """

    def create_attribute(type, itemSize, array):

        attr = OrderedDict()

        attr["type"] = type
        attr["itemSize"] = itemSize
        attr["array"] = array

        return attr

    geom = OrderedDict()

    geom["name"] = name
    geom["type"] = "BufferGeometry"
    geom["uuid"] = str(uuid.uuid4())
    geom["data"] = OrderedDict()
    attr = geom["data"]["attributes"] = OrderedDict()

    for attr_name, array in data.items():
        if attr_name == "index":
            type = "Uint32Array"
            itemSize = 1
        else:
            type = "Float32Array"
            if attr_name in ("uv", "uv2"):
                itemSize = 2
            else:
                type = "Float32Array"
                itemSize = 3
        attr[attr_name] = create_attribute(type, itemSize, array)

    def __str__():
        return "THREE.BufferGeometry: %s" % (name)

    geom.__str__ = __str__
    return geom


def _three_create_output(object, mats, geoms):
    '''
    '''
    out = OrderedDict()

    # create output metadata
    md = out["metadata"] = OrderedDict()
    md["type"] = "Object"
    md["version"] = 4.3
    md["generator"] = ""

    # create output data
    out["object"] = object
    out["materials"] = mats
    out["geometries"] = geoms

    return out


# Global dictionaries.


# dict of THREE.Material dictionaries keyed by Blender material
_g_materials = dict()

# map of THREE.BufferGeometry dictionaries keyed by mesh name
_g_geometries = defaultdict(OrderedDict)

# A dict of shared THREE.BufferGeometry dictionaries keyed by mesh.data name
_g_shared_geometries = dict()

# map of THREE object dictionaries keyed by blender object
_g_objects = dict()

# global root object
_g_root_object = _three_create_object3d("root")


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


def _flip_matrix(m):
    """
    """
    return [
        m[0][0], m[2][0], -m[1][0], m[3][0],
        m[0][2], m[2][2], m[2][1], m[3][1],
        -m[0][1], m[1][2], m[1][1], m[3][2],
        m[0][3], m[2][3], -m[1][3], m[3][3]
    ]


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

    return matrix, parent


def _get_geometry(mesh, scene, **props):
    """
    Generator for mesh geometry
    """
    apply_mesh_modifiers = props["apply_mesh_modifiers"]
    mesh_modifier_mode = props["mesh_modifier_mode"]
    uniform_scale = props["uniform_scale"]
    export_normals = props["export_normals"]
    split_by_material = props["split_by_material"]

    bm = bmesh.new()

    try:

        # fill the bmesh with vertex data
        if apply_mesh_modifiers:

            render = mesh_modifier_mode == 'RENDER'

            bm.from_object(mesh, scene, render=render, face_normals=False)

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

        # re-calculate normals
        if export_normals:
            bm.normal_update()

        # determine if the mesh should be split by material.
        if not split_by_material or not mesh.data.materials:

            # yield the entire mesh with the first material
            mat = mesh.data.materials[0] if mesh.data.materials else None

            yield mat, bm

        else:

            # loop through unique materials ...
            for mat, index_list in \
                    _map_seq_indices(mesh.data.materials).items():

                mat_bm = bm.copy()

                try:

                    geom = [f for f in mat_bm.faces
                            if f.material_index not in index_list]

                    bmesh.ops.delete(mat_bm, geom=geom, context=DEL_FACES)

                    if len(mat_bm.faces) > 0:

                        yield mat, mat_bm

                finally:

                    mat_bm.free()

    finally:

        bm.free()


def _export_objects(context, **props):
    """
    Generator for export objects
    """
    types = props["object_types"]
    selected_only = props["selected_only"]
    include_descendents = props["include_descendants"]

    if selected_only:

        # filter selected objects by type
        for ob in [o for o in context.selected_objects if o.type in types]:
            yield ob
            if include_descendants:
                # select all visible descendent types
                for d in _get_descendants(ob):
                    if not d.hide and d.type in types:
                        yield d

    else:

        # filter all scene objects by type
        for ob in [o for o in context.scene.objects if o.type in types]:
            yield ob


def _export_material(mat):
    """
    """
    '''
    parses a blender material object into an OrderedDict representing a
    Three.js material instance
    '''
    # ignore null materials
    if not mat:
        return None

    object = _three_create_material(mat.name)

    if mat.use_shadeless:

        # if 'shadeless' is checked, save this material
        # as a Three.js MeshBasicMaterial type.
        object["type"] = "MeshBasicMaterial"

    else:

        # Lambert/Phong common properties
        object["ambient"] = _color_to_int(mat.diffuse_color, mat.ambient)
        object["emissive"] = _color_to_int(mat.diffuse_color, mat.emit)

        if mat.specular_intensity == 0:

            # if material has no specular component, save it as a
            # Three.js MeshLambertMaterial type.
            object["type"] = "MeshLambertMaterial"

        else:

            # Phong properties
            object["type"] = "MeshPhongMaterial"
            object["specular"] = _color_to_int(mat.specular_color,
                                               mat.specular_intensity)
            object["shininess"] = int(mat.specular_hardness / 3)

    print(object.__str__())
    return object


def _export_geometry(mesh, scene, **props):
    """

    """
    apply_mesh_modifiers = props["apply_mesh_modifiers"]
    export_normals = props["export_normals"]
    export_uvs = props["export_uvs"]
    export_colors = props["export_colors"]
    export_index = props["export_index"]

    # only check for, and re-use matching shared geometry if this mesh
    # has no modifiers or we are not applying them ...
    use_shared = not mesh.modifiers or not apply_mesh_modifiers

    if use_shared and mesh.data.name in _g_shared_geometries:

        # yield the uuid's for each shared geometry
        for mat, geom in _g_shared_geometries[mesh.data.name].items():

            print("GOT SHARED:", geom["name"])

            mat_id = _g_materials[mat]["uuid"] if mat else None

            geom_id = geom["uuid"]

            yield mat_id, geom_id

    else:

        geoms = dict()

        for mat, bm in _get_geometry(mesh, scene, **props):

            # parse material
            if mat not in _g_materials:

                _g_materials[mat] = _export_material(mat)

            mat_id = _g_materials[mat]["uuid"] if mat else None

            # get uv layer
            if export_uvs:
                uv_layer = bm.loops.layers.uv.active
                export_uvs = export_uvs and uv_layer

            # get color layer
            if export_colors:
                color_layer = bm.loops.layers.color.active
                export_colors = export_colors and color_layer

            # create vertex data->index map
            if export_index:
                vertex_map = dict()

            # create vertex data arrays
            data = defaultdict(list)

            # append data to the vertex data arrays
            def appendVertex(vertex):

                data["position"] += vertex["position"]

                if export_normals:

                    data["normal"] += vertex["normal"]

                if export_uvs:

                    data["uv"] += vertex["uv"]

                if export_colors:

                    data["color"] += vertex["color"]

            # process each face vertex
            for face in bm.faces:

                for loop in face.loops:

                    # create vertex data
                    vertex = OrderedDict()

                    vertex["position"] = loop.vert.co.to_tuple()

                    if export_normals:
                        vertex["normal"] = loop.vert.normal.to_tuple()

                    if export_uvs:
                        vertex["uv"] = loop[uv_layer].uv.to_tuple()

                    if export_colors:
                        color = loop[color_layer]
                        vertex["color"] = (color.r, color.g, color.b)

                    if export_index:

                        # check for existing vertex
                        key = tuple(vertex.values())
                        if key in vertex_map:
                            index = vertex_map[key]

                        # create new vertex
                        else:
                            index = len(vertex_map)
                            vertex_map[key] = index
                            appendVertex(vertex)

                        data["index"].append(index)

                    else:
                        appendVertex(vertex)

            name = "%s.%s" % (mesh.name, mat.name if mat else None)
            geom = _three_create_buffergeometry(name, data)

            print(geom.__str__())

            geoms[mat] = geom

            geom_id = geom["uuid"]

            yield mat_id, geom_id

        # store mesh geomtries
        _g_geometries[mesh.name] = geoms
        if use_shared:
            _g_shared_geometries[mesh.data.name] = geoms


def _export_mesh(mesh, scene, **props):
    """
    """

    matrix, parent = _get_matrix(mesh, **props)

    object = _three_create_object3d(mesh.name, matrix=matrix)

    children = object["children"]

    for mat, geom in _export_geometry(mesh, scene, **props):

        children.append(_three_create_mesh(mesh.name, geom=geom, mat=mat))

    if len(children) == 1:

        child = children[0]

        child["matrix"] = object["matrix"]

        object = child

    parent["children"].append(object)

    _g_objects[mesh] = object

    print(object.__str__())

    for c in object["children"]:

        print(c.__str__())


def export(context, **props):
    """
    """
    print("Exporting Three.js Objects ...")

    filepath = props["filepath"]
    float_precision = props["float_precision"]

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

        for ob in _export_objects(context, **props):

            print("Exporting %s: %s" % (ob.type, ob.name))

            if ob.type == "MESH":
                _export_mesh(ob, scene, **props)

            else:
                print("TODO: Parse %s objects" % (ob.type))

        # create output content
        if len(_g_root_object["children"]) == 1:
            object = _g_root_object["children"][0]
        else:
            object = _g_root_object

        content = _three_create_output(
            object,
            list(_g_materials.values()),
            _flatten_list([g.values() for g in
                           _g_geometries.values()])
            )

        # export has completed
        duration = time.time() - start
        print("\nParsed scene objects in %.2fs." % (duration))

        # write to file.
        print("\nWriting %s ... " % (filepath), end="")

        file = open(filepath, "w+", encoding="utf8", newline="\n")

        from . import json

        json.dump(content, file, props["float_precision"])

        file.close()

        print("done.")

    finally:

        # always clear globals
        _clear_globals()

        # always restore initial object selection
        _select_objects(sel_obs)

        # always restore initial selected frome
        scene.frame_current = sel_frame

    # export has completed
    duration = time.time() - start

    print("\nCompleted in %.2fs." % (duration))


# END OF FILE
