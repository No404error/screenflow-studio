from pathlib import Path

from screenflow.models import PageDef, Project, RuntimeConfig
from screenflow.project import (
    clear_pairs_involving,
    list_page_pairs,
    set_page_pair,
)


def _proj(*ids: str) -> Project:
    pages = {
        i: PageDef(page_id=i, name=i, detect_relpath=f"{i}.png") for i in ids
    }
    return Project(
        name="t",
        root=Path("."),
        runtime=RuntimeConfig(),
        pages=pages,
        detect_files={},
        click_files={},
    )


def test_set_page_pair_bidirectional():
    p = _proj("cultivate", "forge", "main")
    set_page_pair(p, "cultivate", "forge")
    assert p.pages["cultivate"].pair_with == "forge"
    assert p.pages["forge"].pair_with == "cultivate"
    assert list_page_pairs(p) == [("cultivate", "forge")]


def test_reassign_clears_old_partner():
    p = _proj("a", "b", "c")
    set_page_pair(p, "a", "b")
    set_page_pair(p, "a", "c")
    assert p.pages["a"].pair_with == "c"
    assert p.pages["c"].pair_with == "a"
    assert p.pages["b"].pair_with is None


def test_clear_pair():
    p = _proj("a", "b")
    set_page_pair(p, "a", "b")
    set_page_pair(p, "a", None)
    assert p.pages["a"].pair_with is None
    assert p.pages["b"].pair_with is None
    assert list_page_pairs(p) == []


def test_clear_pairs_involving():
    p = _proj("a", "b")
    set_page_pair(p, "a", "b")
    clear_pairs_involving(p, "a")
    assert p.pages["b"].pair_with is None
