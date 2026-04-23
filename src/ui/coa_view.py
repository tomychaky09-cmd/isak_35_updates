from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView,
                             QMessageBox, QDialog, QFormLayout, QLineEdit, QComboBox,
                             QDialogButtonBox, QFileDialog, QTextEdit)
from PySide6.QtCore import Qt
from ..database_manager import DatabaseManager
import pandas as pd
import os
import shutil

class CoaView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        # Set Page Background
        self.setStyleSheet("background-color: #d1d8e0;") # Slate gray background
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Container
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("📂 MANAJEMEN BAGAN AKUN")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2d3436;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Search Bar
        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 Cari Akun (Nama atau Kode)...")
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
        self.le_search.textChanged.connect(self.filter_accounts)
        header_layout.addWidget(self.le_search)
        layout.addWidget(header_widget)

        # Table for accounts
        self.table_coa = QTableWidget(0, 6)
        self.table_coa.setHorizontalHeaderLabels(["ID", "Kode", "Nama Akun", "Tipe", "Kategori", "Catatan (CaLK)"])
        
        # Table Styling for High Contrast
        self.table_coa.setStyleSheet("""
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
        
        self.table_coa.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_coa.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_coa.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table_coa.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_coa.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table_coa.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table_coa.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_coa.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_coa.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.table_coa)

        # Buttons Container
        button_layout = QHBoxLayout()
        self.btn_add = QPushButton("➕ Tambah Akun")
        self.btn_add.setStyleSheet("""
            QPushButton { background-color: #2ecc71; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #27ae60; }
        """)
        self.btn_add.clicked.connect(self.add_account_dialog)
        
        self.btn_edit = QPushButton("✏️ Edit Akun")
        self.btn_edit.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_edit.clicked.connect(self.edit_account_dialog)
        
        self.btn_delete = QPushButton("🗑️ Hapus Akun")
        self.btn_delete.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_delete.clicked.connect(self.delete_account_action)

        self.btn_export = QPushButton("📤 Ekspor")
        self.btn_export.setStyleSheet("""
            QPushButton { background-color: #778ca3; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #4b6584; }
        """)
        self.btn_export.clicked.connect(self.export_to_excel)

        self.btn_import = QPushButton("📥 Impor")
        self.btn_import.setStyleSheet("""
            QPushButton { background-color: #f1c40f; color: black; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #f39c12; }
        """)
        self.btn_import.clicked.connect(self.import_from_excel)

        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_edit)
        button_layout.addWidget(self.btn_delete)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_export)
        button_layout.addWidget(self.btn_import)
        layout.addLayout(button_layout)

    def load_accounts(self):
        self.table_coa.setRowCount(0)
        accounts = self.db.get_accounts()
        for row_idx, account in enumerate(accounts):
            self.table_coa.insertRow(row_idx)
            
            # Create items with explicit black color for safety
            for col_idx, value in enumerate(account):
                item = QTableWidgetItem(str(value if value is not None else ""))
                item.setForeground(Qt.GlobalColor.black)
                self.table_coa.setItem(row_idx, col_idx, item)

    def filter_accounts(self, text):
        """Menyaring baris di tabel COA berdasarkan teks pencarian."""
        text = text.lower()
        for row in range(self.table_coa.rowCount()):
            code_item = self.table_coa.item(row, 1)
            name_item = self.table_coa.item(row, 2)
            
            show_row = False
            if code_item and text in code_item.text().lower():
                show_row = True
            elif name_item and text in name_item.text().lower():
                show_row = True
            
            self.table_coa.setRowHidden(row, not show_row)

    def add_account_dialog(self):
        dialog = AccountFormDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            code = dialog.le_code.text()
            name = dialog.le_name.text()
            acc_type = dialog.cb_type.currentText()
            category = dialog.cb_category.currentText()
            notes = dialog.te_notes.toPlainText()
            
            try:
                self.db.add_account(code, name, acc_type, category, notes)
                QMessageBox.information(self, "Sukses", "Akun berhasil ditambahkan.")
                self.load_accounts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menambahkan akun: {e}")

    def edit_account_dialog(self):
        selected_items = self.table_coa.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Peringatan", "Pilih akun yang ingin diedit.")
            return
        
        row = selected_items[0].row()
        account_id = int(self.table_coa.item(row, 0).text())
        current_code = self.table_coa.item(row, 1).text()
        current_name = self.table_coa.item(row, 2).text()
        current_type = self.table_coa.item(row, 3).text()
        current_category = self.table_coa.item(row, 4).text()
        current_notes = self.table_coa.item(row, 5).text() if self.table_coa.columnCount() > 5 else ""

        dialog = AccountFormDialog(self, 
                                   account_id=account_id,
                                   code=current_code,
                                   name=current_name,
                                   acc_type=current_type,
                                   category=current_category,
                                   notes=current_notes)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_code = dialog.le_code.text()
            new_name = dialog.le_name.text()
            new_type = dialog.cb_type.currentText()
            new_category = dialog.cb_category.currentText()
            new_notes = dialog.te_notes.toPlainText()
            
            try:
                self.db.update_account(account_id, new_code, new_name, new_type, new_category, new_notes)
                QMessageBox.information(self, "Sukses", "Akun berhasil diperbarui.")
                self.load_accounts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal memperbarui akun: {e}")

    def delete_account_action(self):
        selected_items = self.table_coa.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Peringatan", "Pilih akun yang ingin dihapus.")
            return
        
        row = selected_items[0].row()
        account_id = int(self.table_coa.item(row, 0).text())
        account_name = self.table_coa.item(row, 2).text()

        reply = QMessageBox.question(self, "Konfirmasi Hapus",
                                     f"Anda yakin ingin menghapus akun '{account_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_account(account_id)
                QMessageBox.information(self, "Sukses", "Akun berhasil dihapus.")
                self.load_accounts()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal menghapus akun: {e}")

    def export_to_excel(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Bagan Akun", "Bagan_Akun.xlsx", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                accounts_data = self.db.get_accounts()
                if not accounts_data:
                    QMessageBox.information(self, "Info", "Tidak ada data akun untuk diekspor.")
                    return
                df = pd.DataFrame(accounts_data, columns=["ID", "Kode", "Nama Akun", "Tipe", "Kategori", "Catatan (CaLK)"])
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Sukses", f"Bagan Akun berhasil diekspor ke:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal mengekspor Bagan Akun: {e}")

    def import_from_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih File Excel untuk Import Akun", "", "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                # Membaca excel dan mengganti NaN dengan string kosong segera
                df = pd.read_excel(file_path)
                df = df.fillna("") 
                
                required_columns = ["Kode", "Nama Akun", "Tipe", "Kategori"]
                if not all(col in df.columns for col in required_columns):
                    QMessageBox.critical(self, "Error", f"File Excel harus memiliki kolom: {', '.join(required_columns)}")
                    return
                
                accounts_to_import = []
                # Daftar tipe yang valid sesuai dengan AccountFormDialog
                valid_types = ["Asset", "Liability", "Equity", "Revenue", "Expense", "Asset Net", "Asset (Contra)"]
                
                for index, row in df.iterrows():
                    # Membersihkan data: hapus spasi di awal/akhir dan pastikan tipe data string
                    code = str(row["Kode"]).strip()
                    name = str(row["Nama Akun"]).strip()
                    acc_type = str(row["Tipe"]).strip()
                    category = str(row["Kategori"]).strip()
                    notes = str(row.get("Catatan (CaLK)", "")).strip()
                    
                    # Jika kategori adalah "nan" karena konversi string sebelumnya, kosongkan
                    if category.lower() == "nan":
                        category = ""
                    
                    # Validasi Tipe Akun (Case Insensitive check)
                    matched_type = "Asset" # Default jika tidak cocok
                    for vt in valid_types:
                        if acc_type.lower() == vt.lower():
                            matched_type = vt
                            break
                    
                    accounts_to_import.append({
                        "code": code,
                        "name": name,
                        "type": matched_type,
                        "category": category,
                        "notes": notes
                    })
                
                success_count, fail_count, errors = self.db.bulk_add_accounts(accounts_to_import)
                if success_count > 0:
                    msg = f"{success_count} akun berhasil diimpor/diperbarui."
                    if fail_count > 0:
                        msg += f"\n{fail_count} akun gagal diimpor."
                    QMessageBox.information(self, "Sukses", msg)
                    self.load_accounts()
                else:
                    error_msg = "\n".join(errors[:5]) # Tampilkan 5 error pertama
                    QMessageBox.warning(self, "Peringatan", f"Gagal impor. Detail error:\n{error_msg}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal mengimpor: {e}")

    def download_coa_template(self):
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "coa_template.xlsx")
        if not os.path.exists(template_path): return
        save_path, _ = QFileDialog.getSaveFileName(self, "Simpan Template", "coa_template.xlsx", "Excel Files (*.xlsx)")
        if save_path:
            try:
                shutil.copy(template_path, save_path)
                QMessageBox.information(self, "Sukses", "Template berhasil diunduh.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal unduh: {e}")

class AccountFormDialog(QDialog):
    def __init__(self, parent=None, account_id=None, code="", name="", acc_type="", category="", notes=""):
        super().__init__(parent)
        self.account_id = account_id
        self.setWindowTitle("Tambah/Edit Akun")
        self.setMinimumWidth(350)
        self.init_ui(code, name, acc_type, category, notes)

    def init_ui(self, code, name, acc_type, category, notes):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.le_code = QLineEdit(code)
        self.le_name = QLineEdit(name)
        self.cb_type = QComboBox()
        self.cb_type.addItems(["Asset", "Liability", "Equity", "Revenue", "Expense", "Asset Net", "Asset (Contra)"])
        self.cb_type.setCurrentText(acc_type)
        self.cb_category = QComboBox()
        self.cb_category.addItems(["", "Tanpa Pembatasan", "Dengan Pembatasan"])
        self.cb_category.setCurrentText(category if category else "")
        
        self.te_notes = QTextEdit(notes)
        self.te_notes.setPlaceholderText("Tambahkan narasi atau catatan untuk akun ini (CaLK)")
        self.te_notes.setMaximumHeight(80)

        form_layout.addRow("Kode Akun:", self.le_code)
        form_layout.addRow("Nama Akun:", self.le_name)
        form_layout.addRow("Tipe Akun:", self.cb_type)
        form_layout.addRow("Kategori:", self.cb_category)
        form_layout.addRow("Catatan (CaLK):", self.te_notes)
        layout.addLayout(form_layout)
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
