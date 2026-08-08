from __future__ import annotations

from pathlib import Path

import cv2
import mss
import numpy as np

from screenflow.assets import resolve_asset_path, scoped_asset_key
from screenflow.compete import compete_page_pair
from screenflow.models import DecideParams, MatchResult, Project, RuntimeConfig
from screenflow.roi import expand_roi_for_search, normalize_roi


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
        self.page_rois: dict[str, tuple[float, float, float, float]] = {}
        self.features: dict[str, np.ndarray] = {}
        self.feature_rois: dict[str, tuple[float, float, float, float]] = {}
        self._sct = None
        self._sticky_page_id: str | None = None
        self._load()

    def _load(self) -> None:
        for page_id, page in self.project.pages.items():
            path = resolve_asset_path(self.project, page.detect_relpath)
            if path.exists():
                self.page_templates[page_id] = imread_unicode(path)
            proi = normalize_roi(page.detect_roi)
            if proi is None:
                stem = Path(page.detect_relpath).stem
                proi = normalize_roi(page.feature_rois.get(stem))
            if proi is not None:
                self.page_rois[page_id] = proi
            for name, raw in page.feature_rois.items():
                nroi = normalize_roi(raw)
                if nroi is None:
                    continue
                self.feature_rois[scoped_asset_key(page_id, name)] = nroi
                self.feature_rois.setdefault(name, nroi)

        for key, rel in self.project.feature_files.items():
            path = resolve_asset_path(self.project, rel)
            if path.exists():
                self.features[key] = imread_unicode(path)

        if not self.page_templates:
            raise RuntimeError(
                f"No page detect images under {self.project.root / 'pages'}"
            )

    def store_roi(
        self, key: str
    ) -> tuple[float, float, float, float] | None:
        """Asset-level ROI for a feature store key, if any."""
        return self.feature_rois.get(key)

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
        roi: tuple[float, float, float, float] | None = None,
    ) -> tuple[float, tuple[int, int] | None]:
        sh, sw = screen.shape[:2]
        fw, fh = full_size if full_size else (sw, sh)
        nroi = normalize_roi(roi)
        if nroi is not None:
            # Crop templates are the same size as the drawn ROI. Without pad,
            # matchTemplate cannot slide and small UI jitter tanks confidence.
            y0, y1, x0, x1 = expand_roi_for_search(nroi)
            px0, py0 = int(sw * x0), int(sh * y0)
            px1, py1 = int(sw * x1), int(sh * y1)
            if px1 <= px0 or py1 <= py0:
                return 0.0, None
            region = screen[py0:py1, px0:px1]
            conf, center = self.match_template(region, template, full_size=(fw, fh))
            if center is None:
                return conf, None
            return conf, (center[0] + px0, center[1] + py0)
        tpl = self._scale_template(template, fw, fh)
        th, tw = tpl.shape[:2]
        if th > sh or tw > sw:
            return 0.0, None
        result = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        return float(max_val), (max_loc[0] + tw // 2, max_loc[1] + th // 2)

    def match_feature(
        self,
        screen: np.ndarray,
        key: str,
        *,
        roi: tuple[float, float, float, float] | None = None,
    ) -> tuple[float, tuple[int, int] | None]:
        tpl = self.features.get(key)
        if tpl is None:
            return 0.0, None
        use_roi = normalize_roi(roi) or self.store_roi(key)
        return self.match_template(screen, tpl, roi=use_roi)

    def _pair_sibling(self, page_id: str) -> str | None:
        for a, b in self.project.page_pairs:
            if page_id == a:
                return b
            if page_id == b:
                return a
        return None

    @staticmethod
    def _scores_map(
        scores: dict[str, tuple[float, tuple[int, int] | None]],
    ) -> dict[str, float]:
        return {pid: float(conf) for pid, (conf, _) in scores.items()}

    def _result_from_scores(
        self, scores: dict[str, tuple[float, tuple[int, int] | None]]
    ) -> MatchResult:
        rt = self.runtime
        score_map = self._scores_map(scores)
        if not scores:
            return MatchResult("UNKNOWN", 0.0, None, score_map)

        candidates = [
            (pid, conf, center)
            for pid, (conf, center) in scores.items()
            if conf >= rt.match_threshold
        ]
        if not candidates:
            best = max(scores, key=lambda p: scores[p][0])
            return MatchResult(
                "UNKNOWN", scores[best][0], None, score_map
            )

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
                            score_map,
                        )
                    sc, cen = scores[win]
                    return MatchResult(win, sc, cen, score_map)

        return MatchResult(best_id, best_conf, best_center, score_map)

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
        conf, center = self.match_template(
            screen, tpl, roi=self.page_rois.get(hint)
        )
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
                screen,
                self.page_templates[sibling],
                roi=self.page_rois.get(sibling),
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
            scores[page_id] = self.match_template(
                screen, template, roi=self.page_rois.get(page_id)
            )
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
        template = self.features.get(key)
        if template is None:
            return None
        conf, center = self.match_template(
            screen, template, roi=self.feature_rois.get(key)
        )
        if conf >= self.runtime.match_threshold and center:
            return center
        return None
