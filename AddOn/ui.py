import bpy
from .properties import STANDARD_BONE_NAMES

class OBJECT_PT_RetargeterPanel(bpy.types.Panel):
    bl_label = "Humanoid Retargeter"
    bl_idname = "OBJECT_PT_retargeter_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Retargeter' # N-Panel에 표시될 탭 이름

    def draw(self, context):
        layout = self.layout
        props = context.scene.retargeter_props
        
        # 1. 아마추어 선택 UI
        box = layout.box()
        box.label(text="Armatures", icon='ARMATURE_DATA')
        box.prop(props, "target_armature", text="Target (A)")
        box.prop(props, "source_armature", text="Source (B)")
        
        # 2. 실행 버튼 UI
        layout.separator()
        op_box = layout.box()
        op_box.label(text="Actions", icon='MODIFIER')
        
        row = op_box.row(align=True)
        # 자동 매핑 버튼
        op_target = row.operator("retargeter.auto_map", text="Auto-Map Target")
        op_target.map_type = 'TARGET'
        
        op_source = row.operator("retargeter.auto_map", text="Auto-Map Source")
        op_source.map_type = 'SOURCE'
        
        # 전체 프로세스 실행 버튼
        op_box.operator("retargeter.execute", text="Execute Retargeting", icon='PLAY')
        
        # 3. 옵션 UI
        layout.separator()
        option_box = layout.box()
        option_box.label(text="Options", icon='SETTINGS')
        option_box.prop(props, "use_scale_normalization")
        option_box.prop(props, "use_pose_alignment")
        
        # 3. 본 매핑 목록 UI
        layout.separator()
        map_box = layout.box()
        
        # 헤더
        header = map_box.row()
        header.label(text="Standard Bone")
        header.label(text="Target (A)")
        header.label(text="Source (B)")
        
        target_map = props.target_bone_mapping
        source_map = props.source_bone_mapping
        
        # PropertyGroup이 Blender에 의해 정상적으로 생성되었는지 확인합니다.
        # 만약 이들이 없다면, 등록 과정에 문제가 있는 것이므로 에러를 표시합니다.
        if not target_map or not source_map:
            map_box.label(text="Error: Mapping properties failed to load.", icon='ERROR')
            return

        # 스크롤 가능한 영역
        scroll_box = map_box.box()
        
        # 표준 본 목록을 순회하며, 각 본에 대한 할당 UI를 생성합니다.
        for prop_name, display_name in STANDARD_BONE_NAMES:
            row = scroll_box.row(align=True)
            row.label(text=display_name)
            
            # --- Target 본 할당 UI ---
            # Target UI를 담을 컬럼을 생성하고, 아마추어 선택 여부에 따라 활성화 상태를 제어합니다.
            target_col = row.column()
            target_col.enabled = props.target_armature is not None
            if props.target_armature:
                # 아마추어가 선택된 경우: 본 목록을 검색할 수 있는 UI를 표시합니다.
                target_col.prop_search(target_map, prop_name, props.target_armature.data, "bones", text="")
            else:
                # 아마추어가 없는 경우: 비활성화된 텍스트 박스를 표시합니다.
                target_col.prop(target_map, prop_name, text="")

            # --- Source 본 할당 UI ---
            source_col = row.column()
            source_col.enabled = props.source_armature is not None
            if props.source_armature:
                source_col.prop_search(source_map, prop_name, props.source_armature.data, "bones", text="")
            else:
                source_col.prop(source_map, prop_name, text="")

def register():
    bpy.utils.register_class(OBJECT_PT_RetargeterPanel)

def unregister():
    bpy.utils.unregister_class(OBJECT_PT_RetargeterPanel)