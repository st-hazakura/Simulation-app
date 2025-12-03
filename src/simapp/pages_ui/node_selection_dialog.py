from PyQt5 import QtWidgets, uic
from pathlib import Path

UI_DIR = Path(__file__).resolve().parents[2] / "ui"


class NodeSelectionDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi(str(UI_DIR / "node_selection_dialog.ui"), self)

        # стиль, если есть общий css
        style_path = UI_DIR / "style.css"
        if style_path.exists():
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())

        # настройки таблицы
        header = self.tableNodes.horizontalHeader()
        header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        self.tableNodes.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableNodes.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableNodes.setAlternatingRowColors(True)

        self.buttonBox.accepted.connect(self._on_accept)
        self.buttonBox.rejected.connect(self.reject)

        # результаты выбора
        self._selected_node: str | None = None
        self._selected_ppn: int | None = None
        self._selected_mem_gb: int | None = None

    def set_data(self, nodes: list[str], node_max_days: dict[str, int] | None,
                 node_load: dict[str, str] | None):
        """
        nodes        – список нодов
        node_max_days – {node: max_days} или None
        node_load     – {node: 'описание нагрузки'} или None
        """
        self.tableNodes.setRowCount(len(nodes))

        for row, node in enumerate(nodes):
            # колонка 0: node
            self.tableNodes.setItem(row, 0, QtWidgets.QTableWidgetItem(node))

            # колонка 1: max days
            max_days = None
            if node_max_days is not None:
                max_days = node_max_days.get(node)

            max_text = "—" if max_days is None else str(max_days)
            self.tableNodes.setItem(row, 1, QtWidgets.QTableWidgetItem(max_text))

            # колонка 2: load
            load_text = ""
            if node_load is not None:
                load_text = node_load.get(node, "")
            self.tableNodes.setItem(row, 2, QtWidgets.QTableWidgetItem(load_text))

        self.tableNodes.resizeColumnsToContents()

        # по умолчанию выбираем первую строку
        if nodes:
            self.tableNodes.selectRow(0)

    def _on_accept(self):
        """Считываем выбранный ряд + спинбоксы и сохраняем в атрибуты."""
        row = self.tableNodes.currentRow()
        if row < 0:
            QtWidgets.QMessageBox.warning(self, "Výběr nody", "Vyber prosím jednu nodu v tabulce.")
            return

        node_item = self.tableNodes.item(row, 0)
        if node_item is None:
            QtWidgets.QMessageBox.warning(self, "Chyba", "Vybraný řádek je neplatný.")
            return

        self._selected_node = node_item.text()
        self._selected_ppn = int(self.spinPpn.value())
        self._selected_mem_gb = int(self.spinMemGb.value())

        self.accept()

    # геттеры, чтобы забрать результат из MainWindow
    def selected_node(self) -> str | None:
        return self._selected_node

    def selected_ppn(self) -> int | None:
        return self._selected_ppn

    def selected_mem_gb(self) -> int | None:
        return self._selected_mem_gb
    
