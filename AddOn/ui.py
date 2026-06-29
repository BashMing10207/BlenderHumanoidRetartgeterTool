import bpy
from .properties import STANDARD_BONE_NAMES

class BHR_PT_MainPanel(bpy.types.Panel):
    """Creates the main UI panel for the Humanoid Retargeter in the 3D Viewport."""
    bl_label = "Humanoid Retargeter"
    bl_idname = "BHR_PT_MainPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Retargeter' # Creates a new tab in the N-Panel

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
        
        box.label(text="2. Bone Mapping", icon='BONE_DATA')

        # Tab switcher to select between Source and Target mapping
        row = box.row()
        row.prop(props, "active_mapping_tab", expand=True)

        # Determine which armature/mapping to show based on the active tab
        if props.active_mapping_tab == 'SOURCE':
            armature_to_map = props.source_armature
            mapping_to_edit = props.source_bone_mapping
            map_type = 'SOURCE'
        else:  # 'TARGET'
            armature_to_map = props.target_armature
            mapping_to_edit = props.target_bone_mapping
            map_type = 'TARGET'

        # A sub-box for the actual mapping controls
        map_box = box.box()

        # Disable the mapping UI if the corresponding armature isn't selected
        map_box.enabled = armature_to_map is not None
        
        # Header row with Auto-Map button
        header_row = map_box.row(align=True)
        header_row.label(text=f"Editing: {armature_to_map.name if armature_to_map else 'None'}")
        op = header_row.operator("bhr.auto_map_bones", icon='AUTO', text="Auto-Map")
        op.map_type = map_type

        if not armature_to_map:
            box.label(text=f"Select a {map_type.capitalize()} Armature to begin mapping.", icon='INFO')
            return

        # Create a two-column layout for the long list of bones
        # This significantly improves readability and compactness.
        split = map_box.split(factor=0.5)
        col_left = split.column(align=True)
        col_right = split.column(align=True)
        
        half_len = (len(STANDARD_BONE_NAMES) + 1) // 2
        for i, (prop_name, display_name) in enumerate(STANDARD_BONE_NAMES):
            target_col = col_left if i < half_len else col_right
            
            target_col.prop_search(
                mapping_to_edit, prop_name, armature_to_map.data, "bones", text=display_name
            )

        # --- Section 3: Execute Retargeting ---
        box = layout.box()
        box.label(text="3. Execute Retargeting", icon='PLAY')

        # Retargeting options defined in properties.py
        options_box = box.box()
        options_box.prop(props, "use_scale_normalization")
        options_box.prop(props, "use_pose_alignment")

        # Main execution button
        row = box.row()
        # The button is only active if both armatures are selected.
        row.enabled = props.target_armature is not None and props.source_armature is not None
        # This operator will be created in a subsequent step.
        row.operator("bhr.execute_retarget", text="Run Retargeting", icon='TRIA_RIGHT_BAR')

def register():
    """Registers the UI panel class."""
    bpy.utils.register_class(BHR_PT_MainPanel)

def unregister():
    """Unregisters the UI panel class."""
    bpy.utils.unregister_class(BHR_PT_MainPanel)