import bpy
from mathutils import Matrix, Vector, Quaternion
from .mapping import get_topological_sorted_bones, STANDARD_BONE_HIERARCHY
from .normalization import calculate_scale_factor

def align_and_bake_pose(context, target_arm, patched_arm, patched_meshes, target_map, source_map):
    """
    Implements NEWPLAN.md Phase 1 & 2: Vector-based Pose Alignment and Baking.
    - Aligns the patched armature's pose to the target armature's pose using vector math.
    - Calculates and applies a scale factor to match the target's height.
    - Bakes the final pose and scale into the mesh geometry by applying the armature modifier.
    This replaces the old constraint-based and matrix-mixing methods.
    """
    if not target_arm or not patched_arm:
        print("Alignment Error: Target or Patched armature not provided.")
        return

    print(f"'{patched_arm.name}'의 포즈 및 스케일 동기화 시작 (벡터 기반)...")

    # --- Context Management ---
    original_active = context.view_layer.objects.active
    original_mode = 'OBJECT'
    if original_active and original_active.mode:
        original_mode = original_active.mode

    try:
        # --- Phase 1: Auto-Pose Vector Alignment ---
        bpy.context.view_layer.objects.active = patched_arm
        bpy.ops.object.mode_set(mode='POSE')

        # Create a reverse mapping for faster child lookup
        # { 'parent_prop': ['child_prop1', 'child_prop2'], ... }
        child_map = {}
        for child, parent in STANDARD_BONE_HIERARCHY.items():
            if parent not in child_map:
                child_map[parent] = []
            child_map[parent].append(child)

        # Process bones in topological order (parents before children)
        sorted_bone_props = get_topological_sorted_bones()

        for prop_name, _ in sorted_bone_props:
            source_bone_name = getattr(source_map, prop_name, None)
            target_bone_name = getattr(target_map, prop_name, None)

            if not (source_bone_name and target_bone_name):
                continue

            source_pbone = patched_arm.pose.bones.get(source_bone_name)
            target_pbone = target_arm.pose.bones.get(target_bone_name)

            if not (source_pbone and target_pbone):
                continue
            
            # --- Robust Vector Definition (Topological Approach) ---
            # Instead of relying on tail-head, we define a bone's vector as the
            # direction towards its primary child. This is robust against rigs with
            # different bone axis orientations, fixing the "90-degree flip" issue.
            child_prop_names = child_map.get(prop_name, [])
            source_child_pbone = None
            target_child_pbone = None

            # Find the first valid, mapped child bone
            for child_prop in child_prop_names:
                source_child_name = getattr(source_map, child_prop, None)
                target_child_name = getattr(target_map, child_prop, None)
                if source_child_name and target_child_name:
                    source_child_pbone = patched_arm.pose.bones.get(source_child_name)
                    target_child_pbone = target_arm.pose.bones.get(target_child_name)
                    if source_child_pbone and target_child_pbone:
                        break # Found a valid child pair, exit loop

            if source_child_pbone and target_child_pbone:
                # Define vector from parent's head to child's head
                target_vec = (target_arm.matrix_world @ target_child_pbone.head) - (target_arm.matrix_world @ target_pbone.head)
                source_vec = (patched_arm.matrix_world @ source_child_pbone.head) - (patched_arm.matrix_world @ source_pbone.head)
            else:
                # Fallback for leaf bones (e.g., head, hands, feet) using tail-head
                target_vec = (target_arm.matrix_world @ target_pbone.tail) - (target_arm.matrix_world @ target_pbone.head)
                source_vec = (patched_arm.matrix_world @ source_pbone.tail) - (patched_arm.matrix_world @ source_pbone.head)

            # Skip zero-length bones (e.g., helper bones)
            if source_vec.length < 0.0001 or target_vec.length < 0.0001:
                continue

            # --- Final, Corrected Two-Axis Alignment ---
            # The previous severe twisting was caused by a critical math error: creating a
            # left-handed coordinate system (a "mirror image" of the orientation) instead of
            # a right-handed one. This resulted in nonsensical, inside-out rotations.
            # This new implementation corrects that fundamental flaw.

            def build_orientation_matrix(aim_vec, up_vec_ref, is_target):
                """
                Creates a standard 3x3 local-to-world rotation matrix.
                The matrix columns will be the new X, Y, and Z basis vectors.
                """
                y_axis = aim_vec.normalized()
                
                # Use Gram-Schmidt process to find an orthonormal basis (a set of 3 perpendicular unit vectors).
                
                # 1. Define the 'Up' axis (Z)
                # Project the reference 'up' vector onto the plane perpendicular to the 'aim' vector.
                z_axis_proj = up_vec_ref - up_vec_ref.project(y_axis)

                # Handle gimbal lock: if the reference 'up' is parallel to the 'aim' vector.
                if z_axis_proj.length < 0.0001:
                    # The reference is useless. Pick an arbitrary, non-parallel one.
                    # World X-axis is a safe bet unless the aim is also along X.
                    fallback_ref = Vector((0, 0, 1)) if abs(y_axis.z) < 0.9 else Vector((1, 0, 0))
                    z_axis_proj = fallback_ref - fallback_ref.project(y_axis)
                
                z_axis = z_axis_proj.normalized()

                # 2. Define the 'Right' axis (X)
                # THE CRITICAL FIX: The cross product order must be (up x aim) to produce a
                # right-handed coordinate system. The previous (aim x up) created a left-handed
                # (mirrored) system, causing the severe twists.
                x_axis = z_axis.cross(y_axis)
                
                # Create the matrix from column vectors. This is a standard
                # local-to-world orientation matrix.
                return Matrix((x_axis, y_axis, z_axis)).transposed()

            # Use a stable, global 'up' vector (World Z) as a common reference.
            world_up = Vector((0, 0, 1))

            # Build the orientation matrices for both source and target using the corrected function.
            mat_orient_target = build_orientation_matrix(target_vec, world_up, True)
            mat_orient_source = build_orientation_matrix(source_vec, world_up, False)

            # Calculate the final rotation that transforms the source orientation to the target.
            # R = Target @ Source_Inverse (and for rotation matrices, Inverse == Transpose)
            mat_rot_diff = mat_orient_target @ mat_orient_source.transposed()
            rot_diff = mat_rot_diff.to_quaternion()

            # --- Apply the calculated rotation ---
            current_world_matrix = patched_arm.matrix_world @ source_pbone.matrix
            pivot_point = current_world_matrix.to_translation()

            mat_rotate_around_pivot = (
                Matrix.Translation(pivot_point) @
                rot_diff.to_matrix().to_4x4() @
                Matrix.Translation(-pivot_point)
            )

            new_world_matrix = mat_rotate_around_pivot @ current_world_matrix
            source_pbone.matrix = patched_arm.matrix_world.inverted() @ new_world_matrix
            context.view_layer.update()

        print("  - 포즈 정렬 완료.")

        # --- Phase 2: Scale Synchronization & Baking ---
        bpy.ops.object.mode_set(mode='OBJECT')

        # 2.1: Scale Synchronization
        print("  - 스케일 동기화 중...")
        scale_factor = calculate_scale_factor(target_arm, patched_arm, target_map, source_map)
        
        # Apply scale to the patched armature and its meshes
        patched_arm.scale = Vector(patched_arm.scale) * scale_factor
        for mesh_obj in patched_meshes:
            mesh_obj.scale = Vector(mesh_obj.scale) * scale_factor
        
        context.view_layer.update() # Ensure scale changes are registered before applying

        # 2.2: Bake Form (Apply Armature Modifier)
        print("  - 메쉬 형태 베이킹 중...")
        for mesh_obj in patched_meshes:
            context.view_layer.objects.active = mesh_obj
            
            # Find the correct armature modifier to apply
            armature_mod_name = ""
            for mod in mesh_obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object == patched_arm:
                    armature_mod_name = mod.name
                    break
            
            if armature_mod_name:
                bpy.ops.object.modifier_apply(modifier=armature_mod_name)
                print(f"    - '{mesh_obj.name}'의 Armature Modifier 적용 완료.")
            else:
                print(f"    - Warning: '{mesh_obj.name}'에서 '{patched_arm.name}'을 사용하는 Armature Modifier를 찾지 못했습니다.")

        # After applying modifiers, reset the scale of the objects to 1.0
        # The scale is now baked into the geometry.
        patched_arm.scale = (1.0, 1.0, 1.0)
        for mesh_obj in patched_meshes:
            mesh_obj.scale = (1.0, 1.0, 1.0)

        print("  - 포즈 및 스케일 베이킹 완료.")

    finally:
        # --- Context Restoration ---
        if original_active and original_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = original_active
            if bpy.context.active_object and bpy.context.active_object.mode != original_mode:
                 bpy.ops.object.mode_set(mode=original_mode)
        elif not bpy.context.view_layer.objects.active and patched_arm and patched_arm.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = patched_arm
            bpy.ops.object.mode_set(mode='OBJECT')