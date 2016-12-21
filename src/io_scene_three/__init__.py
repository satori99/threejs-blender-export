# __init__.py

bl_info = {
    "name": "Three.js Object Format 4.4 (.json)",
    "author": "satori99",
    "version": (0, 0, 5),
    "blender": (2, 77, 0),
    "category": "Import-Export",
    "location": "File > Export > Three.js Object Format 4 (.json)",
    "description": "Exports Three.js Object Format 4 JSON files",
    "warning": "Experimental - Export only",
    }

# Check if we need to explicitly reload sub-modules
if "bpy" in locals():
    print("Reloading: io_scene_three")
    import imp
    imp.reload(mesh)
    imp.reload(material)
    imp.reload(texture)
    imp.reload(operator)
    imp.reload(exporter)
    imp.reload(encoder)
    imp.reload(util)
    imp.reload(math)
    imp.reload(scene)
    imp.reload(lamp)
    imp.reload(object)
    imp.reload(camera)
    imp.reload(armature)
    imp.reload(image)
    imp.reload(action)

import bpy

from . import mesh
from . import material
from . import texture
from . import util
from . import math
from . import scene
from . import lamp
from . import object
from . import camera
from . import armature
from . import image
from . import action

from .operator import ExportOperator
from .exporter import Exporter
from .encoder import Encoder

_keymap = None


def register():
    """Registers the Export Operator, adds the export menu item, and keyboard
    shortcut (alt-E in Object mode).
    """
    import bpy
    # register export operator
    bpy.utils.register_class(ExportOperator)
    # add export menu item
    bpy.types.INFO_MT_file_export.append(ExportOperator.menu_func)
    # add keyboard shortcut: object mode -> alt-E
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig:
        keymap = keyconfig.keymaps.new(
                name="Object Mode", space_type="EMPTY")
        keymap_item = keymap.keymap_items.new(
                ExportOperator.bl_idname, "E", "PRESS", alt=True)
        # set operator props here ...
        # keymap_item.properties.mode = (False, True, False, etc ...)


def unregister():
    """Removes keyboard shortcut, export menu item and unregisters the
    Export Operator.
    """
    import bpy
    # remove export menu item
    bpy.types.INFO_MT_file_export.remove(ExportOperator.menu_func)
    # remove keyboard shortcut
    keyconfig = bpy.context.window_manager.keyconfigs.addon
    if keyconfig:
        keymap = keyconfig.keymaps["Object Mode"]
        for keymap_item in keymap.keymap_items:
            if keymap_item.idname == ExportOperator.bl_idname:
                keymap.keymap_items.remove(keymap_item)
                break
    # unregister export operator
    bpy.utils.unregister_class(ExportOperator)


if __name__ == "__main__":
    # register the export operator when this script is run directly (alt-p)
    register()
