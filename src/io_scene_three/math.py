# io_scene_three - math.py

from mathutils import Matrix, Color

MAT4_IDENTITY = Matrix()
MAT4_ROT_X_PI2 = Matrix([
    [1, 0, 0, 0],
    [0, 0, 1, 0],
    [0, -1, 0, 0],
    [0, 0, 0, 1]
    ])

COLOR_BLACK = Color()
COLOR_WHITE = Color((1.0, 1.0, 1.0))


def export_matrix(m):
    """exports a `mathutils.Matrix` instance into a list of floats in the
    three.js matrix order

    :arg m (mathutils.Matrix): Blender matrix

    :returns (list): A list of float values representing a three.js 4x4 matrix
    """
    assert isinstance(m, Matrix), \
        "export_matrix() expects a `mathutils.Matrix` arg"

    return [m[0][0], m[2][0], -m[1][0], m[3][0],
            m[0][2], m[2][2], m[2][1], m[3][1],
            -m[0][1], m[1][2], m[1][1], m[3][2],
            m[0][3], m[2][3], -m[1][3], m[3][3]]


def sRGB2lin(v):
    """"""
    a = 0.055
    if v <= 0.04045:
        return v * (1.0 / 12.92)
    else:
        return pow((v + a) * (1.0 / (1 + a)), 2.4)


def lin2sRGB(v):
    """"""
    a = 0.055
    if v <= 0.0031308:
        return v * 12.92
    else:
        return (1 + a) * pow(v, 1 / 2.4) - a


def export_color(c, sRGB=False):
    """exports a `mathutils.Color` instance as an integer value"""

    assert isinstance(c, Color), \
        "encode_color() expects a `mathutils.Color` arg"

    if sRGB is True:
        c = Color([lin2sRGB(c.r), lin2sRGB(c.g), lin2sRGB(c.b)])

    return int(c.r * 255) << 16 ^ int(c.g * 255) << 8 ^ int(c.b * 255)
