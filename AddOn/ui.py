import bpy
from .properties import STANDARD_BONE_NAMES

class RETARGET_PT_MainPanel(bpy.types.Panel):
    """Creates a Panel in the 3D View's N-Panel"""
    bl_label = "Humanoid Retargeter"
    bl_idname = "OBJECT_PT_retargeter_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Retargeter' # Tab name in the N-Panel

    def draw(self, context):
        layout = self.layout
        props = context.scene.retargeting_tool_props

        # --- Section 1: Armature Selection ---
        box = layout.box()
        box.label(text="1. Select Armatures", icon='ARMATURE_DATA')
        box.prop(props, "target_armature")
        box.prop(props, "source_armature")

        # --- Section 2: Bone Mapping ---
        box = layout.box()
        row = box.row()
        row.label(text="2. Bone Mapping", icon='BONE_DATA')
        
        # Disable auto-map button if armatures aren't selected
        auto_map_row = box.row()
        auto_map_row.enabled = bool(props.target_armature and props.source_armature)
        auto_map_row.operator("retarget.auto_map_bones", text="Auto-Map Bones", icon='AUTOMERGE_ON')

        # Display the bone mapping table
        if props.target_armature and props.source_armature:
            map_box = box.box()
            header = map_box.row()
            header.label(text="Standard Bone")
            header.label(text="Target (A)")
            header.label(text="Source (B)")
            
            for prop_name, label in STANDARD_BONE_NAMES:
                row = map_box.row(align=True)
                row.label(text=label)
                # prop_search lets the user search through the bones of the specified armature
                row.prop_search(props.target_bone_mapping, prop_name, props.target_armature.data, "bones", text="")
                row.prop_search(props.source_bone_mapping, prop_name, props.source_armature.data, "bones", text="")

        # --- Section 3: Execute ---
        box = layout.box()
        box.label(text="3. Execute Retargeting", icon='PLAY')
        
        # Disable execute button if mapping is incomplete
        execute_row = box.row()
        execute_row.enabled = bool(props.target_armature and props.source_armature)
        
        # This is the main button that runs the entire pipeline from operators.py
        execute_row.operator("retarget.execute", text="Run Retargeting", icon='CHECKMARK')


classes = [
    RETARGET_PT_MainPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)