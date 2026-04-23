# src/ui/journal_list_view.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLabel, QAbstractItemView, QMessageBox, QDialog,
    QLineEdit, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from ..database_manager import DatabaseManager
from .beginning_balance_dialog import BeginningBalanceDialog
import os
import shutil
import pandas as pd

class JournalListView(QWidget):
    journal_selected = Signal(int) 
    new_journal_requested = Signal()
    edit_journal_requested = Signal(int)
    back_to_dashboard_requested = Signal()

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
        self.load_journals()

    def init_ui(self):
        # Set Page Background
        self.setStyleSheet("background-color: #d1d8e0;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top bar Container
        top_bar_widget = QWidget()
        top_bar_widget.setStyleSheet("background-color: transparent;")
        top_bar_layout = QHBoxLayout(top_bar_widget)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        # Tombol Kembali
        self.btn_back_home = QPushButton("🏠 Kembali")
        self.btn_back_home.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; font-weight: bold; padding: 10px 15px; border-radius: 6px; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        self.btn_back_home.clicked.connect(self.back_to_dashboard_requested.emit)
        top_bar_layout.addWidget(self.btn_back_home)
        
        self.btn_new_journal = QPushButton("✍️ Buat Jurnal Baru")
        self.btn_new_journal.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; font-weight: bold; padding: 10px 15px; border-radius: 6px; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.btn_new_journal.clicked.connect(self.new_journal_requested.emit)

        self.btn_beginning_balance = QPushButton("💰 Saldo Awal")
        self.btn_beginning_balance.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; font-weight: bold; padding: 10px 15px; border-radius: 6px; }
            QPushButton:hover { background-color: #e67e22; }
        """)
        self.btn_beginning_balance.clicked.connect(self.open_beginning_balance_dialog)
        
        top_bar_layout.addWidget(self.btn_new_journal)
        top_bar_layout.addWidget(self.btn_beginning_balance)
        top_bar_layout.addStretch()
        
        # Search Bar
        self.le_search = QLineEdit()
        self.le_search.setPlaceholderText("🔍 Cari Jurnal (Deskripsi/Ref)...")
        self.le_search.setFixedWidth(250)
        self.le_search.setStyleSheet("""
            QLineEdit {
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid #a5b1c2;
                background-color: white;
                color: #000000;
            }
        """)
        self.le_search.textChanged.connect(self.filter_journals)
        top_bar_layout.addWidget(self.le_search)
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setFixedWidth(40)
        self.btn_refresh.setStyleSheet("background-color: white; border: 1px solid #a5b1c2; padding: 8px; border-radius: 6px;")
        self.btn_refresh.clicked.connect(self.load_journals)
        top_bar_layout.addWidget(self.btn_refresh)

        # Tombol Download Template
        self.btn_template = QPushButton("📋 Template")
        self.btn_template.setStyleSheet("""
            QPushButton { background-color: #7f8c8d; color: white; font-weight: bold; padding: 10px; border-radius: 6px; }
            QPushButton:hover { background-color: #95a5a6; }
        """)
        self.btn_template.clicked.connect(self.download_journal_template)
        top_bar_layout.addWidget(self.btn_template)

        self.btn_import_excel = QPushButton("📥 Impor")
        self.btn_import_excel.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold; padding: 10px; border-radius: 6px;")
        self.btn_import_excel.clicked.connect(self.import_from_excel)
        top_bar_layout.addWidget(self.btn_import_excel)
        
        layout.addWidget(top_bar_widget)

        # Table Styling
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Tanggal", "Deskripsi", "No. Referensi", "Aksi"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #d1d8e0;
                border: 1px solid #a5b1c2;
                border-radius: 4px;
                alternate-background-color: #f1f2f6;
            }
            QHeaderView::section {
                background-color: #4b6584;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """)
        
        self.table.setColumnHidden(0, True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        self.table.cellDoubleClicked.connect(self.on_journal_double_clicked)
        layout.addWidget(self.table)

        self.status_label = QLabel("Memuat jurnal...")
        self.status_label.setStyleSheet("color: #2d3436; font-weight: bold;")
        layout.addWidget(self.status_label)

    def load_journals(self):
        self.table.setRowCount(0)
        try:
            summaries = self.db.get_journal_summaries()
            self.table.setRowCount(len(summaries))
            for row, summary in enumerate(summaries):
                journal_id, date, description, ref_no = summary
                
                # Create items with explicit black color
                items = [str(journal_id), date, description, ref_no]
                for col, text in enumerate(items):
                    item = QTableWidgetItem(text)
                    item.setForeground(Qt.GlobalColor.black)
                    self.table.setItem(row, col, item)
                
                self.add_actions_to_row(row, journal_id)
            self.status_label.setText(f"Menampilkan {len(summaries)} entri jurnal.")
        except Exception as e:
            self.status_label.setText(f"Error: {e}")

    def add_actions_to_row(self, row, journal_id):
        actions_widget = QWidget()
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(5, 2, 5, 2)
        actions_layout.setSpacing(8)

        btn_edit = QPushButton("✏️ Edit")
        btn_edit.setStyleSheet("""
            QPushButton { background-color: #f39c12; color: white; border-radius: 4px; padding: 4px 8px; font-weight: bold; }
            QPushButton:hover { background-color: #e67e22; }
        """)
        btn_edit.clicked.connect(lambda: self.on_edit_button_clicked(journal_id))

        btn_delete = QPushButton("🗑️ Hapus")
        btn_delete.setStyleSheet("""
            QPushButton { background-color: #e74c3c; color: white; border-radius: 4px; padding: 4px 8px; font-weight: bold; }
            QPushButton:hover { background-color: #c0392b; }
        """)
        btn_delete.clicked.connect(lambda: self.on_delete_button_clicked(journal_id))

        actions_layout.addWidget(btn_edit)
        actions_layout.addWidget(btn_delete)
        self.table.setCellWidget(row, 4, actions_widget)

    def on_edit_button_clicked(self, journal_id):
        self.edit_journal_requested.emit(journal_id)

    def on_delete_button_clicked(self, journal_id):
        reply = QMessageBox.question(self, "Konfirmasi", f"Hapus Jurnal ID: {journal_id}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if self.db.delete_journal_entry(journal_id):
                self.load_journals()

    def on_journal_double_clicked(self, row, column):
        if column == 4: return
        journal_id_item = self.table.item(row, 0)
        if journal_id_item:
            self.journal_selected.emit(int(journal_id_item.text()))

    def filter_journals(self, text):
        text = text.lower()
        for row in range(self.table.rowCount()):
            desc = self.table.item(row, 2).text().lower() if self.table.item(row, 2) else ""
            ref = self.table.item(row, 3).text().lower() if self.table.item(row, 3) else ""
            self.table.setRowHidden(row, not (text in desc or text in ref))

    def open_beginning_balance_dialog(self):
        if BeginningBalanceDialog(self).exec() == QDialog.DialogCode.Accepted:
            self.load_journals()

    def import_from_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Jurnal", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                df = pd.read_excel(file_path, sheet_name="Jurnal Umum")
                # Simplified import logic for brevity, keeping existing functionality
                journal_entries_to_import = []
                for (date, description, ref_no), group in df.groupby(["Tanggal", "Deskripsi", "No. Referensi"]):
                    # Pastikan tanggal hanya YYYY-MM-DD (ambil 10 karakter pertama jika berupa string datetime)
                    clean_date = str(date).split(' ')[0] if ' ' in str(date) else str(date)
                    if len(clean_date) > 10: clean_date = clean_date[:10]
                    
                    details = []
                    for _, row in group.iterrows():
                        details.append({
                            "account_code": str(row["Kode Akun"]),
                            "debit": float(row["Debit"]) if pd.notna(row["Debit"]) else 0.0,
                            "credit": float(row["Kredit"]) if pd.notna(row["Kredit"]) else 0.0,
                            "cash_flow_activity": str(row.get("Aktivitas Arus Kas", ""))
                        })
                    journal_entries_to_import.append({"date": clean_date, "description": str(description), "reference_no": str(ref_no), "details": details})
                
                s, f, err = self.db.bulk_add_journal_entries(journal_entries_to_import)
                QMessageBox.information(self, "Hasil Impor", f"{s} Sukses, {f} Gagal.")
                self.load_journals()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal impor: {e}")

    def download_journal_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Simpan Template Jurnal", "template_jurnal_import.xlsx", "Excel Files (*.xlsx)"
        )
        
        if file_path:
            try:
                # Definisikan kolom yang sesuai dengan fungsi import_from_excel
                columns = [
                    "Tanggal", 
                    "No. Referensi", 
                    "Deskripsi", 
                    "Kode Akun", 
                    "Debit", 
                    "Kredit",
                    "Kategori Arus Kas",
                    "Aktivitas Arus Kas"
                ]
                
                # Buat data contoh
                example_data = [
                    ["2026-12-31", "REF-001", "Contoh Transaksi", "1101", 1000000, 0, "ARUS KAS DARI AKTIVITAS OPERASI", "Penerimaan dari Sumbangan/Donasi"],
                    ["2026-12-31", "REF-001", "Contoh Transaksi", "4101", 0, 1000000, "", ""]
                ]
                
                df = pd.DataFrame(example_data, columns=columns)
                
                # Simpan ke Excel dengan nama sheet yang sesuai: 'Jurnal Umum'
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name="Jurnal Umum")
                    
                QMessageBox.information(self, "Sukses", f"Template berhasil dibuat di:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal membuat template: {e}")
