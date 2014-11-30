"""io_mesh_threejs_object

Blender Three.js Object Exporter Addon
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

bl_info = {
    "name": "Export Three.js Object Format 4.3 (.json)",
    "author": "satori99",
    "version": (0, 0, 2),
    "blender": (2, 72, 0),
    "location": "File > Export > Three.js Object (.json)",
    "description": "Exports Blender objects as Three.js"
                   "Object Format 4.3 JSON files",
    "warning": "In Development",
    "category": "Import-Export",
    "wiki_url": "https://github.com/satori99/"
                "threejs-blender-export/wiki",
    "tracker_url": "https://github.com/satori99/"
                   "threejs-blender-export/issues",
    }

if "bpy" in locals():
    import imp
    if "json" in locals():
        imp.reload(json)

###############################################################################

from bpy.types import (
    Operator,
    )

from bpy_extras.io_utils import (
    ExportHelper,
    )

from bpy.props import (
    EnumProperty,
    StringProperty,
    BoolProperty,
    FloatProperty,
    IntProperty,
    )

from bpy.path import (
    display_name_from_filepath,
    ensure_ext,
    )


class ThreeObjectExportOperator(Operator, ExportHelper):
    """
    Export a Three.js Object Format 4.3 JSON file
    """

    bl_idname = "export_threejs_object.json"
    bl_label = "Export Three.js Object"
    bl_description = ""
    bl_options = {'UNDO', 'PRESET', }
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'

    filename_ext = ".json"

    filepath = StringProperty(
        name="File Path",
        description="Export file path",
        maxlen=1024,
        subtype="FILE_PATH",
        options={"SKIP_SAVE"}
        )

    def invoke(self, context, event):

        if not self.filepath:

            blend_filepath = context.blend_data.filepath

            if blend_filepath:

                self.filepath = display_name_from_filepath(blend_filepath)

            else:

                self.filepath = "untitled"

        context.window_manager.fileselect_add(self)

        return {"RUNNING_MODAL"}

    def draw(self, context):
        '''
        Draw the export options
        '''
        layout = self.layout
        layout.separator()

    def execute(self, context):
        '''
        Execute the object export
        '''
        try:

            self.filepath = ensure_ext(self.filepath, self.filename_ext)

            keywords = self.as_keywords(ignore=("", ))

            # from . import object

            # return object.export(context, **keywords)

            return {"FINISHED"}

        except:

            # todo: nice error message popups
            # return {"CANCELLED"}
            raise

    @classmethod
    def poll(cls, context):

        return context.active_object is not None

    @staticmethod
    def menu_func(cls, context):

        cls.layout.operator(
            ThreeObjectExportOperator.bl_idname,
            text="Three.js Object (%s)"
            % (ThreeObjectExportOperator.filename_ext)
            )


###############################################################################

from bpy.utils import register_module, unregister_module

from bpy.types import INFO_MT_file_export


def register():

    register_module(__name__)

    INFO_MT_file_export.append(ThreeObjectExportOperator.menu_func)


def unregister():

    unregister_module(__name__)

    INFO_MT_file_export.remove(ThreeObjectExportOperator.menu_func)


if __name__ == "__main__":
    register()


# END OF FILE
