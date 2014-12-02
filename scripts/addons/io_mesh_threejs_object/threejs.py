"""io_mesh_threejs_object.threejs

Blender Three.js Object Exporter Addon - Three.js dictionary helpers
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

import uuid

from collections import OrderedDict


def create_material(name):
    """
    returns an ordered dictionary of material properties

    Null (None) values are not exported by the custom JSON writer, so this
    template can be used for all material types by setting the appropriate
    values.
    """
    obj = OrderedDict()

    obj["name"] = name
    obj["type"] = "MeshBasicMaterial"
    obj["uuid"] = str(uuid.uuid4())
    obj["vertexColors"] = False
    obj["transparent"] = False
    obj["opacity"] = 1.0
    obj["color"] = 0
    obj["ambient"] = None
    obj["emissive"] = None
    obj["specular"] = None
    obj["shininess"] = None

    return obj


def create_buffergeometry(name, data):
    """
    """
    def create_attribute(type, itemSize, array):

        attr = OrderedDict()

        attr["type"] = type
        attr["itemSize"] = itemSize
        attr["array"] = array

        return attr

    obj = OrderedDict()

    obj["name"] = name
    obj["type"] = "BufferGeometry"
    obj["uuid"] = str(uuid.uuid4())
    obj["data"] = OrderedDict()
    attr = obj["data"]["attributes"] = OrderedDict()

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

    return obj


def create_object3d(name,
                    matrix=None,
                    userData=None,
                    ):
    """
    returns a dict representing a THREE.Object3D instance
    """
    obj = OrderedDict()

    obj["name"] = name
    obj["type"] = "Object3D"
    obj["uuid"] = str(uuid.uuid4())
    obj["matrix"] = matrix
    obj["userData"] = userData
    obj["children"] = list()

    return obj


def create_mesh(name,
                matrix=None,
                userData=None,
                geom=None,
                mat=None,
                ):
    """
    Returns a THREE.Mesh dict
    """
    obj = OrderedDict()

    obj["name"] = name
    obj["type"] = "Mesh"
    obj["uuid"] = str(uuid.uuid4())
    obj["matrix"] = matrix
    obj["userData"] = userData
    obj["geometry"] = geom
    obj["material"] = mat
    obj["children"] = list()

    return obj


def create_light(name,
                 type,
                 matrix=None,
                 userData=None,
                 color=None,
                 groundColor=None,
                 intensity=None,
                 distance=None,
                 angle=None,
                 exponent=None,
                 castShadow=None,
                 onlyShadow=None,
                 ):
    """
    """
    obj = OrderedDict()

    obj["name"] = name
    obj["type"] = type
    obj["uuid"] = str(uuid.uuid4())
    obj["matrix"] = matrix
    obj["userData"] = userData
    obj["color"] = color
    obj["groundColor"] = groundColor
    obj["intensity"] = intensity
    obj["distance"] = distance
    obj["angle"] = angle
    obj["exponent"] = exponent
    obj["castShadow"] = castShadow
    obj["onlyShadow"] = onlyShadow
    obj["children"] = list()

    def __str__():
        return " + THREE.%s: %s" % (type, name)

    obj.__str__ = __str__
    return obj


def create_output(object, mats, geoms):
    """
    """
    out = OrderedDict()

    md = out["metadata"] = OrderedDict()
    md["type"] = "Object"
    md["version"] = 4.3
    md["generator"] = ""

    out["object"] = object
    out["materials"] = mats
    out["geometries"] = geoms

    return out


def print_object(obj):
    """
    """
    print(" + THREE.%s: \"%s\"" % (obj["type"], obj["name"]))
    if "children" in obj:
        for c in obj["children"]:
            print_object(c)


# END OF FILE
