# image.py

from base64 import encodestring

from bpy.types import Image
from bpy.path import basename

from collections import OrderedDict

from .util import get_uuid


def _get_image_data(img):
    import bpy
    data = None
    tmp = img.copy()
    try:
        tmp.pack(as_png=True)
        data = tmp.packed_file.data
    finally:
        bpy.data.images.remove(tmp)
    return data


def _get_base64_str(data):
    return "".join(encodestring(data).decode(encoding="UTF-8").splitlines())


def _get_datauri(img):
    if img.packed_file:
        data = img.packed_file.data
    else:
        data = _get_image_data(img)
    return u"data:%s;base64,%s" % ("image/png", _get_base64_str(data))


def export_image(img, force_datauri=False):
    """exports a Blender image as a dictionary representing a three.js
    image instance

    GENERATED and Packed images will be exported as datauri's

    """
    assert isinstance(img, Image), \
        "export_image() expects a `bpy.types.Image instance"

    if (force_datauri or img.packed_file or img.source == "GENERATED"):
        # use base64 for generated or packed images
        url = _get_datauri(img)
    else:
        # use image file path
        url = basename(img.filepath)

    out = OrderedDict()

    out["uuid"] = get_uuid(img)
    out["name"] = img.name
    out["url"] = url

    return out
