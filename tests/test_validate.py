from pathlib import Path
import tempfile

from screenflow.models import (
    ActionStep,
    MacroDef,
    PageDef,
    PostListen,
    Project,
    RuntimeConfig,
    ScoreSpec,
    StateNode,
)
from screenflow.validate import validate_for_start, validate_project_structure
from studio.i18n import I18n


def _proj(root: Path, pages: dict[str, PageDef], macros=None) -> Project:
    (root / "pages").mkdir(parents=True, exist_ok=True)
    return Project(
        name="t",
        root=root,
        runtime=RuntimeConfig(),
        pages=pages,
        detect_files={},
        click_files={},
        macros=macros or {},
    )


def test_scoreless_non_else_is_error():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        page = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            state_tree=[
                StateNode(id="a", name="A", score=ScoreSpec(key="main")),
                StateNode(id="b", name="B"),  # no score, not else
            ],
        )
        (root / "pages" / "p" / "detect").mkdir(parents=True)
        (root / "pages" / "p" / "detect" / "main.png").write_bytes(b"x")
        issues = validate_project_structure(_proj(root, {"p": page}), I18n().t)
        assert any(i.level == "error" and "B" in i.text for i in issues)


def test_frames_mode_requires_count():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        page = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            state_tree=[
                StateNode(
                    id="a",
                    name="A",
                    is_else=True,
                    actions=[],
                    post=PostListen(mode="frames", frames=None, tree=[]),
                )
            ],
        )
        issues = validate_project_structure(_proj(root, {"p": page}), I18n().t)
        assert any(
            i.level == "error"
            and (
                "count" in i.text.lower()
                or "观察" in i.text
                or "固定" in i.text
                or "look" in i.text.lower()
                or "再看" in i.text
                or "frame" in i.text.lower()
            )
            for i in issues
        )


def test_missing_macro_and_script_warn():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "pages" / "p" / "detect").mkdir(parents=True)
        (root / "pages" / "p" / "detect" / "main.png").write_bytes(b"x")
        page = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            state_tree=[
                StateNode(
                    id="a",
                    name="A",
                    is_else=True,
                    actions=[
                        ActionStep("macro", "nope"),
                        ActionStep("script", "scripts/missing.py"),
                    ],
                )
            ],
        )
        issues = validate_for_start(_proj(root, {"p": page}), I18n().t)
        warns = [i for i in issues if i.level == "warning"]
        assert any("nope" in i.text or "macro" in i.text.lower() or "宏" in i.text for i in warns)
        assert any("missing.py" in i.text or "script" in i.text.lower() or "脚本" in i.text for i in warns)


def test_macro_click_missing_is_warning_not_error():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        (root / "pages" / "p" / "detect").mkdir(parents=True)
        (root / "pages" / "p" / "click").mkdir(parents=True)
        (root / "pages" / "p" / "detect" / "main.png").write_bytes(b"x")
        (root / "pages" / "p" / "click" / "ok.png").write_bytes(b"x")
        page = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            click_map={"ok": "pages/p/click/ok.png"},
            state_tree=[StateNode(id="DEFAULT", is_else=True, actions=[])],
        )
        macros = {
            "m": MacroDef(
                id="m",
                name="M",
                steps=[
                    ActionStep("click", "ok"),
                    ActionStep("click", "ghost"),
                ],
            )
        }
        issues = validate_for_start(_proj(root, {"p": page}, macros=macros), I18n().t)
        ghost = [i for i in issues if "ghost" in i.text]
        assert ghost and all(i.level == "warning" for i in ghost)
        assert not any(i.level == "error" and "ghost" in i.text for i in issues)
        assert not any(i.level == "error" and "ok" in i.text for i in issues)


def test_else_sole_ok():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        page = PageDef(
            page_id="p",
            detect_relpath="x.png",
            state_tree=[StateNode(id="DEFAULT", is_else=True, actions=[])],
        )
        issues = validate_project_structure(_proj(root, {"p": page}), I18n().t)
        assert not [i for i in issues if i.level == "error"]


def test_score_key_must_exist_in_page_library():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        detect = root / "pages" / "p" / "detect"
        detect.mkdir(parents=True)
        (detect / "main.png").write_bytes(b"x")
        page = PageDef(
            page_id="p",
            detect_relpath="pages/p/detect/main.png",
            state_tree=[
                StateNode(
                    id="a",
                    name="A",
                    score=ScoreSpec(key="missing_img", source="detect"),
                    actions=[ActionStep("wait", 0.1)],
                ),
                StateNode(id="DEFAULT", is_else=True, actions=[]),
            ],
        )
        issues = validate_project_structure(_proj(root, {"p": page}), I18n().t)
        errs = [i for i in issues if i.level == "error"]
        assert any("missing_img" in i.text for i in errs)
