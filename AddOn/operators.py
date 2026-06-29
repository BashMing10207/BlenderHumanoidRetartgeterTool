import bpy
# Import all necessary core modules for the pipeline
from .core import mapping, alignment, normalization, finalization
import traceback


class BHR_OT_AutoMapBones(bpy.types.Operator):
    """
    Automatically maps bones of the Source Armature to the standard humanoid rig
    based on name heuristics. This operator fills in unmapped bone slots.
    """
    bl_idname = "bhr.auto_map_bones"
    bl_label = "Auto-Map Bones"
    bl_options = {'REGISTER', 'UNDO'}

    map_type: bpy.props.StringProperty(name="Mapping Type", default='SOURCE')

    @classmethod
    def poll(cls, context):
        """Disable the operator if no armatures are selected at all."""
        props = context.scene.retargeting_tool_props
        # The UI will handle enabling/disabling for specific cases.
        # This poll is a general safeguard.
        return props.source_armature is not None or props.target_armature is not None

    def execute(self, context):
        """
        Executes the auto-mapping process by calling the core logic
        from the mapping module.
        """
        props = context.scene.retargeting_tool_props
        armature = None
        bone_mapping = None

        if self.map_type == 'SOURCE':
            armature = props.source_armature
            bone_mapping = props.source_bone_mapping
        elif self.map_type == 'TARGET':
            armature = props.target_armature
            bone_mapping = props.target_bone_mapping
        
        if not armature:
            self.report({'WARNING'}, f"{self.map_type.capitalize()} Armature not set.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Running automatic bone mapping for {self.map_type.capitalize()}...")
        
        # Call the core function that contains the mapping logic
        mapping.auto_bone_map(armature, bone_mapping)
        
        self.report({'INFO'}, "Auto-mapping complete. Please review the results.")
        return {'FINISHED'}

class BHR_OT_ExecuteRetarget(bpy.types.Operator):
    """
    Executes the entire retargeting pipeline:
    1. Duplicates the source model.
    2. Aligns pose and normalizes scale (optional).
    3. Bakes the mesh shape by applying the modifier.
    4. Merges weights from unmapped bones to their parents.
    5. Rebinds the final mesh to the target armature.
    """
    bl_idname = "bhr.execute_retarget"
    bl_label = "Execute Retargeting"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        """Disables the operator if the required armatures are not set."""
        props = context.scene.retargeting_tool_props
        if not props.target_armature or not props.source_armature:
            return False
        return True

    def execute(self, context):
        props = context.scene.retargeting_tool_props
        
        # Ensure we are in Object mode for safety
        if context.active_object and context.active_object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, "Starting retargeting process...")

        new_armature = None
        new_meshes = []

        # 실행 로직이 core 모듈의 실제 함수를 호출하도록 리팩토링하여 AttributeError를 해결합니다.
        try:
            # --- PHASE 1: DUPLICATION ---
            self.report({'INFO'}, "Phase 1: Duplicating and isolating source model...")
            new_armature, new_meshes = mapping.duplicate_and_isolate(props.source_armature)
            if not new_armature or not new_meshes:
                raise RuntimeError("Failed to duplicate the source model. Check console for errors.")
            
            # --- PHASE 2: ALIGNMENT, NORMALIZATION, AND BAKING ---
            # 이 단계는 TODO2.md 설계에 따라 포괄적인 단일 함수를 호출하도록 변경되었습니다.
            # 이를 통해 'align_pose' 관련 에러가 해결됩니다.
            # 참고: 이 코드가 정상 동작하려면 'core/alignment.py'에 'align_and_bake_pose' 함수가 구현되어 있어야 합니다.
            self.report({'INFO'}, "Phase 2: Aligning, scaling, and baking...")
            # alignment.py가 제공되지 않았으므로, 해당 모듈에 아래 함수가 구현되어 있다고 가정합니다.
            # 이 함수는 포즈, 스케일, 메쉬 베이크를 모두 처리해야 합니다.
            alignment.align_and_bake_pose(
                context,
                props.target_armature,
                new_armature,
                new_meshes,
                props.target_bone_mapping,
                props.source_bone_mapping,
                use_pose=props.use_pose_alignment,
                use_scale=props.use_scale_normalization
            )
            
            # --- PHASE 3: MERGE WEIGHTS ---
            self.report({'INFO'}, "Phase 3: Merging unmapped bone weights...")
            mapping.merge_unmapped_weights(new_armature, new_meshes, props.source_bone_mapping)

            # --- PHASE 4: FINALIZATION ---
            # 존재하지 않는 'rebind_to_target' 대신, 실제 구현된 'run_finalization_phase'를 호출하도록 수정합니다.
            self.report({'INFO'}, "Phase 4: Rebinding mesh to target armature...")
            finalization.run_finalization_phase(
                context, new_meshes, new_armature, props.target_armature, props.target_bone_mapping, props.source_bone_mapping
            )
            new_armature = None # Armature는 run_finalization_phase 내부에서 삭제됩니다.

            self.report({'INFO'}, "Retargeting process completed successfully!")

        except Exception as e:
            self.report({'ERROR_INVALID_INPUT'}, f"Retargeting failed: {e}")
            traceback.print_exc()
            
            if new_armature:
                # 새로 구현된 정리 함수를 호출하여 두 번째 에러를 해결합니다.
                finalization.cleanup_generated_objects(new_armature, new_meshes)
            
            return {'CANCELLED'}
        
        return {'FINISHED'}

classes = (
    BHR_OT_AutoMapBones,
    BHR_OT_ExecuteRetarget,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)