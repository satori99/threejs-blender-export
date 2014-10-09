bl_info = {
	"name" : "Export Three.js Object",
	"author" : "satori99",
	"version" : (0, 0, 1),
	"blender" : (2, 71, 0),
	"location" : "File > Export > Three.js Object (.js)",
	"description" : "Export Three.js mesh objects",
	"warning" : "In Development",
	"category" : "Import-Export"
	}

JSON_FLOAT_PRECISION = 8
JSON_INDENT = 4

import bpy
import uuid
import math
from bpy.props import (FloatProperty, IntProperty, BoolProperty, StringProperty)
from bpy_extras.io_utils import ExportHelper
from mathutils import Matrix
from collections import OrderedDict

####################################################################################################
# Three.js Object Exporter
####################################################################################################

class ExportThreejsObject(bpy.types.Operator, ExportHelper):

	bl_idname = "export_threejs_object.js"
	bl_label = "Export Three.js Object"

	filename_ext = ".js"

	selected_only = BoolProperty(
			name = "Selected Objects Only",
			description = "Export selected scene objects only",
			default = True
			)
	
	split_by_material = BoolProperty(
			name = "Split by Material",
			description = "Split exported mesh object by material",
			default = True
			)
	
	def __init__(self):
		
		metadata = self.metadata = OrderedDict()
		metadata["type"] = "Object"
		metadata["version"] = 4.3
		metadata["generator"] = "Blender Script"
		
		self.children = []
		self.materials = set()
		self.geometries = {}

	@classmethod
	def poll(cls, context):
		return context.active_object != None
	
	def draw(self, context):
		layout = self.layout
		row = layout.row()
		row.prop(self.properties, "selected_only")
		row = layout.row()
		row.prop(self.properties, "split_by_material", icon="MATERIAL")

	def execute(self, context):

		if not self.filepath:
			raise Exception("Export filepath not set")

		self.filepath = bpy.path.ensure_ext(self.filepath, self.filename_ext)

		self.display_name = bpy.path.display_name_from_filepath(self.filepath)

		if context.scene.objects.active:
			bpy.ops.object.mode_set(mode="OBJECT")

		initial_selected_objects = context.selected_objects[:]

		if not self.properties.selected_only:
			bpy.ops.object.select_all(action="SELECT")

		num_selected_objects = len(context.selected_objects)
		if num_selected_objects == 0:
			raise Exception("No objects selected!")

		try:
			
			# parse all mesh objects
			for object in context.selected_objects:
				if object.type == "MESH":
					self.parse_mesh_object(context.scene, object)

		except:
			
			# something went wrong!
			raise

		else:
			
			# great success

			# clean up. delete unique vertex-index maps
			for geometry in self.geometries.values():
				del geometry["_index_map"]

			# create result dict
			result = OrderedDict()
			result["metadata"] = self.metadata

			# object attribute is either a THREE.Mesh or a THREE.Object3D
			num_children = len(self.children)
			if num_children == 1:
				result["object"] = self.children[0]
			else:
				# make the root object an Object3D
				result["object"] = create_object_dict(self.display_name, "Object3D", children=self.children)
				
			# convert geometries and materials collections to lists
			result["geometries"] = [g for g in self.geometries.values()]
			result["materials"] = [create_material_dict(m) for m in self.materials]

			# write json file
			print("Writing file '%s' ... " % str(self.filepath), end="")
			file = open(self.filepath, "w", encoding="utf-8")
			write_json(file, result)
			file.close()
			print("Done")
			
		finally:
			
			# restore initial selected objects
			bpy.ops.object.select_all(action="DESELECT")
			for o in initial_selected_objects:
				o.select = True

		return {"FINISHED"}

	def parse_mesh_object(self, scene, object):
		
		"""Parses a scene mesh object into self.children, self.geometries, and self.materials"""
		
		print("Parsing Mesh Object: %s (%s) ..." % (object.name, object.data.name))
		
		try:
			
			# create temp copy of mesh data
			mesh = object.to_mesh(scene, True, "RENDER")
			mesh.transform(Matrix.Rotation(-math.pi / 2, 4, "X") * object.matrix_world)
			mesh.calc_normals()
			mesh.calc_tessface()

			# mesh_name = object.name #if self.properties.split_by_object else self.display_name
			mesh_name = self.display_name

			# parse mesh faces into geometries
			num_materials = len(mesh.materials)
			if not self.properties.split_by_material or num_materials == 0:
				self.parse_mesh_faces(mesh, mesh_name)
			else:
				for material_index in range(num_materials):
					self.parse_mesh_faces(mesh, mesh_name, material_index)

		finally:
			
			# delete temp mesh
			bpy.data.meshes.remove(mesh)

	def parse_mesh_faces(self, mesh, mesh_name, material_index=None):
		
		"""Parses mesh faces into geometries"""
		
		material = mesh.materials[material_index] if material_index != None else None
		material_name = material.name if material else None
		material_faces = [f for f in mesh.tessfaces if f.material_index == material_index] if material_index != None else mesh.tessfaces
		num_material_faces = len(material_faces)
		if num_material_faces == 0:
			return

		# add current material to unique materials set
		if material != None:
			self.materials.update([material])
			
		num_uv_layers = len(mesh.tessface_uv_textures)
		geometry_name = mesh_name + "." + str(material_name)
		
		if geometry_name in self.geometries:
			
			# adding new verts to an existing geometry
			geometry = self.geometries[geometry_name]
			
		else:
			
			# create a new geometry
			geometry = self.geometries[geometry_name] = create_geometry_dict(geometry_name, num_uv_layers)
			
			# create a new child mesh
			self.children.append(create_object_dict(geometry_name, material_name=material_name))
			
		# get geometry array refs
		index_map = geometry["_index_map"]
		attributes = geometry["data"]["attributes"]
		position_array = attributes["position"]["array"]
		normal_array = attributes["normal"]["array"]
		if num_uv_layers > 0:
			uv_array = attributes["uv"]["array"]
			if num_uv_layers > 1:
				uv2_array = attributes["uv2"]["array"]
		index_array = attributes["index"]["array"]

		# process material faces
		for face in material_faces:
			face_vertices = [mesh.vertices[v] for v in face.vertices]
			num_face_vertices = len(face_vertices)
			
			# get vertex positions
			positions = [(v.co.x, v.co.y, v.co.z) for v in face_vertices]
			
			# get vertex normals
			if face.use_smooth:
				normals = [(v.normal.x, v.normal.y, v.normal.z) for v in face_vertices]
			else:
				normals = [(face.normal.x, face.normal.y, face.normal.z) for v in face_vertices]
				
			uvs = [None] * num_face_vertices
			uv2s = [None] * num_face_vertices
			
			if num_uv_layers > 0:
				# get vertex uvs
				uv_layer = mesh.tessface_uv_textures[0].data[face.index].uv
				uvs = [(uv[0], uv[1]) for uv in uv_layer]
				
				if num_uv_layers > 1:
					# get vertex uv2s
					uv_layer = mesh.tessface_uv_textures[1].data[face.index].uv
					uv2s = [(uv[0], uv[1]) for uv in uv_layer]
					
			# get face indices
			indices = [None] * num_face_vertices

			# add each unique vertex to the index map
			for i in range(num_face_vertices):
				vertex_key = hash((positions[i], normals[i], uvs[i], uv2s[i]))
				if vertex_key in index_map:
					# unique entry already exists. Get the existing index
					indices[i] = index_map[vertex_key]
				else:
					# this is a new unique entry. Calculate the new index
					indices[i] = index_map[vertex_key] = len(index_map)
					# store the vertex attribute data
					position_array += positions[i]
					normal_array += normals[i]
					if num_uv_layers > 0:
						uv_array += uvs[i]
						if num_uv_layers > 1:
							uv2_array += uv2s[i]

			# add triangle faces to the index array
			index_array += [indices[0], indices[1], indices[2]]
			if num_face_vertices == 4:
				index_array += [indices[2], indices[3], indices[0]]
			
####################################################################################################
# Internal stuff
####################################################################################################

def flatten_list(list):
	return [a for b in list for a in b]

def flatten_matrix(matrix):
	return flatten_list([r.to_tuple() for r in matrix])
	
def create_uuid_string(name=None):
	# creates a deterministic uuid based on name if provided, otherwise a random uuid is created
	if isinstance(name, str):
		out = uuid.uuid5(uuid.NAMESPACE_DNS, name)
	else:
		out = uuid.uuid4()
	return str(out)

def create_material_dict(material):
	"Converts a blender material object to a dict of three.js material attributes"
	if not material:
		return None

	def color_to_int(color, intensity=1.0):
		"Converts a blender color object to an integer value"
		return int(color.r * intensity * 255) << 16 ^ \
               int(color.g * intensity * 255) <<  8 ^ \
			   int(color.b * intensity * 255)

	# create dict with common attributes
	m = OrderedDict()
	m["name"] = material.name
	m["type"] = None
	m["uuid"] = create_uuid_string(material.name)
	m["transparent"] = bool(material.use_transparency)
	m["opacity"] = material.alpha if material.use_transparency else 1.0
	m["color"] = color_to_int(material.diffuse_color, material.diffuse_intensity)
	# m["fog"] = material.use_mist
	if material.use_shadeless:
		# any material with use_shadeless checked, is exported as a basic material type
		m["type"] = "MeshBasicMaterial"
	else:
		# common attributes for Lambert and Phong types
		m["ambient"] = color_to_int(material.diffuse_color, material.ambient)
		m["emissive"] = color_to_int(material.diffuse_color, material.emit)
		if material.specular_intensity == 0:
			# materials with no specular value are exported as Lambert material type
			m["type"] = "MeshLambertMaterial"
		else:
			# all other materials are exported as Phong material type
			m["type"] = "MeshPhongMaterial"
			m["specular"] = color_to_int(material.specular_color, material.specular_intensity)
			m["shininess"] = int(material.specular_hardness)
	return m

def create_geometry_dict(name, num_uv_layers):
	geometry = OrderedDict()
	geometry["_index_map"] = {}
	geometry["name"] = name
	type = geometry["type"] = "BufferGeometry"
	geometry["uuid"] = create_uuid_string(name + type)
	data = geometry["data"] = OrderedDict()
	attributes = data["attributes"] = OrderedDict()
	attributes["position"] = {"type" : "Float32Array", "itemSize" : 3, "array" : []}
	attributes["normal"] = {"type" : "Float32Array", "itemSize" : 3, "array" : []}
	if num_uv_layers > 0:
		attributes["uv"] = {"type" : "Float32Array", "itemSize" : 2, "array" : []}
		if num_uv_layers > 1:
			attributes["uv2"] = {"type" : "Float32Array", "itemSize" : 2, "array" : []}
	attributes["index"] = {"type" : "Uint32Array", "itemSize" : 1, "array" : []}
	return geometry

def create_object_dict(name, type="Mesh", material_name=None, matrix=Matrix.Identity(4), children=[]):
	mesh = OrderedDict()
	mesh["name"] = name
	mesh["type"] = type
	mesh["uuid"] = create_uuid_string(name + type)
	mesh["matrix"] = flatten_matrix(matrix)
	if type == "Mesh":
		mesh["geometry"] = create_uuid_string(name + "BufferGeometry")
		if material_name:
			mesh["material"] = create_uuid_string(material_name)
	elif type == "Object3D":
		mesh["children"] = children
	return mesh

def write_json(file, obj, level=0):

	def list_to_json(list, level):
		sep = ""
		file.write("[")
		for item in list:
			if sep:
				file.write(sep)
			else:
				sep = ","
			write_json(file, item, level + 1)
		file.write("]")

	def dict_to_json(dict, level):
		sep = ""
		file.write("{\n")
		for key, value in dict.items():
			if value == None: continue
			if sep:
				file.write(sep)
			else:
				sep = ",\n"
			file.write(" " * JSON_INDENT * (level + 1))
			file.write('"' + str(key) + '" : ')
			write_json(file, value, level + 1)
		file.write("\n" + " " * JSON_INDENT * level + "}")

	if   isinstance(obj, str) : file.write("".join(['"', obj, '"']))
	elif isinstance(obj, bool) : file.write("true" if obj else "false")
	elif isinstance(obj, int) : file.write(str(obj))
	elif isinstance(obj, float) : file.write("%.*g" % (JSON_FLOAT_PRECISION, obj))
	elif isinstance(obj, list) : list_to_json(obj, level)
	elif isinstance(obj, dict) : dict_to_json(obj, level)
	else : raise TypeError("Can't convert type '%s' to json" % str(type(obj)))

####################################################################################################
# Blender Add-On Stuff
####################################################################################################

def menu_func_export(self, context):
	default_path = bpy.data.filepath.replace(".blend", ExportThreejsObject.filename_ext)
	self.layout.operator(
			ExportThreejsObject.bl_idname,
			text="Three.js Object (%s)" % (ExportThreejsObject.filename_ext)
			).filepath = default_path

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)
