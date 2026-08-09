# ScreenFlow

**Language / 语言：** [中文](#zh) · [English](#en)

ScreenFlow 是面向 Windows 的前台视觉自动化应用。通过屏幕截取与模板匹配识别界面状态，并模拟键鼠执行既定流程。编辑器为 **Web Studio**（本机 API + Vue）。

ScreenFlow is a Windows foreground vision-automation app. It identifies UI state via screen capture and template matching, then simulates mouse and keyboard input. The editor is **Web Studio** (local API + Vue).

---

<a id="zh"></a>

## 中文文档

**[English](#en)**

### 概述

ScreenFlow 根据使用者配置的项目规则，对**前台**应用程序进行视觉识别与键鼠操作。识别依赖屏幕截图与图像模板匹配，不依赖目标进程的内存读取或代码注入。

使用 **Web Studio**（Vue + 本机 API）编辑项目：支持画面特征 / 原图 / 匹配方案三区模型、变量声明、引用绑定等。

推荐远程仓库名称：`screenflow-studio`。产品显示名称与可执行文件名称保持为 **ScreenFlow**。

### 能力与限制

**支持的能力**

- 依据页面「画面特征」所选用的匹配方案（模板 + 搜索区）判定当前界面
- 在页面内按情况树选择分支，并执行点击、按键、等待、宏等动作
- 在主动作完成后进行后续观察（post-listen），以处理界面后续变化
- 通过 Web Studio 编辑项目；支持界面语言中文 / English
- 动作步骤支持最小可用的 **脚本**（`op: script`），详见下文「脚本步骤」

**明确不支持或不适用的情形**

- 不读取目标进程内存，不进行注入，不提供后台（非前台）输入
- 运行期间目标程序须保持在前台，否则识别与操作可能失效
- 不对第三方软件的服务条款合规性作保证；是否允许自动化由使用者自行核实
- 脚本能力仅为最小实现，不具备完整插件体系（见待完善列表）

### 使用打包版本

1. 启动 `release/ScreenFlow.exe`（单文件；首次启动需解压运行时，可能稍慢），浏览器中打开 Web Studio。
2. 打开或新建项目文件夹。
3. 添加页面：创建匹配方案与画面特征，并为特征选用方案（可设「用作本页识别」）。
4. 编辑情况树：为不同界面情况配置动作；未匹配时使用「默认情况」。
5. 按需配置后续观察。
6. **保存**后点击 **开始**。默认**提权外部引擎**可能弹出 UAC；也可选用 **inline（进程内）** 模式。
7. 可在界面中切换语言。

关闭应用时会尝试停止引擎进程。若仍残留，可在任务管理器中结束对应的 `ScreenFlow.exe`。

Web Studio 与引擎可共用同一可执行文件：提权模式下以 `--engine-runner` 启动第二进程；inline 模式不另起进程。

### 项目模型

自动化配置以**项目文件夹**形式存放与分发，而非安装式插件。主要概念如下：

| 概念 | 说明 |
|------|------|
| 页面 | 一类可识别的界面 |
| 画面特征 | 逻辑符号（情况打分、点击、本页识别都引用它）；只选用 / 取消选用一个匹配方案 |
| 原图 | 页级整窗截图列表（`sources`）；Studio 素材，匹配方案从其上裁切；不参与运行 |
| 匹配方案 | 选用一张原图 + 搜索区 + 匹配裁切（派生小图在 `features/`）；可共用、可闲置 |
| 情况 | 同一页面下的分支条件；支持多层判定，并以「默认情况」作为未匹配时的回退 |
| 动作 | 点击、按键、等待、宏、脚本等可执行步骤 |
| 后续观察 | 主动作包执行完毕后，按规则继续观察并执行跟进动作 |

### 脚本步骤

**现状（已支持，最小实现）**

- 在动作列表中可添加类型为「脚本」的步骤，目标为项目内相对路径（例如 `scripts/my_script.py`）。
- 脚本文件须定义可调用入口 `run(ctx, params)`。
- `ctx` 当前提供：`project_root`、`page_id`、`vars`、`log`。
- 步骤可配置可选的 JSON 对象作为 `params`（未配置时为 `{}`）。
- 若 `run` 返回 `"abort_pack"`，将中止当前动作包。
- 脚本路径不得逃逸出项目根目录；启动前校验会检查文件是否存在。

**后续待完善**

- 执行超时、取消与更明确的错误呈现
- 开发期热重载（修改脚本后无需整包重启引擎）
- 运行隔离 / 沙箱策略
- 更丰富的 `ctx`（例如受控的匹配、输入等引擎能力）
- Studio 内更完整的脚本编辑与调试体验

目录结构示例：

```text
my_project/
  project.json              # 运行参数、宏、页面列表、vars 等
  pages/{page_id}/
    page.json               # 画面特征、sources（原图）、visuals（匹配方案）、recognize_with、情况树
    sources/                # 页级原图（整窗截图）
    features/               # 匹配方案派生的裁切小图（运行时模板）
  layer_templates/          # 可选：可复用情况模板
  scripts/                  # 可选：脚本步骤
```

### 用户设置位置

Web Studio 的界面与会话偏好（语言、最近项目、是否重新打开上次项目、引擎运行模式等）保存在用户配置目录，**不属于**项目文件夹：

```text
C:\Users\<用户名>\.screenflow\ui.json
```

### 责任声明

请在适用法律法规及第三方软件许可与服务条款允许的范围内使用本软件。因使用本软件对第三方程序进行自动化操作而导致的账号限制、封禁或其他损失，由使用者自行承担。

### 开发者说明

**Web Studio（Vue）**：

```powershell
python -m pip install -r requirements.txt
cd web
npm install
cd ..
# 终端 1：API
python -m studio_api
# 终端 2：前端
cd web
npm run dev
# 浏览器打开 http://127.0.0.1:5173 （Vite 将 /api 代理到 8787）
```

或一键（API + Vite，并尝试打开浏览器）：

```powershell
python .\run_web_studio.py --dev
```

已构建前端时，可只起 API 并托管 `web/dist`：

```powershell
cd web
npm run build
cd ..
python .\run_web_studio.py
```

构建 Windows 单文件可执行程序（输出至 `release/ScreenFlow.exe`；需先构建 `web/dist`）：

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

ScreenFlow is a **foreground** vision-automation application for Windows. Configure projects in **Web Studio**, identify on-screen UI via capture and template matching, then run mouse/keyboard actions. It does not read process memory and does not inject code.

Recommended remote repository name: `screenflow-studio`. The product name and executable remain **ScreenFlow**.

### Capabilities and limitations

**Supported**

- Detect the current page using **screen features** that select a match setup (template + search area)
- Select a branch via a per-page case tree and run actions (click, key, wait, macro, and related steps)
- Optionally arm post-listen behavior after the main action pack to follow up on UI changes
- Edit projects in Web Studio; UI language may be Chinese or English
- Minimal **script** action steps (`op: script`); see “Script steps” below

**Out of scope**

- No memory reading, no injection, and no background (non-foreground) input
- The target application must remain in the foreground while the engine runs; otherwise detection and input may fail
- Compliance with third-party terms of service is the operator’s responsibility; ScreenFlow does not warrant that automation is permitted for any given software
- Scripting is a minimal implementation only, not a full plugin framework (see planned work)

### Using the packaged build

1. Launch `release/ScreenFlow.exe` (standalone; first start may be slower while unpacking) and open Web Studio in the browser.
2. Open or create a project folder.
3. Add pages: create match setups and screen features, then select a setup on each feature (mark one for page recognition).
4. Edit the case tree; use the default case when nothing else matches.
5. Configure post-listen where needed.
6. **Save**, then **Start**. Default **elevated external runner** may show UAC; **inline** mode runs in-process without UAC.
7. Switch UI language in the app as needed.

Closing the app attempts to stop the engine. If a process remains, end the corresponding `ScreenFlow.exe` in Task Manager.

Web Studio and the engine can share one executable: elevate mode starts a second process with `--engine-runner`; inline mode does not.

### Project model

Automation is stored as a **project folder** (not an installable plugin). Core concepts:

| Concept | Description |
|---------|-------------|
| Page | A recognizable UI surface |
| Screen feature | Logical id used by cases, clicks, and page recognition; selects at most one match setup |
| Originals | Page-level full-window screenshots (`sources`); Studio material that setups crop from; not used at runtime |
| Match setup | Picks one original + search area + match crop (derived template under `features/`); shareable, may be idle |
| Case | Branching conditions within a page; multi-layer trees with a default case fallback |
| Actions | Executable steps such as click, key, wait, macro, and script |
| Post-listen | After the main action pack, continue observing the screen and run follow-up actions per rules |

### Script steps

**Current status (supported, minimal)**

- Action lists may include a **Script** step whose target is a project-relative path (for example `scripts/my_script.py`).
- The file must expose a callable `run(ctx, params)`.
- `ctx` currently provides: `project_root`, `page_id`, `vars`, and `log`.
- An optional JSON object on the step is passed as `params` (defaults to `{}`).
- If `run` returns `"abort_pack"`, the current action pack is aborted.
- Script paths must remain under the project root; pre-start validation checks that the file exists.

**Planned improvements**

- Execution timeout, cancellation, and clearer error reporting
- Hot reload during development (apply script edits without a full engine restart)
- Isolation / sandbox policy for user scripts
- Richer `ctx` (controlled access to matching, input, and related engine capabilities)
- Fuller in-Studio editing and debugging for scripts

Example layout:

```text
my_project/
  project.json              # Runtime, macros, page list, vars, etc.
  pages/{page_id}/
    page.json               # Features, sources (originals), visuals, recognize_with, case tree
    sources/                # Page originals (full-window screenshots)
    features/               # Derived match crops (runtime templates)
  layer_templates/          # Optional reusable case templates
  scripts/                  # Optional script steps
```

### Where settings are stored

Web Studio UI and session preferences (language, recent projects, reopen-last-project, runner mode, and similar) live in the user config directory, **not** inside the project folder:

```text
C:\Users\<you>\.screenflow\ui.json
```

### Disclaimer

Use this software only where permitted by applicable law and by the licenses and terms of any third-party software you automate. You assume all risk for account restrictions, bans, or other consequences arising from such automation.

### Developer notes

**Web Studio (Vue)**:

```powershell
python -m pip install -r requirements.txt
cd web
npm install
cd ..
python -m studio_api
# other terminal:
cd web
npm run dev
# open http://127.0.0.1:5173
```

Or: `python .\run_web_studio.py --dev`

Build the Windows standalone executable to `release/ScreenFlow.exe` (build `web/dist` first):

```powershell
powershell -File .\scripts\build_exe.ps1
```

Run tests:

```powershell
python -m pytest tests -q
```
