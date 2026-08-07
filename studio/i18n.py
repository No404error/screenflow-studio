from __future__ import annotations

from studio.settings import load_ui_settings, update_ui_settings

# UI language codes
LANG_EN = "en"
LANG_ZH = "zh"

_STRINGS: dict[str, dict[str, str]] = {
    LANG_EN: {
        "app_title": "ScreenFlow — Foreground Vision Automation",
        "menu_file": "&File",
        "menu_language": "&Language",
        "menu_help": "&Help",
        "act_new": "New Project…",
        "act_open": "Open Project Folder…",
        "act_save": "Save Project",
        "act_exit": "Exit",
        "act_about": "About ScreenFlow",
        "menu_recent": "Open &Recent",
        "recent_title": "Recent projects",
        "recent_empty": "(No recent projects)",
        "recent_open": "Open selected",
        "recent_clear": "Clear recently opened",
        "welcome_title": "ScreenFlow",
        "welcome_subtitle": (
            "Create or open a project, then:\n"
            "1) Add a page and upload a recognition image\n"
            "2) Set up cases and actions for each page\n"
            "3) Save and press Start — keep the target app in the foreground"
        ),
        "dlg_new_parent": "Choose parent folder (a project folder will be created inside)",
        "confirm_open_existing": "A project already exists here:\n{path}\n\nOpen it?",
        "err_folder_not_empty": "Folder already exists and is not empty:\n{path}",
        "err_recent_missing": "Project no longer found:\n{path}\nRemoved from recent list.",
        "lang_en": "English",
        "lang_zh": "中文",
        "no_project": "No project open",
        "project_label": "Project: {name}  —  {path}",
        "tree_title": "Project",
        "tree_macros": "Macros",
        "tree_macro_detail": "{n} steps",
        "tree_pages": "Pages",
        "tree_group_count": "{n}",
        "tree_page_pair_hint": "look-alike with “{name}”",
        "tree_col_item": "Item",
        "tree_col_detail": "Detail",
        "tree_no_state": "Default (single action set)",
        "tree_action": "step",
        "tree_actions_node": "Actions",
        "tree_macro_detail_short": "{n} steps",
        "btn_add_page": "Add page",
        "btn_add_macro": "Add macro",
        "btn_del_sel": "Delete",
        "params_group": "Run",
        "param_state_near": "Near-tie tolerance",
        "param_state_margin": "Required lead",
        "param_log_lang": "Log language",
        "param_redecide": "Abort steps when the page changes",
        "param_redecide_hint": "Between steps, stop the current action list if the screen becomes another page",
        "save_reload_hint": "Project saved. Press Stop, then Start, if you changed structure or images that were already loaded.",
        "params_advanced": "More options (rarely needed)",
        "param_threshold": "Min. similarity",
        "param_poll": "Screenshot interval (s)",
        "param_ref_w": "Reference width (scaling)",
        "param_ref_h": "Reference height (scaling)",
        "param_verbose": "Verbose log",
        "param_verbose_hint": "Show more detail in the log panel",
        "param_runner_mode": "Engine process",
        "runner_mode_elevate": "Elevated subprocess (UAC)",
        "runner_mode_inline": "In-process (debug)",
        "btn_apply": "Save run settings",
        "btn_start": "Start",
        "btn_pause": "Pause",
        "btn_resume": "Continue",
        "btn_stop": "Stop",
        "log_label": "Log",
        "tip": (
            "Foreground vision only — no injection, no background input. "
            "Starting a run may request Administrator once for the engine process."
        ),
        "about_title": "About ScreenFlow",
        "about_body": (
            "ScreenFlow helps you automate on-screen tasks by watching "
            "the foreground window and simulating mouse and keyboard input.\n\n"
            "How to use:\n"
            "1. Create or open a project\n"
            "2. Add pages, recognition/click images, cases, and actions\n"
            "3. Save, then press Start — keep the target app in the foreground\n\n"
            "Notes:\n"
            "• Foreground only (no injection, no background control)\n"
            "• Switch UI language under Language\n"
            "• When you press Start, the engine may request Administrator "
            "so clicks and keys reach protected apps"
        ),
        "dlg_new_title": "Choose folder for new project",
        "dlg_new_name": "New project",
        "dlg_new_name_label": "Project name:",
        "dlg_new_name_default": "Untitled Project",
        "dlg_open_title": "Open ScreenFlow project folder",
        "dlg_image": "Choose image",
        "dlg_page_name": "New page",
        "dlg_page_name_label": "Page name:",
        "dlg_macro_name": "New macro",
        "dlg_macro_name_label": "Macro name:",
        "dlg_state_name": "New case",
        "dlg_state_name_label": "Case name:",
        "err_title": "Error",
        "err_open_title": "Failed to open project",
        "err_save_title": "Failed to save",
        "err_page_dup": "A page with this name already exists.",
        "err_macro_dup": "A macro with this name already exists.",
        "err_state_dup": "A case with this name already exists.",
        "err_no_pages": "Add at least one page with a recognition image before starting.",
        "log_opened": "Opened project: {path}",
        "log_saved": "Saved project: {path}",
        "log_params": "Runtime settings applied",
        "log_lang": "Language switched to English",
        "log_dirty": "Project modified (unsaved)",
        "confirm_delete": "Delete “{name}”?",
        "confirm_unsaved": "Save changes to the project files before closing?",
        "editor_empty": "Select a page or macro on the left. Expand a page to browse cases; click a case to edit it.",
        "editor_title_empty": "Editor",
        "editor_title_page": "Page — {name}",
        "editor_title_state": "Case — {page} / {state}",
        "editor_title_actions": "Actions — {page} / {state}",
        "editor_title_macro": "Macro — {name}",
        "editor_title_macros": "Macros",
        "macros_overview_hint": "Reusable click/key/wait sequences. Create with “Add macro”, edit steps here or from the tree, then call from a case action with operation Macro.",
        "macros_overview_empty": "(No macros yet — click “Add macro”)",
        "ed_advanced": "More options",
        "ed_page_name": "Page name",
        "ed_page_id": "Internal ID",
        "ed_page_detect": "Recognition image",
        "ed_page_priority": "Recognition priority",
        "ed_page_pair": "Look-alike page",
        "editor_title_pairs": "Look-alike pages",
        "tree_page_pairs": "Look-alike pages",
        "pairs_hint": "Pair pages that are easy to confuse. When identifying the screen, both are compared carefully before deciding. Each page belongs to at most one pair.",
        "pairs_add": "Add look-alike pair",
        "pairs_del": "Remove look-alike pair",
        "pairs_page_a": "Page A",
        "pairs_page_b": "Page B",
        "pairs_row": "{a}  ↔  {b}",
        "pairs_err_same": "Choose two different pages.",
        "ed_page_hint_no_detect": "This page has no recognition image yet. Upload one to identify the screen.",
        "ed_add_state": "Add case…",
        "ed_edit_default_actions": "Edit default actions…",
        "ed_edit_actions": "Edit actions…",
        "ed_res_add": "Add…",
        "ed_res_del": "Remove",
        "ed_state_name": "Name",
        "ed_state_priority": "Priority",
        "ed_state_detect_asset": "Recognition image",
        "ed_macro_id": "Internal ID",
        "ed_macro_name": "Macro name",
        "asset_panel_title": "Pictures on this page",
        "asset_panel_hint": "Each page has its own recognition and click pictures. Upload here; storage paths are managed for you.",
        "asset_detect": "Recognition pictures",
        "asset_click": "Click pictures",
        "asset_upload": "Upload…",
        "asset_delete": "Delete",
        "asset_pick": "Choose an image…",
        "asset_pick_detect": "Recognition image:",
        "asset_name_title": "Image name",
        "asset_name_label": "Name (optional):",
        "asset_empty_detect": "No recognition images on this page yet. Upload one first.",
        "step_add": "Add step",
        "step_del": "Remove",
        "step_up": "Up",
        "step_down": "Down",
        "step_op": "Operation",
        "step_target": "Target",
        "step_target_click": "Click picture",
        "step_target_key": "Key",
        "step_target_wait": "Wait (seconds)",
        "step_target_hold_key": "Key",
        "step_target_macro": "Macro",
        "step_target_set_var": "Variable (name or name=value)",
        "step_target_clear_var": "Variable name",
        "step_target_script": "Script path",
        "step_hold": "Hold duration (s)",
        "step_reason": "Note",
        "step_op_click": "Click",
        "step_op_key": "Key",
        "step_op_wait": "Wait",
        "step_op_hold_key": "Hold key",
        "step_op_macro": "Macro",
        "step_op_advanced": "── Advanced ──",
        "step_op_set_var": "Set variable",
        "step_op_clear_var": "Clear variable",
        "step_op_script": "Script",
        "step_ph_key": "e.g. space, enter, a",
        "step_ph_hold_key": "e.g. space, shift, f",
        "step_ph_set_var": "name=value  or  name",
        "step_ph_clear_var": "variable name",
        "step_ph_script": "scripts/my_script.py",
        "st_when_var": "Only when variable condition holds",
        "st_when_var_ph": "e.g. flag  or  mode=farm",
        "st_layer_params": "Separate matching for nested cases",
        "st_layer_threshold": "Nested: min. similarity",
        "st_layer_near": "Nested: near-tie tolerance",
        "st_layer_margin": "Nested: required lead",
        "status_idle": "Not running",
        "status_waiting_admin": "Waiting for Administrator permission…",
        "status_running": "Current: {page} / {state}",
        "status_running_unknown": "Current: unrecognized",
        "status_paused": "Paused · last: {page} / {state}",
        "status_paused_unknown": "Paused · last: unrecognized",
        "status_stopped": "Stopped",
        "status_na": "—",
        "err_runner": "Engine runner failed to start.",
        "err_runner_uac": "Administrator permission was denied or the engine runner failed to launch.",
        "wiz_title": "New page",
        "wiz_step_name": "Step 1 — Page name",
        "wiz_step_image": "Step 2 — Recognition image (optional)",
        "wiz_step_done": "Step 3 — Next",
        "wiz_img_hint": "Upload a recognition image now, or skip and add it later.",
        "wiz_skip_img": "Clear / skip",
        "wiz_edit_actions": "Open default actions editor after creating",
        "wiz_back": "Back",
        "wiz_next": "Next",
        "wiz_finish": "Create",
        "wiz_cancel": "Cancel",
        "val_title": "Cannot start",
        "val_warn_title": "Warnings",
        "val_no_pages": "Add at least one page first.",
        "val_no_detect": "Page “{page}” has no recognition image.",
        "val_no_actions": "Page “{page}” / case “{state}” has no actions.",
        "val_click_empty": "Page “{page}” / “{state}” step {step}: click target is empty.",
        "val_click_missing": "Page “{page}” / “{state}” step {step}: click target “{target}” is not in this page’s click images.",
        "val_macro_click_missing": "Macro “{macro}” step {step}: click target “{target}” is not in any page’s click images.",
        "val_continue": "Start anyway",
        "val_abort": "Cancel",

        "tree_states": "Cases",
        "tree_states_detail": "{n} cases",
        "editor_title_states": "Cases — {name}",
        "ed_edit_states": "Edit cases…",
        "st_add_sibling": "Add case",
        "st_add_child": "Add nested case",
        "st_delete": "Delete",
        "st_name": "Name",
        "st_id": "Internal id",
        "st_priority": "Priority number",
        "st_priority_hint": "Usually leave this alone — drag cases up/down instead. Changing the number reorders the list (higher = preferred when scores are close).",
        "st_else": "Other case",
        "st_else_hint": "Used when nothing else matches (always stays at the bottom)",
        "st_else_tag": " · Other",
        "st_score_kind": "Recognition method",
        "st_score_source": "Image source",
        "st_score_key": "Image name",
        "st_roi": "Search region (optional)",
        "st_constant": "Fixed similarity value",
        "st_actions": "Actions",
        "st_post": "Follow-up",
        "st_post_enable": "Enable follow-up",
        "st_post_enable_hint": "After these actions finish, keep checking for follow-up screens",
        "st_post_mode": "Follow-up mode",
        "st_post_frames": "Observation count",
        "st_post_settle": "Wait before first observation (s)",
        "st_post_settle_hint": "After actions finish, wait this long before the first follow-up capture (e.g. 0.8).",
        "st_post_end_unknown": "End when page is unrecognized",
        "st_post_end_unknown_hint": "Off: skip unrecognized screens and continue observing",
        "val_post_empty": "{where}: follow-up has no cases — add at least one (not required for “Until another page”)",
        "val_post_until_case_else": "{where}: “Until another case matches” should include an “other case”",
        "val_post_settle": "{where}: wait before first observation cannot be negative",
        "st_edit_post_tree": "Edit follow-up cases…",
        "st_path": "Location: {path}",
        "st_err_branch": "This case already has actions or follow-up. Clear them before adding nested cases.",
        "st_err_else_child": "An “other case” cannot have nested cases.",
        "st_err_drop_self": "Cannot move a case into one of its own nested cases.",
        "st_err_drop_else_parent": "Cannot put cases under an “other case”.",
        "st_err_drop_leaf": "This case already has actions or follow-up. Clear them before nesting other cases under it.",
        "val_else_dup": "More than one “other case” under {where}",
        "val_branch_actions": "“{node}” under {where} has nested cases, so it cannot have actions",
        "val_branch_post": "“{node}” under {where} has nested cases, so it cannot have follow-up",
        "val_scoreless": "Case “{node}” under {where} needs a recognition image, or mark it as “other case”",
        "val_score_key_empty": "{where}: case “{node}” has no image selected",
        "val_score_missing": "{where}: case “{node}” image “{image}” is not in this page’s {lib}",
        "val_frames_missing": "{where}: “Fixed count” needs an observation count ≥ 1",
        "val_macro_missing": "Page “{page}” / “{state}” step {step}: macro “{macro}” not found",
        "val_script_missing": "Page “{page}” / “{state}” step {step}: script “{script}” not found",
        "st_move_up": "Move up",
        "st_move_down": "Move down",
        "ed_page_threshold": "Min. similarity (this page)",
        "ed_page_near": "Near-tie tolerance (this page)",
        "ed_page_margin": "Required lead (this page)",
        "ed_page_on_close": "When cases are close",
        "on_close_inherit": "Use project default (by priority)",
        "on_close_priority": "Choose by priority",
        "on_close_abstain": "Do not act (use Other case if any)",
        "page_decide_hint_abstain": "This page: when cases are close, do not act{extra}. Change under “Matching”.",
        "page_decide_hint_priority": "This page: when cases are close, choose by priority{extra}. Change under “Matching”.",
        "page_decide_hint_gap": " (required lead < {gap})",
        "ed_page_default_post": "Edit page default follow-up…",
        "st_save_template": "Save case template…",
        "st_template_saved": "Case template saved.",
        "st_load_template": "Load case template…",
        "st_no_templates": "No case templates saved yet.",
        "st_hint_order": "Drag to reorder or nest. Higher in the list wins when scores are close. “Other case” stays at the bottom.",
        "st_col_state": "Case",
        "st_col_detail": "Detail",
        "st_grp_basic": "This case",
        "st_grp_advanced": "More options (id / priority)",
        "st_kind_template": "Match an image",
        "st_kind_constant": "Fixed similarity (advanced)",
        "st_kind_invert": "Match when image is absent",
        "st_src_detect": "Recognition images",
        "st_src_click": "Click images",
        "st_mode_once": "Observe once",
        "st_mode_until_page": "Until another page",
        "st_mode_until_case": "Until another case matches",
        "st_mode_frames": "Fixed count",
        "st_detail_else": "When nothing else matches",
        "st_detail_branch": "{n} nested cases",
        "st_detail_leaf": "{n} actions",
        "st_detail_post": "follow-up",
        "tree_state_detail": "{detail}",
        "tree_state_else": "Other case",
        "tree_state_branch": "{n} nested",
        "tree_state_leaf": "actions",
        "sec_page_match": "Matching (rarely needed)",
        "sec_case_basic": "This case",
        "sec_case_post": "Follow-up",
        "sec_steps": "Actions",
        "help_missing": "(No help text)",
        "help_button_a11y": "Section help",
        "help_dialog_title": "Section help",
        "help_runtime": (
            "Project-wide defaults for how often to capture the screen and how strict matching is.\n"
            "• Min. similarity — score must reach this (0–1) to count as a match; raise to reduce false matches, lower if matches are missed.\n"
            "• Screenshot interval (s) — time between captures; shorter reacts faster but uses more CPU.\n"
            "Open “More options” for near-tie rules, reference resolution, and log settings."
        ),
        "help_runtime_advanced": (
            "Usually leave these alone; they affect scaling and close-score decisions.\n"
            "• Reference width / height — resolution your screenshots were taken at; used to scale matches.\n"
            "• Near-tie tolerance — candidates within this distance of the best score are treated as “close”.\n"
            "• Required lead — the winner must beat the runner-up by at least this much; if not, page “When cases are close” applies (choose by priority vs do not act).\n"
            "• Log language — language of messages in the log panel.\n"
            "• Verbose log — extra diagnostic lines in the log.\n"
            "• Abort steps when the page changes — stop the current action list mid-way if the recognized page switches.\n"
            "• Engine process — Elevated subprocess requests Administrator on Start; In-process runs inside Studio (debug / CI)."
        ),
        "help_page_match": (
            "Per-page matching overrides. Leave a field empty to inherit the project default from Run.\n"
            "• Internal ID — stable key stored in project files (usually leave as-is).\n"
            "• Recognition priority — when several pages match at once, higher priority wins.\n"
            "• Look-alike page — optional pairing with another page that is easy to confuse; both are compared carefully.\n"
            "• Min. similarity — score must reach this (0–1) for a case on this page to count as a match; raise to reduce false matches, lower if matches are missed. Overrides Run for this page only.\n"
            "• Near-tie tolerance — case candidates within this distance of the best score are treated as “close”. Overrides Run for this page only.\n"
            "• Required lead — the winning case must beat the runner-up by at least this much; if not, “When cases are close” applies. Overrides Run for this page only.\n"
            "• When cases are close — if the top two case scores fail Required lead: Choose by priority, or Do not act (route to Other case if present).\n"
            "• Edit page default follow-up — default follow-up used when a case has none of its own."
        ),
        "help_page_images": (
            "Images that belong only to this page.\n"
            "• Recognition pictures — identify this screen and score cases that match an image.\n"
            "• Click pictures — locate where to click in action steps.\n"
            "• Upload / Delete — add or remove files; storage is handled automatically.\n"
            "After uploading, select them in cases and click steps."
        ),
        "help_case_basic": (
            "One case on this page: when it wins, its actions run.\n"
            "• Name — label shown in the list and tree.\n"
            "• Other case — used when no other case matches; always stays at the bottom.\n"
            "• Recognition method — Match an image (compare a picture), Fixed similarity (advanced; use a constant score), or Match when image is absent.\n"
            "• Image source / Image name — which library (recognition vs click) and which picture to use.\n"
            "• Search region (optional) — left,right,top,bottom as 0–1 of the window (e.g. 0.75,1,0.75,1 = bottom-right); leave empty to search the whole window.\n"
            "• Fixed similarity value — only for Fixed similarity method.\n"
            "• Actions — ordered steps when this case is selected."
        ),
        "help_case_post": (
            "After the main actions finish, optionally keep checking the screen for follow-up UI.\n"
            "• Enable follow-up — turn follow-up on or off for this case.\n"
            "• Follow-up mode — Observe once; Until another page; Until another case matches; or Fixed count.\n"
            "  Until another page — wait until the detected page changes; the follow-up case tree may be empty (optional actions while waiting).\n"
            "  Until another case matches — keep observing until the follow-up tree picks the other-case (ELSE) branch.\n"
            "• Observation count — how many captures when mode is Fixed count.\n"
            "• Wait before first observation (s) — pause after actions so the UI can appear (e.g. 0.5).\n"
            "• End when page is unrecognized — stop follow-up if no page can be identified; Off skips those frames and continues.\n"
            "• Edit follow-up cases — the case tree used only during follow-up."
        ),
        "help_case_advanced": (
            "Internal details; safe to ignore for most projects.\n"
            "• Internal id — stable key stored in project files.\n"
            "• Priority number — when scores are close, higher wins (dragging the list is usually enough; changing the number reorders).\n"
            "• Only when variable condition holds — consider this case only if a flag/value was set by an earlier step (e.g. flag or mode=farm).\n"
            "• Separate matching for nested cases — optional overrides that apply only when scoring children under this branch: Min. similarity (score floor), Near-tie tolerance (how close counts as a near tie), Required lead (how far the winner must beat #2)."
        ),
        "help_steps": (
            "Ordered steps when this case (or macro) is chosen.\n"
            "• Operation — Click, Key, Wait, Hold key, Macro; Advanced: Set/Clear variable, Script.\n"
            "• Click picture — image from this page’s click library to locate and click.\n"
            "• Key — keyboard key to press (or to hold for Hold key).\n"
            "• Wait (seconds) — pause duration.\n"
            "• Macro — run another reusable step list from the project.\n"
            "• Hold duration (s) — how long to hold the key (Hold key only).\n"
            "• Note — optional comment (not executed).\n"
            "• Set / Clear variable — flags used by “Only when variable condition holds” on cases.\n"
            "• Script path — optional project-relative Python script."
        ),
        "help_macros": (
            "A macro is a reusable sequence of click/key/wait steps.\n"
            "• Create with “Add macro” under the tree.\n"
            "• Edit the name and steps in this editor.\n"
            "• From a page case action, choose operation Macro and select this macro.\n"
            "Click targets can use click pictures from any page in the project."
        ),
        "help_pairs": (
            "Look-alike pages are screens that are easy to confuse when identifying the current page.\n"
            "• Page A / Page B — the two pages in the pair.\n"
            "• Add look-alike pair / Remove look-alike pair — create or delete a pairing.\n"
            "When either page is a top candidate, both are compared carefully before deciding.\n"
            "Each page belongs to at most one pair."
        ),

    },

    LANG_ZH: {
        "app_title": "ScreenFlow — 前台视觉自动化",
        "menu_file": "文件(&F)",
        "menu_language": "语言(&L)",
        "menu_help": "帮助(&H)",
        "act_new": "新建项目…",
        "act_open": "打开项目文件夹…",
        "act_save": "保存项目",
        "act_exit": "退出",
        "act_about": "关于 ScreenFlow",
        "menu_recent": "打开最近的项目(&R)",
        "recent_title": "最近的项目",
        "recent_empty": "（暂无最近项目）",
        "recent_open": "打开所选",
        "recent_clear": "清除最近打开的记录",
        "welcome_title": "ScreenFlow",
        "welcome_subtitle": (
            "新建或打开项目后：\n"
            "1）添加页面并上传识别图\n"
            "2）为每个页面配置情况与动作\n"
            "3）保存并开始 — 保持目标程序在前台"
        ),
        "dlg_new_parent": "选择父文件夹（将在其中创建项目文件夹）",
        "confirm_open_existing": "此处已有项目：\n{path}\n\n要打开它吗？",
        "err_folder_not_empty": "文件夹已存在且非空：\n{path}",
        "err_recent_missing": "找不到该项目：\n{path}\n已从最近列表移除。",
        "lang_en": "English",
        "lang_zh": "中文",
        "no_project": "未打开项目",
        "project_label": "项目：{name}  —  {path}",
        "tree_title": "项目",
        "tree_macros": "宏",
        "tree_macro_detail": "{n} 步",
        "tree_pages": "页面",
        "tree_group_count": "{n}",
        "tree_page_pair_hint": "与「{name}」易混淆",
        "tree_col_item": "项",
        "tree_col_detail": "详情",
        "tree_no_state": "默认（单套动作）",
        "tree_action": "步骤",
        "tree_actions_node": "动作",
        "tree_macro_detail_short": "{n} 步",
        "btn_add_page": "添加页面",
        "btn_add_macro": "添加宏",
        "btn_del_sel": "删除",
        "params_group": "运行",
        "param_state_near": "相近容差",
        "param_state_margin": "领先要求",
        "param_log_lang": "日志语言",
        "param_redecide": "页面变化时中止当前步骤",
        "param_redecide_hint": "步骤之间若识别到其它页面，则中止当前动作列表",
        "save_reload_hint": "项目已保存。若改过结构或图片，请先点「停止」再「开始」才会用上新内容。",
        "params_advanced": "更多选项（通常无需修改）",
        "param_threshold": "最低相似度",
        "param_poll": "截屏间隔（秒）",
        "param_ref_w": "参考宽度（缩放）",
        "param_ref_h": "参考高度（缩放）",
        "param_verbose": "详细日志",
        "param_verbose_hint": "在日志面板输出更多细节",
        "param_runner_mode": "引擎进程方式",
        "runner_mode_elevate": "提权子进程（UAC）",
        "runner_mode_inline": "本进程（调试）",
        "btn_apply": "保存运行设置",
        "btn_start": "开始",
        "btn_pause": "暂停",
        "btn_resume": "继续",
        "btn_stop": "停止",
        "log_label": "日志",
        "tip": (
            "仅前台视觉识别与键鼠模拟 — 不注入、不后台操作。"
            "开始运行时，引擎进程可能会申请一次管理员权限。"
        ),
        "about_title": "关于 ScreenFlow",
        "about_body": (
            "ScreenFlow 通过识别前台画面、模拟鼠标和键盘，"
            "帮你自动完成屏幕上的重复操作。\n\n"
            "怎么用：\n"
            "1. 新建或打开一个项目\n"
            "2. 添加页面、识别图/点击图、情况与动作\n"
            "3. 保存后点击「开始」，并保持目标程序在前台\n\n"
            "说明：\n"
            "• 仅支持前台操作（不注入、不后台控制）\n"
            "• 可在「语言」菜单切换中英文界面\n"
            "• 点击「开始」时，引擎可能会申请管理员权限，以便控制受保护的目标程序"
        ),
        "dlg_new_title": "选择新建项目所用文件夹",
        "dlg_new_name": "新建项目",
        "dlg_new_name_label": "项目名称：",
        "dlg_new_name_default": "未命名项目",
        "dlg_open_title": "打开 ScreenFlow 项目文件夹",
        "dlg_image": "选择图片",
        "dlg_page_name": "新建页面",
        "dlg_page_name_label": "页面名称：",
        "dlg_macro_name": "新建宏",
        "dlg_macro_name_label": "宏名称：",
        "dlg_state_name": "新建情况",
        "dlg_state_name_label": "情况名称：",
        "err_title": "错误",
        "err_open_title": "无法打开项目",
        "err_save_title": "保存失败",
        "err_page_dup": "已存在相同名称的页面。",
        "err_macro_dup": "已存在相同名称的宏。",
        "err_state_dup": "已存在相同名称的情况。",
        "err_no_pages": "请先添加至少一个带识别图的页面再开始。",
        "log_opened": "已打开项目：{path}",
        "log_saved": "已保存项目：{path}",
        "log_params": "已应用运行设置",
        "log_lang": "界面语言已切换为中文",
        "log_dirty": "项目已修改（未保存）",
        "confirm_delete": "确定删除「{name}」？",
        "confirm_unsaved": "关闭前是否保存到项目文件？",
        "editor_empty": "在左侧选择页面或宏。点开页面可浏览全部情况；点击某个情况即可在中间编辑。",
        "editor_title_empty": "编辑器",
        "editor_title_page": "页面 — {name}",
        "editor_title_state": "情况 — {page} / {state}",
        "editor_title_actions": "动作 — {page} / {state}",
        "editor_title_macro": "宏 — {name}",
        "editor_title_macros": "宏",
        "macros_overview_hint": "可复用的点击/按键/等待序列。用树下方「添加宏」新建，在此或左侧树中编辑步骤；情况动作中选操作「宏」即可调用。",
        "macros_overview_empty": "（还没有宏 — 请点「添加宏」）",
        "ed_advanced": "更多选项",
        "ed_page_name": "页面名称",
        "ed_page_id": "内部 ID",
        "ed_page_detect": "识别图",
        "ed_page_priority": "识别优先级",
        "ed_page_pair": "易混淆页面",
        "editor_title_pairs": "易混淆页面",
        "tree_page_pairs": "易混淆页面",
        "pairs_hint": "将容易认错的页面配成一对。识别当前界面时会仔细比较二者再决定。每个页面最多属于一对。",
        "pairs_add": "添加易混淆对",
        "pairs_del": "删除易混淆对",
        "pairs_page_a": "页面 A",
        "pairs_page_b": "页面 B",
        "pairs_row": "{a}  ↔  {b}",
        "pairs_err_same": "请选择两个不同的页面。",
        "ed_page_hint_no_detect": "该页还没有识别图。请先上传，以便识别当前界面。",
        "ed_add_state": "添加情况…",
        "ed_edit_default_actions": "编辑默认动作…",
        "ed_edit_actions": "编辑动作…",
        "ed_res_add": "添加…",
        "ed_res_del": "移除",
        "ed_state_name": "名称",
        "ed_state_priority": "优先级",
        "ed_state_detect_asset": "识别图",
        "ed_macro_id": "内部 ID",
        "ed_macro_name": "宏名称",
        "asset_panel_title": "本页图片",
        "asset_panel_hint": "每个页面有自己的识别图和点击图。在此上传即可，存放位置由程序管理。",
        "asset_detect": "识别图",
        "asset_click": "点击图",
        "asset_upload": "上传…",
        "asset_delete": "删除",
        "asset_pick": "选择图片…",
        "asset_pick_detect": "识别图：",
        "asset_name_title": "图片名称",
        "asset_name_label": "名称（可选）：",
        "asset_empty_detect": "该页还没有识别图，请先上传。",
        "step_add": "添加步骤",
        "step_del": "删除",
        "step_up": "上移",
        "step_down": "下移",
        "step_op": "操作",
        "step_target": "目标",
        "step_target_click": "点击图",
        "step_target_key": "按键",
        "step_target_wait": "等待（秒）",
        "step_target_hold_key": "按键",
        "step_target_macro": "宏",
        "step_target_set_var": "变量（名称 或 名称=值）",
        "step_target_clear_var": "变量名",
        "step_target_script": "脚本路径",
        "step_hold": "按住时长（秒）",
        "step_reason": "备注",
        "step_op_click": "点击",
        "step_op_key": "按键",
        "step_op_wait": "等待",
        "step_op_hold_key": "按住按键",
        "step_op_macro": "宏",
        "step_op_advanced": "── 高级 ──",
        "step_op_set_var": "设置变量",
        "step_op_clear_var": "清除变量",
        "step_op_script": "脚本",
        "step_ph_key": "如 space、enter、a",
        "step_ph_hold_key": "如 space、shift、f",
        "step_ph_set_var": "名称=值  或  名称",
        "step_ph_clear_var": "变量名",
        "step_ph_script": "scripts/my_script.py",
        "st_when_var": "仅当变量条件满足",
        "st_when_var_ph": "例如 flag  或  mode=farm",
        "st_layer_params": "为下级情况单独设置匹配参数",
        "st_layer_threshold": "下级：最低相似度",
        "st_layer_near": "下级：相近容差",
        "st_layer_margin": "下级：领先要求",
        "status_idle": "未运行",
        "status_waiting_admin": "正在等待管理员权限…",
        "status_running": "当前：{page} / {state}",
        "status_running_unknown": "当前：未识别",
        "status_paused": "暂停 · 最后：{page} / {state}",
        "status_paused_unknown": "暂停 · 最后：未识别",
        "status_stopped": "已停止",
        "status_na": "—",
        "err_runner": "引擎运行进程启动失败。",
        "err_runner_uac": "未获得管理员权限，或引擎运行进程启动失败。",
        "wiz_title": "新建页面",
        "wiz_step_name": "步骤 1 — 页面名称",
        "wiz_step_image": "步骤 2 — 识别图（可跳过）",
        "wiz_step_done": "步骤 3 — 接下来",
        "wiz_img_hint": "现在上传识别图，或跳过稍后再加。",
        "wiz_skip_img": "清除 / 跳过",
        "wiz_edit_actions": "创建后打开默认动作编辑",
        "wiz_back": "上一步",
        "wiz_next": "下一步",
        "wiz_finish": "创建",
        "wiz_cancel": "取消",
        "val_title": "无法开始",
        "val_warn_title": "警告",
        "val_no_pages": "请先添加至少一个页面。",
        "val_no_detect": "页面「{page}」没有识别图。",
        "val_no_actions": "页面「{page}」/ 情况「{state}」没有动作。",
        "val_click_empty": "页面「{page}」/「{state}」第 {step} 步：点击目标为空。",
        "val_click_missing": "页面「{page}」/「{state}」第 {step} 步：点击目标「{target}」不在该页点击图中。",
        "val_macro_click_missing": "宏「{macro}」第 {step} 步：点击目标「{target}」不在任何页面的点击图中。",
        "val_continue": "仍要开始",
        "val_abort": "取消",

        "tree_states": "情况",
        "tree_states_detail": "{n} 个情况",
        "editor_title_states": "情况 — {name}",
        "ed_edit_states": "编辑情况…",
        "st_add_sibling": "添加情况",
        "st_add_child": "添加下级情况",
        "st_delete": "删除",
        "st_name": "名称",
        "st_id": "内部编号",
        "st_priority": "优先级数字",
        "st_priority_hint": "通常无需修改——把情况拖到上面/下面即可。改数字会按大小重排列表（数字越大，分数接近时越优先）。",
        "st_else": "其它情况",
        "st_else_hint": "其它都未命中时走这里（始终排在最下方）",
        "st_else_tag": " · 其它",
        "st_score_kind": "识别方式",
        "st_score_source": "图片来源",
        "st_score_key": "图片名称",
        "st_roi": "限定搜索区域（可选）",
        "st_constant": "固定相似度",
        "st_actions": "动作",
        "st_post": "后续观察",
        "st_post_enable": "启用后续观察",
        "st_post_enable_hint": "本情况动作结束后，继续检测后续界面",
        "st_post_mode": "观察模式",
        "st_post_frames": "观察次数",
        "st_post_settle": "首次观察前等待（秒）",
        "st_post_settle_hint": "主动作结束后，等待这么久再进行第一次后续截屏（例如 0.8）。",
        "st_post_end_unknown": "无法识别页面时结束",
        "st_post_end_unknown_hint": "关闭：跳过无法识别的画面并继续观察",
        "val_post_empty": "「{where}」：后续观察没有情况，请至少添加一个（「直到命中其他页面」可不配情况）",
        "val_post_until_case_else": "「{where}」：「直到命中其它情况」建议包含一条「其它情况」",
        "val_post_settle": "「{where}」：首次观察前等待不能为负数",
        "st_edit_post_tree": "编辑后续情况…",
        "st_path": "当前位置：{path}",
        "st_err_branch": "该情况已有动作或「后续观察」，请先清空再添加下级情况。",
        "st_err_else_child": "「其它情况」下不能再挂下级情况。",
        "st_err_drop_self": "不能把情况拖进自己的下级里。",
        "st_err_drop_else_parent": "不能把情况挂到「其它情况」下面。",
        "st_err_drop_leaf": "该情况已有动作或「后续观察」，请先清空再把其它情况拖到它下面。",
        "val_else_dup": "「{where}」下有多条「其它情况」",
        "val_branch_actions": "「{node}」（{where}）含有下级情况，不能再挂动作",
        "val_branch_post": "「{node}」（{where}）含有下级情况，不能再挂「后续观察」",
        "val_scoreless": "「{where}」下的情况「{node}」需要识别图，或勾选「其它情况」",
        "val_score_key_empty": "「{where}」：情况「{node}」未选择图片",
        "val_score_missing": "「{where}」：情况「{node}」的图片「{image}」不在本页「{lib}」中",
        "val_frames_missing": "{where}：「固定次数」需要观察次数 ≥ 1",
        "val_macro_missing": "页面「{page}」/「{state}」第 {step} 步：找不到宏「{macro}」",
        "val_script_missing": "页面「{page}」/「{state}」第 {step} 步：找不到脚本「{script}」",
        "st_move_up": "上移",
        "st_move_down": "下移",
        "ed_page_threshold": "最低相似度（本页）",
        "ed_page_near": "相近容差（本页）",
        "ed_page_margin": "领先要求（本页）",
        "ed_page_on_close": "情况接近时",
        "on_close_inherit": "沿用项目默认（按优先级）",
        "on_close_priority": "按优先级选择",
        "on_close_abstain": "暂不执行（有「其它情况」则走其它）",
        "page_decide_hint_abstain": "本页：情况接近时暂不执行{extra}。可在「匹配参数」中修改。",
        "page_decide_hint_priority": "本页：情况接近时按优先级选择{extra}。可在「匹配参数」中修改。",
        "page_decide_hint_gap": "（领先要求 < {gap}）",
        "ed_page_default_post": "编辑本页默认后续观察…",
        "st_save_template": "保存情况模板…",
        "st_template_saved": "情况模板已保存。",
        "st_load_template": "加载情况模板…",
        "st_no_templates": "还没有保存的情况模板。",
        "st_hint_order": "拖拽可调整顺序或嵌套。同一组越靠上，分数接近时越优先。「其它情况」固定在最下方。",
        "st_col_state": "情况",
        "st_col_detail": "说明",
        "st_grp_basic": "当前情况",
        "st_grp_advanced": "更多选项（编号 / 优先级）",
        "st_kind_template": "匹配图片",
        "st_kind_constant": "固定相似度（高级）",
        "st_kind_invert": "图片未出现时匹配",
        "st_src_detect": "识别图",
        "st_src_click": "点击图",
        "st_mode_once": "只观察一次",
        "st_mode_until_page": "直到命中其他页面",
        "st_mode_until_case": "直到命中其它情况",
        "st_mode_frames": "固定次数",
        "st_detail_else": "其它未命中时",
        "st_detail_branch": "{n} 个下级情况",
        "st_detail_leaf": "{n} 个动作",
        "st_detail_post": "后续观察",
        "tree_state_detail": "{detail}",
        "tree_state_else": "其它情况",
        "tree_state_branch": "{n} 个下级",
        "tree_state_leaf": "有动作",
        "sec_page_match": "匹配参数（通常无需修改）",
        "sec_case_basic": "本情况",
        "sec_case_post": "后续观察",
        "sec_steps": "动作步骤",
        "help_missing": "（暂无说明）",
        "help_button_a11y": "本区说明",
        "help_dialog_title": "本区说明",
        "help_runtime": (
            "项目级默认：多久截一次屏，以及匹配要多严格。\n"
            "• 最低相似度 — 达到该值（0～1）才算匹配；调高可减少误认，调低可减少漏认。\n"
            "• 截屏间隔（秒） — 两次截屏之间的等待；越短反应越快，也更占资源。\n"
            "「更多选项」中可设置相近判定、参考分辨率与日志。"
        ),
        "help_runtime_advanced": (
            "通常无需修改；影响缩放与分数接近时的取舍。\n"
            "• 参考宽度 / 高度 — 截图时的参考分辨率，用于缩放对齐。\n"
            "• 相近容差 — 与最高分相差在此范围内的候选项视为「接近」。\n"
            "• 领先要求 — 第一名须比第二名至少高出该值；否则由页面「情况接近时」决定：按优先级选择，或暂不执行。\n"
            "• 日志语言 — 日志面板使用的语言。\n"
            "• 详细日志 — 在日志中输出更多诊断信息。\n"
            "• 页面变化时中止当前步骤 — 动作执行中若识别到其它页面，则中止当前动作列表。\n"
            "• 引擎进程方式 —「提权子进程」在开始时申请管理员；「本进程」在 Studio 内运行（调试/测试用）。"
        ),
        "help_page_match": (
            "本页专用的匹配设置。某一项留空则沿用右侧「运行」里的项目默认值。\n"
            "• 内部 ID — 保存在项目文件中的稳定编号，一般无需改。\n"
            "• 识别优先级 — 多个页面同时匹配时，数字更大的优先被认定。\n"
            "• 易混淆页面 — 可与另一个容易认错的页面配对；出现候选时会仔细比较二者。\n"
            "• 最低相似度 — 本页情况得分须达到该值（0～1）才算匹配；调高减少误认，调低减少漏认。在此填写后只覆盖本页，不影响其它页。\n"
            "• 相近容差 — 与最高分相差在此范围内的情况视为「接近」。在此填写后只覆盖本页。\n"
            "• 领先要求 — 第一名情况须比第二名至少高出该值；否则由下方「情况接近时」决定怎么处理。在此填写后只覆盖本页。\n"
            "• 情况接近时 — 前两名未满足「领先要求」时：按优先级选择，或暂不执行（有「其它情况」则走其它）。\n"
            "• 编辑本页默认后续观察 — 情况未单独配置后续观察时使用的默认项。"
        ),
        "help_page_images": (
            "只属于本页的图片。\n"
            "• 识别图 — 用于判断当前是否为本界面，以及情况中的「匹配图片」。\n"
            "• 点击图 — 用于动作步骤中定位点击位置。\n"
            "• 上传 / 删除 — 增删文件；存放位置由程序管理。\n"
            "上传后，在情况和点击步骤中选用。"
        ),
        "help_case_basic": (
            "本页上的一种情况：命中后执行其动作。\n"
            "• 名称 — 列表与导航树中显示的名称。\n"
            "• 其它情况 — 其它情况都未命中时使用；始终排在最下方。\n"
            "• 识别方式 — 匹配图片（用图片比对）、固定相似度（高级；使用恒定分数）、或图片未出现时匹配。\n"
            "• 图片来源 / 图片名称 — 使用识别图还是点击图，以及具体图片。\n"
            "• 限定搜索区域（可选） — 左,右,上,下，用 0～1 表示相对窗口（如 0.75,1,0.75,1 为右下角）；留空则搜索整窗。\n"
            "• 固定相似度 — 仅在识别方式为「固定相似度」时使用。\n"
            "• 动作 — 选中本情况后按顺序执行的步骤。"
        ),
        "help_case_post": (
            "主动作结束后，可继续检测后续界面。\n"
            "• 启用后续观察 — 是否为本情况开启后续观察。\n"
            "• 观察模式 — 只观察一次；直到命中其他页面；直到命中其它情况；或固定次数。\n"
            "  直到命中其他页面 — 等到定到别的页面才结束；后续情况树可为空（仅等换页；需要等待期间动作时再配情况）。\n"
            "  直到命中其它情况 — 持续观察，直到后续情况树走到「其它情况」分支才结束。\n"
            "• 观察次数 — 模式为「固定次数」时的截屏次数。\n"
            "• 首次观察前等待（秒） — 动作结束后先等待再截第一张（如 0.5）。\n"
            "• 无法识别页面时结束 — 定不了页时结束本次后续观察；关闭则跳过并继续。\n"
            "• 编辑后续情况 — 仅在后续观察阶段使用的情况树。"
        ),
        "help_case_advanced": (
            "内部细节，多数项目通常无需修改。\n"
            "• 内部编号 — 保存在项目文件中的稳定 id。\n"
            "• 优先级数字 — 分数接近时数字大的优先（一般拖列表即可；改数字会重排）。\n"
            "• 仅当变量条件满足 — 仅当前面步骤设置过相应标记/取值时才考虑本情况（如 flag 或 mode=farm）。\n"
            "• 为下级情况单独设置匹配参数 — 仅在给本分支下级打分时生效的可选覆盖：最低相似度（达到才算匹配）、相近容差（与最高分差多少算接近）、领先要求（第一名须比第二名高出多少）。"
        ),
        "help_steps": (
            "选中情况（或宏）后按顺序执行的步骤。\n"
            "• 操作 — 点击、按键、等待、按住按键、宏；高级：设置/清除变量、脚本。\n"
            "• 点击图 — 本页点击图库中的图片，用于定位并点击。\n"
            "• 按键 — 要按下的键（「按住按键」时为按住的键）。\n"
            "• 等待（秒） — 暂停时长。\n"
            "• 宏 — 调用项目中可复用的步骤序列。\n"
            "• 按住时长（秒） — 「按住按键」时按住多久。\n"
            "• 备注 — 可选说明，不参与执行。\n"
            "• 设置 / 清除变量 — 供情况「仅当变量条件满足」使用的标记。\n"
            "• 脚本路径 — 可选的项目内 Python 脚本。"
        ),
        "help_macros": (
            "宏是可复用的点击/按键/等待步骤序列。\n"
            "• 用树下方「添加宏」新建。\n"
            "• 在此编辑名称与步骤。\n"
            "• 在页面情况的动作中选操作「宏」并选择本宏即可调用。\n"
            "点击目标可使用项目中任意页面的点击图。"
        ),
        "help_pairs": (
            "易混淆页面指识别当前界面时容易认错的两个页面。\n"
            "• 页面 A / 页面 B — 配对的两个页面。\n"
            "• 添加易混淆对 / 删除易混淆对 — 创建或删除配对。\n"
            "当其中一页成为候选时，会仔细比较二者再决定当前页面。\n"
            "每个页面最多属于一对。"
        ),

    },
}


def load_saved_lang() -> str:
    data = load_ui_settings()
    lang = str(data.get("lang", ""))
    if lang in _STRINGS:
        return lang
    try:
        import locale

        loc = (locale.getdefaultlocale()[0] or "").lower()
        if loc.startswith("zh"):
            return LANG_ZH
    except Exception:
        pass
    return LANG_EN


def save_lang(lang: str) -> None:
    update_ui_settings(lang=lang)


class I18n:
    def __init__(self, lang: str | None = None) -> None:
        self.lang = lang or load_saved_lang()
        if self.lang not in _STRINGS:
            self.lang = LANG_EN

    def set_lang(self, lang: str) -> None:
        if lang not in _STRINGS:
            return
        self.lang = lang
        save_lang(lang)

    def t(self, key: str, **kwargs: object) -> str:
        text = _STRINGS.get(self.lang, _STRINGS[LANG_EN]).get(key)
        if text is None:
            text = _STRINGS[LANG_EN].get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text
