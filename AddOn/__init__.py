bl_info = {
    "name": "Blender Humanoid Retargeter Tool",
    "author": "Hydrogen102",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "3D View > N-Panel > Retargeter",
    "description": "Automatically retargets humanoid armatures.",
    "warning": "",
    "doc_url": "",
    "category": "Rigging",
}

import bpy
import importlib

# 개발 중 F8 키로 애드온을 리로드할 때, 하위 모듈들도 모두 리로드되도록 처리합니다.
# 이 부분이 없으면 .py 파일을 수정해도 블렌더를 재시작하기 전까지 변경사항이 반영되지 않을 수 있습니다.
if "bpy" in locals():
    # core 패키지 내부 모듈부터 리로드
    from .core import mapping, alignment, finalization, normalization
    importlib.reload(mapping)
    importlib.reload(alignment)
    importlib.reload(finalization)
    importlib.reload(normalization)
    # 상위 모듈 리로드
    from . import properties, ui, operators
    importlib.reload(properties)
    importlib.reload(operators)
    importlib.reload(ui)

# 애드온의 각 모듈을 가져옵니다.
from . import properties
from . import ui
from . import operators

# 등록/해제할 모듈들을 리스트로 관리합니다.
# 등록 순서는 매우 중요합니다: 데이터(properties) -> 기능(operators) -> UI(ui)
modules = [
    properties,
    operators,
    ui,
]

def register():
    for module in modules:
        if hasattr(module, 'register'):
            module.register()

def unregister():
    for module in reversed(modules):
        if hasattr(module, 'unregister'):
            module.unregister()