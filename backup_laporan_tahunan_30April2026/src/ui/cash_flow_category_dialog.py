import sys
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QFormLayout, QLineEdit, QComboBox, QMessageBox, QHeaderView)
from PySide6.QtCore import Qt
from src.database_manager import DatabaseManager

class CashFlowCategoryDialog(QDialog):
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.setWindowTitle("Manajemen Kategori Arus Kas")
        self.setGeometry(100, 100, 600, 400)
        self.init_ui()
        self.load_categories()

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Form untuk menambah/mengedit kategori
        form_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.main_category_combo = QComboBox()
        self.main_category_combo.addItems(["ARUS KAS DARI AKTIVITAS OPERASI", 
                                           "ARUS KAS DARI AKTIVITAS INVESTASI", 
                                           "ARUS KAS DARI AKTIVITAS PENDANAAN"])
        
        form_layout.addRow("Nama Aktivitas:", self.name_input)
        form_layout.addRow("Kategori Utama:", self.main_category_combo)
        main_layout.addLayout(form_layout)

        # Tombol Add/Update
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Tambah")
        self.add_button.clicked.connect(self.add_category)
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_category)
        self.update_button.setEnabled(False) # Disable initially
        self.clear_button = QPushButton("Batal/Bersihkan")
        self.clear_button.clicked.connect(self.clear_form)
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)

        # Tabel untuk menampilkan kategori
        self.table = QTableWidget(0, 3) # ID, Nama, Kategori Utama
        self.table.setHorizontalHeaderLabels(["ID", "Nama Aktivitas", "Kategori Utama"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnHidden(0, True) # Sembunyikan kolom ID
        self.table.itemSelectionChanged.connect(self.select_category)
        main_layout.addWidget(self.table)

        # Tombol Delete
        delete_button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Hapus Kategori Terpilih")
        self.delete_button.clicked.connect(self.delete_category)
        delete_button_layout.addStretch()
        delete_button_layout.addWidget(self.delete_button)
        main_layout.addLayout(delete_button_layout)

        self.setLayout(main_layout)

    def load_categories(self):
        self.table.setRowCount(0)
        categories = self.db.get_cash_flow_categories()
        for row_idx, (cat_id, name, main_category) in enumerate(categories):
            self.table.insertRow(row_idx)
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(cat_id)))
            self.table.setItem(row_idx, 1, QTableWidgetItem(name))
            self.table.setItem(row_idx, 2, QTableWidgetItem(main_category))

    def add_category(self):
        name = self.name_input.text().strip()
        main_category = self.main_category_combo.currentText()

        if not name:
            QMessageBox.warning(self, "Peringatan", "Nama aktivitas tidak boleh kosong.")
            return
        if not main_category:
            QMessageBox.warning(self, "Peringatan", "Kategori utama tidak boleh kosong.")
            return
        
        try:
            self.db.add_cash_flow_category(name, main_category)
            QMessageBox.information(self, "Sukses", "Kategori berhasil ditambahkan.")
            self.load_categories()
            self.clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal menambahkan kategori: {e}")

    def select_category(self):
        selected_items = self.table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            self.current_selected_id = int(self.table.item(row, 0).text())
            self.name_input.setText(self.table.item(row, 1).text())
            self.main_category_combo.setCurrentText(self.table.item(row, 2).text())
            self.add_button.setEnabled(False)
            self.update_button.setEnabled(True)
        else:
            self.clear_form()

    def update_category(self):
        if not hasattr(self, 'current_selected_id'):
            QMessageBox.warning(self, "Peringatan", "Pilih kategori yang ingin diupdate.")
            return

        name = self.name_input.text().strip()
        main_category = self.main_category_combo.currentText()

        if not name:
            QMessageBox.warning(self, "Peringatan", "Nama aktivitas tidak boleh kosong.")
            return
        if not main_category:
            QMessageBox.warning(self, "Peringatan", "Kategori utama tidak boleh kosong.")
            return
        
        try:
            self.db.update_cash_flow_category(self.current_selected_id, name, main_category)
            QMessageBox.information(self, "Sukses", "Kategori berhasil diupdate.")
            self.load_categories()
            self.clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mengupdate kategori: {e}")

    def delete_category(self):
        selected_items = self.table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Peringatan", "Pilih kategori yang ingin dihapus.")
            return
        
        reply = QMessageBox.question(self, "Konfirmasi Hapus", 
                                     "Anda yakin ingin menghapus kategori ini? Transaksi yang sudah ada mungkin terpengaruh.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                row = selected_items[0].row()
                category_id = int(self.table.item(row, 0).text())
                self.db.delete_cash_flow_category(category_id)
                QMessageBox.information(self, "Sukses", "Kategori berhasil dihapus.")
                self.load_categories()
                self.clear_form()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menghapus kategori: {e}")

    def clear_form(self):
        self.name_input.clear()
        self.main_category_combo.setCurrentIndex(0)
        self.add_button.setEnabled(True)
        self.update_button.setEnabled(False)
        if hasattr(self, 'current_selected_id'):
            del self.current_selected_id
        self.table.clearSelection()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    db_manager = DatabaseManager()
    dialog = CashFlowCategoryDialog(db_manager)
    dialog.exec()
    sys.exit(app.exec())
