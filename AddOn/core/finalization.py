import bpy
from ..properties import STANDARD_BONE_NAMES

def rename_vertex_groups(mesh_obj, target_mapping, source_mapping):
    """
    Patched 메쉬의 Vertex Group 이름을 본 매핑 정보에 따라
    Target 아마추어의 본 이름으로 일괄 변경합니다.
    """
    if not mesh_obj or mesh_obj.type != 'MESH':
        return

    print("Vertex Group 이름 변경 시작...")
    
    # { 'source_bone_name': 'target_bone_name' } 형태의 딕셔너리 생성
    rename_map = {}
    for prop_name, _ in STANDARD_BONE_NAMES:
        source_bone_name = getattr(source_mapping, prop_name, None)
        target_bone_name = getattr(target_mapping, prop_name, None)
        if source_bone_name and target_bone_name:
            rename_map[source_bone_name] = target_bone_name

    # Vertex Group 순회 및 이름 변경
    for vg in mesh_obj.vertex_groups:
        if vg.name in rename_map:
            new_name = rename_map[vg.name]
            print(f"  '{vg.name}' -> '{new_name}'")
            vg.name = new_name
    
    print("Vertex Group 이름 변경 완료.")


def switch_armature_dependency(mesh_obj, target_armature):
    """
    Patched 메쉬의 기존 아마추어 수정자를 제거하고,
    Target 아마추어를 가리키는 새 수정자를 추가합니다.
    """
    if not mesh_obj or mesh_obj.type != 'MESH' or not target_armature:
        return

    print("아마추어 종속성 교체 시작...")

    # 기존의 모든 아마추어 수정자 제거 (리스트를 복사해서 순회)
    for mod in list(mesh_obj.modifiers):
        if mod.type == 'ARMATURE':
            print(f"  제거된 수정자: '{mod.name}' (대상: {mod.object.name if mod.object else 'None'})")
            mesh_obj.modifiers.remove(mod)

    # Target 아마추어를 가리키는 새 수정자 추가
    new_mod = mesh_obj.modifiers.new(name="Retargeted Armature", type='ARMATURE')
    new_mod.object = target_armature
    print(f"  새 수정자 추가: '{new_mod.name}' (대상: {target_armature.name})")
    
    print("아마추어 종속성 교체 완료.")

def cleanup_patched_armature(armature_obj):
    """
    역할을 다한 Patched 아마추어 오브젝트와 데이터 블록을 제거하고,
    참조되지 않는 데이터를 정리합니다.
    """
    if not armature_obj:
        return

    print(f"'{armature_obj.name}' 아마추어 정리 시작...")
    armature_data = armature_obj.data
    # 데이터 블록이 제거되기 전에 이름을 변수에 저장합니다.
    # 제거된 데이터에 접근하면 ReferenceError가 발생하기 때문입니다.
    armature_data_name = armature_data.name
    
    # 오브젝트 제거
    bpy.data.objects.remove(armature_obj, do_unlink=True)
    
    # 데이터 블록이 다른 사용자(오브젝트)를 가지고 있지 않은 경우에만 제거
    if armature_data and armature_data.users == 0:
        bpy.data.armatures.remove(armature_data, do_unlink=True)
        print(f"  '{armature_data_name}' 데이터 블록 제거 완료.")
    
    # 고아 데이터 정리 (메모리 누수 방지)
    bpy.ops.outliner.orphans_purge()
    print("고아 데이터 정리 완료.")