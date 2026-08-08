from __future__ import annotations

from pathlib import Path

import cv2
import mss
import numpy as np

from screenflow.assets import resolve_asset_path
from screenflow.compete import compete_page_pair
from screenflow.models import DecideParams, MatchResult, Project, RuntimeConfig


def imread_unicode(path: Path) -> np.ndarray:
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img


class ScreenMatcher:
    """Capture + template match. No game-specific logic."""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.runtime = project.runtime
        self.page_templates: dict[str, np.ndarray] = {}
        self.detect: dict[str, np.ndarray] = {}
        self.click: dict[str, np.ndarray] = {}
        self._sct = None
        self._sticky_page_id: str | None = None
        self._load()

    def _load(self) -> None:
        for page_id, page in self.project.pages.items():
            path = resolve_asset_path(self.project, page.detect_relpath)
            if path.exists():
                self.page_templates[page_id] = imread_unicode(path)

        for key, rel in self.project.detect_files.items():
            path = resolve_asset_path(self.project, rel)
            if path.exists():
                self.detect[key] = imread_unicode(path)

        for key, rel in self.project.click_files.items():
            path = resolve_asset_path(self.project, rel)
            if path.exists():
                self.click[key] = imread_unicode(path)

        if not self.page_templates:
            raise RuntimeError(
                f"No page detect images under {self.project.root / 'pages'}"
            )

    def clear_page_sticky(self) -> None:
        self._sticky_page_id = None

    def capture_screen(self) -> np.ndarray:
        if self._sct is None:
            self._sct = mss.mss()
        monitor = self._sct.monitors[1]
        shot = self._sct.grab(monitor)
        return cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)

    def _scale_template(
        self, template: np.ndarray, full_w: int, full_h: int
    ) -> np.ndarray:
        rt = self.runtime
        scale = min(full_w / rt.ref_width, full_h / rt.ref_height)
        if abs(scale - 1.0) < 0.02:
            return template
        new_w = max(8, int(template.shape[1] * scale))
        new_h = max(8, int(template.shape[0] * scale))
        return cv2.resize(template, (new_w, new_h), interpolation=cv2.INTER_AREA)

    def match_template(
        self,
        screen: np.ndarray,
        template: np.ndarray,
        *,
        full_size: tuple[int, int] | None = None,
    ) -> tuple[float, tuple[int, int] | None]:
        sh, sw = screen.shape[:2]
        fw, fh = full_size if full_size else (sw, sh)
        tpl = self._scale_template(template, fw, fh)
        th, tw = tpl.shape[:2]
        if th > sh or tw > sw:
            return 0.0, None
        result = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return float(max_val), (max_loc[0] + tw // 2, max_loc[1] + th // 2)

    def _match_store(
        self,
        store: dict[str, np.ndarray],
        screen: np.ndarray,
        key: str,
        *,
        roi: tuple[float, float, float, float] | None = None,
    ) -> tuple[float, tuple[int, int] | None]:
        tpl = store.get(key)
        if tpl is None:
            return 0.0, None
        h, w = screen.shape[:2]
        if roi is None:
            return self.match_template(screen, tpl)
        y0, y1, x0, x1 = roi
        region = screen[int(h * y0) : int(h * y1), int(w * x0) : int(w * x1)]
        conf, center = self.match_template(region, tpl, full_size=(w, h))
        if center is None:
            return conf, None
        return conf, (center[0] + int(w * x0), center[1] + int(h * y0))

    def match_detect(
        self,
        screen: np.ndarray,
        key: str,
        *,
        roi: tuple[float, float, float, float] | None = None,
    ) -> tuple[float, tuple[int, int] | None]:
        return self._match_store(self.detect, screen, key, roi=roi)

    def match_click(
        self,
        screen: np.ndarray,
        key: str,
        *,
        roi: tuple[float, float, float, float] | None = None,
    ) -> tuple[float, tuple[int, int] | None]:
        return self._match_store(self.click, screen, key, roi=roi)

    def _pair_sibling(self, page_id: str) -> str | None:
        for a, b in self.project.page_pairs:
            if page_id == a:
                return b
            if page_id == b:
                return a
        return None

    def _result_from_scores(
        self, scores: dict[str, tuple[float, tuple[int, int] | None]]
    ) -> MatchResult:
        rt = self.runtime
        if not scores:
            return MatchResult("UNKNOWN", 0.0, None)

        candidates = [
            (pid, conf, center)
            for pid, (conf, center) in scores.items()
            if conf >= rt.match_threshold
        ]
        if not candidates:
            best = max(scores, key=lambda p: scores[p][0])
            return MatchResult("UNKNOWN", scores[best][0], None)

        top_conf = max(c for _, c, _ in candidates)
        near = [x for x in candidates if top_conf - x[1] <= rt.page_detect_near]
        pri = self.project.detect_priority
        best_id, best_conf, best_center = max(
            near, key=lambda x: (pri.get(x[0], 0), x[1])
        )

        pair_params = DecideParams(
            threshold=rt.match_threshold,
            near=rt.page_detect_near,
            margin=rt.page_pair_margin,
        )
        for a, b in self.project.page_pairs:
            if best_id in (a, b):
                sibling = b if best_id == a else a
                sibling_conf = scores.get(sibling, (0.0, None))[0]
                if best_conf - sibling_conf < rt.page_pair_margin:
                    win = compete_page_pair(
                        best_id,
                        best_conf,
                        sibling,
                        sibling_conf,
                        pri,
                        pair_params,
                        rt.match_threshold,
                    )
                    if win is None:
                        return MatchResult(
                            "UNKNOWN",
                            best_conf,
                            None,
                            {
                                a: scores.get(a, (0.0, None))[0],
                                b: scores.get(b, (0.0, None))[0],
                            },
                        )
                    sc, cen = scores[win]
                    return MatchResult(win, sc, cen)

        return MatchResult(best_id, best_conf, best_center)

    def _commit_page_result(self, result: MatchResult) -> MatchResult:
        if result.page_id == "UNKNOWN":
            self._sticky_page_id = None
        else:
            self._sticky_page_id = result.page_id
        return result

    def _detect_prefer(
        self, screen: np.ndarray, hint: str
    ) -> MatchResult | None:
        """
        Sticky / prefer fast path. Returns None to fall through to full scan.
        """
        tpl = self.page_templates.get(hint)
        if tpl is None:
            return None
        conf, center = self.match_template(screen, tpl)
        if conf < self.runtime.match_threshold:
            return None

        # Weak prefer hit — verify with full scan (avoids false sticky).
        if conf < self.runtime.match_threshold + self.runtime.page_detect_near:
            return None

        scores: dict[str, tuple[float, tuple[int, int] | None]] = {
            hint: (conf, center)
        }
        sibling = self._pair_sibling(hint)
        if sibling and sibling in self.page_templates:
            scores[sibling] = self.match_template(
                screen, self.page_templates[sibling]
            )
        result = self._result_from_scores(scores)
        # Pair conflict / UNKNOWN must not block full scan of other pages.
        if result.page_id == "UNKNOWN":
            return None
        return self._commit_page_result(result)

    def _detect_full(
        self, screen: np.ndarray, *, commit_sticky: bool = True
    ) -> MatchResult:
        scores: dict[str, tuple[float, tuple[int, int] | None]] = {}
        for page_id, template in self.page_templates.items():
            scores[page_id] = self.match_template(screen, template)
        result = self._result_from_scores(scores)
        if commit_sticky:
            return self._commit_page_result(result)
        return result

    def detect_page(
        self,
        screen: np.ndarray,
        *,
        prefer: str | None = None,
        force_full: bool = False,
        commit_sticky: bool = True,
    ) -> MatchResult:
        if not force_full:
            hint = prefer if prefer is not None else self._sticky_page_id
            if hint:
                sticky_hit = self._detect_prefer(screen, hint)
                if sticky_hit is not None:
                    return sticky_hit
        return self._detect_full(screen, commit_sticky=commit_sticky)

    def find_click_target(
        self, screen: np.ndarray, key: str
    ) -> tuple[int, int] | None:
        template = self.click.get(key)
        if template is None:
            return None
        conf, center = self.match_template(screen, template)
        if conf >= self.runtime.match_threshold and center:
            return center
        return None
