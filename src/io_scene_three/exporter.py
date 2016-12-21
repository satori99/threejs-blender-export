# exporter.py
from bpy.types import (
    Context, Scene, Object, Mesh, Material, Texture, Image, Action)
from collections import OrderedDict
from mathutils import Matrix, Color, Vector

from .util import traverse_visible_objects
from .math import export_color, export_matrix, MAT4_ROT_X_PI2
from .mesh import export_mesh, ModifiedMesh
from .material import export_material, MultiMaterial
from .scene import export_scene
from .object import export_object
from .texture import export_texture
from .image import export_image
from .action import export_action


class Exporter():
    """Three.js Exporter Class

    Use this class to parse a Blender scene-graph, and create a JSON Encodable
    dictionary representing a three.js Object Format 4.4 file.

    The output dictionary will still contain native Blender types, however
    these can be encoded by applying the Exporter.export method as the JSON
    Encoders default property.
    """

    scene = None    # export scene
    root = None     # export root object
    objects = None  # export object list

    _ob_map = dict()    # maps Object -> (parent, matrix)
    _geom_map = dict()  # maps Object -> Mesh
    _mat_map = dict()   # maps Object -> Material
    _tex_map = dict()   # maps Material -> {textures}
    _arm_map = dict()   # maps Object -> Armature
    _bone_map = dict()  # maps Armature -> [export bones]
    _act_map = dict()   # maps Object -> Action

    def parse(self, context, **kw):
        """Parses the scene graph to identify exportable objects, populates
        the internal maps, and returns an encodable dictionary

        :arg context (bpy.types.Context): Blender context
        :arg kw (keyword arguments)
        :   [export_scene] (bool=True):
        :   [selected_only] (bool=False):
        :   [export_geometries] (bool=True):

        :returns (dict): A dictionary representing a Three.js Object Formet
                         4.4 JSON file.
        """
        assert isinstance(context, Context), \
            "parse() expects a `bpy.types.Context` arg"

        def _parse_args():
            self.export_scene = kw.get("export_scene", True)
            self.selected_only = kw.get("selected_only", False)
            self.export_geometries = kw.get("export_geometries", True)
            self.export_materials = \
                kw.get("export_materials", True) and self.export_geometries
            self.export_textures = \
                kw.get("export_textures", True) and \
                self.export_geometries and \
                self.export_materials
            self.export_images = \
                kw.get("export_images", True) and \
                self.export_geometries and \
                self.export_materials and \
                self.export_textures
            self.export_animations = kw.get("export_animations", True)

        def _clear_maps():
            self._ob_map.clear()
            self._geom_map.clear()
            self._mat_map.clear()
            self._tex_map.clear()
            self._arm_map.clear()
            self._bone_map.clear()
            self._act_map.clear()

        def _get_export_parent_ob(ob):
            if ob.parent in self.objects:
                return ob.parent
            elif ob.parent is not None:
                return _get_export_parent_ob(ob.parent)
            else:
                return None

        def _get_export_matrix(ob, parent):
            if parent is None:
                matrix = ob.matrix_world
            elif parent == ob.parent:
                matrix = ob.matrix_local
            else:
                parentMatrixInv = parent.matrix_world.copy()
                parentMatrixInv.invert()
                matrix = parentMatrixInv * ob.matrix_world
            # handle special cases...
            if ob.type == "CAMERA":
                # blender cameras are aligned differently from three.js cameras
                matrix = matrix * MAT4_ROT_X_PI2
            elif parent == "CAMERA":
                # if a camera has children, they  need to be counter-rotated
                raise Exception("TODO: rotate direct children of camera"
                                " objects back to counter camera rotation")
            elif ob.type == "LAMP" and (ob.data.type == "SUN" or
                                        ob.data.type == "HEMI" or
                                        ob.data.type == "SPOT"):
                # lights in three.js use the objects translation
                # compared to the scene origin, to calculate the lights vector
                loc = Vector((0, 0, -1))
                loc.rotate(ob.rotation_euler)
                matrix = Matrix.Translation((-loc.x * ob.location.length,
                                             -loc.y * ob.location.length,
                                             -loc.z * ob.location.length))
            return matrix

        def _get_export_textures(mat):

            if mat is None or mat in self._tex_map:
                return None

            textures = [s for i, s in enumerate(mat.texture_slots)
                        if s is not None and
                        mat.use_textures[i] is True and
                        s.texture.type in ("IMAGE", "ENVIRONMENT_MAP") and
                        s.texture_coords in ["UV", "REFLECTION"]]

            out = dict()

            # todo: A better way to select exportable texture maps
            #       for now, the first image texture found is used ...

            map = out["map"] = next(((s.texture, s.uv_layer) for s in textures
                                    if s.use_map_color_diffuse), None)

            out["alphaMap"] = next(((s.texture, s.uv_layer) for s in textures
                                   if s.use_map_alpha and
                                   map is not None and
                                   s.texture != map[0]), None)

            out["normalMap"] = next(((s.texture, s.uv_layer) for s in textures
                                    if s.use_map_normal), None)

            out["aoMap"] = next(((s.texture, s.uv_layer) for s in textures
                                if s.use_map_ambient), None)

            out["specularMap"] = next(((s.texture, s.uv_layer) for s in textures
                                if s.use_map_color_spec), None)

            out["envMap"] = next(((s.texture, s.uv_layer) for s in textures
                                 if s.texture.type == "ENVIRONMENT_MAP" or
                                 s.texture_coords == "REFLECTION"), None)

            print("\nmaterial textures", mat.name, out)

            return out

        def _is_bone_visible(arm, bone):
            if bone.hide:
                return False
            arm_layers = [i for i, v in enumerate(arm.layers) if v is True]
            bone_layers = [i for i, v in enumerate(bone.layers) if v is True]
            return any(True for i in arm_layers if i in bone_layers)

        def _get_export_bones(arm):
            return [b for b in arm.bones
                    if b.use_deform and
                    _is_bone_visible(arm, b)]

        def _map_export_object(ob):
            # map ob to export parent and matrix
            parent = _get_export_parent_ob(ob)
            matrix = _get_export_matrix(ob, parent)
            self._ob_map[ob] = (parent, matrix)

        def _map_export_geometry(ob):
            # map ob to geometry data
            geom = None
            if self.export_geometries:
                if ob.type == "MESH" and ob.data is not None:
                    if ob.is_modified(self.scene, "PREVIEW"):
                        geom = ModifiedMesh(ob.name, ob)
                    else:
                        geom = ob.data
            self._geom_map[ob] = geom
            return geom

        def _map_export_material(ob, geom):
            # map ob to its material data
            mat = None
            if self.export_materials and geom is not None:
                if isinstance(geom, ModifiedMesh):
                    mats = geom.object.data.materials
                else:
                    mats = geom.materials
                num_mats = len(mats)
                if num_mats == 0:
                    mat = None
                elif num_mats == 1:
                    mat = mats[0]
                else:
                    mat = MultiMaterial(geom.name, mats)
            self._mat_map[ob] = mat
            return mat

        def _map_export_textures(mat):
            # map material to texture data
            if self.export_textures and mat is not None:
                if isinstance(mat, MultiMaterial):
                    for m in mat.materials:
                        if m not in self._tex_map:
                            self._tex_map[m] = _get_export_textures(m)
                elif mat not in self._tex_map:
                    self._tex_map[mat] = _get_export_textures(mat)

        def _map_export_armature(ob):
            arm_ob = ob if ob.type == "ARMATURE" else ob.find_armature()
            if arm_ob and arm_ob.data and arm_ob in self.objects:
                self._arm_map[ob] = arm_ob.data
                self._bone_map[arm_ob.data] = _get_export_bones(arm_ob.data)

        def _map_export_animations(ob):
            # map object to its export action
            act = None
            if self.export_animations and ob.animation_data is not None:
                act = ob.animation_data.action
                if act:
                    self._act_map[act] = ob
            return act

        def _create_metadata():
            metadata = OrderedDict()
            metadata["name"] = self.root.name
            metadata["type"] = "Object"
            metadata["version"] = 4.4
            return metadata

        def _create_geometries():
            return set(m for m in self._geom_map.values() if m is not None)

        def _create_materials():
            return set(m for m in self._mat_map.values() if m is not None)

        def _create_textures():
            return set(a for b in ([v[0] for v in tv.values()
                       if v is not None] for tv in
                       (t for t in self._tex_map.values()
                       if t is not None and
                       any(t.values()))) for a in b)

        def _create_animations():
            return set(a for a in self._act_map.keys() if a is not None)

        def _create_output_dict():
            # create and return a THree.JS Object Format 4.x dict
            out = OrderedDict()
            out["metadata"] = _create_metadata()
            out["object"] = self.root
            out["geometries"] = _create_geometries()
            out["materials"] = _create_materials()
            out["textures"] = _create_textures()
            out["images"] = set(t.image for t in out["textures"])
            out["animations"] = _create_animations()
            return out

        # parse keyword arguments
        _parse_args()

        # reset internal maps
        _clear_maps()

        # start parsing scene graph ...
        self.scene = context.scene
        if self.export_scene:

            # export all visible (and possibly selected) objects
            self.root = self.scene
            self.objects = list(traverse_visible_objects(
                self.scene, selected_only=self.selected_only))

        else:

            # export all visible objects starting from the active object
            self.root = context.active_object
            self.objects = list(traverse_visible_objects(
                self.scene,
                start_ob=self.root,
                selected_only=self.selected_only))

        # parse each export object to populate internal dict's ...
        for ob in self.objects:

            # map export object to export parent and matrix
            _map_export_object(ob)

            # map export object to geometry data
            geom = _map_export_geometry(ob)

            # map export object to material data
            mat = _map_export_material(ob, geom)

            # map material to texture data
            _map_export_textures(mat)

            # map object to its armature and export bones data
            _map_export_armature(ob)

            # map object to its export animation data
            _map_export_animations(ob)

        # create output dictionary
        return _create_output_dict()

    def export(self, ob):
        """Encodes Blender types (`bpy.types.ID`) to encodable dictionaries or
        lists representing three.js types

        Note: Pass this method as the `default` keyword argument to the
              `Encoder` class constructor to automatically encode dicts or
              lists consisting of blender types.
        """
        if isinstance(ob, Color):
            return export_color(ob, sRGB=True)

        elif isinstance(ob, Matrix):
            return export_matrix(ob)

        elif isinstance(ob, Scene):
            return export_scene(ob, exporter=self)

        elif isinstance(ob, Object):
            out = export_object(ob, exporter=self)

        elif isinstance(ob, (Mesh, ModifiedMesh)):
            out = export_mesh(ob, exporter=self)

        elif isinstance(ob, (Material, MultiMaterial)):
            out = export_material(ob, exporter=self)

        elif isinstance(ob, Texture):
            out = export_texture(ob)

        elif isinstance(ob, Image):
            out = export_image(ob)

        elif isinstance(ob, Action):
            out = export_action(ob, exporter=self)

        else:
            raise TypeError("type `%s` is not exportable yet!" % (type(ob)))

        print("-> THREE.%s(\"%s\")" % (
            out.get("type") or "Image", out["name"]))

        return out
