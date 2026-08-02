import sys

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QWidget

from studio.no_wheel import NoWheelEditFilter, install_no_wheel_value_change


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_wheel_blocked_on_spin_and_combo():
    _app()
    filt = NoWheelEditFilter()
    spin = QDoubleSpinBox()
    combo = QComboBox()
    combo.addItems(["a", "b", "c"])
    ev = QWheelEvent(
        QPoint(0, 0),
        QPoint(0, 0),
        QPoint(0, 0),
        QPoint(0, 120),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    assert filt.eventFilter(spin, ev) is True
    assert filt.eventFilter(combo, ev) is True
    assert filt.eventFilter(QWidget(), ev) is False
    assert filt.eventFilter(spin, QEvent(QEvent.Type.FocusIn)) is False


def test_install_on_app():
    app = _app()
    filt = install_no_wheel_value_change(app)
    assert filt.parent() is app
