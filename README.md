# JsonProcessor

一个完全开源、本地优先的 JSON、TXT、XLSX 脚本与工作流管理工具。当前版本采用统一工作台设计，包含：

- JSON 字段选择、空值过滤、去重和 TXT 序列化等独立原子节点
- JSON 缩进、压缩、Unicode 显示和 Unicode 转义等独立原子操作
- JSON 字符串只解码一层
- 文本只删除反斜杠
- JSON 字符串值中的换行、回车和制表符分别清理
- JSON 记录映射、Jinja2 模板渲染和 XLSX 写出等独立原子节点
- TXT ID 生成 JSON、写入新 XLSX 或填充现有模板的声明式工作流
- JSON 提取 ID 后按模板生成 XLSX 的五步工作流
- YAML 工具注册、元数据驱动表单、参数预设、运行记录和结果下载
- 声明式多步骤工作流，每个步骤独立记录状态、输入、输出和错误
- 可视化线性工作流设计器，可选择已有脚本、固定场景参数并持久化
- 工具搜索与标签过滤、完整产物下载、输入文件与步骤历史
- Excel 模板工作表和列自动识别、模板内容预览

JSON 输入工具支持上传文件或直接粘贴文本。缩进、压缩、Unicode 显示、Unicode 转义、
解码一层、删除反斜杠、删除空格，以及分别移除换行符、回车符和制表符均为独立操作。
界面不会用一个按钮自动猜测并连续执行多种变换。缩进和压缩只改变 JSON 结构排版，保留
字符串的原始转义写法；字符清理操作只删除明确选中的字符。无效 JSON 会直接阻止需要合法
JSON 的工具运行。

JSON 相关操作统一放在“JSON 工作台”：顶部只有一个文件上传栏和一个共享文本编辑器；
文本操作通过分组下拉框选择后应用；每次点击只执行一个操作，并支持最多 30 步撤销。
字段提取、Excel 导出
及以 JSON 为起点的工作流也通过下拉框切换，直接消费当前 JSON，不需要再次上传或粘贴。
编辑器内容变化后，旧运行结果会显示过期提醒。

所有页面共用同一套页面标题、工具身份、输入区、参数/预设区、执行区和结果区。脚本不再各自
编写专用页面；Excel 工作表、列选择等特殊能力也通过工具元数据声明，由通用渲染器解释。

所有文件默认只在本机 `data/` 目录处理，不依赖云服务。

## 启动

推荐使用 Python 3.11–3.13：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
streamlit run app.py
```

浏览器将打开 `http://localhost:8501`。

## 工具定义

工具和工作流在 `registry/tools.yaml` 中声明。页面读取参数定义并生成表单，执行逻辑位于
`workbench/processors.py`。编辑器操作目录位于 `workbench/operations.py`，统一视觉组件位于
`workbench/ui.py`。新增处理器时需要：

1. 在 `processors.py` 中实现函数。
2. 在 `PROCESSORS` 中注册函数。
3. 在 `registry/tools.yaml` 中声明一个或多个文件输入和参数。

常用扩展元数据：

- 输入的 `inspector: xlsx`：启用通用 Excel 内容检查器。
- 参数的 `ui_control: workbook_sheet` 或 `workbook_column`：让通用表单根据已上传的工作簿生成选择项。
- `source_input`、`sheet_parameter`、`header_row_parameter`：声明控件依赖，不需要在页面代码里判断工具 ID。
- `outputs[].content_type`：声明每个产物的数据类型；工作流会在加载和设计阶段阻止不兼容连接。

新增功能应优先做成单一职责的脚本。多个原子操作的固定顺序、参数和输入输出关系由工作流
负责组合和持久化；不要把多个清理动作塞进一个处理器或一个按钮。

每个工具使用 `inputs` 和 `outputs` 声明输入输出契约。当前类型包括 `json`、`json_array`、
`text` 和 `xlsx`。处理器接收 `{输入 ID: 文件路径}`，因此可自然支持
“ID 文件 + Excel 模板”这类多文件场景；每个输入都单独保存文件名、路径和 SHA-256。

脚本由 `ExecutionService` 调用，存储层只负责运行、步骤和产物的持久化。处理器返回
`ProcessorResult`，其中可包含一个或多个带哈希、大小和媒体类型的 `Artifact`。

## 工作流定义

工作流不再对应一个复合 Python 函数，而是在 YAML 中引用已有脚本：

```yaml
- id: example_workflow
  name: 示例工作流
  kind: workflow
  description: 提取 ID 后生成 Excel
  inputs:
    - id: source_json
      label: JSON 文件
  parameters: []
  steps:
    - id: extract
      uses: json_select_values
      inputs:
        source_json: ${inputs.source_json}
      params:
        field_path: data.items[*].id
    - id: filter_empty
      uses: json_filter_empty_values
      inputs:
        source_json: ${steps.extract.outputs.result}
      params: {}
    - id: deduplicate
      uses: json_deduplicate_values
      inputs:
        source_json: ${steps.filter_empty.outputs.result}
      params: {}
    - id: render
      uses: json_render_template_rows
      inputs:
        source_json: ${steps.deduplicate.outputs.result}
      params:
        id_variable: id
        common_params: "{}"
        json_template: '{"id": {{ id | tojson }}}'
        column_name: json_body
    - id: write
      uses: json_rows_to_xlsx
      inputs:
        source_json: ${steps.render.outputs.result}
      params:
        sheet_name: Data
```

当前工作流按声明顺序执行；每个步骤的产物只能引用已经完成的上游步骤。

## 工作流设计器

页面中的“工作流设计器”适合创建参数固定、重复执行的线性处理场景：

1. 设置工作流 ID、名称和用途。
2. 按顺序选择已有的单输入原子脚本；下拉框只显示能接收上一步输出类型的节点。
3. 为每一步填写并固定参数。
4. 检查生成的 YAML，保存到本机工具库或下载备份。

保存后的工作流位于 `data/custom_tools.yaml`，下次启动时会与内置工具一起加载。当前设计器
按顺序把上一步的主要产物传给下一步；需要多输入映射或分支时，仍可直接编写 YAML。

## 数据目录

每次运行都会创建独立目录：

```text
data/runs/<run-id>/
├── inputs/<input-id>/
├── outputs/
└── run.json
```

SQLite 中保存运行索引；`run.json` 保存完整参数和产物信息。业务文件、数据库和参数预设默认
被 `.gitignore` 排除。

## 开源许可证

本项目采用 AGPL-3.0-or-later。运行依赖均采用兼容的开源许可证。
