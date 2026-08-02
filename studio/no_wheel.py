"""Block mouse-wheel from changing spinboxes / comboboxes app-wide."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QAbstractSpinBox, QApplication, QComboBox, QWidget


class NoWheelEditFilter(QObject):
    """
    Ignore wheel events on value editors so scrolling the panel does not
    accidentally change numbers or combo selections. Users can still type
    or use the spinbox arrow buttons.
    """

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() != QEvent.Type.Wheel:
            return False
        if isinstance(watched, (QAbstractSpinBox, QComboBox)):
            return True
        # Internal line-edit / viewport of a spinbox or combo
        if isinstance(watched, QWidget):
            p = watched.parent()
            while p is not None:
                if isinstance(p, (QAbstractSpinBox, QComboBox)):
                    return True
                p = p.parent()
        return False


def install_no_wheel_value_change(app: QApplication) -> NoWheelEditFilter:
    filt = NoWheelEditFilter(app)
    app.installEventFilter(filt)
    return filt
