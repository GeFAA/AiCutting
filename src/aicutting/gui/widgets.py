from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PathPicker(QWidget):
    path_changed = Signal(object)

    def __init__(self, label: str, button_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.label_text = label
        self._path: Path | None = None

        self.label = QLabel(label)
        self.input = QLineEdit()
        self.input.setReadOnly(True)
        self.button = QPushButton(button_text)

        layout = QHBoxLayout(self)
        layout.addWidget(self.label)
        layout.addWidget(self.input, 1)
        layout.addWidget(self.button)

    def set_path(self, path: Path | None) -> None:
        self._path = path
        self.input.setText("" if path is None else str(path))
        self.path_changed.emit(path)

    def path(self) -> Path | None:
        return self._path


class StatusPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_message = "Ready"
        self.message_label = QLabel(self.current_message)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(500)

        layout = QVBoxLayout(self)
        layout.addWidget(self.message_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)

    def set_status(self, message: str, busy: bool = False) -> None:
        self.current_message = message
        self.message_label.setText(message)
        self.progress.setVisible(busy)

    def append_log(self, line: str) -> None:
        self.log.appendPlainText(line)
