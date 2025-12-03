from PyQt5 import QtWidgets, uic
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[2] / "ui"


class UnfinishedSimulationsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_DIR / "unfinished_simulations_dialog.ui"), self)
        with open(UI_DIR /"style.css", "r") as file:
            self.setStyleSheet(file.read()) 

        # 1) Настройка таблицы
        header = self.tableUnfinished.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)  # последний столбец тянется, чтобы не было пустоты
        self.tableUnfinished.setAlternatingRowColors(True)
        # 2) Кнопки (имена задай в .ui)
        self.closeButton.clicked.connect(self.reject)   # или self.close
        self.actionButton.clicked.connect(self.on_action_button_clicked)

    def set_data(self, rows):
        """
        rows: [(folder, last_step | None, expected_nrun), ...]
        """
        self.tableUnfinished.setRowCount(len(rows))

        for row, (folder, last_step, expected) in enumerate(rows):
            self.tableUnfinished.setItem(row, 0, QtWidgets.QTableWidgetItem(folder))

            last_text = "—" if last_step is None else str(last_step)
            self.tableUnfinished.setItem(row, 1, QtWidgets.QTableWidgetItem(last_text))
            self.tableUnfinished.setItem(
                row, 2, QtWidgets.QTableWidgetItem(str(expected))
            )

        # на всякий случай ещё раз пересчитать после заполнения
        self.tableUnfinished.resizeColumnsToContents()

    def on_action_button_clicked(self):
        # пока заглушка, чтобы не падало
        # потом сюда впишешь свою логику
        pass