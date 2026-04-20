from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel, 
                             QDateEdit, QLineEdit, QComboBox, QMessageBox, QCompleter, QFrame)
from PySide6.QtCore import QDate, Qt, Signal
from ..database_manager import DatabaseManager

class JournalEntryView(QWidget):
    # Sinyal untuk memberitahu main_window agar kembali ke daftar
    back_requested = Signal()

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager('database/foundation_finance.db')
        self.editing_journal_id = None
        self.account_list = {}
        self._populate_account_list()
        self.init_ui()

    def _populate_account_list(self):
        accounts = self.db.get_accounts()
        self.account_list = {f"{acc[1]} - {acc[2]}": acc[0] for acc in accounts}

    def init_ui(self):
        self.setStyleSheet("background-color: #d1d8e0;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top bar with Back Button
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton("⬅️ Kembali ke Daftar")
        self.btn_back.setStyleSheet("""
            QPushButton { background-color: #7f8c8d; color: white; padding: 8px 15px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #636e72; }
        """)
        self.btn_back.clicked.connect(self.back_requested.emit)
        top_bar.addWidget(self.btn_back)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Header Container (Tanggal, Deskripsi, Ref)
        header_box = QFrame()
        header_box.setStyleSheet("background-color: #ffffff; border-radius: 8px; border: 1px solid #a5b1c2;")
        header_layout = QHBoxLayout(header_box)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setStyleSheet("background-color: white; color: black; padding: 5px; border: 1px solid #ced4da;")
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Deskripsi Transaksi...")
        self.desc_input.setStyleSheet("background-color: white; color: black; padding: 5px; border: 1px solid #ced4da;")
        
        self.ref_input = QLineEdit()
        self.ref_input.setPlaceholderText("No. Referensi...")
        self.ref_input.setStyleSheet("background-color: white; color: black; padding: 5px; border: 1px solid #ced4da;")
        
        header_layout.addWidget(QLabel("Tanggal:"))
        header_layout.addWidget(self.date_input)
        header_layout.addWidget(QLabel("Deskripsi:"))
        header_layout.addWidget(self.desc_input, 2) # Give description more space
        header_layout.addWidget(QLabel("Ref:"))
        header_layout.addWidget(self.ref_input)
        
        layout.addWidget(header_box)

        # Table Styling with Adjusted Widths
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nama Akun", "Debet", "Kredit", "Aktivitas Arus Kas"])
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #d1d8e0;
                border: 1px solid #a5b1c2;
                border-radius: 4px;
            }
            QHeaderView::section {
                background-color: #4b6584;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """)
        
        # Penyesuaian Lebar Kolom:
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 250) # Kecilkan kolom Akun (250px)
        
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 120) # Lebar Debet tetap
        
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(2, 120) # Lebar Kredit tetap
        
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Lebarkan Arus Kas (Stretch)
        
        layout.addWidget(self.table)

        # Footer
        footer_layout = QHBoxLayout()
        self.btn_add_row = QPushButton("+ Tambah Baris")
        self.btn_add_row.setStyleSheet("background-color: #2c3e50; color: white; padding: 8px 15px; border-radius: 4px; font-weight: bold;")
        self.btn_add_row.clicked.connect(self.add_new_row)
        
        self.label_total_debit = QLabel("Total Debet: 0")
        self.label_total_credit = QLabel("Total Kredit: 0")
        
        self.btn_save = QPushButton("💾 Simpan Jurnal")
        self.btn_save.clicked.connect(self.save_journal)
        
        footer_layout.addWidget(self.btn_add_row)
        footer_layout.addStretch()
        footer_layout.addWidget(self.label_total_debit)
        footer_layout.addWidget(self.label_total_credit)
        footer_layout.addWidget(self.btn_save)
        layout.addLayout(footer_layout)

        self.table.itemChanged.connect(self.update_totals)
        self.reset_form()

    def _setup_account_combo_widget(self, row):
        combo = QComboBox()
        combo.setEditable(True)
        combo.setStyleSheet("background-color: white; color: black; border: none;")
        items = list(self.account_list.keys())
        combo.addItems(items)
        completer = QCompleter(items)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        combo.setCompleter(completer)
        self.table.setCellWidget(row, 0, combo)
        return combo

    def _setup_cash_flow_combo_widget(self, row):
        cash_flow_categories = self.db.get_cash_flow_categories()
        activities = ["", "Tidak Berlaku"] + [c[1] for c in cash_flow_categories]
        combo = QComboBox()
        combo.addItems(activities)
        combo.setStyleSheet("background-color: white; color: black; border: none;")
        self.table.setCellWidget(row, 3, combo)
        return combo

    def setup_row_widgets(self, row):
        self._setup_account_combo_widget(row)
        for col in [1, 2]:
            it = QTableWidgetItem("0")
            it.setForeground(Qt.GlobalColor.black)
            it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, col, it)
        self._setup_cash_flow_combo_widget(row)

    def add_new_row(self):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.setup_row_widgets(r)

    def update_totals(self):
        td = 0; tc = 0
        for r in range(self.table.rowCount()):
            try:
                d = self.table.item(r, 1); c = self.table.item(r, 2)
                td += float(d.text().replace(',', '')) if d else 0
                tc += float(c.text().replace(',', '')) if c else 0
            except: continue
        self.label_total_debit.setText(f"Debet: Rp {td:,.0f}")
        self.label_total_credit.setText(f"Kredit: Rp {tc:,.0f}")
        col = "#27ae60" if abs(td-tc) < 0.01 and td > 0 else "#e74c3c"
        self.label_total_debit.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 14px;")
        self.label_total_credit.setStyleSheet(f"color: {col}; font-weight: bold; font-size: 14px;")

    def reset_form(self):
        self.editing_journal_id = None
        self.desc_input.clear(); self.ref_input.clear()
        self.date_input.setDate(QDate.currentDate())
        self.table.setRowCount(0); self.table.setRowCount(2)
        for r in range(2): self.setup_row_widgets(r)
        self.update_totals()
        self.btn_save.setText("💾 Simpan Jurnal")
        self.btn_save.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px;")

    def load_journal_for_edit(self, j_id):
        self.editing_journal_id = j_id
        d = self.db.get_journal_details(j_id)
        if not d: return
        h = d['header']; det = d['details']
        
        # Bersihkan tanggal dari jam (00:00:00) jika ada
        raw_date = str(h[0])
        clean_date = raw_date.split(' ')[0] if ' ' in raw_date else raw_date
        if len(clean_date) > 10: clean_date = clean_date[:10]
        
        self.date_input.setDate(QDate.fromString(clean_date, "yyyy-MM-dd"))
        self.desc_input.setText(h[1]); self.ref_input.setText(h[2])
        self.table.setRowCount(len(det))
        for r, itm in enumerate(det):
            code, name, deb, cre, cf = itm
            self.table.setItem(r, 1, QTableWidgetItem(str(deb)))
            self.table.setItem(r, 2, QTableWidgetItem(str(cre)))
            self.table.item(r, 1).setForeground(Qt.GlobalColor.black)
            self.table.item(r, 2).setForeground(Qt.GlobalColor.black)
            self._setup_account_combo_widget(r).setCurrentText(f"{code} - {name}")
            self._setup_cash_flow_combo_widget(r).setCurrentText(cf if cf else "Tidak Berlaku")
        self.update_totals()
        self.btn_save.setText(f"🆙 Update Jurnal #{j_id}")
        self.btn_save.setStyleSheet("background-color: #f39c12; color: white; font-weight: bold; padding: 10px 20px; border-radius: 6px;")

    def save_journal(self):
        date = self.date_input.date().toString("yyyy-MM-dd")
        desc = self.desc_input.text().strip()
        ref = self.ref_input.text().strip()
        if not desc:
            QMessageBox.warning(self, "Peringatan", "Deskripsi tidak boleh kosong")
            return
        details = []; td = 0; tc = 0
        for r in range(self.table.rowCount()):
            combo = self.table.cellWidget(r, 0)
            if not combo: continue
            ac_txt = combo.currentText()
            if ac_txt not in self.account_list: continue
            
            cf_combo = self.table.cellWidget(r, 3)
            cf = cf_combo.currentText() if cf_combo else ""
            if cf in ["Tidak Berlaku", ""]: cf = None
            
            try:
                d = float(self.table.item(r, 1).text().replace(',', ''))
                c = float(self.table.item(r, 2).text().replace(',', ''))
                if d > 0 or c > 0:
                    details.append({'account_id': self.account_list[ac_txt], 'debit': d, 'credit': c, 'cash_flow_activity': cf})
                    td += d; tc += c
            except: continue
            
        if not details:
            QMessageBox.warning(self, "Peringatan", "Data jurnal tidak lengkap")
            return
            
        if abs(td-tc) > 0.01:
            QMessageBox.critical(self, "Gagal", "Jurnal tidak seimbang!")
            return
            
        if self.editing_journal_id:
            if self.db.update_journal_entry(self.editing_journal_id, date, desc, ref, details):
                QMessageBox.information(self, "Sukses", "Update Berhasil"); self.back_requested.emit()
        else:
            if self.db.add_journal_entry(date, desc, ref, details):
                QMessageBox.information(self, "Sukses", "Simpan Berhasil"); self.back_requested.emit()
