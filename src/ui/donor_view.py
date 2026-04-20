from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView, 
                             QLineEdit, QDialog, QFormLayout, QMessageBox, QComboBox, QTextEdit)
from PySide6.QtCore import Qt
from ..database_manager import DatabaseManager

class DonorDialog(QDialog):
    def __init__(self, donor_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Form Donatur")
        self.setMinimumWidth(400)
        self.donor_data = donor_data
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.name_edit = QLineEdit()
        self.phone_edit = QLineEdit()
        self.address_edit = QTextEdit()
        self.address_edit.setMaximumHeight(80)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Perorangan", "Perusahaan/Lembaga", "Hamba Allah"])
        self.desc_edit = QLineEdit()

        layout.addRow("Nama Donatur:", self.name_edit)
        layout.addRow("Telepon:", self.phone_edit)
        layout.addRow("Alamat:", self.address_edit)
        layout.addRow("Tipe:", self.type_combo)
        layout.addRow("Keterangan:", self.desc_edit)

        self.btn_save = QPushButton("Simpan")
        self.btn_save.clicked.connect(self.accept)
        layout.addRow(self.btn_save)

        if self.donor_data:
            self.name_edit.setText(self.donor_data[1])
            self.phone_edit.setText(self.donor_data[2])
            self.address_edit.setPlainText(self.donor_data[3])
            self.type_combo.setCurrentText(self.donor_data[4])
            self.desc_edit.setText(self.donor_data[5])

    def get_data(self):
        return {
            "name": self.name_edit.text(),
            "phone": self.phone_edit.text(),
            "address": self.address_edit.toPlainText(),
            "type": self.type_combo.currentText(),
            "desc": self.desc_edit.text()
        }

class DonorView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QHBoxLayout()
        title = QLabel("🤝 MANAJEMEN DONATUR")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2d3436;")
        header.addWidget(title)
        header.addStretch()
        
        self.btn_add = QPushButton("+ Tambah Donatur")
        self.btn_add.setStyleSheet("background-color: #3498db; color: white; padding: 8px 15px; font-weight: bold;")
        self.btn_add.clicked.connect(self.open_add_dialog)
        header.addWidget(self.btn_add)
        layout.addLayout(header)

        # Search
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Cari nama donatur atau alamat...")
        self.search_edit.textChanged.connect(self.load_donors)
        search_layout.addWidget(QLabel("Cari:"))
        search_layout.addWidget(self.search_edit)
        layout.addLayout(search_layout)

        # Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["ID", "Nama", "Telepon", "Tipe", "Keterangan", "Aksi"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setStyleSheet("background-color: white; color: black;")
        layout.addWidget(self.table)
        
        self.load_donors()

    def load_donors(self):
        self.table.setRowCount(0)
        search_text = self.search_edit.text().lower()
        donors = self.db.get_donors()
        
        for donor in donors:
            if search_text and search_text not in donor[1].lower() and search_text not in donor[3].lower():
                continue
                
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            self.table.setItem(row, 0, QTableWidgetItem(str(donor[0])))
            self.table.setItem(row, 1, QTableWidgetItem(donor[1]))
            self.table.setItem(row, 2, QTableWidgetItem(donor[2]))
            self.table.setItem(row, 3, QTableWidgetItem(donor[4]))
            self.table.setItem(row, 4, QTableWidgetItem(donor[5]))

            btn_box = QWidget()
            btn_layout = QHBoxLayout(btn_box)
            btn_layout.setContentsMargins(2, 2, 2, 2)
            
            btn_edit = QPushButton("Edit")
            btn_edit.setStyleSheet("background-color: #3498db; color: white;")
            btn_edit.clicked.connect(lambda checked, d=donor: self.open_edit_dialog(d))
            
            btn_del = QPushButton("Hapus")
            btn_del.setStyleSheet("background-color: #e74c3c; color: white;")
            btn_del.clicked.connect(lambda checked, i=donor[0]: self.delete_donor(i))
            
            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_del)
            self.table.setCellWidget(row, 5, btn_box)

    def open_add_dialog(self):
        d = DonorDialog(parent=self)
        if d.exec() == QDialog.DialogCode.Accepted:
            data = d.get_data()
            self.db.add_donor(data['name'], data['phone'], data['address'], data['type'], data['desc'])
            self.load_donors()

    def open_edit_dialog(self, donor):
        d = DonorDialog(donor_data=donor, parent=self)
        if d.exec() == QDialog.DialogCode.Accepted:
            data = d.get_data()
            self.db.update_donor(donor[0], data['name'], data['phone'], data['address'], data['type'], data['desc'])
            self.load_donors()

    def delete_donor(self, donor_id):
        if QMessageBox.question(self, "Konfirmasi", "Hapus donatur ini?") == QMessageBox.StandardButton.Yes:
            self.db.delete_donor(donor_id)
            self.load_donors()
