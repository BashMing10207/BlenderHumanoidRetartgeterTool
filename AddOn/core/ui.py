import bpy
from .properties import STANDARD_BONE_NAMES

class BHRT_PT_MainPanel(bpy.types.Panel):
    """Creates a Panel in the 3D Viewport 'N' Tool Shelf"""
    bl_label = "Humanoid Retargeter"
    bl_idname = "BHRT_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Retargeter' # Tab name in the N-Panel

    def draw(self, context):
        layout = self.layout
        props = context.scene.retargeting_tool_props

        # --- Main Controls ---
        box = layout.box()
        box.label(text="1. Select Armatures", icon='ARMATURE_DATA')
        col = box.column()
        col.prop(props, "target_armature")
        col.prop(props, "source_armature")

        layout.separator()

        # --- Execution Button ---
        box = layout.box()
        box.label(text="2. Run Process", icon='PLAY')
        row = box.row()
        # Make the button large and prominent
        row.scale_y = 2.0
        # The operator's poll method will automatically disable this button
        # if the armatures are not set.
        op = row.operator("bhrt.execute_retargeting", text="Execute Full Retargeting")
        
        layout.separator()

        # --- Bone Mapping Display (Collapsible) ---
        box = layout.box()
        row = box.row()
        # Use a WindowManager property to store the collapsed state
        row.prop(context.window_manager, "bhrt_show_mapping",
                 icon="TRIA_DOWN" if context.window_manager.bhrt_show_mapping else "TRIA_RIGHT",
                 text="Advanced: Bone Mappings",
                 emboss=False)

        if context.window_manager.bhrt_show_mapping:
            if not props.target_armature or not props.source_armature:
                box.label(text="Select armatures to see mappings.", icon='INFO')
                return

            main_split = box.split(factor=0.5)
            
            # Target and Source mapping columns
            for side, mapping_prop in [("Target", props.target_bone_mapping), ("Source", props.source_bone_mapping)]:
                col = main_split.column()
                col.label(text=f"{side} Mapping")
                map_box = col.box()
                for prop_name, display_name in STANDARD_BONE_NAMES:
                    row = map_box.row(align=True)
                    row.label(text=display_name)
                    row.prop(mapping_prop, prop_name, text="")

def register():
    bpy.types.WindowManager.bhrt_show_mapping = bpy.props.BoolProperty(default=False)
    bpy.utils.register_class(BHRT_PT_MainPanel)

def unregister():
    bpy.utils.unregister_class(BHRT_PT_MainPanel)
    del bpy.types.WindowManager.bhrt_show_mapping