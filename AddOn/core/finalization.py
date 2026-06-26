import bpy
from ..properties import STANDARD_BONE_NAMES

def _rename_vertex_groups(mesh_obj, target_mapping, source_mapping):
    """
    Helper function to rename vertex groups of a mesh based on the bone mapping.
    (Internal use for run_finalization_phase)
    """
    if not mesh_obj or mesh_obj.type != 'MESH':
        return

    print(f"    - Renaming vertex groups for '{mesh_obj.name}'...")
    
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
            # Check if the new name already exists (unlikely edge case, but safe)
            new_name = rename_map[vg.name]
            if vg.name != new_name and not mesh_obj.vertex_groups.get(new_name):
                vg.name = new_name
                renamed_count += 1
    
    if renamed_count > 0:
        print(f"      - Renamed {renamed_count} groups.")


def _switch_armature_dependency(mesh_obj, target_armature):
    """
    Helper function to switch the mesh's armature modifier to the target armature.
    (Internal use for run_finalization_phase)
    """
    if not mesh_obj or mesh_obj.type != 'MESH' or not target_armature:
        return

    # Remove any existing armature modifiers to ensure a clean slate.
    for mod in list(mesh_obj.modifiers):
        if mod.type == 'ARMATURE':
            mesh_obj.modifiers.remove(mod)

    # Add a new armature modifier pointing to the final target armature.
    new_mod = mesh_obj.modifiers.new(name="Retargeted Armature", type='ARMATURE')
    new_mod.object = target_armature
    print(f"    - Switched armature dependency for '{mesh_obj.name}' to '{target_armature.name}'.")


def _cleanup_patched_armature(armature_obj):
    """
    Helper function to safely remove the temporary patched armature and its data block.
    (Internal use for run_finalization_phase)
    """
    if not armature_obj:
        return
    armature_data = armature_obj.data
    
    # Store the name before removing, as accessing removed data can cause errors.
    armature_data_name = armature_data.name
    
    # Remove the object from the scene.
    bpy.data.objects.remove(armature_obj, do_unlink=True)
    
    # If the armature data block has no other users, remove it as well.
    if armature_data and armature_data.users == 0:
        bpy.data.armatures.remove(armature_data, do_unlink=True)
        print(f"  - Removed data block: '{armature_data_name}'.")


def run_finalization_phase(context, patched_meshes, patched_armature, target_armature, target_map, source_map):
    """
    Implements NEWPLAN.md Phase 4: Target Rebind.
    - Renames vertex groups to match the target armature.
    - Normalizes all weights.
    - Switches the armature modifier to the target armature.
    - Cleans up the temporary patched armature.
    """
    print("Finalization Phase 시작...")

    original_active = context.view_layer.objects.active
    original_mode = 'OBJECT'
    if original_active and original_active.mode:
        original_mode = original_active.mode

    try:
        for mesh_obj in patched_meshes:
            context.view_layer.objects.active = mesh_obj
            if context.object.mode != 'OBJECT':
                bpy.ops.object.mode_set(mode='OBJECT')

            # 1. Rename vertex groups to match target bone names
            _rename_vertex_groups(mesh_obj, target_map, source_map)

            # 2. Normalize all weights (as per NEWPLAN.md spec)
            print(f"    - Normalizing all weights for '{mesh_obj.name}'...")
            bpy.ops.object.vertex_group_normalize_all(lock_active=False)

            # 3. Switch armature dependency to the final target
            _switch_armature_dependency(mesh_obj, target_armature)

        # 4. Clean up the now-unnecessary patched armature
        print(f"  - Cleaning up temporary armature '{patched_armature.name}'...")
        _cleanup_patched_armature(patched_armature)

        print("Finalization Phase 완료.")

    finally:
        # Restore original context
        if original_active and original_active.name in bpy.data.objects:
            context.view_layer.objects.active = original_active
            if context.active_object and context.active_object.mode != original_mode:
                 bpy.ops.object.mode_set(mode=original_mode)