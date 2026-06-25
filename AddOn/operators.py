import bpy
from .core import mapping, alignment, finalization

class RETARGET_OT_AutoMapBones(bpy.types.Operator):
    """Heuristically maps bones for both target and source armatures."""
    bl_idname = "retarget.auto_map_bones"
    bl_label = "Auto-Map Bones"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.retargeting_tool_props
        return props.target_armature and props.source_armature

    def execute(self, context):
        props = context.scene.retargeting_tool_props
        mapping.auto_bone_map(props.target_armature, props.target_bone_mapping)
        mapping.auto_bone_map(props.source_armature, props.source_bone_mapping)
        self.report({'INFO'}, "Auto-mapping complete.")
        return {'FINISHED'}

class RETARGET_OT_Execute(bpy.types.Operator):
    """Executes the full retargeting pipeline according to GuidLine.md and NEWPLAN.md"""
    bl_idname = "retarget.execute"
    bl_label = "Execute Retargeting"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.retargeting_tool_props
        return props.target_armature and props.source_armature

    def execute(self, context):
        props = context.scene.retargeting_tool_props
        target_arm = props.target_armature
        source_arm = props.source_armature
        target_map = props.target_bone_mapping
        source_map = props.source_bone_mapping

        # --- Setup: Isolate source objects by duplicating them ---
        print("--- Phase: Isolation & Duplication ---")
        patched_arm, patched_meshes = mapping.duplicate_and_isolate(source_arm)
        if not patched_arm or not patched_meshes:
            self.report({'ERROR'}, "Failed to duplicate source objects. Aborting.")
            return {'CANCELLED'}
        
        # --- Pre-process: Apply transforms as a baseline requirement ---
        print("--- Phase: Applying Transforms ---")
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = patched_arm
        patched_arm.select_set(True)
        for mesh in patched_meshes:
            mesh.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        print("  - Applied scale to all patched objects.")

        # --- Guideline.md Phase 1: Constraint-based Alignment ---
        print("\n--- Phase 1: Aligning Pose with Constraints ---")
        alignment.apply_alignment_constraints(context, target_arm, patched_arm, target_map, source_map)

        # --- Guideline.md Phase 2: Bake Mesh and Clear Constraints ---
        print("\n--- Phase 2: Baking Mesh and Clearing Constraints ---")
        
        # Part A: Bake the Armature modifier for each patched mesh
        for mesh_obj in patched_meshes:
            context.view_layer.objects.active = mesh_obj
            
            armature_mod_name = None
            for mod in mesh_obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object == patched_arm:
                    armature_mod_name = mod.name
                    break
            
            if armature_mod_name:
                print(f"  - Baking Armature modifier '{armature_mod_name}' for mesh '{mesh_obj.name}'...")
                try:
                    bpy.ops.object.modifier_apply(modifier=armature_mod_name)
                    print(f"  - Bake successful for '{mesh_obj.name}'.")
                except RuntimeError as e:
                    self.report({'ERROR'}, f"Failed to apply modifier on '{mesh_obj.name}': {e}. Aborting.")
                    alignment.clear_alignment_constraints(patched_arm)
                    # TODO: Add cleanup for duplicated objects
                    return {'CANCELLED'}
            else:
                self.report({'WARNING'}, f"No Armature modifier found on '{mesh_obj.name}'. Skipping bake for this mesh.")

        # Part B: Clear all alignment constraints from the patched armature
        alignment.clear_alignment_constraints(patched_arm)

        # --- Guideline.md Phase 3: Weight Merge & Renaming ---
        print("\n--- Phase 3: Reconstructing Weights ---")
        mapping.merge_unmapped_weights(patched_arm, patched_meshes, source_map)
        for mesh_obj in patched_meshes:
             finalization.rename_vertex_groups(mesh_obj, target_map, source_map)

        # --- Guideline.md Phase 4: Finalization ---
        print("\n--- Phase 4: Finalizing Dependencies ---")
        for mesh_obj in patched_meshes:
            finalization.switch_armature_dependency(mesh_obj, target_arm)
        
        finalization.cleanup_patched_armature(patched_arm)

        # --- Post-process: Select final objects ---
        bpy.ops.object.select_all(action='DESELECT')
        context.view_layer.objects.active = target_arm
        target_arm.select_set(True)
        for mesh in patched_meshes:
            mesh.select_set(True)

        self.report({'INFO'}, "Retargeting process completed.")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RETARGET_OT_AutoMapBones)
    bpy.utils.register_class(RETARGET_OT_Execute)

def unregister():
    bpy.utils.unregister_class(RETARGET_OT_AutoMapBones)
    bpy.utils.unregister_class(RETARGET_OT_Execute)