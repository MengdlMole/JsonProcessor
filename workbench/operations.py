from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EditorOperation:
    id: str
    label: str
    group: str
    description: str
    warning: str = ""

    @property
    def display_name(self) -> str:
        return f"{self.group} · {self.label}"


EDITOR_OPERATIONS = (
    EditorOperation("pretty", "格式化缩进", "排版", "只调整 JSON 结构缩进。"),
    EditorOperation("compact", "压缩为单行", "排版", "只移除 JSON 结构外的排版空白。"),
    EditorOperation("show_unicode", "显示 Unicode 字符", "编码", "将 Unicode 转义显示为字符。"),
    EditorOperation(
        "escape_unicode", "转义 Unicode 字符", "编码", "将非 ASCII 字符改为 Unicode 转义。"
    ),
    EditorOperation(
        "unwrap_one_layer",
        "解码一层 JSON 字符串",
        "解码",
        "只解码最外层一次，不继续递归处理。",
    ),
    EditorOperation(
        "remove_backslashes",
        "删除所有反斜杠",
        "字符清理",
        "只删除原始文本中的反斜杠字符。",
        "可能改变路径、正则表达式和转义字符含义。",
    ),
    EditorOperation(
        "remove_spaces",
        "移除字符串值中的空格",
        "字符清理",
        "只移除 JSON 字符串值中的 ASCII 空格，不处理换行、回车或制表符。",
    ),
    EditorOperation(
        "remove_newlines",
        "移除字符串值中的换行符",
        "字符清理",
        "只移除 JSON 字符串值中的换行符，不处理其他空白字符。",
    ),
    EditorOperation(
        "remove_carriage_returns",
        "移除字符串值中的回车符",
        "字符清理",
        "只移除 JSON 字符串值中的回车符，不处理其他空白字符。",
    ),
    EditorOperation(
        "remove_tabs",
        "移除字符串值中的制表符",
        "字符清理",
        "只移除 JSON 字符串值中的制表符，不处理其他空白字符。",
    ),
)

EDITOR_OPERATION_BY_ID = {operation.id: operation for operation in EDITOR_OPERATIONS}
