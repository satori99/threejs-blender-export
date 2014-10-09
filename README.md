Blender Three.js Object Export
==============================

A Three.js Object Format 4.3 Exporter for Blender
-------------------------------------------------

This add-on will export one or more blender meshes as a single three.js object that can be imported
with the existing `THREE.ObjectLoader`. The exported object will either be a `THREE.Mesh`, or a 
`THREE.Object3D`, with two or more `THREE.Mesh` children, depending on export options.

![Blender Suzanne mesh with 6 materials](https://satori99.github.io/threejs-blender-export/suzanne.png)

 - [Live Example](https://satori99.github.io/threejs-blender-export/index.html)
 
 - [Example JSON](https://satori99.github.io/threejs-blender-export/suzanne.js)

## Features ##

 - Exports indexed `THREE.BufferGeometry` (position, normal, uv, uv2, color)

 - Exports core Three.js Material types (Basic, Lambert, or Phong)

 - Exports both flat and smooth shaded faces.

 - Doesn't modify blender scene at all.

 - Can split source mesh faces by material to support multi-material objects + BufferGeometry

 - small, simple code (< 400 lines)

## Flaws ##

 - Blender 2.71 only (probably)

 - Export only

 - no texture support (not part of spec yet, but UV's are exported, so you can textures yourself in js code. )

 - Blender scene hierarchy is not preserved. Export is always a single logical mesh.

 - no multiple draw calls or offsets are calculated. (If your geometries are large
   you may have to deal with this in code too)

## Use ##

 - Add file (io_mesh_threejs_object.py) to blender add-ons folder

 - Export using File > Export > Three.js Object (.js)

## Options ##

 - Selected Objects Only

    When checked, only currently selected mesh objects are exported, otherwise 
    all visible mesh objects will be exported.

 - Split by Material

	When checked, a separate THREE.Mesh and THREE.BufferGeometry will be created for each
	unique material	assigned to any of the input mesh objects

## Materials ##

Exported material values are determined by existing blender (Blender Render) material settings.

 *	Diffuse > Color

	Determines exported material diffuse color.

 *	Diffuse > Intensity
 
	Determines exported material diffuse color.

 *	Transparency
 
	Sets exported material transparent flag.

 *	Transparency > Alpha

	Sets exported material opacity value.
 
 *	Shading > Shadeless

	When checked, exported material is THREE.MeshBasicMaterial, and following
	 are ignored.

 *	Shading > Emit

	Determines exported material emissive color.

 *	Shading > Ambient

	Determines exported material ambient color.

 *	Specular > Intensity
 
	Determines specular color. When set to zero, exported material is THREE.LambertMaterial
	and following attributes are ignored.

 *	Specular > Color

	Determines specular color.

 *	Specular > Hardness

 	Determines exported material shininess.

## TODO ##

 - Implement split by object and preserve scene transformations

 - Export linked-objects by re-using buffer geometries
 