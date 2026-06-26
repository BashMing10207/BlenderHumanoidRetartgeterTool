import bpy
import time
from . import mapping
from . import alignment
from . import finalization

class BHRT_OT_ExecuteRetargeting(bpy.types.Operator):
    """
    Executes the entire retargeting process based on the NEWPLAN.md specification.
    Orchestrates all phases from duplication to finalization.
    """
    bl_idname = "bhrt.execute_retargeting"
    bl_label = "Execute Retargeting"
    bl_description = "Run the full automatic retargeting process"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        props = context.scene.retargeting_tool_props
        return props.target_armature and props.source_armature

    def execute(self, context):
        start_time = time.time()
        print("\n" + "="*50)
        print("Blender Humanoid Retargeter: Process Started")
        print("="*50)

        props = context.scene.retargeting_tool_props
        target_arm = props.target_armature
        source_arm = props.source_armature
        target_map = props.target_bone_mapping
        source_map = props.source_bone_mapping

        patched_armature = None
        patched_meshes = []

        try:
            # --- PRE-FLIGHT: Non-destructive Duplication ---
            print("\n[Step 1/5] Isolating source objects (Non-destructive)...")
            patched_armature, patched_meshes = mapping.duplicate_and_isolate(source_arm)
            if not patched_armature or not patched_meshes:
                raise RuntimeError("Failed to duplicate source armature or meshes.")
            print(f"  - Created temporary objects: '{patched_armature.name}' and {len(patched_meshes)} meshes.")

            # --- PRE-FLIGHT: Heuristic Bone Mapping ---
            print("\n[Step 2/5] Running automatic bone mapping...")
            mapping.auto_bone_map(target_arm, target_map)
            mapping.auto_bone_map(patched_armature, source_map)
            print("  - Bone mapping complete.")

            # --- PHASE 1 & 2: Pose Alignment and Baking ---
            print("\n[Step 3/5] Aligning pose and baking geometry (Phase 1 & 2)...")
            alignment.align_and_bake_pose(
                context, target_arm, patched_armature, patched_meshes, target_map, source_map
            )

            # --- PHASE 3: Weight Topology Reconstruction ---
            print("\n[Step 4/5] Reconstructing weight topology (Phase 3)...")
            mapping.merge_unmapped_weights(
                patched_armature, patched_meshes, source_map
            )

            # --- PHASE 4: Finalization and Cleanup ---
            print("\n[Step 5/5] Finalizing and rebinding to target (Phase 4)...")
            finalization.run_finalization_phase(
                context, patched_meshes, patched_armature, target_arm, target_map, source_map
            )

            # --- Process Complete ---
            end_time = time.time()
            print("\n" + "="*50)
            self.report({'INFO'}, f"Retargeting complete in {end_time - start_time:.2f} seconds.")
            print("="*50)

            return {'FINISHED'}

        except Exception as e:
            # --- Error Handling & Cleanup ---
            self.report({'ERROR'}, f"Process failed: {e}")
            print(f"\n[ERROR] An exception occurred: {e}")
            
            # Clean up any created temporary objects on failure
            if patched_armature:
                bpy.data.objects.remove(patched_armature, do_unlink=True)
            for mesh in patched_meshes:
                bpy.data.objects.remove(mesh, do_unlink=True)
            
            # Unhide originals
            source_arm.hide_set(False)
            # This is a simplified version; a full implementation would track original meshes too.

            return {'CANCELLED'}


def register():
    bpy.utils.register_class(BHRT_OT_ExecuteRetargeting)

def unregister():
    bpy.utils.unregister_class(BHRT_OT_ExecuteRetargeting)