import bpy
from mathutils import Matrix
from ..properties import STANDARD_BONE_NAMES

def align_pose_to_target(target_armature, source_armature, target_mapping, source_mapping):
    """
    Source 아마추어의 포즈를 수정하여, 각 본의 방향이 Target 아마추어의
    기준 포즈(Rest Pose) 방향과 일치하도록 정렬합니다.
    각 포즈 본의 `matrix_basis`를 계산하여 적용합니다.
    """
    if not all([target_armature, source_armature, target_mapping, source_mapping]):
        print("정렬 오류: Target, Source, 또는 매핑 정보가 누락되었습니다.")
        return

    # --- 컨텍스트 관리 ---
    original_active = bpy.context.view_layer.objects.active
    original_mode = 'OBJECT'
    if original_active:
        original_mode = original_active.mode
    
    # --- 데이터 수집 (에딧 모드에서 기준 포즈 행렬 추출) ---
    target_rest_matrices = {}
    source_rest_matrices = {}

    try:
        # Target 아마추어를 에딧 모드로 전환하여 기준 행렬 추출
        bpy.context.view_layer.objects.active = target_armature
        bpy.ops.object.mode_set(mode='EDIT')
        for prop_name, _ in STANDARD_BONE_NAMES:
            target_bone_name = getattr(target_mapping, prop_name)
            edit_bone = target_armature.data.edit_bones.get(target_bone_name)
            if edit_bone:
                target_rest_matrices[target_bone_name] = edit_bone.matrix.copy()
        
        # Source 아마추어를 에딧 모드로 전환하여 기준 행렬 추출
        bpy.context.view_layer.objects.active = source_armature
        bpy.ops.object.mode_set(mode='EDIT')
        for prop_name, _ in STANDARD_BONE_NAMES:
            source_bone_name = getattr(source_mapping, prop_name)
            if source_bone_name:
                edit_bone = source_armature.data.edit_bones.get(source_bone_name)
                if edit_bone:
                    source_rest_matrices[source_bone_name] = edit_bone.matrix.copy()

    finally:
        # 항상 오브젝트 모드로 복귀 보장
        bpy.ops.object.mode_set(mode='OBJECT')

    # --- 포즈 적용 (포즈 모드에서) ---
    try:
        bpy.context.view_layer.objects.active = source_armature
        bpy.ops.object.mode_set(mode='POSE')

        for prop_name, _ in STANDARD_BONE_NAMES:
            target_bone_name = getattr(target_mapping, prop_name)
            source_bone_name = getattr(source_mapping, prop_name)

            if not source_bone_name or target_bone_name not in target_rest_matrices or source_bone_name not in source_rest_matrices:
                continue
            
            source_pose_bone = source_armature.pose.bones.get(source_bone_name)
            if not source_pose_bone:
                continue

            target_rest_matrix = target_rest_matrices[target_bone_name]
            source_rest_matrix = source_rest_matrices[source_bone_name]

            # 최종 포즈 행렬은 다음을 가져야 함:
            # - Target 기준 본의 '회전'
            # - Source 기준 본의 '위치'와 '스케일' (길이 보존)
            source_loc, _, source_scl = source_rest_matrix.decompose()
            _, target_rot, _ = target_rest_matrix.decompose()

            # 원하는 최종 행렬(아마추어 공간 기준)을 재구성
            final_matrix = (
                Matrix.Translation(source_loc) @
                target_rot.to_matrix().to_4x4() @
                Matrix.Diagonal(source_scl).to_4x4()
            )

            # 이 final_matrix를 만들기 위한 matrix_basis를 역산
            # final_matrix = source_rest_matrix @ matrix_basis
            # => matrix_basis = source_rest_matrix.inverted() @ final_matrix
            if source_rest_matrix.determinant() != 0:
                matrix_basis = source_rest_matrix.inverted() @ final_matrix
                source_pose_bone.matrix_basis = matrix_basis

    finally:
        # --- 컨텍스트 복원 ---
        bpy.ops.object.mode_set(mode='OBJECT')
        if original_active:
            bpy.context.view_layer.objects.active = original_active
            bpy.ops.object.mode_set(mode=original_mode)

    print("포즈 정렬이 완료되었습니다.")