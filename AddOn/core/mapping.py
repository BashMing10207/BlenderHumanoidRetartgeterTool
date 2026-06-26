import bpy
from ..properties import STANDARD_BONE_NAMES # Import from the centralized properties file
from collections import deque

# 표준 본 이름과 매칭될 키워드 사전
# 더 정확한 매핑을 위해 키워드를 추가/수정할 수 있습니다.
BONE_KEYWORDS = {
    'hips': ['hip', 'pelvis', 'root'],
    'spine': ['spine'],
    'chest': ['chest', 'spine1', 'spine2', 'spine.001', 'spine.002', 'upper_torso', 'upperchest'],
    'neck': ['neck'],
    'head': ['head'],
    'leftUpperArm': ['upperarm', 'uparm', 'shoulder', 'arm', 'l', 'left'],
    'leftLowerArm': ['lowerarm', 'loarm', 'forearm', 'elbow', 'l', 'left'],
    'leftHand': ['hand', 'wrist', 'l', 'left'],
    'rightUpperArm': ['upperarm', 'uparm', 'shoulder', 'arm', 'r', 'right'],
    'rightLowerArm': ['lowerarm', 'loarm', 'forearm', 'elbow', 'r', 'right'],
    'rightHand': ['hand', 'wrist', 'r', 'right'],
    'leftUpperLeg': ['upperleg', 'upleg', 'thigh', 'leg', 'l', 'left'],
    'leftLowerLeg': ['lowerleg', 'loleg', 'shin', 'knee', 'leg', 'l', 'left'],
    'leftFoot': ['foot', 'ankle', 'l', 'left'],
    'rightUpperLeg': ['upperleg', 'upleg', 'thigh', 'leg', 'r', 'right'],
    'rightLowerLeg': ['lowerleg', 'loleg', 'shin', 'knee', 'leg', 'r', 'right'],
    'rightFoot': ['foot', 'ankle', 'r', 'right'],
    'leftToe': ['toe', 'l', 'left'],
    'rightToe': ['toe', 'r', 'right'],
}

# 오탐지를 방지하기 위한 부정 키워드 (예: 'upperarm'은 'lower'를 포함하면 안 됨)
NEGATIVE_KEYWORDS = {
    'leftUpperArm': ['lower', 'forearm', 'hand', 'wrist', 'leg', 'clavicle'],
    'leftLowerArm': ['upper', 'shoulder', 'hand', 'wrist', 'leg'],
    'leftHand': ['upper', 'lower', 'forearm', 'elbow', 'leg'],
    'rightUpperArm': ['lower', 'forearm', 'hand', 'wrist', 'leg', 'clavicle'],
    'rightLowerArm': ['upper', 'shoulder', 'hand', 'wrist', 'leg'],
    'rightHand': ['upper', 'lower', 'forearm', 'elbow', 'leg'],
    'leftUpperLeg': ['lower', 'shin', 'foot', 'ankle', 'arm'],
    'leftLowerLeg': ['upper', 'thigh', 'foot', 'ankle', 'arm'],
    'leftFoot': ['upper', 'lower', 'thigh', 'knee', 'arm'],
    'rightUpperLeg': ['lower', 'shin', 'foot', 'ankle', 'arm'],
    'rightLowerLeg': ['upper', 'thigh', 'foot', 'ankle', 'arm'],
    'rightFoot': ['upper', 'lower', 'thigh', 'knee', 'arm'],
    'leftToe': ['hand', 'finger', 'thumb', 'heel'],
    'rightToe': ['hand', 'finger', 'thumb', 'heel'],
    'spine': ['chest', 'neck', 'head'],
    'chest': ['spine0', 'neck', 'head'], # 'spine'이 'chest'보다 하위 본이라고 가정
}

# VETO_KEYWORDS: 이 키워드가 발견되면 해당 본은 후보에서 즉시 제외됩니다.
# 신체의 다른 부위와 혼동되는 것을 막기 위함입니다.
VETO_KEYWORDS = {
    'hips': ['arm', 'leg', 'hand', 'foot', 'head', 'finger', 'toe', 'shoulder', 'clavicle', 'neck', 'chest', 'spine'],
    'spine': ['arm', 'leg', 'hand', 'foot', 'head', 'finger', 'toe', 'shoulder', 'clavicle', 'hip'],
    'chest': ['arm', 'leg', 'hand', 'foot', 'head', 'finger', 'toe', 'shoulder', 'clavicle', 'hip', 'neck'],
    'neck': ['arm', 'leg', 'hand', 'foot', 'finger', 'toe', 'shoulder', 'clavicle', 'hip', 'spine', 'chest'],
    'head': ['arm', 'leg', 'hand', 'foot', 'finger', 'toe', 'shoulder', 'clavicle', 'hip', 'spine', 'chest', 'neck', 'torso'],
    'leftUpperArm': ['leg', 'foot', 'toe', 'head', 'right', '_r', 'r.'],
    'leftLowerArm': ['leg', 'foot', 'toe', 'head', 'right', '_r', 'r.'],
    'leftHand': ['leg', 'foot', 'toe', 'head', 'right', '_r', 'r.'],
    'leftUpperLeg': ['arm', 'hand', 'finger', 'head', 'right', '_r', 'r.'],
    'leftLowerLeg': ['arm', 'hand', 'finger', 'head', 'right', '_r', 'r.'],
    'leftFoot': ['arm', 'hand', 'finger', 'head', 'right', '_r', 'r.'],
}

def _generate_finger_keywords():
    """Programmatically generate keywords for all finger bones."""
    keywords = {}
    neg_keywords = {}
    sides = [('left', 'l'), ('right', 'r')]
    finger_types = [
        ('thumb', ['thumb']),
        ('index', ['index', 'point']),
        ('middle', ['middle', 'mid']),
        ('ring', ['ring']),
        ('pinky', ['pinky', 'little', 'small'])
    ]
    all_finger_names = [f[0] for f in finger_types]

    for side_prefix, side_short in sides:
        for finger_name, finger_keys in finger_types:
            num_joints = 2 if finger_name == 'thumb' else 3
            for i in range(1, num_joints + 1):
                prop_name = f'{side_prefix}{finger_name.capitalize()}{i:02d}'
                
                # Positive keywords
                pos = finger_keys + [side_prefix, side_short, str(i), f'{i:02d}']
                keywords[prop_name] = pos
                
                # Negative keywords
                neg = [name for name in all_finger_names if name != finger_name]
                neg += [str(j) for j in range(1, 5) if j != i]
                neg += ['arm', 'leg', 'foot', 'toe', 'palm']
                neg_keywords[prop_name] = neg
    return keywords, neg_keywords

# Generate and update the main keyword dictionaries
FINGER_KEYWORDS, NEGATIVE_FINGER_KEYWORDS = _generate_finger_keywords()
BONE_KEYWORDS.update(FINGER_KEYWORDS)
NEGATIVE_KEYWORDS.update(NEGATIVE_FINGER_KEYWORDS)
# VETO_KEYWORDS의 right/left 부분을 동적으로 생성하여 확장
for prop_name in list(VETO_KEYWORDS.keys()):
    if 'right' in prop_name:
        new_key = prop_name.replace('right', 'left')
        new_val = [v.replace('right', 'left').replace('_r', '_l').replace('r.', 'l.') for v in VETO_KEYWORDS[prop_name]]
        VETO_KEYWORDS[new_key] = new_val
    if 'left' in prop_name:
        new_key = prop_name.replace('left', 'right')
        new_val = [v.replace('left', 'right').replace('_l', '_r').replace('l.', 'r.') for v in VETO_KEYWORDS[prop_name]]
        VETO_KEYWORDS[new_key] = new_val

# 점수 상수: 가독성 및 튜닝 편의성
SCORE_EXACT_MATCH = 20
SCORE_HIERARCHY_BONUS = 10
SCORE_KEYWORD_WORD = 5
SCORE_SIDE_MATCH = 5
SCORE_KEYWORD_SUBSTRING = 1
PENALTY_NEGATIVE_KEYWORD = -10
MINIMUM_SCORE_THRESHOLD = 6 # 매칭을 위한 최소 점수

# --- Standard Bone Hierarchy ---
# Defines the expected parent for each bone in the standard rig. 
# Used to give a score bonus during auto-mapping if the hierarchy matches.
STANDARD_BONE_HIERARCHY = {
    # Body
    'spine': 'hips', 'chest': 'spine', 'neck': 'chest', 'head': 'neck',
    # Left Arm
    'leftUpperArm': 'chest', 'leftLowerArm': 'leftUpperArm', 'leftHand': 'leftLowerArm',
    # Right Arm
    'rightUpperArm': 'chest', 'rightLowerArm': 'rightUpperArm', 'rightHand': 'rightLowerArm',
    # Left Leg
    'leftUpperLeg': 'hips', 'leftLowerLeg': 'leftUpperLeg', 'leftFoot': 'leftLowerLeg', 'leftToe': 'leftFoot',
    # Right Leg
    'rightUpperLeg': 'hips', 'rightLowerLeg': 'rightUpperLeg', 'rightFoot': 'rightLowerLeg', 'rightToe': 'rightFoot',
}

def _generate_finger_hierarchy():
    """Programmatically generate the hierarchy for finger bones."""
    hierarchy = {}
    sides = ['left', 'right']
    finger_types = [
        ('thumb', 2), ('index', 3), ('middle', 3), ('ring', 3), ('pinky', 3)
    ]
    for side in sides:
        for finger_name, num_joints in finger_types:
            # First joint connects to the hand
            hierarchy[f'{side}{finger_name.capitalize()}01'] = f'{side}Hand'
            # Subsequent joints connect to the previous one
            for i in range(2, num_joints + 1):
                parent_prop = f'{side}{finger_name.capitalize()}{i-1:02d}'
                child_prop = f'{side}{finger_name.capitalize()}{i:02d}'
                hierarchy[child_prop] = parent_prop
    return hierarchy

# Update the main hierarchy dictionary with finger data
STANDARD_BONE_HIERARCHY.update(_generate_finger_hierarchy())

def get_topological_sorted_bones():
    """
    STANDARD_BONE_HIERARCHY를 기반으로 본 목록을 위상 정렬합니다.
    이를 통해 부모 본이 항상 자식 본보다 먼저 처리되도록 보장합니다.
    """
    all_props_map = {p: d for p, d in STANDARD_BONE_NAMES}
    all_props_set = set(all_props_map.keys())
    
    graph = {prop_name: [] for prop_name in all_props_set}
    in_degree = {prop_name: 0 for prop_name in all_props_set}

    for child, parent in STANDARD_BONE_HIERARCHY.items():
        if parent in all_props_set and child in all_props_set:
            if child not in graph[parent]:
                graph[parent].append(child)
                in_degree[child] += 1

    queue = deque([prop for prop, degree in in_degree.items() if degree == 0])
    sorted_order = []
    while queue:
        parent_prop = queue.popleft()
        sorted_order.append(parent_prop)
        
        for child_prop in graph.get(parent_prop, []):
            in_degree[child_prop] -= 1
            if in_degree[child_prop] == 0:
                queue.append(child_prop)

    # 정렬 결과에 포함되지 않은 나머지 노드들을 추가 (계층 구조에 없거나 독립적인 본)
    sorted_props_set = set(sorted_order)
    remaining = sorted(list(all_props_set - sorted_props_set))
    
    final_sorted_list = [(prop, all_props_map[prop]) for prop in sorted_order]
    final_sorted_list.extend([(prop, all_props_map[prop]) for prop in remaining])

    return final_sorted_list

def _calculate_match_score(prop_name, bone, bone_mapping):
    """특정 본과 속성 간의 매칭 점수를 계산합니다."""
    score = 0
    bone_name_norm = bone.name.lower().replace('_', ' ').replace('.', ' ').replace('-', ' ')
    bone_name_words = set(bone_name_norm.split())

    # 1. Veto 키워드 확인 (즉시 탈락)
    for keyword in VETO_KEYWORDS.get(prop_name, []):
        if keyword in bone_name_norm:
            return -1

    # 2. 정확한 이름 일치 보너스
    if prop_name.lower() in bone_name_words:
        score += SCORE_EXACT_MATCH

    # 3. 긍정 키워드 점수
    for keyword in BONE_KEYWORDS.get(prop_name, []):
        if keyword in bone_name_words:
            score += SCORE_KEYWORD_WORD
        elif keyword in bone_name_norm:
            score += SCORE_KEYWORD_SUBSTRING

    # 4. 부정 키워드 페널티
    for keyword in NEGATIVE_KEYWORDS.get(prop_name, []):
        if keyword in bone_name_norm:
            score += PENALTY_NEGATIVE_KEYWORD

    # 5. 좌/우 구분 점수
    target_has_left = 'left' in prop_name.lower()
    target_has_right = 'right' in prop_name.lower()
    bone_has_left = any(p in bone.name.lower() for p in ['_l', '.l', ' l', 'left'])
    bone_has_right = any(p in bone.name.lower() for p in ['_r', '.r', ' r', 'right'])

    if (target_has_left and bone_has_right) or (target_has_right and bone_has_left):
        return -1 # 명확한 좌우 불일치는 즉시 탈락
    elif (target_has_left and bone_has_left) or (target_has_right and bone_has_right):
        score += SCORE_SIDE_MATCH

    # 6. 계층 구조 보너스 (부모가 이미 매핑된 경우)
    expected_parent_prop = STANDARD_BONE_HIERARCHY.get(prop_name)
    if expected_parent_prop and bone.parent:
        mapped_parent_name = getattr(bone_mapping, expected_parent_prop, None)
        if mapped_parent_name and bone.parent.name == mapped_parent_name:
            score += SCORE_HIERARCHY_BONUS

    return score

def auto_bone_map(source_armature, bone_mapping):
    """Source 아마추어의 본 이름을 분석하여 휴리스틱하게 본 매핑을 수행합니다."""
    if not source_armature or source_armature.type != 'ARMATURE':
        return

    source_bones = source_armature.data.bones
    mapped_source_bones = {getattr(bone_mapping, p) for p, _ in STANDARD_BONE_NAMES if getattr(bone_mapping, p)}
    
    sorted_bone_props = get_topological_sorted_bones()

    for prop_name, _ in sorted_bone_props:
        if getattr(bone_mapping, prop_name): continue

        best_match, best_score = "", 0
        for bone in source_bones:
            if bone.name in mapped_source_bones: continue
            score = _calculate_match_score(prop_name, bone, bone_mapping)
            if score > best_score:
                best_score, best_match = score, bone.name
        
        if best_match and best_score >= MINIMUM_SCORE_THRESHOLD:
            setattr(bone_mapping, prop_name, best_match)
            mapped_source_bones.add(best_match)

def duplicate_and_isolate(source_armature):
    """
    Source 아마추어와 그에 종속된 메쉬들을 복제하고 원본은 숨깁니다.
    이 작업은 비파괴적으로 이루어지며, Material을 포함한 모든 데이터를 보존합니다.
    """
    if not source_armature:
        return None, []

    # 1. 아마추어에 의해 변형되는 모든 메쉬 오브젝트를 찾습니다.
    meshes_to_duplicate = [
        obj for obj in bpy.data.objects
        if obj.type == 'MESH' and any(
            mod.type == 'ARMATURE' and mod.object == source_armature
            for mod in obj.modifiers
        )
    ]

    # --- 2. 아마추어 복제 (API 사용) ---
    # .copy()는 오브젝트의 데이터(armature, modifiers 등)에 대한 참조를 복사합니다.
    new_armature = source_armature.copy()
    # .data.copy()는 실제 아마추어 데이터(본, 계층 구조 등)를 복제합니다.
    new_armature.data = source_armature.data.copy()
    new_armature.name = source_armature.name + "_Patched"
    # 복제된 오브젝트를 씬에 연결합니다.
    bpy.context.collection.objects.link(new_armature)

    # --- 3. 메쉬 복제 (API 사용) ---
    new_meshes = []
    for mesh_obj in meshes_to_duplicate:
        # 오브젝트와 메쉬 데이터를 각각 복제합니다.
        new_mesh = mesh_obj.copy()
        new_mesh.data = mesh_obj.data.copy()
        new_mesh.name = mesh_obj.name + "_Patched"

        # .copy()는 material_slots를 보존하므로 Material이 유지됩니다.

        # 복제된 메쉬를 씬에 연결합니다.
        bpy.context.collection.objects.link(new_mesh)

        # 아마추어 수정자의 대상을 새 아마추어로 변경합니다.
        for mod in new_mesh.modifiers:
            if mod.type == 'ARMATURE' and mod.object == source_armature:
                mod.object = new_armature
        new_meshes.append(new_mesh)

    # 4. 원본 오브젝트들을 숨깁니다.
    originals_to_hide = [source_armature] + meshes_to_duplicate
    for obj in originals_to_hide:
        obj.hide_set(True)
        
    return new_armature, new_meshes

def find_mapped_parent(armature_data, bone_name, mapped_bone_names):
    """지정된 본에서부터 계층 구조를 따라 올라가면서, 매핑된 첫 번째 부모 본의 이름을 찾습니다."""
    bone = armature_data.bones.get(bone_name)
    if not bone:
        return None

    parent = bone.parent
    while parent:
        if parent.name in mapped_bone_names:
            return parent.name
        parent = parent.parent
    return None

def merge_unmapped_weights(armature_obj, mesh_objs, bone_mapping):
    """
    Implements Guideline.md Phase 3:
    Identifies unmapped bones, merges their weights to the closest mapped parent
    by iterating vertices, and removes the now-unnecessary bones and vertex groups.
    """
    armature_data = armature_obj.data
    all_bone_names = {b.name for b in armature_data.bones}

    # Get a set of all mapped source bone names
    mapped_source_bones = {
        getattr(bone_mapping, prop_name)
        for prop_name, _ in STANDARD_BONE_NAMES
        if getattr(bone_mapping, prop_name, None)
    }

    unmapped_bone_names = all_bone_names - mapped_source_bones
    if not unmapped_bone_names:
        print("  - No unmapped bones to merge.")
        return

    print(f"Found {len(unmapped_bone_names)} unmapped bones. Planning weight merge...")

    # Plan which unmapped bones to merge into which parent
    # merge_plan: bones to merge to a parent
    # bones_to_discard: orphan bones whose vertex groups will just be deleted
    merge_plan = {}
    bones_to_discard = set()

    # This prevents weight loss for orphan chains, as per TODO2.md's warning.
    root_bone_name = getattr(bone_mapping, 'hips', None)

    for unmapped_bone in unmapped_bone_names:
        parent_target = find_mapped_parent(armature_data, unmapped_bone, mapped_source_bones)
        if parent_target:
            merge_plan[unmapped_bone] = parent_target
        elif root_bone_name:
            # Fallback for orphan bones/chains: merge to the main root bone
            print(f"  - Info: No mapped parent for '{unmapped_bone}'. Merging to root '{root_bone_name}'.")
            merge_plan[unmapped_bone] = root_bone_name
        else:
            # If even the root isn't mapped, we have to discard the weights.
            print(f"  - Warning: No mapped parent or root for '{unmapped_bone}'. Its weights will be discarded.")
            bones_to_discard.add(unmapped_bone)

    if not merge_plan and not bones_to_discard:
        print("  - No unmapped bones to process.")
        return

    # Store original context to restore it safely
    original_active = bpy.context.view_layer.objects.active
    original_mode = 'OBJECT'
    if original_active and original_active.mode:
        original_mode = original_active.mode

    try:
        # This list contains all bone names that will be removed from the armature.
        bones_to_process_names = list(merge_plan.keys()) + list(bones_to_discard)

        # Execute the merge plan for each mesh
        for mesh_obj in mesh_objs:
            bpy.context.view_layer.objects.active = mesh_obj
            if bpy.context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            print(f"  - Reconstructing weights for mesh '{mesh_obj.name}'...")

            vgs = mesh_obj.vertex_groups
            mesh_data = mesh_obj.data

            # Create a map from unmapped group index to the target group object for fast lookup
            merge_index_map = {}
            for unmapped_name, target_name in merge_plan.items():
                unmapped_vg = vgs.get(unmapped_name)
                target_vg = vgs.get(target_name)
                if unmapped_vg and target_vg:
                    merge_index_map[unmapped_vg.index] = target_vg

            if merge_index_map:
                # Iterate through all vertices ONCE to transfer weights
                # This is much more performant than using modifiers in a loop.
                for v in mesh_data.vertices:
                    # --- Safe Weight Transfer Pattern ---
                    # Step 1: Read all weights that need to be transferred for this vertex.
                    # We collect them first to avoid modifying the v.groups collection while iterating over it,
                    # which can cause errors or crashes.
                    transfers_for_this_vertex = []
                    for g in v.groups:
                        if g.group in merge_index_map:
                            transfers_for_this_vertex.append((merge_index_map[g.group], g.weight))

                    # Step 2: Now, safely apply the collected weights to their new target groups.
                    for target_vg, weight in transfers_for_this_vertex:
                        target_vg.add([v.index], weight, 'ADD')

                print(f"    - Merged weights from {len(merge_index_map)} groups.")

            # Remove the now-redundant vertex groups
            groups_to_remove_names = bones_to_process_names
            removed_count = 0
            for vg_name in groups_to_remove_names:
                vg_to_remove = vgs.get(vg_name)
                if vg_to_remove:
                    vgs.remove(vg_to_remove)
                    removed_count += 1

            if removed_count > 0:
                print(f"    - Removed {removed_count} old vertex groups.")

        # Finally, remove the unmapped bones from the armature itself
        bpy.context.view_layer.objects.active = armature_obj
        bpy.ops.object.mode_set(mode='EDIT')

        for bone_name in bones_to_process_names:
            edit_bone = armature_obj.data.edit_bones.get(bone_name)
            if edit_bone:
                armature_obj.data.edit_bones.remove(edit_bone)

        bpy.ops.object.mode_set(mode='OBJECT')
        print(f"  - Cleaned up {len(bones_to_process_names)} unmapped bones from armature.")

    finally:
        # Safely restore original context
        if original_active and original_active.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = original_active
            if bpy.context.active_object and bpy.context.active_object.mode != original_mode:
                 bpy.ops.object.mode_set(mode=original_mode)
        elif not bpy.context.view_layer.objects.active and armature_obj and armature_obj.name in bpy.data.objects:
            bpy.context.view_layer.objects.active = armature_obj
            bpy.ops.object.mode_set(mode='OBJECT')