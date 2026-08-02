# ScreenFlow

**Language / 语言：** [中文](#zh) · [English](#en)

ScreenFlow 是面向 Windows 的前台视觉自动化应用（Studio）。通过屏幕截取与模板匹配识别界面状态，并模拟键鼠执行既定流程。

ScreenFlow is a Windows desktop application (Studio) for foreground vision automation. It identifies UI state via screen capture and template matching, then simulates mouse and keyboard input according to your project rules.

---

<a id="zh"></a>

## 中文文档

**[English](#en)**

### 概述

ScreenFlow 根据使用者配置的项目规则，对**前台**应用程序进行视觉识别与键鼠操作。识别依赖屏幕截图与图像模板匹配，不依赖目标进程的内存读取或代码注入。

推荐远程仓库名称：`screenflow-studio`。产品显示名称与可执行文件名称保持为 **ScreenFlow**。

### 能力与限制

**支持的能力**

- 依据页面特征图像判定当前界面
- 在页面内按状态树选择分支，并执行点击、按键、等待、宏等动作
- 在主动作完成后进行后续观察（post-listen），以处理界面后续变化
- 通过 Studio 图形界面编辑项目；支持界面语言中文 / English
- 动作步骤支持最小可用的 **脚本**（`op: script`），详见下文「脚本步骤」

**明确不支持或不适用的情形**

- 不读取目标进程内存，不进行注入，不提供后台（非前台）输入
- 运行期间目标程序须保持在前台，否则识别与操作可能失效
- 不对第三方软件的服务条款合规性作保证；是否允许自动化由使用者自行核实
- 脚本能力仅为最小实现，不具备完整插件体系（见待完善列表）

### 使用打包版本

1. 启动 `release/ScreenFlow/ScreenFlow.exe`（或发布包中的同名可执行文件）。
2. 选择 **文件 → 打开项目文件夹…** 或 **新建项目文件夹…**。
3. 添加页面，并导入用于识别与点击定位的图像资源。
4. 编辑状态树：为不同界面情况配置动作；在无其他分支匹配时可使用「其他」（ELSE）分支。
5. 按需配置后续观察，以在主动作之后继续根据画面作出响应。
6. **保存**后点击 **开始**。首次启动引擎时，系统可能提示用户账户控制（UAC）；需允许后方可提权运行引擎进程。
7. 可在设置中切换 Studio 界面语言。

关闭 Studio 时，应用会尝试停止引擎进程。若进程仍残留，可在任务管理器中结束对应的 `ScreenFlow.exe`。

引擎与 Studio 共用同一可执行文件：在需要时由 Studio 以 `--engine-runner` 参数启动第二进程（必要时请求提权）。

### 项目模型

自动化配置以**项目文件夹**形式存放与分发，而非安装式插件。主要概念如下：

| 概念 | 说明 |
|------|------|
| 页面 | 一类可识别的界面；通常对应一张特征检测图 |
| 识别图 / 点击图 | 分别用于判定匹配与确定点击位置的图像资源 |
| 状态 | 同一页面下的分支条件；支持多层判定，并以「其他」作为未匹配时的回退 |
| 动作 | 点击、按键、等待、宏、脚本等可执行步骤 |
| 后续观察 | 主动作包执行完毕后，按规则继续观察并执行跟进动作 |

### 脚本步骤

**现状（已支持，最小实现）**

- 在动作列表中可添加类型为「脚本」的步骤，目标为项目内相对路径（例如 `scripts/my_script.py`）。
- 脚本文件须定义可调用入口 `run(ctx, params)`。
- `ctx` 当前提供：`project_root`、`page_id`、`vars`、`log`。
- 若 `run` 返回 `"abort_pack"`，将中止当前动作包。
- 脚本路径不得逃逸出项目根目录；启动前校验会检查文件是否存在。

**后续待完善**

- 将步骤级参数传入 `params`（当前实现固定传入空字典 `{}`）
- 执行超时、取消与更明确的错误呈现
- 开发期热重载（修改脚本后无需整包重启引擎）
- 运行隔离 / 沙箱策略
- 更丰富的 `ctx`（例如受控的匹配、输入等引擎能力）
- Studio 内更完整的脚本编辑与调试体验

目录结构示例：

```text
my_project/
  project.json              # 运行参数、宏、页面列表等
  pages/{page_id}/
    page.json               # 页面检测与状态树定义
    detect/                 # 识别用图像
    click/                  # 点击定位用图像
  layer_templates/          # 可选：可复用状态模板
  scripts/                  # 可选：脚本步骤
```

### 用户设置位置

Studio 的界面与会话偏好（语言、最近项目、是否重新打开上次项目、窗口布局、引擎运行模式等）保存在用户配置目录，**不属于**项目文件夹：

```text
C:\Users\<用户名>\.screenflow\ui.json
```

### 责任声明

请在适用法律法规及第三方软件许可与服务条款允许的范围内使用本软件。因使用本软件对第三方程序进行自动化操作而导致的账号限制、封禁或其他损失，由使用者自行承担。

### 开发者说明

从源码启动 Studio：

```powershell
cd screenflow
python -m pip install -r requirements.txt
python .\run_studio.py
```

构建 Windows 发布目录（输出至 `release/ScreenFlow/`）：

```powershell
powershell -File .\scripts\build_exe.ps1
```

运行测试：

```powershell
python -m pytest tests -q
```

---

<a id="en"></a>

## English

**[中文](#zh)**

### Overview

ScreenFlow is a **foreground** vision-automation application for Windows. Given a project you configure in Studio, it identifies on-screen UI state through capture and template matching, then performs mouse and keyboard actions. It does not read process memory and does not inject code into the target application.

Recommended remote repository name: `screenflow-studio`. The product name and executable remain **ScreenFlow**.

### Capabilities and limitations

**Supported**

- Detect the current screen/page using feature (template) images
- Select a branch via a per-page state tree and run actions (click, key, wait, macro, and related steps)
- Optionally arm post-listen behavior after the main action pack to follow up on UI changes
- Edit projects in the Studio GUI; UI language may be Chinese or English
- Minimal **script** action steps (`op: script`); see “Script steps” below

**Out of scope**

- No memory reading, no injection, and no background (non-foreground) input
- The target application must remain in the foreground while the engine runs; otherwise detection and input may fail
- Compliance with third-party terms of service is the operator’s responsibility; ScreenFlow does not warrant that automation is permitted for any given software
- Scripting is a minimal implementation only, not a full plugin framework (see planned work)

### Using the packaged build

1. Launch `release/ScreenFlow/ScreenFlow.exe` (or the same executable from your distribution package).
2. Use **File → Open Project Folder…** or **New Project Folder…**.
3. Add pages and import images used for detection and click targeting.
4. Edit the state tree: assign actions to situations; use the ELSE (“Other”) branch when no scored candidate matches.
5. Configure post-listen where follow-up observation after the main actions is required.
6. **Save**, then **Start**. On first engine launch, Windows may show a UAC prompt; elevation must be allowed for the elevated runner process.
7. Switch the Studio UI language in settings as needed.

Closing Studio attempts to stop the engine process. If a process remains, end the corresponding `ScreenFlow.exe` in Task Manager.

Studio and the engine share one executable: when required, Studio starts a second process of the same binary with `--engine-runner` (requesting elevation when configured to do so).

### Project model

Automation is stored as a **project folder** (not an installable plugin). Core concepts:

| Concept | Description |
|---------|-------------|
| Page | A recognizable UI surface, typically keyed by a detection image |
| Detect / click images | Assets used to score a match and to resolve click coordinates |
| State | Branching conditions within a page; multi-layer trees are supported, with ELSE as the unmatched fallback |
| Actions | Executable steps such as click, key, wait, macro, and script |
| Post-listen | After the main action pack, continue observing the screen and run follow-up actions per rules |

### Script steps

**Current status (supported, minimal)**

- Action lists may include a **Script** step whose target is a project-relative path (for example `scripts/my_script.py`).
- The file must expose a callable `run(ctx, params)`.
- `ctx` currently provides: `project_root`, `page_id`, `vars`, and `log`.
- If `run` returns `"abort_pack"`, the current action pack is aborted.
- Script paths must remain under the project root; pre-start validation checks that the file exists.

**Planned improvements**

- Pass step-level arguments into `params` (today the implementation always passes `{}`)
- Execution timeout, cancellation, and clearer error reporting
- Hot reload during development (apply script edits without a full engine restart)
- Isolation / sandbox policy for user scripts
- Richer `ctx` (controlled access to matching, input, and related engine capabilities)
- Fuller in-Studio editing and debugging for scripts

Example layout:

```text
my_project/
  project.json              # Runtime settings, macros, page list, etc.
  pages/{page_id}/
    page.json               # Page detection and state tree
    detect/                 # Detection images
    click/                  # Click-target images
  layer_templates/          # Optional reusable state templates
  scripts/                  # Optional script steps
```

### Where settings are stored

Studio UI and session preferences (language, recent projects, reopen-last-project, window layout, runner mode, and similar) live in the user config directory, **not** inside the project folder:

```text
C:\Users\<you>\.screenflow\ui.json
```

### Disclaimer

Use this software only where permitted by applicable law and by the licenses and terms of any third-party software you automate. You assume all risk for account restrictions, bans, or other consequences arising from such automation.

### Developer notes

Run Studio from source:

```powershell
cd screenflow
python -m pip install -r requirements.txt
python .\run_studio.py
```

Build the Windows distribution into `release/ScreenFlow/`:

```powershell
powershell -File .\scripts\build_exe.ps1
```

Run tests:

```powershell
python -m pytest tests -q
```
