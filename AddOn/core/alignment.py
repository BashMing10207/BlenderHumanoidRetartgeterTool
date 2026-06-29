import bpy
from mathutils import Matrix, Vector, Quaternion
from .mapping import get_topological_sorted_bones, STANDARD_BONE_HIERARCHY
from .normalization import calculate_scale_factor

def align_and_bake_pose(context, target_arm, patched_arm, patched_meshes, target_map, source_map, use_pose=True, use_scale=True):
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

    if use_pose:
        try:
            # --- Phase 1: Auto-Pose Vector Alignment ---
            # All scaling pre-passes have been removed due to instability causing severe distortions.
            # This phase now ONLY performs rotation alignment for maximum stability.
            print("  - 포즈 정렬 시작 (방향 전용)...")

            bpy.context.view_layer.objects.active = patched_arm
            bpy.ops.object.mode_set(mode='POSE')

            # Reset all pose transforms to a clean state before starting.
            for pbone in patched_arm.pose.bones:
                pbone.location = (0, 0, 0)
                pbone.rotation_quaternion = (1, 0, 0, 0)
                pbone.scale = (1, 1, 1)
            context.view_layer.update()

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
                    # This is a leaf bone. For stability, we define its direction as a continuation
                    # of its parent's direction. This avoids twists from unreliable tail positions,
                    # which was causing 90-degree flips on fingertips.
                    if source_pbone.parent and target_pbone.parent:
                        # Vector from parent's head to current bone's head, which defines the parent's direction.
                        target_vec = (target_arm.matrix_world @ target_pbone.head) - (target_arm.matrix_world @ target_pbone.parent.head)
                        source_vec = (patched_arm.matrix_world @ source_pbone.head) - (patched_arm.matrix_world @ source_pbone.parent.head)
                    else:
                        # Absolute fallback for parentless leaf bones (e.g., hips): use the original tail-head vector.
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

                    # 2. Define the 'Right' axis (X) - THE CRITICAL FIX
                    # The cross product order must be (aim x up) to produce a right-handed
                    # coordinate system (X = Y x Z). The previous order (up x aim) created a
                    # left-handed (mirrored) system, which was the root cause of the severe twisting.
                    x_axis = y_axis.cross(z_axis)
                    
                    # Create the matrix from column vectors. This is a standard
                    # local-to-world orientation matrix.
                    return Matrix((x_axis, y_axis, z_axis)).transposed() # Transpose to make them columns

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

            # --- Proportional Fix Pass (Limb Root Shifting) ---
            # After rotation alignment, the orientation is correct, but proportions might be off.
            # This pass corrects the positions of limb ends (hands, feet, and now fingers)
            # by shifting the root of the limb (upper arm, upper leg, or first finger joint).
            # This is safer than scaling individual bones, which has proven unstable.
            print("  - 비율 보정 시작 (팔/다리 위치 조정)...")

            # Define limb chains: [ancestor, root, ..., leaf]
            limb_chains = {
                # Main Limbs
                'Left Arm':  ['chest', 'leftUpperArm', 'leftLowerArm', 'leftHand'],
                'Right Arm': ['chest', 'rightUpperArm', 'rightLowerArm', 'rightHand'],
                'Left Leg':  ['hips', 'leftUpperLeg', 'leftLowerLeg', 'leftFoot'],
                'Right Leg': ['hips', 'rightUpperLeg', 'rightLowerLeg', 'rightFoot'],
            }

            # Dynamically generate finger limb chains
            finger_types_data = [
                ('Thumb', 2),
                ('Index', 3),
                ('Middle', 3),
                ('Ring', 3),
                ('Pinky', 3)
            ]
            sides = [('left', 'leftHand'), ('right', 'rightHand')]

            for side_prefix, hand_prop in sides:
                for finger_type, num_joints in finger_types_data:
                    finger_prop_base = f'{side_prefix}{finger_type}'
                    
                    # Build the chain for the current finger: [hand, first_joint, ..., last_joint]
                    chain = [hand_prop] # Ancestor is the hand bone
                    for i in range(1, num_joints + 1):
                        chain.append(f'{finger_prop_base}{i:02d}')
                    
                    limb_chains[f'{side_prefix} {finger_type}'] = chain

            for limb_name, prop_chain in limb_chains.items():
                ancestor_prop, root_prop, leaf_prop = prop_chain[0], prop_chain[1], prop_chain[-1]

                # Get the pose bones for the source armature
                s_root = patched_arm.pose.bones.get(getattr(source_map, root_prop, None))
                s_leaf = patched_arm.pose.bones.get(getattr(source_map, leaf_prop, None))

                # Get the data bones for the target armature (using rest pose for stable proportions)
                t_root = target_arm.data.bones.get(getattr(target_map, root_prop, None))
                t_leaf = target_arm.data.bones.get(getattr(target_map, leaf_prop, None))

                if not all([s_root, s_leaf, t_root, t_leaf]):
                    print(f"    - Skipping {limb_name}: one or more bones not mapped or found.")
                    continue

                # --- CRITICAL FIX: The vector must be calculated from the limb's actual root (e.g., shoulder), not the ancestor (e.g., chest).
                # This prevents a "lever" effect that causes the final position to be biased.

                # Determine if the leaf is an extremity joint (like a wrist) or a true end-point (like a fingertip).
                # For hands/feet, the vector ends at their head. For fingers/toes, it ends at their tail.
                is_extremity_joint = leaf_prop in {'leftHand', 'rightHand', 'leftFoot', 'rightFoot'}

                # 1. Get the target limb's vector in WORLD space from its rest pose.
                target_root_world = target_arm.matrix_world @ t_root.head_local
                
                target_leaf_pos_local = t_leaf.head_local if is_extremity_joint else t_leaf.tail_local
                target_leaf_world = target_arm.matrix_world @ target_leaf_pos_local
                target_limb_vec_world = target_leaf_world - target_root_world

                # 2. Get the source limb's current vector in WORLD space from its posed state.
                source_root_world = patched_arm.matrix_world @ s_root.head

                source_leaf_pos_local = s_leaf.head if is_extremity_joint else s_leaf.tail
                source_leaf_world = patched_arm.matrix_world @ source_leaf_pos_local
                source_limb_vec_world = source_leaf_world - source_root_world

                # 3. Calculate the correction vector in WORLD space (Revised Logic).
                # The previous logic (source_ancestor + target_limb_vector) created a directional
                # bias if the armatures had different world orientations.
                # This revised logic correctly separates length from direction. It takes the source's
                # already-aligned direction and applies the target's length to it.
                if source_limb_vec_world.length < 0.0001:
                    continue

                # The ideal vector for the source limb should have its current direction but the target's length.
                ideal_limb_vec = source_limb_vec_world.normalized() * target_limb_vec_world.length
                # The correction is the difference between this ideal vector and the current source vector.
                world_correction_vec = ideal_limb_vec - source_limb_vec_world

                # 4. Apply the correction by shifting the 'location' of the limb's root bone.
                if s_root.parent:
                    # The correction vector is in world space. It must be transformed into the
                    # local space of the root bone's parent (e.g., the chest bone).
                    mat_parent_to_world = patched_arm.matrix_world @ s_root.parent.matrix
                    correction_in_parent_space = mat_parent_to_world.inverted().to_3x3() @ world_correction_vec
                    s_root.location += correction_in_parent_space
                else: # Should not happen for limbs, but as a fallback
                    correction_in_arm_space = patched_arm.matrix_world.inverted().to_3x3() @ world_correction_vec
                    s_root.location += correction_in_arm_space
                
                # A scene update is CRITICAL here. It ensures that when we process child limbs
                # (like fingers), they are calculated based on the newly updated position of their
                # parent limb (the arm). Without this, finger positions would be incorrect.
                context.view_layer.update()

            print("  - 비율 보정 완료.")
        finally:
            # Ensure we switch back to object mode even if pose alignment fails
            if patched_arm and patched_arm.name in bpy.data.objects and patched_arm.mode == 'POSE':
                bpy.ops.object.mode_set(mode='OBJECT')

    # --- Phase 2: Scale Synchronization & Baking ---
    bpy.ops.object.mode_set(mode='OBJECT')

    if use_scale:
        # --- Phase 2: Scale Synchronization & Baking ---
        # 2.1: Scale Synchronization
        print("  - 스케일 동기화 중...")
        scale_factor = calculate_scale_factor(target_arm, patched_arm, target_map, source_map)
        
        # Apply scale to the patched armature and its meshes
        patched_arm.scale = Vector(patched_arm.scale) * scale_factor
        for mesh_obj in patched_meshes:
            mesh_obj.scale = Vector(mesh_obj.scale) * scale_factor
        
    context.view_layer.update() # Ensure scale changes are registered before applying

    # 2.2: Bake Form (Apply Armature Modifier)
    # This step is now always performed to bake the results of the previous optional steps.
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

    try:
        # --- Context Restoration ---
        if original_active and original_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = original_active
            if bpy.context.active_object and bpy.context.active_object.mode != original_mode:
                 bpy.ops.object.mode_set(mode=original_mode)
        elif not bpy.context.view_layer.objects.active and patched_arm and patched_arm.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = patched_arm
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as e:
        print(f"Context restoration failed: {e}")