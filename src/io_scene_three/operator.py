from time import time
from shutil import copyfile
from bpy.types import Operator
from bpy.props import StringProperty, BoolProperty, IntProperty, CollectionProperty
from bpy.path import ensure_ext, display_name_from_filepath, basename
from bpy.app import tempdir


from .util import traverse_visible_objects
from .exporter import Exporter
from .encoder import Encoder


class ExportOperator(Operator):
    """Saves a Three.js Object Format 4.4 JSON file"""

    bl_idname = "export_scene.three"
    bl_label = "Three.js Object Format 4 (.json)"
    bl_options = {"PRESET"}
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"

    filename_ext = ".json"

    filter_glob = StringProperty(
        default="*.json;*.js",
        options={'HIDDEN'},
        )

    filepath = StringProperty(
        name="File Path",
        maxlen=1024,
        subtype="FILE_PATH",
        description="Filepath used for exporting the file",
        )

    export_scene = BoolProperty(
        name="Export Scene",
        default=True,
        description="Export the entire scene graph",
        )

    selected_only = BoolProperty(
        name="Selected Only",
        default=False,
        description="Only export selected objects",
        )

    export_geometries = BoolProperty(
        name="Export Geometries",
        default=True,
        description="Export mesh data as indexed THREE.BufferGeometry",
        )

    export_materials = BoolProperty(
        name="Export Materials",
        default=True,
        description="Export mesh materials as THREE.MeshStandardMaterial"
                    "or THREE.MultiMaterial",
        )

    export_textures = BoolProperty(
        name="Export Textures",
        default=True,
        description="Export material textures",
        )

    export_images = BoolProperty(
        name="Export Images",
        default=True,
        description="Export image data",
        )

    export_animations = BoolProperty(
        name="Export Animations",
        default=False,
        description="Export actions as THREE.Animation",
        )

    # selected_animations = CollectionProperty(
    #     name="Selected Animations",
    #     description="Selected actions",
    #     default=[]
    #     )

    float_precision = IntProperty(
        name="FP Precision",
        default=5,
        min=0,
        max=8,
        description="Num. of decimal places to export for float values",
        )

    pretty_print = BoolProperty(
        name="Pretty Print",
        default=True,
        description="Use indenting and newlines for pretty-printed JSON",
        )

    console_only = BoolProperty(
        name="Console Only",
        default=False,
        description="print JSON to console only."
                    " (Dry run - Don't write to file)",
        )

    check_existing = BoolProperty(
        name="Check Existing",
        default=True,
        options={'HIDDEN'},
        description="Check and warn on overwriting existing files",
        )

    def invoke(self, context, event):
        """called when the operator is invoked by the export menu item or
        the keyboard shortcut
        """
        # set a default filepath based on the blender filepath
        # if the filepath is not already set
        if not self.filepath:
            self.filepath = ensure_ext(
                    display_name_from_filepath(
                        context.blend_data.filepath or "untitled"),
                    self.filename_ext)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def draw(self, context):
        """called to draw the addon ui"""

        # count the exportable (visible and/or selected) objects
        if self.export_scene:
            export_ob = context.scene
            num_obs = len([o for o in traverse_visible_objects(
                    context.scene, selected_only=self.selected_only)])
        else:

            export_ob = context.active_object
            num_obs = len([o for o in traverse_visible_objects(
                    context.scene,
                    start_ob=export_ob,
                    selected_only=self.selected_only)])

        layout = self.layout
        layout.label(text="Exporting %s: %s (%d objects)" % (
                export_ob.rna_type.name, export_ob.name, num_obs))

        row = layout.row()
        row.prop(self, "export_scene")
        row.enabled = (context.active_object is not None and
                       context.active_object.is_visible(context.scene))

        row = layout.row()
        row.prop(self, "selected_only")
        row.enabled = len(context.selected_objects) > 0

        row = layout.row()
        row.prop(self, "export_geometries")

        row = layout.row()
        row.prop(self, "export_materials")
        row.enabled = self.export_geometries

        row = layout.row()
        row.prop(self, "export_textures")
        row.enabled = (self.export_geometries and self.export_materials)

        row = layout.row()
        row.prop(self, "export_images")
        row.enabled = (self.export_geometries and
                       self.export_materials and
                       self.export_textures)

        layout.separator()
        layout.label(text="-- Experimental --")

        row = layout.row()
        row.prop(self, "export_animations")

        # row = layout.row()
        # row.template_list("UI_UL_list", "modifiers", ob, "modifiers", ob, "modifier_active_index", rows=rows)
        # row.prop(self, "selected_animations")

        layout.separator()
        layout.label(text="-- Advanced --")

        row = layout.row()
        row.prop(self, "float_precision")

        row = layout.row()
        row.prop(self, "pretty_print")

        row = layout.row()
        row.prop(self, "console_only")

    def execute(self, context):
        """executes the export operator"""
        keywords = self.as_keywords(ignore=(
            "filter_glob", "filepath", "float_precision",
            "pretty_print", "console_only", "check_existing", 
            "selected_animations"))
        exporter = Exporter()
        start = time()

        # parse the scene-graph for exportable objects and create export dict
        out = exporter.parse(context, **keywords)
        print("\nExporting \"%s\" ...\n\n"
              "----------------\n"
              "  objects: %d\n"
              "  geometries: %d\n"
              "  materials: %d\n"
              "  textures: %d\n"
              "  images: %d (%d internal)\n"
              "  skeletons: %d\n"
              "  animations: %d\n"
              "----------------\n" % (
                  out["object"].name,
                  len(exporter.objects),
                  len(out["geometries"]) if "geometries" in out else 0,
                  len(out["materials"]) if "materials" in out else 0,
                  len(out["textures"]) if "textures" in out else 0,
                  len(out["images"]) if "images" in out else 0,
                  len([i for i in out["images"]
                       if i.packed_file or
                       i.source == "GENERATED"]) if "images" in out else 0,
                  len(out["skeletons"]) if "skeletons" in out else 0,
                  len(out["animations"]) if "animations" in out else 0,
                  ))

        # create a JSON encoder to encode the result dictionary
        encoder = Encoder(default=exporter.export,
                          indent=("\t" if self.pretty_print else None),
                          separators=((",", ": ") if self.pretty_print
                                      else (",", ":")),
                          float_precision=self.float_precision,
                          skip_empty=True,
                          )

        # create a generator for output chunks
        chunks = encoder.iterencode(out)

        if self.console_only:

            # dump text chunks to the blender console
            print("".join(chunks))

        else:

            print("writing to \"%s\" ..." % (self.filepath))
            # write to a tmp filepath and then move it to output folder
            tmp = tempdir + basename(self.filepath)
            with open(tmp, "w") as file:
                for chunk in chunks:
                    file.write(chunk)
            copyfile(tmp, self.filepath)

        # all done
        dur = time() - start
        print("completed in %fs" % (dur))
        return {'FINISHED'}

    @staticmethod
    def menu_func(cls, context):
        """
        """
        cls.layout.operator(ExportOperator.bl_idname,
                            text=ExportOperator.bl_label)
