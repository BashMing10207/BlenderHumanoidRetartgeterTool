import bpy

# 이 리스트는 UI 표시 순서와 이름을 정의하며, 다른 모듈(ui, mapping 등)에서 가져와 사용합니다.
STANDARD_BONE_NAMES = [
    # Main Body
    ("hips", "Hips"),
    ("spine", "Spine"),
    ("chest", "Chest"),
    ("neck", "Neck"),
    ("head", "Head"),
    # Left Arm
    ("leftUpperArm", "Upper Arm (L)"),
    ("leftLowerArm", "Lower Arm (L)"),
    ("leftHand", "Hand (L)"),
    # Right Arm
    ("rightUpperArm", "Upper Arm (R)"),
    ("rightLowerArm", "Lower Arm (R)"),
    ("rightHand", "Hand (R)"),
    # Left Leg
    ("leftUpperLeg", "Upper Leg (L)"),
    ("leftLowerLeg", "Lower Leg (L)"),
    ("leftFoot", "Foot (L)"),
    ("leftToe", "Toe (L)"),
    # Right Leg
    ("rightUpperLeg", "Upper Leg (R)"),
    ("rightLowerLeg", "Lower Leg (R)"),
    ("rightFoot", "Foot (R)"),
    ("rightToe", "Toe (R)"),
]

# 동적으로 손가락 본 리스트를 생성하여 추가합니다.
def _add_finger_bones():
    finger_list = []
    sides = [('left', '(L)'), ('right', '(R)')]
    finger_types = ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']
    for side_prefix, side_suffix in sides:
        for finger_type in finger_types:
            num_joints = 2 if finger_type == 'Thumb' else 3
            for i in range(1, num_joints + 1):
                prop_name = f'{side_prefix}{finger_type}{i:02d}'
                display_name = f'{finger_type} {i} {side_suffix}'
                finger_list.append((prop_name, display_name))
    return finger_list

STANDARD_BONE_NAMES.extend(_add_finger_bones())


class HumanoidBoneMapping(bpy.types.PropertyGroup):
    """표준 본 이름과 실제 아마추어의 본 이름을 매핑하여 저장합니다."""
    # register 함수에서 동적으로 속성을 추가합니다.
    pass


# PointerProperty에서 아마추어 타입의 오브젝트만 선택할 수 있도록 제한하는 함수입니다.
def poll_armature(self, object):
    return object.type == 'ARMATURE'

class RetargeterProperties(bpy.types.PropertyGroup):
    """애드온의 메인 데이터 그룹. 씬(Scene)에 저장됩니다."""
    
    target_armature: bpy.props.PointerProperty(
        name="Target Armature",
        description="표준이 될 타겟 리그 (A)",
        type=bpy.types.Object,
        poll=poll_armature
    )
    
    source_armature: bpy.props.PointerProperty(
        name="Source Armature",
        description="리타겟팅할 원본 모델 (B)",
        type=bpy.types.Object,
        poll=poll_armature
    )
    
    # Target과 Source를 위한 두 개의 독립된 매핑 데이터를 가집니다.
    target_bone_mapping: bpy.props.PointerProperty(type=HumanoidBoneMapping)
    source_bone_mapping: bpy.props.PointerProperty(type=HumanoidBoneMapping)

    # 실행 옵션
    use_scale_normalization: bpy.props.BoolProperty(
        name="Use Scale Normalization",
        description="Target과 Source의 키를 비교하여 스케일을 자동으로 맞춥니다.",
        default=True
    )
    use_pose_alignment: bpy.props.BoolProperty(
        name="Use Pose Alignment",
        description="Source의 포즈를 Target의 기준 포즈(Rest Pose)에 맞춥니다.",
        default=True
    )


def register():
    # HumanoidBoneMapping 클래스의 __annotations__에 동적으로 속성을 추가합니다.
    # 이 방식은 setattr을 사용하는 것보다 애드온 리로드 시 훨씬 더 안정적입니다.
    # 기존에 속성이 보이지 않던 근본적인 원인을 해결합니다.
    HumanoidBoneMapping.__annotations__ = {}
    for prop_name, display_name in STANDARD_BONE_NAMES:
        HumanoidBoneMapping.__annotations__[prop_name] = bpy.props.StringProperty(name=display_name, default="")

    bpy.utils.register_class(HumanoidBoneMapping)
    bpy.utils.register_class(RetargeterProperties)
    
    # 씬에 메인 프로퍼티를 등록합니다.
    bpy.types.Scene.retargeter_props = bpy.props.PointerProperty(type=RetargeterProperties)

def unregister():
    del bpy.types.Scene.retargeter_props
    
    bpy.utils.unregister_class(RetargeterProperties)
    bpy.utils.unregister_class(HumanoidBoneMapping)
    # __annotations__를 사용하면 클래스가 unregister될 때 Blender가 자동으로 정리해줍니다.