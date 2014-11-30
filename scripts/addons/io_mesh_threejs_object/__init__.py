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

    # object options

    object_types = EnumProperty(
        name="Object Types",
        description="Export object types.",
        items=(("MESH", "Mesh", "", "", 1),      # OUTLINER_OB_MESH
               ("CURVE", "Curve", "", "", 2),    # OUTLINER_OB_CURVE
               ("LAMP", "Lamp", "", "", 4),      # OUTLINER_OB_LAMP
               ("CAMERA", "Camera", "", "", 8),  # OUTLINER_OB_CAMERA
               ("EMPTY", "Empty", "", "", 16),   # OUTLINER_OB_EMPTY
               ),
        default={"MESH"},
        options={"ENUM_FLAG"}
        )

    uniform_scale = FloatProperty(
        name="Uniform Scale",
        description="Apply uniform scale to all exported objects.",
        default=1.0,
        min=0.01,
        max=100,
        )

    selected_only = BoolProperty(
        name="Selected Only",
        description="Export selected scene objects only.",
        default=False
        )

    include_descendents = BoolProperty(
        name="Include Descendents",
        description="Always export descendents of selected objects,"
                    "even when they are not explicitly selected themselves.",
        default=False
        )

    # mesh options

    apply_mesh_modifiers = BoolProperty(
        name="Apply Mesh Modifiers",
        description="Apply mesh modifiers to exported geometry",
        default=True
        )

    mesh_modifier_mode = EnumProperty(
        name="Mesh Modifier Mode",
        description="Modifier mode type",
        items=(("VIEW", "View", "", "RESTRICT_VIEW_OFF", 1),
               ("RENDER", "Render", "", "RESTRICT_RENDER_OFF", 2)),
        default="RENDER"
        )

    split_by_material = BoolProperty(
        name="Split by Material",
        description="Split exported geometry by material",
        default=True
        )

    # geometry options

    export_normals = BoolProperty(
        name="Normal",
        description="Export BufferGeometry normal attribute",
        default=True
        )

    export_uvs = BoolProperty(
        name="UV",
        description="Export BufferGeometry uv attributes",
        default=True
        )

    export_colors = BoolProperty(
        name="Color",
        description="Export BufferGeometry color attribute",
        default=True
        )

    export_index = BoolProperty(
        name="Index",
        description="Export BufferGeometry index attribute",
        default=True
        )

    # material options

    export_materials = BoolProperty(
        name="Export Materials",
        description="Export assigned mesh materials",
        default=True
        )

    #

    def draw(self, context):
        '''
        Draw the export options
        '''
        layout = self.layout

        # Object Options

        layout.label("Object Options:", icon="OBJECT_DATA")
        row = layout.row()
        col = row.column()
        col.prop(self.properties, "selected_only")
        col = row.column()
        col.prop(self.properties, "include_descendents")
        col.enabled = self.selected_only
        layout.prop(self.properties, "uniform_scale")
        layout.prop(self, "object_types")

        # Mesh Options

        box = layout.box()
        box.label("Mesh Options:", icon="OUTLINER_OB_MESH")
        row = box.row()
        col = row.column()
        col.prop(self.properties, "apply_mesh_modifiers")
        col = row.column()
        col.prop(self.properties, "mesh_modifier_mode", text="")
        col.enabled = self.apply_mesh_modifiers
        row = box.row()
        col = row.column()
        col.prop(self.properties, "split_by_material")
        box.enabled = "MESH" in self.object_types

        # BufferGeometry Attributes

        box = layout.box()
        box.label("BufferGeometry Attributes:", icon="OUTLINER_DATA_MESH")
        row = box.row()
        row.prop(self.properties, "export_normals")
        row.prop(self.properties, "export_uvs")
        row = box.row()
        row.prop(self.properties, "export_colors")
        row.prop(self.properties, "export_index")
        box.enabled = any(i in self.object_types for i in ("MESH", "CURVE"))

        # Material Options

        box = layout.box()
        box.label("Materials:", icon="MATERIAL")
        box.prop(self.properties, "export_materials")

    def execute(self, context):
        '''
        Execute the object export
        '''
        try:

            # self.filepath = ensure_ext(self.filepath, self.filename_ext)

            # keywords = self.as_keywords(ignore=("", ))

            from .export import export

            return export(context, **self.as_keywords())

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