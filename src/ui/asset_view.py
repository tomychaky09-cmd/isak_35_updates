from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView, 
                             QLineEdit, QDialog, QFormLayout, QDateEdit, QDoubleSpinBox,
                             QSpinBox, QMessageBox, QFileDialog)
from PySide6.QtCore import Qt, QDate
from ..database_manager import DatabaseManager
import pandas as pd
import os

class AssetDialog(QDialog):
    def __init__(self, asset_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Form Aset Inventaris")
        self.setMinimumWidth(400)
        self.asset_data = asset_data
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.date_edit = QDateEdit(calendarPopup=True)
        self.date_edit.setDate(QDate.currentDate())
        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.location_edit = QLineEdit()
        self.value_edit = QDoubleSpinBox()
        self.value_edit.setRange(0, 1000000000)
        self.value_edit.setGroupSeparatorShown(True)
        self.qty_edit = QSpinBox()
        self.qty_edit.setRange(1, 10000)
        self.desc_edit = QLineEdit()

        layout.addRow("Tanggal Perolehan:", self.date_edit)
        layout.addRow("Kode Aset:", self.code_edit)
        layout.addRow("Nama Barang:", self.name_edit)
        layout.addRow("Lokasi:", self.location_edit)
        layout.addRow("Nilai Perkiraan (Rp):", self.value_edit)
        layout.addRow("Jumlah:", self.qty_edit)
        layout.addRow("Keterangan:", self.desc_edit)

        self.btn_save = QPushButton("Simpan")
        self.btn_save.clicked.connect(self.accept)
        layout.addRow(self.btn_save)

        if self.asset_data:
            self.date_edit.setDate(QDate.fromString(self.asset_data[1], "yyyy-MM-dd"))
            self.code_edit.setText(self.asset_data[2])
            self.name_edit.setText(self.asset_data[3])
            self.location_edit.setText(self.asset_data[4])
            self.value_edit.setValue(self.asset_data[5])
            self.qty_edit.setValue(self.asset_data[6])
            self.desc_edit.setText(self.asset_data[7])

    def get_data(self):
        return {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "code": self.code_edit.text(),
            "name": self.name_edit.text(),
            "location": self.location_edit.text(),
            "value": self.value_edit.value(),
            "qty": self.qty_edit.setValue(self.qty_edit.value()), # Actually just return value
            "qty_val": self.qty_edit.value(),
            "desc": self.desc_edit.text()
        }

class AssetView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QHBoxLayout()
        title = QLabel("📦 INVENTARIS ASET YAYASAN")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2d3436;")
        header.addWidget(title)
        header.addStretch()
        
        self.btn_add = QPushButton("+ Tambah Aset")
        self.btn_add.setStyleSheet("background-color: #27ae60; color: white; padding: 8px 15px; font-weight: bold;")
        self.btn_add.clicked.connect(self.open_add_dialog)
        header.addWidget(self.btn_add)
        
        self.btn_import = QPushButton("📥 Import Excel")
        self.btn_import.clicked.connect(self.import_excel)
        header.addWidget(self.btn_import)
        
        self.btn_export = QPushButton("📤 Export Excel")
        self.btn_export.clicked.connect(self.export_excel)
        header.addWidget(self.btn_export)
        
        layout.addLayout(header)

        # Search
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cari nama aset atau lokasi...")
        self.search_edit.textChanged.connect(self.load_assets)
        search_layout.addWidget(QLabel("Cari:"))
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Tanggal", "Kode", "Nama Barang", "Lokasi", "Nilai (Rp)", "Jumlah", "Aksi"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: white; color: black;")
        layout.addWidget(self.table)
        
        self.load_assets()

    def load_assets(self):
        self.table.setRowCount(0)
        search_text = self.search_edit.text().lower()
        assets = self.db.get_assets_inventory()
        
        for asset in assets:
            if search_text and search_text not in asset[3].lower() and search_text not in asset[4].lower():
                continue
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(asset[0])))
            self.table.setItem(row, 1, QTableWidgetItem(asset[1]))
            self.table.setItem(row, 2, QTableWidgetItem(asset[2]))
            self.table.setItem(row, 3, QTableWidgetItem(asset[3]))
            self.table.setItem(row, 4, QTableWidgetItem(asset[4]))
            
            val_item = QTableWidgetItem(f"{asset[5]:,.0f}")
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, 5, val_item)
            
            qty_item = QTableWidgetItem(str(asset[6]))
            qty_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 6, qty_item)

            btn_box = QWidget()
            btn_layout = QHBoxLayout(btn_box)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            btn_edit = QPushButton("Edit")
            btn_edit.setStyleSheet("background-color: #3498db; color: white;")
            btn_edit.clicked.connect(lambda checked, a=asset: self.open_edit_dialog(a))
            
            btn_del = QPushButton("Hapus")
            btn_del.setStyleSheet("background-color: #e74c3c; color: white;")
            btn_del.clicked.connect(lambda checked, i=asset[0]: self.delete_asset(i))
            
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 7, btn_box)

    def open_add_dialog(self):
        d = AssetDialog(parent=self)
        if d.exec() == QDialog.DialogCode.Accepted:
            data = d.get_data()
            self.db.add_asset_inventory(data['date'], data['code'], data['name'], data['location'], data['value'], data['qty_val'], data['desc'])
            self.load_assets()

    def open_edit_dialog(self, asset):
        d = AssetDialog(asset_data=asset, parent=self)
        if d.exec() == QDialog.DialogCode.Accepted:
            data = d.get_data()
            self.db.update_asset_inventory(asset[0], data['date'], data['code'], data['name'], data['location'], data['value'], data['qty_val'], data['desc'])
            self.load_assets()

    def delete_asset(self, asset_id):
        if QMessageBox.question(self, "Konfirmasi", "Hapus aset ini?") == QMessageBox.StandardButton.Yes:
            self.db.delete_asset_inventory(asset_id)
            self.load_assets()

    def export_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Aset", "Daftar_Aset_Yayasan.xlsx", "Excel Files (*.xlsx)")
        if path:
            assets = self.db.get_assets_inventory()
            df = pd.DataFrame(assets, columns=["ID", "Tanggal", "Kode", "Nama Barang", "Lokasi", "Nilai", "Jumlah", "Keterangan"])
            df.to_excel(path, index=False)
            QMessageBox.information(self, "Sukses", "Data aset berhasil diekspor.")

    def import_excel(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Aset", "", "Excel Files (*.xlsx)")
        if path:
            try:
                df = pd.read_excel(path)
                # Map column names to DB fields
                assets_data = []
                for _, row in df.iterrows():
                    assets_data.append({
                        'date': str(row.get('Tanggal', QDate.currentDate().toString("yyyy-MM-dd"))),
                        'code': str(row.get('Kode', '')),
                        'name': str(row.get('Nama Barang', '')),
                        'location': str(row.get('Lokasi', '')),
                        'estimated_value': float(row.get('Nilai', 0)),
                        'quantity': int(row.get('Jumlah', 1)),
                        'description': str(row.get('Keterangan', ''))
                    })
                if self.db.bulk_add_assets(assets_data):
                    QMessageBox.information(self, "Sukses", "Data aset berhasil diimpor.")
                    self.load_assets()
                else:
                    QMessageBox.warning(self, "Gagal", "Gagal mengimpor data. Pastikan format benar.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Terjadi kesalahan: {e}")
