import bpy
from ..properties import STANDARD_BONE_NAMES # Import from the centralized properties file

def apply_alignment_constraints(context, target_arm, patched_arm, target_map, source_map):
    """
    Implements GuidLine.md Phase 1: Proportion & Pose Alignment using Constraints.
    Forces the patched_arm to match the target_arm's bone locations and orientations
    by adding temporary 'WORLD' to 'WORLD' space constraints. This is the new, correct method.
    """
    if not target_arm or not patched_arm:
        print("Alignment Error: Target or Patched armature not provided.")
        return

    print(f"'{patched_arm.name}'의 체형 및 포즈 동기화 시작 (제약 조건 방식)...")

    # Ensure we are in Pose Mode for the patched armature
    original_active = context.view_layer.objects.active
    original_mode = 'OBJECT'
    if original_active and original_active.mode:
        original_mode = original_active.mode

    bpy.context.view_layer.objects.active = patched_arm
    bpy.ops.object.mode_set(mode='POSE')

    # Process all mapped bones
    for prop_name, _ in STANDARD_BONE_NAMES:
        source_bone_name = getattr(source_map, prop_name, None)
        target_bone_name = getattr(target_map, prop_name, None)

        if source_bone_name and target_bone_name:
            source_pbone = patched_arm.pose.bones.get(source_bone_name)
            target_pbone = target_arm.pose.bones.get(target_bone_name)

            if source_pbone and target_pbone:
                # 1. Copy Location Constraint
                # Guideline: 공간은 반드시 WORLD to WORLD로 설정
                loc_constraint = source_pbone.constraints.new('COPY_LOCATION')
                loc_constraint.target = target_arm
                loc_constraint.subtarget = target_bone_name
                loc_constraint.owner_space = 'WORLD'
                loc_constraint.target_space = 'WORLD'

                # 2. Copy Rotation Constraint
                # Guideline: 공간은 반드시 WORLD to WORLD로 설정
                rot_constraint = source_pbone.constraints.new('COPY_ROTATION')
                rot_constraint.target = target_arm
                rot_constraint.subtarget = target_bone_name
                rot_constraint.owner_space = 'WORLD'
                rot_constraint.target_space = 'WORLD'

                # 3. (Optional) Stretch To Constraint
                # Guideline: 필요시 STRETCH_TO 제약 조건 부여
                # Note: This can sometimes cause undesirable scaling. Enable if needed.
                # stretch_constraint = source_pbone.constraints.new('STRETCH_TO')
                # stretch_constraint.target = target_arm
                # stretch_constraint.subtarget = target_bone_name
                # # Stretch To doesn't have space settings, it works with bone tips.

    # Force the viewport to update to reflect the new pose
    context.view_layer.update()

    # Restore original context
    if original_active and original_active.name in bpy.data.objects:
        bpy.context.view_layer.objects.active = original_active
        if bpy.context.active_object.mode != original_mode:
            bpy.ops.object.mode_set(mode=original_mode)
    else:
        bpy.ops.object.mode_set(mode='OBJECT')

    print("  - 제약 조건 기반 동기화 완료.")


def clear_alignment_constraints(patched_arm):
    """
    Removes all retargeting-related constraints from the patched armature.
    This is called after baking the mesh to break the dependency (Phase 2).
    """
    if not patched_arm or patched_arm.type != 'ARMATURE':
        print("Constraint Clear Error: Patched armature not provided.")
        return

    print(f"'{patched_arm.name}'의 동기화 제약 조건 정리 시작...")

    constraint_types_to_remove = {'COPY_LOCATION', 'COPY_ROTATION', 'STRETCH_TO'}

    for pbone in patched_arm.pose.bones:
        constraints_to_remove = [
            c for c in pbone.constraints if c.type in constraint_types_to_remove
        ]
        for c in constraints_to_remove:
            pbone.constraints.remove(c)

    print("  - 제약 조건 정리 완료.")