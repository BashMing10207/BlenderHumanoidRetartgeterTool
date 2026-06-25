import bpy
from .core import mapping, normalization, alignment, finalization

class RETARGET_OT_AutoMap(bpy.types.Operator):
    """이름 기반 휴리스틱을 사용하여 본을 자동으로 매핑합니다."""
    bl_idname = "retargeter.auto_map"
    bl_label = "Auto-Map Bones"
    bl_options = {'REGISTER', 'UNDO'}

    map_type: bpy.props.EnumProperty(
        items=[
            ('TARGET', "Target", "Target 아마추어를 매핑합니다."),
            ('SOURCE', "Source", "Source 아마추어를 매핑합니다."),
        ]
    )

    def execute(self, context):
        props = context.scene.retargeter_props
        
        if self.map_type == 'TARGET':
            armature = props.target_armature
            bone_map = props.target_bone_mapping
            if not armature:
                self.report({'WARNING'}, "Target Armature가 설정되지 않았습니다.")
                return {'CANCELLED'}
        else: # SOURCE
            armature = props.source_armature
            bone_map = props.source_bone_mapping
            if not armature:
                self.report({'WARNING'}, "Source Armature가 설정되지 않았습니다.")
                return {'CANCELLED'}

        if not bone_map:
            self.report({'ERROR'}, "본 매핑 속성이 초기화되지 않았습니다.")
            return {'CANCELLED'}

        mapping.auto_bone_map(armature, bone_map)
        self.report({'INFO'}, f"{self.map_type.lower()} 아마추어 자동 매핑 완료.")
        return {'FINISHED'}

class RETARGET_OT_Execute(bpy.types.Operator):
    """전체 리타겟팅 프로세스를 실행합니다."""
    bl_idname = "retargeter.execute"
    bl_label = "Execute Retargeting"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.retargeter_props

        # --- 1. 유효성 검사 ---
        if not props.target_armature or not props.source_armature:
            self.report({'ERROR'}, "Target과 Source 아마추어를 모두 지정해야 합니다.")
            return {'CANCELLED'}
        
        if not props.source_bone_mapping.hips or not props.target_bone_mapping.hips:
            self.report({'ERROR'}, "본 매핑이 완료되지 않았습니다. Auto-Map을 먼저 실행하거나 수동으로 Hips 본을 지정하세요.")
            return {'CANCELLED'}

        self.report({'INFO'}, "리타겟팅 파이프라인 시작...")

        target_arm = props.target_armature
        source_arm = props.source_armature
        target_map = props.target_bone_mapping
        source_map = props.source_bone_mapping

        # --- Phase 2: 격리, 매핑, 병합 ---
        self.report({'INFO'}, "[Phase 2] 원본 격리 및 복제 중...")
        patched_arm, patched_meshes = mapping.duplicate_and_isolate(source_arm)
        if not patched_arm:
            self.report({'ERROR'}, "모델 복제에 실패했습니다.")
            return {'CANCELLED'}

        self.report({'INFO'}, "[Phase 2] 매핑되지 않은 가중치 병합 중...")
        mapping.merge_unmapped_weights(patched_arm, patched_meshes, source_map)

        if props.use_scale_normalization:
            # --- Phase 3: 스케일 정규화 ---
            self.report({'INFO'}, "[Phase 3] 스케일 정규화 중...")
            scale_factor = normalization.calculate_scale_factor(target_arm, patched_arm, target_map, source_map)
            
            patched_arm.scale = (scale_factor, scale_factor, scale_factor)
            for mesh in patched_meshes:
                mesh.scale = (scale_factor, scale_factor, scale_factor)
            
            # 컨텍스트 오류를 방지하기 위해 bpy.ops.object.select_all 대신 직접 API를 사용합니다.
            for obj in context.view_layer.objects:
                obj.select_set(False)

            patched_arm.select_set(True)
            for mesh in patched_meshes: mesh.select_set(True)
            context.view_layer.objects.active = patched_arm
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

        if props.use_pose_alignment:
            # --- Phase 4: 포즈 정렬 ---
            self.report({'INFO'}, "[Phase 4] 포즈 정렬 중...")
            alignment.align_pose_to_target(target_arm, patched_arm, target_map, source_map)

            self.report({'INFO'}, "[Phase 4] 정렬된 포즈를 메쉬에 적용 중...")
            for mesh in patched_meshes:
                context.view_layer.objects.active = mesh
                armature_mod = next((mod for mod in mesh.modifiers if mod.type == 'ARMATURE'), None)
                if armature_mod:
                    bpy.ops.object.modifier_apply(modifier=armature_mod.name)
        
        # --- Phase 5: 최종화 ---
        self.report({'INFO'}, "[Phase 5] 최종화 작업 중...")
        for mesh in patched_meshes:
            finalization.rename_vertex_groups(mesh, target_map, source_map)
            finalization.switch_armature_dependency(mesh, target_arm)
        
        finalization.cleanup_patched_armature(patched_arm)

        # 원본 오브젝트 선택 해제 및 숨김 처리
        source_arm.select_set(False)

        self.report({'INFO'}, "리타겟팅 완료!")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(RETARGET_OT_AutoMap)
    bpy.utils.register_class(RETARGET_OT_Execute)

def unregister():
    bpy.utils.unregister_class(RETARGET_OT_Execute)
    bpy.utils.unregister_class(RETARGET_OT_AutoMap)