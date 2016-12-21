import json
from types import GeneratorType


class Encoder(json.JSONEncoder):
    """This is a `JSONEncoder` sub-class with support for `Generator` types and
    better support for pretty-printing (Only dict types are indented, lists ar
    e always inline).

    Also, floating-point numbers are always written in decimal format with the
    max. number of decimal places controlled by the `float_precision`
    parameter.

    It supports all of the normal JSON encoder options; see  ...
    Plus some extra options:

    :arg skip_empty: Skip non-numeric or boolean dict items with null or empty
                     values (Default=True)
    :type skip_empty: bool

    :arg float_precision: Controls the maximum number of decimal places used
                          for encoding floating point numbers
    :type float_precision: int

    Note: python dicts do not guarantee a specific key order, so use
    `collections.OrderedDict` (w/ sort_keys=False) to control the order of
    object keys in encoded JSON output.

    """
    skip_empty = True  # skip empty non-numeric or bool values

    float_precision = 5  # default floating point precision

    def __init__(self,
                 float_precision=float_precision,
                 skip_empty=skip_empty,
                 **kwargs
                 ):
        self.float_precision = float_precision
        self.skip_empty = skip_empty
        super().__init__(**kwargs)

    def encode_float(self, f):
        """encodes a floating point number to a decimal string"""
        return ("%.*f" % (self.float_precision,
                          round(float(f), self.float_precision) + 0
                          )).rstrip("0").rstrip(".")

    def iterencode(self, o, **kw):
        """This is a re-write of the super method to add support for `Generator`
        types and to always encode list data without line breaks.
        """
        json_null = 'null'
        json_true = 'true'
        json_false = 'false'

        default = self.default
        sort_keys = self.sort_keys
        skipkeys = self.skipkeys
        skip_empty = self.skip_empty
        item_separator = self.item_separator
        key_separator = self.key_separator

        encode_float = self.encode_float
        if self.ensure_ascii:
            encode_str = json.encoder.encode_basestring_ascii
        else:
            encode_str = json.encoder.encode_basestring
        if self.check_circular:
            markers = dict()
        else:
            markers = None
        indent = self.indent
        if indent is not None and not isinstance(indent, str):
            indent = " " * self.indent

        def _iterencode_iter(l, level):
            if not l:
                yield "[]"
                return
            if markers is not None:
                markerid = id(l)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = l
            yield "["
            newline_indent = None
            separator = item_separator
            first = True
            for value in l:
                if first:
                    first = False
                    buf = ""
                else:
                    buf = separator
                if value is None:
                    yield buf + json_null
                elif value is True:
                    yield buf + json_true
                elif value is False:
                    yield buf + json_false
                elif isinstance(value, int):
                    yield buf + str(int(value))
                elif isinstance(value, float):
                    yield buf + encode_float(value)
                elif isinstance(value, str):
                    yield buf + encode_str(value)
                else:
                    yield buf
                    if isinstance(value, (list, set, GeneratorType)):
                        yield from _iterencode_iter(value, level)
                    elif isinstance(value, dict):
                        yield from _iterencode_dict(value, level)
                    else:
                        yield from _iterencode(value, level)
            yield "]"
            if markers is not None:
                del markers[markerid]

        def _iterencode_dict(d, level):
            if not d:
                yield "{}"
                return
            if markers is not None:
                markerid = id(d)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = d
            yield "{"
            if indent is not None:
                level += 1
                newline_indent = "\n" + indent * level
                separator = item_separator + newline_indent
                yield newline_indent
            else:
                newline_indent = None
                separator = item_separator
            first = True
            if sort_keys:
                items = sorted(d.items(), key=lambda kv: kv[0])
            else:
                items = d.items()
            for key, value in items:
                if (skip_empty and
                    not isinstance(value, (bool, int, float)) and
                        not value):
                    continue
                elif isinstance(key, str):
                    pass
                elif key is None:
                    key = json_null
                elif key is True:
                    key = json_true
                elif key is False:
                    key = json_false
                elif isinstance(key, int):
                    key = str(int(key))
                elif isinstance(key, float):
                    key = str(float(key))
                elif skipkeys:
                    continue
                else:
                    raise TypeError("key " + repr(key) + " is not a string")
                if first:
                    first = False
                else:
                    yield separator
                yield encode_str(key)
                yield key_separator
                if value is None:
                    yield json_null
                elif value is True:
                    yield json_true
                elif value is False:
                    yield json_false
                elif isinstance(value, int):
                    yield str(int(value))
                elif isinstance(value, float):
                    yield encode_float(value)
                elif isinstance(value, str):
                    yield encode_str(value)
                elif isinstance(value, (list, set, GeneratorType)):
                    yield from _iterencode_iter(value, level)
                elif isinstance(value, dict):
                    yield from _iterencode_dict(value, level)
                else:
                    yield from _iterencode(value, level)
            if newline_indent is not None:
                level -= 1
                yield "\n" + indent * level
            yield "}"
            if markers is not None:
                del markers[markerid]

        def _iterencode(o, level):
            if o is None:
                yield json_null
            elif o is True:
                yield json_true
            elif o is False:
                yield json_false
            elif isinstance(o, int):
                yield str(o)
            elif isinstance(o, float):
                yield encode_float(o)
            elif isinstance(o, str):
                yield encode_str(o)
            elif isinstance(o, (list, set, GeneratorType)):
                yield from _iterencode_iter(o, level)
            elif isinstance(o, dict):
                yield from _iterencode_dict(o, level)
            else:
                if markers is not None:
                    markerid = id(o)
                    if markerid in markers:
                        raise ValueError("Circular reference detected")
                    markers[markerid] = o
                o = default(o)
                yield from _iterencode(o, level)
                if markers is not None:
                    del markers[markerid]

        yield from _iterencode(o, 0)
