"""io_mesh_threejs_object.json

Blender Three.js Object Exporter Addon - Custom JSON writer

NOTE: This is not a general purpose JSON writer. It is designed to export
only dictionaries that are guaranteed not to have circular refs, or special
objects.

Lists are written without line breaks between items, and the precision of
floating point values is customizable.

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

import json

from mathutils import Matrix


JSON_FLOAT_PRECISION = 6


def _make_iterencode(markers,
                     _default,
                     _encoder,
                     _indent,
                     _floatstr,
                     _key_separator,
                     _item_separator,
                     _sort_keys,
                     _skipkeys,
                     _one_shot,
                     ):
    """
    """

    def _float_str(o):
        """
        Converts float values using built-in string formatting and strips
        trailing zeros
        """
        o = round(o, JSON_FLOAT_PRECISION) + 0
        return ("%.*f" % (JSON_FLOAT_PRECISION, o)).rstrip('0').rstrip('.')

    def _iterencode_list(l, level):

        if not l:
            return

        buf = '['
        newline_indent = None
        separator = _item_separator
        first = True

        for value in l:

            if first:
                first = False
            else:
                buf = separator

            if isinstance(value, str):
                yield buf + _encoder(value)

            elif value is None:
                yield buf + 'null'

            elif value is True:
                yield buf + 'true'

            elif value is False:
                yield buf + 'false'

            elif isinstance(value, int):
                yield buf + str(value)

            elif isinstance(value, float):
                yield buf + _float_str(value)

            else:
                yield buf

                if isinstance(value, list):
                    chunks = _iterencode_list(value, level)

                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, level)

                else:
                    chunks = _iterencode(value, level)

                for chunk in chunks:
                    yield chunk

        if newline_indent is not None:
            level -= 1
            yield '\n' + _indent * level

        yield ']'

    def _iterencode_dict(d, level):

        if not d:
            return

        yield '{'

        if _indent is not None:
            level += 1
            newline_indent = '\n' + _indent * level
            item_separator = _item_separator + newline_indent
            yield newline_indent

        else:
            newline_indent = None
            item_separator = _item_separator

        first = True
        for key, value in d.items():

            if value is None or key is None:
                continue

            if isinstance(value, (list, dict)) and not value:
                continue

            elif isinstance(key, str):
                pass

            elif isinstance(key, float):
                key = _float_str(key)

            elif key is True:
                key = 'true'

            elif key is False:
                key = 'false'

            elif isinstance(key, int):
                key = str(key)

            elif _skipkeys:
                continue

            else:
                raise TypeError("key " + repr(key) + " is not a string")

            if first:
                first = False

            else:
                yield item_separator

            yield _encoder(key)

            yield _key_separator

            if isinstance(value, str):
                yield _encoder(value)

            elif value is True:
                yield 'true'

            elif value is False:
                yield 'false'

            elif isinstance(value, int):
                yield str(value)

            elif isinstance(value, float):
                yield _float_str(value)

            else:
                if isinstance(value, list):
                    chunks = _iterencode_list(value, level)

                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, level)

                else:
                    chunks = _iterencode(value, level)

                for chunk in chunks:
                    yield chunk

        if newline_indent is not None:
            level -= 1
            yield '\n' + _indent * level

        yield '}'

    def _iterencode(o, level):

        if isinstance(o, str):
            yield _encoder(o)

        elif o is None:
            return

        elif o is True:
            yield 'true'

        elif o is False:
            yield 'false'

        elif isinstance(o, int):
            yield str(o)

        elif isinstance(o, float):
            yield _float_str(o)

        elif isinstance(o, list):
            for chunk in _iterencode_list(o, level):
                yield chunk

        elif isinstance(o, dict):
            for chunk in _iterencode_dict(o, level):
                yield chunk
        else:
            o = _default(o)
            for chunk in _iterencode(o, level):
                yield chunk

    if _indent is not None and not isinstance(_indent, str):
        _indent = ' ' * _indent

    return _iterencode


json.encoder._make_iterencode = _make_iterencode


def dump(content, file, precision=JSON_FLOAT_PRECISION):

    global JSON_FLOAT_PRECISION

    JSON_FLOAT_PRECISION = precision

    json.dump(content, file, indent=4, check_circular=False)


# END OF FILE
