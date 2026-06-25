import bpy
from ..properties import STANDARD_BONE_NAMES

def rename_vertex_groups(mesh_obj, target_mapping, source_mapping):
    """
    Renames the vertex groups of the patched mesh to match the target bone names
    according to the bone mapping. This is part of Guideline.md Phase 3.
    Note: Unmapped groups are assumed to be already merged/removed by mapping.py.
    """
    if not mesh_obj or mesh_obj.type != 'MESH':
        return

    print(f"    - Renaming vertex groups for mesh '{mesh_obj.name}'...")
    
    # { 'source_bone_name': 'target_bone_name' } 형태의 딕셔너리 생성
    rename_map = {
        getattr(source_mapping, prop): getattr(target_mapping, prop)
        for prop, _ in STANDARD_BONE_NAMES
        if getattr(source_mapping, prop) and getattr(target_mapping, prop)
    }

    renamed_count = 0
    
    # Iterate through vertex groups and rename them if they are in the map.
    for vg in mesh_obj.vertex_groups:
        if vg.name in rename_map:
            new_name = rename_map[vg.name]
            if vg.name != new_name:
                vg.name = new_name
                renamed_count += 1
    
    print(f"    - Renaming complete. {renamed_count} groups renamed.")


def switch_armature_dependency(mesh_obj, target_armature):
    """
    Patched 메쉬의 제어권을 Target 아마추어로 이관합니다. (TODO2.md - Phase 4)
    """
    if not mesh_obj or mesh_obj.type != 'MESH' or not target_armature:
        return

    print(f"  - Switching armature dependency for '{mesh_obj.name}' to '{target_armature.name}'...")

    # Remove any existing armature modifiers to ensure a clean slate.
    for mod in list(mesh_obj.modifiers):
        if mod.type == 'ARMATURE':
            mesh_obj.modifiers.remove(mod)

    # Add a new armature modifier pointing to the final target armature.
    new_mod = mesh_obj.modifiers.new(name="Retargeted Armature", type='ARMATURE')
    new_mod.object = target_armature


def cleanup_patched_armature(armature_obj):
    """
    역할을 다한 Patched 아마추어와 관련 데이터를 정리합니다. (TODO2.md - Phase 4)
    """
    if not armature_obj:
        return

    print(f"  - Cleaning up temporary armature '{armature_obj.name}'...")
    armature_data = armature_obj.data
    
    # Store the name before removing, as accessing removed data can cause errors.
    armature_data_name = armature_data.name
    
    # Remove the object from the scene.
    bpy.data.objects.remove(armature_obj, do_unlink=True)
    
    # If the armature data block has no other users, remove it as well.
    if armature_data and armature_data.users == 0:
        bpy.data.armatures.remove(armature_data, do_unlink=True)
        print(f"    - Removed data block '{armature_data_name}'.")