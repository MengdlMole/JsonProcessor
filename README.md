# JsonProcessor

> 当前版本：1.0.0 · 开源协议：AGPL-3.0-or-later

JsonProcessor 是一个完全开源、本地优先的 JSON、TXT、XLSX 脚本与工作流管理工具。
它将零散的 Python 数据处理脚本注册为可复用的原子工具，再通过声明式工作流组合、固定参数
并重复执行。文件默认只在本机处理，不依赖云服务。

## 主要能力

当前版本采用统一工作台设计，包含：

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

## 设计原则

- **原子化**：一个脚本只完成一项操作，例如删除反斜杠、删除空格和删除换行符是三个独立功能。
- **相互隔离**：工具拥有明确的输入、输出和参数契约，不依赖页面中的隐式状态。
- **组合优先**：多个原子步骤通过工作流编排，不在单个按钮中隐藏连续处理逻辑。
- **统一交互**：脚本使用相同的输入区、参数区、执行区和结果区，不为每个脚本重复设计页面。
- **本地优先**：上传文件、运行记录和生成结果保存在本机，应用本身不上传业务数据。
- **声明式扩展**：页面根据 YAML 元数据生成表单，新增大部分工具不需要编写新的 UI 页面。

## 环境要求

| 环境 | 要求 |
| --- | --- |
| Python | 3.11 或更高版本，推荐 3.11–3.13 |
| 操作系统 | Windows、macOS 或 Linux |
| 浏览器 | Chrome、Edge、Firefox、Safari 等现代浏览器 |
| Git | 仅克隆和更新项目时需要 |
| 网络 | 首次下载依赖时需要，正常运行不需要 |

项目不需要 Node.js、Docker、Java、MySQL 或独立的 SQLite 服务。Excel 文件由 `openpyxl`
直接处理，运行索引使用 Python 内置的 SQLite 支持。

检查 Python 版本：

```bash
python --version
```

如果系统中的命令是 `python3`，请在下面的命令中将 `python` 替换为 `python3`。

## 快速开始

### 1. 获取项目

使用 HTTPS：

```bash
git clone https://github.com/MengdlMole/JsonProcessor.git
cd JsonProcessor
```

已配置 GitHub SSH 时也可以使用：

```bash
git clone git@github.com:MengdlMole/JsonProcessor.git
cd JsonProcessor
```

### 2. 创建虚拟环境并安装依赖

macOS / Linux：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell：

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

如需运行测试和代码检查，请将最后一条安装命令改为：

```bash
python -m pip install -e ".[dev]"
```

### 3. 启动应用

确保虚拟环境已激活，然后运行：

```bash
python -m streamlit run app.py
```

浏览器通常会自动打开 [http://localhost:8501](http://localhost:8501)。如果没有自动打开，
请手动访问该地址。终端中按 `Ctrl+C` 可以停止服务，输入 `deactivate` 可以退出虚拟环境。

以后再次运行时，不需要重新安装依赖。进入项目目录、激活 `.venv`，再执行启动命令即可。

## 更新项目

```bash
git pull
python -m pip install -e .
python -m streamlit run app.py
```

重新执行安装命令可以同步新版本增加或调整的依赖，不会删除本地 `data/` 中的业务数据。

## 使用入口

- **JSON 工作台**：上传 JSON 文件或粘贴文本，在同一个编辑器中执行格式化和字符处理。
- **脚本中心**：搜索并运行已注册的原子脚本，保存常用参数预设，下载运行结果。
- **工作流中心**：运行由多个原子脚本组成的固定处理流程。
- **工作流设计器**：选择已有脚本、固定各步骤参数，并保存为可重复执行的线性工作流。
- **运行记录**：查看每次执行的输入、参数、步骤状态和输出产物。

## 项目结构

```text
JsonProcessor/
├── app.py                    # Streamlit 页面与导航入口
├── pyproject.toml            # 项目版本、依赖和开发工具配置
├── registry/
│   └── tools.yaml            # 内置脚本和工作流声明
├── workbench/
│   ├── execution.py          # 脚本及工作流执行服务
│   ├── models.py             # 工具、输入、输出和运行模型
│   ├── operations.py         # JSON 共享编辑器的原子文本操作
│   ├── processors.py         # 原子处理器实现及注册表
│   ├── registry.py           # YAML 工具库加载与校验
│   ├── storage.py            # 运行记录、产物和预设持久化
│   └── ui.py                 # 通用 Streamlit 视觉组件
├── tests/                    # 自动化测试
└── data/                     # 本地运行数据，不上传业务文件
```

## 数据与隐私

每次运行都会创建独立目录：

```text
data/runs/<run-id>/
├── inputs/<input-id>/
├── outputs/
└── run.json
```

- `data/workbench.db`：运行记录索引。
- `data/runs/`：每次运行的输入副本、输出产物和完整运行信息。
- `data/presets.json`：保存的参数预设。
- `data/custom_tools.yaml`：工作流设计器保存的自定义工作流。

业务文件、数据库、运行产物和参数预设默认不会提交到 Git。需要迁移设备时，请自行备份
所需的 `data/` 内容，尤其是自定义工作流。

## 常见问题

### `python` 命令不存在

macOS 或 Linux 可以尝试 `python3`；Windows 可以使用 `py -3.11`。如果仍然不可用，请先从
Python 官方发行版或系统包管理器安装受支持的 Python 版本。

### PowerShell 不允许激活虚拟环境

可以仅为当前 PowerShell 进程调整执行策略，然后重新激活：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

也可以不激活虚拟环境，直接运行：

```powershell
.venv\Scripts\python.exe -m streamlit run app.py
```

### 端口 8501 已被占用

指定另一个端口启动：

```bash
python -m streamlit run app.py --server.port 8502
```

### 安装依赖失败

先确认 Python 版本，再升级安装工具后重试：

```bash
python -m pip install --upgrade pip setuptools
python -m pip install -e .
```

### 如何彻底重建本地环境

停止应用，删除 `.venv`，然后重新执行“创建虚拟环境并安装依赖”中的步骤。`data/` 与 `.venv`
相互独立，删除虚拟环境不会删除业务数据。

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

## 开发与验证

安装开发依赖后运行：

```bash
python -m pytest -q
python -m ruff check .
```

提交新工具前，建议同时验证：工具定义能够加载、输入输出类型可以连接、处理器保持单一职责，
以及所有测试和代码检查均通过。

## 开源许可证

本项目采用 AGPL-3.0-or-later。运行依赖均采用兼容的开源许可证。
