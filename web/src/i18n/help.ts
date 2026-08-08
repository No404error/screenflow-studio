/** Section help texts for Web Studio (en / zh). Aligned with Run drawer layout. */

export const helpEn: Record<string, string> = {
  tip:
    'Foreground vision only — no injection, no background input. Starting a run may request Administrator once for the engine process.',
  help_missing: '(No help text)',
  help_button_a11y: 'Details',
  help_dialog_title: 'Details',
  help_runtime:
    'Project-wide defaults for how often to capture the screen and how strict matching is.\n' +
    '• Engine process — Run as Administrator (separate process) may show a system prompt on Start; In-process is for debug only.\n' +
    '• Min. similarity — score must reach this (0–1) to count as a match; raise to reduce false matches, lower if matches are missed.\n' +
    '• Screenshot interval (s) — time between captures; shorter reacts faster but uses more CPU.\n' +
    '• Case near-tie tolerance / Case required lead — how close case scores may be, and how far the winner must beat #2.\n' +
    'Open “More options” for delays, page-level knobs, log language, and hotkeys.',
  help_runtime_advanced:
    'Usually leave these alone unless you need finer timing or page disambiguation.\n' +
    '• Screenshot scale size — resolution used to scale captures for template matching.\n' +
    '• Action delay / cooldown — pause after a click/key, and minimum gap between actions.\n' +
    '• Look-alike score gap — when two look-alike pages compete, how much one must win by.\n' +
    '• Page recognition near-tie — how close page scores may be when identifying the current page.\n' +
    '• Log language — language of messages in the log panel (does not change this UI language).\n' +
    '• Verbose log — extra diagnostic lines in the log.\n' +
    '• Abort steps when the page changes — stop the current action list if the recognized page switches.\n' +
    '• Hotkeys — shown for the desktop engine; this browser tab does not capture global keys.',
  help_page_match:
    'Per-page matching overrides. Leave a field empty to inherit the project default from Controls → Run defaults.\n' +
    '• Internal ID — stable key stored in project files (usually leave as-is).\n' +
    '• Recognition priority — when several pages match at once, higher priority wins.\n' +
    '• Look-alike page — optional pairing with another page that is easy to confuse.\n' +
    '• Min. similarity / Case near-tie / Case required lead — override Run defaults for cases on this page only.\n' +
    '• When cases are close — if the top two case scores fail required lead: choose by priority, or do not act (route to Default case if present).',
  help_page_default_post:
    'Page-level fallback follow-up — used after a case’s actions finish when that case has no follow-up of its own.\n' +
    'This is not a matching setting: it runs after actions, watching the screen for the next UI.\n' +
    '• Enable — turn the page default on or off.\n' +
    '• Follow-up mode / Observation count / Wait before first observation — same meaning as case follow-up.\n' +
    '• Edit follow-up cases — which follow-up situations to watch for (page default).\n' +
    'A case can still override this by enabling its own Follow-up in Case details.',
  help_page_images:
    'Screen features — logical names; matching is edited separately after select.\n' +
    'Matching = search area + match picture; template library files are reusable pixels only.\n' +
    'From a full-window screenshot: set search area, then crop the match picture.\n' +
    'Mark one feature as “Use for page” for page recognition.',
  help_page_source:
    'Reference canvas is updated when you create a match setup from a full screenshot.\n' +
    'It is edited inside Match setups, not as a separate page section. Not used at runtime.',
  help_page_features:
    'Screen features — logical names for recognition, case scoring, and clicks.\n' +
    'Here you only Use / Clear a match setup. Create and edit setups in Match setups.\n' +
    'Start is blocked if a used feature has no setup selected.',
  help_page_setups:
    'Match setups — ready “where to look + what to compare” packages.\n' +
    'New from screenshot: upload a full window, set search area, crop match picture.\n' +
    'Or create from a library template (full-screen search). Features then Use a setup.\n' +
    'Setups can be idle or shared by multiple features.',
  help_page_artwork:
    'Template library — reusable match-picture files only (no search area).\n' +
    'Upload here without creating features or setups. Used when creating a match setup.\n' +
    'Deleting a template removes setups that used it and clears feature selection.',
  help_case_basic:
    'Details for the selected case: when it wins, its actions run.\n' +
    '• Name — label shown in the case list.\n' +
    '• Default case — used when nothing else matches; always stays at the bottom.\n' +
    '• How to recognize — Match an image, Fixed score (advanced), or Match when image is absent.\n' +
    '• Screen feature — which feature to match (must have matching set for Start).\n' +
    '• Search region (optional) — overrides the feature’s matching search area; leave empty to use that area, or full-screen if none.\n' +
    '• Actions — ordered steps when this case is selected (drag ⋮⋮ to reorder).\n' +
    'Drag ⋮⋮ on the case list to reorder (Default case stays last).',
  help_case_post:
    'After the main actions finish, optionally keep checking the screen for what appears next.\n' +
    '• Enable follow-up — turn this on or off for the selected case.\n' +
    '• Follow-up mode — Observe once; Until another page; Until default case; or Fixed count.\n' +
    '  Until another page — wait until a different page is recognized; you may leave follow-up cases empty. ' +
    'A normal follow-up case runs its actions and keeps waiting for a page change; Default case waits without repeating actions.\n' +
    '  Until default case — keep observing until Default case wins; a normal hit runs its actions and continues.\n' +
    '• Observation count — attempts when mode is Fixed count.\n' +
    '• Wait before first observation (s) — pause after actions so the UI can appear.\n' +
    '• End when page unrecognized — stop follow-up if no page can be identified; Off skips those frames and continues.\n' +
    '• Edit follow-up cases — which situations to watch for during follow-up only.',
  help_case_when:
    'Optional filter before this case can win.\n' +
    '• Left — variable name (from Set variable steps).\n' +
    '• Right — required value; leave empty to mean “variable is set / true”.\n' +
    'If the condition fails, this case is skipped even if its picture matches.',
  help_case_advanced:
    'Usually leave alone unless you use sub-cases or need a stable file id.\n' +
    '• Internal ID — stable key in project files (renaming the case label does not change this).\n' +
    '• Nested match params — apply only when this case has sub-cases and those sub-cases are being scored.\n' +
    '  See the “?” next to Nested match params for each field.\n' +
    '• Priority — set on the case itself (not in this panel); when scores are close, higher wins (drag the list to reorder).',
  help_case_layer:
    'These values apply only after this case wins, when choosing among its sub-cases. ' +
    'They do not change how this case competes with other cases at the same level.\n' +
    'Leave a field empty to inherit: page Matching overrides → Run defaults (Controls).\n' +
    'Useful when a submenu or dialog under this case needs stricter or looser scoring than the rest of the page.\n' +
    '\n' +
    '• Internal ID — stable key stored in project files; usually leave as-is.\n' +
    '• Min. similarity (0–1) — a sub-case must reach this score to count as a candidate. ' +
    'Raise to reject weak matches; lower if sub-cases are often missed.\n' +
    '• Case near-tie tolerance — how close a sub-case’s score may be to the top score and still count as “close”. ' +
    'When several are close, priority / “When cases are close” rules decide.\n' +
    '• Case required lead — how far the top sub-case must beat #2. ' +
    'If the lead is too small, the run may skip acting, or follow page “When cases are close”.\n' +
    '\n' +
    'If this case has no sub-cases (it only runs actions), these fields do nothing until you add some.',
  help_steps:
    'Ordered steps when this case (or macro) is chosen.\n' +
    '• Operation — Click, Key, Wait, Hold key, Macro; Advanced: Set/Clear variable, Script.\n' +
    '• Click picture — a feature picture from this page to locate and click.\n' +
    '• Key / Hold — keyboard key (and hold duration for Hold key).\n' +
    '• Wait (seconds) — pause duration.\n' +
    '• Macro — run another reusable step list.\n' +
    '• Note — optional comment (not executed).\n' +
    '• Set / Clear variable — values used by “Only when variable condition holds” on cases.\n' +
    '• Script — optional project-relative Python script; Script params are an optional key–value object for advanced use.\n' +
    'Drag ⋮⋮ on a step to change order.',
  help_macros:
    'A macro is a reusable sequence of click/key/wait steps.\n' +
    '• Create with “Add macro”.\n' +
    '• Edit the name and steps here.\n' +
    '• From a case action, choose Macro and select this macro.\n' +
    'Click targets can use feature pictures from any page in the project.',
  help_pairs:
    'Look-alike pages are screens that are easy to confuse when identifying the current page.\n' +
    '• Page A / Page B — the two pages in the pair.\n' +
    '• Add / Remove — create or delete a pairing.\n' +
    'When either page is a top candidate, both are compared carefully before deciding.\n' +
    'Each page belongs to at most one pair.',
  help_vars:
    'Use variables when the screen alone is not enough — you need the flow to remember something across steps ' +
    '(for example “already logged in”, “chose difficulty hard”, “quest A finished”).\n' +
    '\n' +
    'Typical use:\n' +
    '1) Add a variable here and set its starting value (Default).\n' +
    '2) In a case’s Actions, use Set variable / Clear variable when something important happens.\n' +
    '3) On another case, turn on “Only when variable condition holds” so it only runs in the right situation.\n' +
    '\n' +
    'You can skip this page entirely if every decision can be made from pictures alone.\n' +
    '\n' +
    'On this table:\n' +
    '• Name — the label you pick in Set/Clear steps and case conditions.\n' +
    '• Type — yes/no, number, or text; pick what matches how you use it.\n' +
    '• Default — value at Start; each new Start resets to this.\n' +
    '• Description — optional note for yourself.\n' +
    '• Refs — how many places use this name; click to jump there.\n' +
    'If a name appears in steps but is missing from this list, you will see a warning — add it here when convenient.',
  sec_runtime: 'Run defaults',
  sec_runtime_advanced: 'More options',
  sec_page_match: 'Matching (usually leave alone)',
  sec_page_images: 'Screen features',
  sec_page_features: 'Screen features',
  sec_page_setups: 'Match setups',
  sec_page_artwork: 'Template library',
  sec_page_source: 'Reference shot',
  sec_page_default_post: 'Page default follow-up',
  sec_case_basic: 'Case details',
  sec_case_post: 'Follow-up',
  sec_case_advanced: 'More options',
  sec_steps: 'Actions',
  sec_macros: 'Macro',
  sec_pairs: 'Look-alike pages',
  sec_vars: 'Project variables',
  sec_detect: 'Page recognition',
  sec_pages: 'Pages',
  help_pages:
    'Pages are recognizable screens in your project.\n' +
    '• Each page has feature pictures, a recognition image, and cases with actions.\n' +
    '• Open a page from this list or from the sidebar.\n' +
    '• Look-alike pairs disambiguate screens that are easy to confuse.',
}

export const helpZh: Record<string, string> = {
  tip: '仅前台视觉识别与键鼠模拟 — 不注入、不后台操作。开始运行时，引擎进程可能会申请一次管理员权限。',
  help_missing: '（暂无说明）',
  help_button_a11y: '详细说明',
  help_dialog_title: '详细说明',
  help_runtime:
    '项目级默认：多久截一次屏，以及匹配要多严格。\n' +
    '• 引擎进程方式 —「以管理员身份运行」在开始时可能弹出系统权限提示；「在本程序内运行」仅供调试。\n' +
    '• 最低相似度 — 达到该值（0～1）才算匹配；调高可减少误认，调低可减少漏认。\n' +
    '• 截屏间隔（秒） — 两次截屏之间的等待；越短反应越快，也更占资源。\n' +
    '• 情况相近容差 / 情况领先要求 — 情况得分多接近算「接近」，以及第一名须比第二名高出多少。\n' +
    '「更多选项」中可设置动作延迟、页面级参数、日志语言与快捷键说明。',
  help_runtime_advanced:
    '通常无需修改；需要更细的节奏或页面区分时再调。\n' +
    '• 截屏缩放分辨率 — 模板匹配时用于缩放截屏的分辨率。\n' +
    '• 动作延迟 / 冷却 — 点击或按键后的停顿，以及两次动作之间的最短间隔。\n' +
    '• 易混淆页领先差距 — 两个易混淆页面竞争时，一方须比另一方高出多少。\n' +
    '• 页面识别相近容差 — 识别当前是哪一页时，页面得分多接近算「接近」。\n' +
    '• 日志语言 — 日志面板使用的语言（不改变本界面语言）。\n' +
    '• 详细日志 — 在日志中输出更多诊断信息。\n' +
    '• 页面变化时中止当前步骤 — 动作执行中若识别到其它页面，则中止当前动作列表。\n' +
    '• 快捷键 — 供桌面引擎使用；本浏览器标签页不抢占全局键。',
  help_page_match:
    '本页专用的匹配设置。某一项留空则沿用「控制」抽屉里的运行默认。\n' +
    '• 内部编号 — 保存在项目文件中的稳定编号，一般无需改。\n' +
    '• 识别优先级 — 多个页面同时匹配时，数字更大的优先被认定。\n' +
    '• 易混淆页面 — 可与另一个容易认错的页面配对。\n' +
    '• 最低相似度 / 情况相近容差 / 情况领先要求 — 只覆盖本页情况，不影响其它页。\n' +
    '• 情况接近时 — 前两名未满足领先要求时：按优先级选择，或暂不执行（有「默认情况」则走默认）。',
  help_page_default_post:
    '本页默认的后续观察 — 某个情况动作结束后，若该情况自己没有配置后续观察，则使用这里的设置。\n' +
    '这不是匹配参数：它在动作跑完之后才会开始，用于继续盯屏幕上的下一步界面。\n' +
    '• 启用 — 是否打开本页默认后续观察。\n' +
    '• 观察模式 / 观察次数 / 首次观察前等待 — 含义与情况里的「后续观察」相同。\n' +
    '• 编辑后续情况 — 配置本页默认要继续盯住的后续界面。\n' +
    '情况详情里仍可为单个情况单独开启「后续观察」，优先于本页默认。',
  help_page_images:
    '画面特征 — 逻辑名；选中后再单独编辑匹配方式。\n' +
    '匹配方式 = 搜索区域 + 匹配内容；模板库只有可复用像素文件。\n' +
    '从整窗截图：先定搜索区域，再裁切匹配内容。\n' +
    '将其中一个特征设为「用作识别」。',
  help_page_source:
    '参考画布在「匹配方案」从整窗截图新建时自动更新。\n' +
    '不在页面上单独成区；不参与运行。',
  help_page_features:
    '画面特征 — 逻辑名，用于本页识别、情况打分与点击。\n' +
    '此处只「选用 / 取消选用」匹配方案；方案在「匹配方案」区创建与编辑。\n' +
    '流程用到的特征若未选用完备方案，将无法开始。',
  help_page_setups:
    '匹配方案 — 已编好的「在哪找 + 找什么」。\n' +
    '从截图新建：上传整窗 → 定搜索区域 → 裁匹配内容。\n' +
    '或从模板库新建（默认全屏搜索）。然后在画面特征上选用。\n' +
    '方案可闲置，也可被多个特征共用。',
  help_page_artwork:
    '模板库 — 仅可复用的匹配内容文件（不含搜索区域）。\n' +
    '在此上传不会创建特征或方案；编匹配方案时可选用。\n' +
    '删除模板会删除依赖它的方案，并取消相关特征的选用。',
  help_case_basic:
    '当前选中情况的详情：命中后执行其动作。\n' +
    '• 名称 — 情况列表中显示的名称。\n' +
    '• 默认情况 — 其余都未命中时使用；始终排在最下方。\n' +
    '• 识别方式 — 匹配图片、固定相似度（高级），或图片未出现时匹配。\n' +
    '• 画面特征 — 用哪个特征来匹配（开始前须已设置匹配内容）。\n' +
    '• 限定搜索区域（可选） — 覆盖特征默认搜索区域；留空则用特征自带区域，都没有则全屏搜索。\n' +
    '• 动作 — 选中该情况后按顺序执行的步骤（拖 ⋮⋮ 调整顺序）。\n' +
    '在情况列表拖 ⋮⋮ 可调整顺序（「默认情况」始终在最下）。',
  help_case_post:
    '主动作结束后，可继续盯住屏幕上接下来出现的界面。\n' +
    '• 启用后续观察 — 是否为当前情况开启。\n' +
    '• 观察模式 — 观察一次；直到换页；直到默认情况；或固定次数。\n' +
    '  直到换页 — 等到识别为其它页面才结束；后续情况可以不配。' +
    '命中普通后续情况会执行动作并继续等到换页；「默认情况」在等待换页时不会反复执行动作。\n' +
    '  直到默认情况 — 持续观察直到选中「默认情况」；命中普通后续情况会执行动作并继续观察。\n' +
    '• 观察次数 — 模式为「固定次数」时的观察次数。\n' +
    '• 首次观察前等待（秒） — 动作结束后先等待再截第一张。\n' +
    '• 无法识别页面时结束 — 认不出当前页面时结束本次后续观察；关闭则跳过并继续。\n' +
    '• 编辑后续情况 — 配置后续观察阶段要识别的各种界面与动作。',
  help_case_when:
    '可选条件：不满足则本情况不会被选中（即使图片匹配）。\n' +
    '• 左侧 — 变量名（由「设置变量」步骤写入）。\n' +
    '• 右侧 — 要求的取值；留空表示「变量已设置 / 为真」即可。',
  help_case_advanced:
    '多数项目通常无需修改；只有使用子情况或要固定文件编号时才用。\n' +
    '• 内部编号 — 项目文件中的稳定键（改显示名称不会自动改这里）。\n' +
    '• 下级匹配参数 — 仅当本情况带有子情况、正在从中挑选时生效。\n' +
    '  各字段含义见「下级匹配参数」旁的「？」。\n' +
    '• 优先级 — 在情况本身上设置（不在本面板）；分数接近时数字大的优先（可拖列表调整顺序）。',
  help_case_layer:
    '这些参数只影响「本情况已经选中之后，在其子情况之间」如何挑选；' +
    '不会改变本情况与其它同级情况的竞争。\n' +
    '某一项留空则沿用：页面「匹配」覆盖 → 运行默认（控制台里的最低相似度 / 情况相近容差 / 情况领先要求）。\n' +
    '适合：本情况下的子菜单、弹层等，需要比本页其它地方更严或更松的打分时。\n' +
    '\n' +
    '• 内部编号 — 保存在项目文件中的稳定键，一般不用改。\n' +
    '• 最低相似度（0～1） — 子情况的匹配分至少达到此值才算有效候选。' +
    '调高更挑剔（减少误认）；调低更宽松（减少漏认）。\n' +
    '• 情况相近容差 — 子情况里与最高分相差不超过此值的，都算「接近」。' +
    '接近时会结合优先级、以及页面上的「情况接近时」策略再决定。\n' +
    '• 情况领先要求 — 第一名须比第二名至少高出此值。' +
    '领先不够时，可能暂不执行，或按页面「情况接近时」走默认情况等策略。\n' +
    '\n' +
    '若本情况没有子情况（只执行动作），填了这些参数也不会生效，直到添加子情况。',
  help_steps:
    '选中情况（或宏）后按顺序执行的步骤。\n' +
    '• 操作 — 点击、按键、等待、按住按键、宏；高级：设置/清除变量、脚本。\n' +
    '• 点击图 — 本页特征图，用于定位并点击。\n' +
    '• 按键 / 按住 — 要按下的键（及按住时长）。\n' +
    '• 等待（秒） — 暂停时长。\n' +
    '• 宏 — 调用项目中可复用的步骤序列。\n' +
    '• 备注 — 可选说明，不参与执行。\n' +
    '• 设置 / 清除变量 — 供情况「仅当变量条件满足」使用。\n' +
    '• 脚本 — 可选的项目内脚本；脚本参数为可选键值（高级，一般不用）。\n' +
    '拖步骤左侧 ⋮⋮ 可调整执行顺序。',
  help_macros:
    '宏是可复用的点击/按键/等待步骤序列。\n' +
    '• 用「添加宏」新建。\n' +
    '• 在此编辑名称与步骤。\n' +
    '• 在情况动作中选「宏」并选择本宏即可调用。\n' +
    '点击目标可使用项目中任意页面的特征图。',
  help_pairs:
    '易混淆页面指识别当前界面时容易认错的两个页面。\n' +
    '• 页面 A / 页面 B — 配对的两个页面。\n' +
    '• 添加 / 删除 — 创建或删除配对。\n' +
    '当其中一页成为候选时，会仔细比较二者再决定当前页面。\n' +
    '每个页面最多属于一对。',
  help_vars:
    '当「只看画面」不够时再用变量 — 让流程记住跨步骤的信息' +
    '（例如：已经登录、选了困难难度、任务 A 已完成）。\n' +
    '\n' +
    '常见用法：\n' +
    '1）在本页添加变量，并写好开始时的默认值。\n' +
    '2）在某个情况的动作里，用「设置变量 / 清除变量」记下重要变化。\n' +
    '3）在另一个情况里打开「仅当变量条件满足」，让它只在对的时机才执行。\n' +
    '\n' +
    '如果每一步都能单靠图片认出来，可以完全不用本页。\n' +
    '\n' +
    '表格里各列：\n' +
    '• 名称 — 在设置/清除步骤和情况条件里选用的名字。\n' +
    '• 类型 — 是/否、数字或文本，按你怎么用它来选。\n' +
    '• 默认值 — 点「开始」时的初值；每次重新开始都会回到这里。\n' +
    '• 说明 — 给你自己看的备注，可选。\n' +
    '• 引用 — 有多少处用到了这个名字；点击可跳转。\n' +
    '若步骤里用了某个名字但本表没有，会出现警告 — 方便时在此补上即可。',
  sec_runtime: '运行默认',
  sec_runtime_advanced: '更多选项',
  sec_page_match: '匹配参数（通常无需修改）',
  sec_page_images: '画面特征',
  sec_page_features: '画面特征',
  sec_page_setups: '匹配方案',
  sec_page_artwork: '模板库',
  sec_page_source: '参考截图',
  sec_page_default_post: '本页默认后续观察',
  sec_case_basic: '情况详情',
  sec_case_post: '后续观察',
  sec_case_advanced: '更多选项',
  sec_steps: '动作步骤',
  sec_macros: '宏',
  sec_pairs: '易混淆页面',
  sec_vars: '项目变量',
  sec_detect: '本页识别',
  sec_pages: '页面',
  help_pages:
    '页面是项目中可识别的界面。\n' +
    '• 每个页面包含特征图、识别图，以及带动作的情况。\n' +
    '• 可从此列表或左侧栏打开某一页。\n' +
    '• 「易混淆页面」配对用于区分容易认错的两个界面。',
}
