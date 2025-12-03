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


        self.selected_folder: str | None = None
        self.selected_last_step: int | None = None
        self.selected_expected_nrun: int | None = None


    def set_data(self, rows):
        """
        rows: [(folder, last_step | None, expected_nrun), ...]
        """
        self.tableUnfinished.setRowCount(len(rows))

        for row, (folder, last_step, expected) in enumerate(rows):
            self.tableUnfinished.setItem(row, 0, QtWidgets.QTableWidgetItem(folder))

            last_text = "—" if last_step is None else str(last_step)
            self.tableUnfinished.setItem(row, 1, QtWidgets.QTableWidgetItem(last_text))
            self.tableUnfinished.setItem(row, 2, QtWidgets.QTableWidgetItem(str(expected)))

        # на всякий случай ещё раз пересчитать после заполнения
        self.tableUnfinished.resizeColumnsToContents()



    def on_action_button_clicked(self):
        """Забираем выбранную строку и закрываем диалог с Accepted."""
        row = self.tableUnfinished.currentRow()
        
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Výběr simulace", "Vyber prosím jednu simulaci v tabulce.")
            return
    
        folder_item = self.tableUnfinished.item(row, 0)
        last_item = self.tableUnfinished.item(row, 1)
        expected_item = self.tableUnfinished.item(row, 2)
        
        if folder_item is None or expected_item is None:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Vybraný řádek je neplatný.")
            return
        
        self.selected_folder = folder_item.text()
        
        # проверяем если вообще симуляция прошла до первой записи рестарта
        last_text = last_item.text() if last_item is not None else "-"
        if last_text in ("", "-"):
            self.selected_last_step = None
        else:
            try:
                self.selected_last_step = int(last_text)
            except ValueError:
                self.selected_last_step = None
                
        try:
            self.selected_expected_nrun = int(expected_item.text())
        except ValueError:
            self.selected_expected_nrun = None

        self.accept()