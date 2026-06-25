import bpy

def get_armature_height(armature_obj, head_bone_name, l_foot_bone_name, r_foot_bone_name):
    """
    지정된 본들의 월드 좌표를 기준으로 아마추어의 높이를 계산합니다.
    머리, 왼발, 오른발 본이 없으면 높이를 계산할 수 없으므로 None을 반환합니다.
    """
    if not armature_obj or armature_obj.type != 'ARMATURE':
        return None

    pose_bones = armature_obj.pose.bones
    
    head_bone = pose_bones.get(head_bone_name)
    l_foot_bone = pose_bones.get(l_foot_bone_name)
    r_foot_bone = pose_bones.get(r_foot_bone_name)

    if not all([head_bone, l_foot_bone, r_foot_bone]):
        print(f"Warning: Height calculation failed for {armature_obj.name}. Missing one or more key bones: head, left foot, right foot.")
        return None

    world_matrix = armature_obj.matrix_world
    
    # 본의 head 위치를 월드 좌표로 변환
    head_pos_world = world_matrix @ head_bone.head
    l_foot_pos_world = world_matrix @ l_foot_bone.head
    r_foot_pos_world = world_matrix @ r_foot_bone.head
    
    # Z축 높이 계산
    highest_point = head_pos_world.z
    lowest_point = min(l_foot_pos_world.z, r_foot_pos_world.z)
    
    height = abs(highest_point - lowest_point)
    
    return height

def calculate_scale_factor(target_armature, source_armature, target_mapping, source_mapping):
    """
    Target과 Source 아마추어의 신체 비율을 비교하여 스케일 팩터를 계산합니다.
    """
    # Target 아마추어 높이 계산 (표준 본 이름 사용)
    target_head = getattr(target_mapping, 'head', 'head')
    target_lfoot = getattr(target_mapping, 'leftFoot', 'leftFoot')
    target_rfoot = getattr(target_mapping, 'rightFoot', 'rightFoot')
    target_height = get_armature_height(target_armature, target_head, target_lfoot, target_rfoot)
    
    # Source 아마추어 높이 계산 (매핑된 본 이름 사용)
    source_height = get_armature_height(source_armature, source_mapping.head, source_mapping.leftFoot, source_mapping.rightFoot)

    if target_height is None or source_height is None or source_height == 0:
        print("Could not calculate heights or source height is zero. Returning scale factor of 1.0.")
        return 1.0
        
    scale_factor = target_height / source_height
    print(f"Target Height: {target_height:.4f}, Source Height: {source_height:.4f}, Scale Factor: {scale_factor:.4f}")
    
    return scale_factor