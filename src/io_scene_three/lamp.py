# lamp.py
from bpy.types import Scene, Object
from bpy.path import clean_name
from collections import OrderedDict

from .util import get_uuid, get_custom_props
from .math import COLOR_BLACK


def export_ambient_light(scene):
    """exports Blender Scene ambient light properties as a dictionary
    representing a THREE.AmbientLight instance.

    :arg scene (bpy.types.Scene): Blender Scene

    :returns (dict): A Dictionary representing three.js AmbientLight type
    """

    out = None

    if scene.world and scene.world.ambient_color != COLOR_BLACK:

        out = OrderedDict()
        out["name"] = "Ambient"
        out["type"] = "AmbientLight"
        out["color"] = scene.world.ambient_color

        print("-> THREE.AmbientLight()")

    return out


def export_hemi_lamp_object(ob):
    """exports a Blender HEMI LAMP Object as a dictionary repesenting a
    THREE.HemisphereLight instance

    :arg ob (bpy.types.Object(type="LAMP").data(type="HEMI")): Blender
        HEMI light object

    :returns (dict): A dictionary repesenting a THREE.HemisphereLight instance
    """

    assert isinstance(ob, Object) and \
        ob.type == "LAMP" and \
        ob.data.type == "HEMI", \
        "encode_sun_lamp() expects a " \
        "`bpy.types.Object(type=\"LAMP\").data(type=\"HEMI\")` arg"

    out = OrderedDict()

    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)
    out["type"] = "HemisphereLight"

    out["color"] = ob.data.color
    out["groundColor"] = ob.data.color * 0.5  # for now
    out["intensity"] = ob.data.energy

    return out


def export_point_lamp_object(ob):
    """exports a Blender POINT LAMP Object as a dictionary repesenting a
    THREE.PointLight instance

    :arg ob (bpy.types.Object(type="LAMP").data(type="POINT")): Blender POINT
        lamp object

    :returns (dict): A dictionary repesenting a THREE.PointLight instance
    """

    assert isinstance(ob, Object) and \
        ob.type == "LAMP" and \
        ob.data.type == "POINT", \
        "export_point_lamp() expects a " \
        "`bpy.types.Object(type=\"LAMP\").data(type=\"POINT\")` arg"

    out = OrderedDict()

    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)
    out["type"] = "PointLight"
    out["color"] = ob.data.color

    # todo: more pointlight props

    return out


def export_sun_lamp_object(ob):
    """

    """

    assert isinstance(ob, Object) and \
        ob.type == "LAMP" and \
        ob.data.type == "SUN", \
        "export_sun_lamp_object() expects a " \
        "`bpy.types.Object(type=\"LAMP\").data(type=\"SUN\")` arg"

    out = OrderedDict()

    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)
    out["type"] = "DirectionalLight"
    out["color"] = ob.data.color
    out["intensity"] = ob.data.energy

    if ob.data.shadow_method != "NOSHADOW":

        out["castShadow"] = True
        shadow = out["shadow"] = OrderedDict()
        shadow["bias"] = ob.data.shadow_buffer_bias - 1
        shadow["mapSize"] = [ob.data.shadow_buffer_size,
                             ob.data.shadow_buffer_size]

        camera = shadow["camera"] = OrderedDict()
        camera["name"] = out["name"] + "ShadowCamera"
        camera["type"] = "OrthographicCamera"

        frustum_size = ob.data.shadow_frustum_size

        camera["top"] = ob.data.get('three_camera.top') or frustum_size
        camera["bottom"] = ob.data.get('three_camera.bottom') or -frustum_size
        camera["left"] = ob.data.get('three_camera.left') or -frustum_size
        camera["right"] = ob.data.get('three_camera.right') or frustum_size

        camera["near"] = ob.data.shadow_buffer_clip_start
        camera["far"] = ob.data.shadow_buffer_clip_end

        # add custom/override shadowcam properties
        shadow.update(get_custom_props(ob.data))

    return out


def export_spot_lamp_object(ob):
    """

    """

    assert isinstance(ob, Object) and \
        ob.type == "LAMP" and \
        ob.data.type == "SPOT", \
        "export_spot_lamp_object() expects a " \
        "`bpy.types.Object(type=\"LAMP\").data(type=\"SPOT\")` arg"

    out = OrderedDict()

    out["uuid"] = get_uuid(ob)
    out["name"] = clean_name(ob.name)
    out["type"] = "SpotLight"
    out["color"] = ob.data.color
    out["intensity"] = ob.data.energy
    out["distance"] = ob.data.distance
    out["angle"] = ob.data.spot_size / 2
    out["penumbra"] = ob.data.spot_blend
    # out["decay"]     = X
    # todo: spotlight shadow camera props

    return out


def export_lamp_object(ob):
    """exports a Blender LAMP object as a dictionary representing a
    THREE.*Light instance

    :arg ob (bpy.types.Object(type="LAMP")): Blender POINT lamp object

    """

    assert isinstance(ob, Object) and \
        ob.type == "LAMP", \
        "export_lamp_object() expects a " \
        "`bpy.types.Object(type=\"LAMP\")` arg"

    type = ob.data.type

    if type == "HEMI":
        return export_hemi_lamp_object(ob)

    elif type == "POINT":
        return export_point_lamp_object(ob)

    elif type == "SUN":
        return export_sun_lamp_object(ob)

    elif type == "SPOT":
        return export_spot_lamp_object(ob)

    else:
        raise TypeError("LAMP type '%s' is not supported yet" % (type))
