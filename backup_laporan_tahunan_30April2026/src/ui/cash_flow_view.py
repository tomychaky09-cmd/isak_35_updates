from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDialogButtonBox, QFileDialog)
from PySide6.QtCore import Qt, Signal
from src.database_manager import DatabaseManager

class CashFlowView(QWidget):
    back_to_dashboard_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.init_ui()
        self.load_categories()

    def init_ui(self):
        self.setStyleSheet("background-color: #d1d8e0;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Container
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tombol Kembali
        self.btn_back = QPushButton("🏠 Kembali")
        self.btn_back.setFixedWidth(100)
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                padding: 8px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        self.btn_back.clicked.connect(self.back_to_dashboard_requested.emit)
        header_layout.addWidget(self.btn_back)

        title = QLabel("🌊 MANAJEMEN KATEGORI ARUS KAS")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2d3436; margin-left: 10px;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Search Bar
        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 Cari Aktivitas...")
        self.le_search.setFixedWidth(300)
        self.le_search.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #a5b1c2;
                background-color: white;
                color: #000000;
                font-size: 13px;
            }
        """)
        self.le_search.textChanged.connect(self.filter_categories)
        header_layout.addWidget(self.le_search)
        layout.addLayout(header_layout)

        # Table for categories
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Nama Aktivitas", "Kategori Utama"])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #d1d8e0;
                border: 1px solid #a5b1c2;
                border-radius: 4px;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #4b6584;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(0, True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)

        # Buttons Container
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Tambah Aktivitas")
        self.btn_add.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_add.clicked.connect(self.add_category_dialog)
        
        self.btn_edit = QPushButton("✏️ Edit Aktivitas")
        self.btn_edit.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_edit.clicked.connect(self.edit_category_dialog)
        
        self.btn_delete = QPushButton("🗑️ Hapus Aktivitas")
        self.btn_delete.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_delete.clicked.connect(self.delete_category_action)

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def load_categories(self):
        self.table.setRowCount(0)
        categories = self.db.get_cash_flow_categories()
        for row_idx, (cat_id, name, main_cat) in enumerate(categories):
            self.table.insertRow(row_idx)
            items = [str(cat_id), name, main_cat]
            for col_idx, value in enumerate(items):
                item = QTableWidgetItem(value)
                item.setForeground(Qt.GlobalColor.black)
                self.table.setItem(row_idx, col_idx, item)

    def filter_categories(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 1)
            cat_item = self.table.item(row, 2)
            show = (name_item and text in name_item.text().lower()) or (cat_item and text in cat_item.text().lower())
            self.table.setRowHidden(row, not show)

    def add_category_dialog(self):
        dialog = CashFlowFormDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.le_name.text().strip()
            main_cat = dialog.cb_main_cat.currentText()
            try:
                self.db.add_cash_flow_category(name, main_cat)
                QMessageBox.information(self, "Sukses", "Kategori berhasil ditambahkan.")
                self.load_categories()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal: {e}")

    def edit_category_dialog(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Peringatan", "Pilih data yang ingin diedit.")
            return
        
        row = selected[0].row()
        cat_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()
        main_cat = self.table.item(row, 2).text()

        dialog = CashFlowFormDialog(self, name=name, main_cat=main_cat)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.le_name.text().strip()
            new_main_cat = dialog.cb_main_cat.currentText()
            try:
                self.db.update_cash_flow_category(cat_id, new_name, new_main_cat)
                QMessageBox.information(self, "Sukses", "Data berhasil diperbarui.")
                self.load_categories()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal: {e}")

    def delete_category_action(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Peringatan", "Pilih data yang ingin dihapus.")
            return
        
        row = selected[0].row()
        cat_id = int(self.table.item(row, 0).text())
        name = self.table.item(row, 1).text()

        if QMessageBox.question(self, "Konfirmasi", f"Hapus '{name}'?") == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_cash_flow_category(cat_id)
                self.load_categories()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal: {e}")

class CashFlowFormDialog(QDialog):
    def __init__(self, parent=None, name="", main_cat=""):
        super().__init__(parent)
        self.setWindowTitle("Form Aktivitas Arus Kas")
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.le_name = QLineEdit(name)
        self.cb_main_cat = QComboBox()
        self.cb_main_cat.addItems(["ARUS KAS DARI AKTIVITAS OPERASI", 
                                   "ARUS KAS DARI AKTIVITAS INVESTASI", 
                                   "ARUS KAS DARI AKTIVITAS PENDANAAN"])
        self.cb_main_cat.setCurrentText(main_cat)
        form.addRow("Nama Aktivitas:", self.le_name)
        form.addRow("Kategori Utama:", self.cb_main_cat)
        layout.addLayout(form)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        layout.addWidget(btns)
