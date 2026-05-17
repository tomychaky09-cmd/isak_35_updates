from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QLabel, 
                             QDateEdit, QLineEdit, QComboBox, QMessageBox, QCompleter, QFrame)
from PySide6.QtCore import QDate, Qt, Signal
from ..database_manager import DatabaseManager
from ..ai_manager import AIManager

class JournalEntryView(QWidget):
    # Sinyal untuk memberitahu main_window agar kembali ke daftar
    back_requested = Signal()

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager('database/foundation_finance.db')
        self.ai = AIManager() # Inisialisasi AI Manager
        self.editing_journal_id = None
        self.account_list = {}
        self.full_account_info = [] # Simpan info lengkap untuk AI
        self.cf_mapping = {} # {Kategori_Utama: [List_Aktivitas]}
        self._populate_account_list()
        self._populate_cf_mapping()
        self.init_ui()

    def _populate_account_list(self):
        accounts = self.db.get_accounts()
        # accounts format: (id, code, name, type, category, notes)
        self.account_list = {f"{acc[1]} - {acc[2]}": acc[0] for acc in accounts}
        self.full_account_info = [
            {"id": acc[0], "code": acc[1], "name": acc[2], "type": acc[3], "category": acc[4]}
            for acc in accounts
        ]

    def _populate_cf_mapping(self):
        categories = self.db.get_cash_flow_categories()
        # categories format: (id, name, main_category)
        self.cf_mapping = {}
        for _, name, main_cat in categories:
            if main_cat not in self.cf_mapping:
                self.cf_mapping[main_cat] = []
            self.cf_mapping[main_cat].append(name)

    def init_ui(self):
        self.setStyleSheet("background-color: #d1d8e0;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Top bar with Back Button
        top_bar = QHBoxLayout()
        self.btn_back = QPushButton("⬅️ Kembali ke Daftar")
        top_bar.addWidget(self.btn_back)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Header Container (Tanggal, Deskripsi, Ref)
        header_box = QFrame()
        header_box.setStyleSheet("background-color: #ffffff; border-radius: 8px; border: 1px solid #a5b1c2;")
        header_layout = QHBoxLayout(header_box)
        
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Masukkan deskripsi transaksi...")
        self.ref_input = QLineEdit()
        
        # Tombol Saran AI
        self.btn_ai = QPushButton("🤖 Saran")
        self.btn_ai.setStyleSheet("""
            QPushButton { 
                background-color: #8e44ad; color: white; font-weight: bold; 
                padding: 5px 15px; border-radius: 4px;
            }
            QPushButton:hover { background-color: #9b59b6; }
        """)
        
        header_layout.addWidget(QLabel("Tanggal:"))
        header_layout.addWidget(self.date_input)
        header_layout.addWidget(QLabel("Deskripsi:"))
        header_layout.addWidget(self.desc_input, 2)
        header_layout.addWidget(self.btn_ai)
        header_layout.addWidget(QLabel("Ref:"))
        header_layout.addWidget(self.ref_input)
        layout.addWidget(header_box)

        # Table for journal details (5 columns now)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nama Akun", "Debet", "Kredit", "Kategori Arus Kas", "Aktivitas Arus Kas"])
        self.table.setStyleSheet("""
            QTableWidget { background-color: #ffffff; color: #000000; border: 1px solid #a5b1c2; }
            QHeaderView::section { background-color: #4b6584; color: white; padding: 8px; font-weight: bold; }
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 250)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(1, 100)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(2, 100)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(3, 180)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.table)

        # Footer
        footer_layout = QHBoxLayout()
        self.btn_add_row = QPushButton("+ Tambah Baris")
        self.label_total_debit = QLabel("Total Debet: 0")
        self.label_total_credit = QLabel("Total Kredit: 0")
        self.btn_save = QPushButton("💾 Simpan Jurnal")
        
        footer_layout.addWidget(self.btn_add_row)
        footer_layout.addStretch()
        footer_layout.addWidget(self.label_total_debit)
        footer_layout.addWidget(self.label_total_credit)
        footer_layout.addWidget(self.btn_save)
        layout.addLayout(footer_layout)

        # Connect signals
        self.btn_back.clicked.connect(self.back_requested.emit)
        self.btn_add_row.clicked.connect(self.add_new_row)
        self.btn_save.clicked.connect(self.save_journal)
        self.btn_ai.clicked.connect(self.get_ai_suggestion)
        self.table.itemChanged.connect(self.update_totals)
        
        self.reset_form()

    def get_ai_suggestion(self):
        desc = self.desc_input.text().strip()
        if not desc:
            QMessageBox.warning(self, "AI Assistant", "Silakan isi deskripsi terlebih dahulu.")
            return

        self.btn_ai.setText("⏳ Menganalisis...")
        self.btn_ai.setEnabled(False)
        
        # Jalankan di background jika memungkinkan, tapi untuk prototipe ini kita gunakan blocking call
        # dengan repaint agar UI tidak terlihat hang (sebenarnya lebih baik pakai QThread)
        self.repaint()
        
        suggestion = self.ai.get_accounting_suggestion(desc, self.full_account_info, self.cf_mapping)
        
        self.btn_ai.setText("🤖 Saran AI")
        self.btn_ai.setEnabled(True)

        if "error" in suggestion:
            QMessageBox.critical(self, "AI Error", f"Gagal mendapatkan saran: {suggestion['error']}")
            return

        # Tampilkan saran ke user
        msg = f"<b>Kesimpulan AI:</b><br>{suggestion.get('kesimpulan', 'Analisis tidak tersedia.')}<br><br><b>Saran Jurnal:</b><br>"
        for item in suggestion.get('saran', []):
            akun = item.get('akun', 'Akun tidak dikenal')
            posisi = item.get('posisi', 'Debet/Kredit')
            alasan = item.get('alasan', '') # Gunakan string kosong jika tidak ada
            
            msg += f"- {akun} ({posisi})"
            if alasan:
                msg += f": {alasan}"
            msg += "<br>"
        
        msg += "<br>Apakah Anda ingin menerapkan saran ini ke tabel?"
        
        reply = QMessageBox.question(self, "AI Assistant", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.apply_ai_suggestion(suggestion)

    def apply_ai_suggestion(self, suggestion_data):
        saran_list = suggestion_data.get('saran', [])
        # Ambil nominal, bersihkan jika AI memberikan string berformat (Rp 500.000)
        raw_nominal = str(suggestion_data.get('nominal', 0))
        import re
        clean_nominal_str = "".join(re.findall(r'\d+', raw_nominal))
        nominal = float(clean_nominal_str) if clean_nominal_str else 0
        
        self.table.setRowCount(0)
        for i, item in enumerate(saran_list):
            self.add_new_row()
            combo = self.table.cellWidget(i, 0)
            if combo:
                target_account = item.get('akun', '')
                found = False
                
                # 1. Cek match persis
                if target_account in self.account_list:
                    combo.setCurrentText(target_account)
                    found = True
                
                # 2. Cek berdasarkan kode (jika AI hanya kasih kode di awal)
                if not found:
                    code_match = re.search(r'^(\d+)', target_account)
                    if code_match:
                        target_code = code_match.group(1)
                        for acc_full_name in self.account_list.keys():
                            if acc_full_name.startswith(target_code):
                                combo.setCurrentText(acc_full_name)
                                found = True
                                break
                
                # 3. Cek berdasarkan nama saja
                if not found:
                    for acc_full_name in self.account_list.keys():
                        if target_account.lower() in acc_full_name.lower():
                            combo.setCurrentText(acc_full_name)
                            found = True
                            break
            
            # Isi nominal
            posisi = item.get('posisi', '').lower()
            if 'debet' in posisi or 'debit' in posisi:
                self.table.item(i, 1).setText(f"{nominal:,.0f}")
                self.table.item(i, 2).setText("0")
            elif 'kredit' in posisi or 'credit' in posisi:
                self.table.item(i, 1).setText("0")
                self.table.item(i, 2).setText(f"{nominal:,.0f}")
            
            # Isi Arus Kas jika ada saran
            main_cat = item.get('arus_kas_utama', '')
            activity = item.get('arus_kas_aktivitas', '')
            
            if main_cat:
                main_combo = self.table.cellWidget(i, 3)
                if main_combo:
                    # Cari index yang paling cocok
                    for idx in range(main_combo.count()):
                        if main_cat.lower() in main_combo.itemText(idx).lower():
                            main_combo.setCurrentIndex(idx)
                            # Trigger update untuk activity combo
                            self._update_activity_options(i, main_combo.itemText(idx))
                            
                            if activity:
                                act_combo = self.table.cellWidget(i, 4)
                                if act_combo:
                                    # Cari aktivitas yang paling mirip
                                    for a_idx in range(act_combo.count()):
                                        if activity.lower() in act_combo.itemText(a_idx).lower():
                                            act_combo.setCurrentIndex(a_idx)
                                            break
                            break
        
        self.update_totals()
            
    def _setup_account_combo_widget(self, row):
        combo = QComboBox()
        combo.setEditable(True)
        items = list(self.account_list.keys())
        combo.addItems(items)
        completer = QCompleter(items)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        combo.setCompleter(completer)
        self.table.setCellWidget(row, 0, combo)
        return combo

    def _setup_cf_widgets(self, row):
        # 1. Main Category Combo
        main_combo = QComboBox()
        main_categories = ["", "Tidak Berlaku"] + list(self.cf_mapping.keys())
        main_combo.addItems(main_categories)
        self.table.setCellWidget(row, 3, main_combo)
        
        # 2. Activity Combo (linked to main)
        activity_combo = QComboBox()
        activity_combo.addItems([""])
        self.table.setCellWidget(row, 4, activity_combo)
        
        # Connect change signal
        main_combo.currentTextChanged.connect(lambda text: self._update_activity_options(row, text))
        return main_combo, activity_combo

    def _update_activity_options(self, row, main_cat):
        activity_combo = self.table.cellWidget(row, 4)
        if not activity_combo: return
        
        activity_combo.clear()
        if main_cat in self.cf_mapping:
            activity_combo.addItems([""] + self.cf_mapping[main_cat])
        else:
            activity_combo.addItems([""])

    def setup_row_widgets(self, row):
        self._setup_account_combo_widget(row)
        for col in [1, 2]:
            it = QTableWidgetItem("0")
            it.setForeground(Qt.GlobalColor.black)
            it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, col, it)
        self._setup_cf_widgets(row)

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
        
        raw_date = str(h[0])
        clean_date = raw_date.split(' ')[0] if ' ' in raw_date else raw_date
        self.date_input.setDate(QDate.fromString(clean_date[:10], "yyyy-MM-dd"))
        self.desc_input.setText(h[1]); self.ref_input.setText(h[2])
        self.table.setRowCount(len(det))
        
        # Get category mapping for reverse lookup
        all_cats = self.db.get_cash_flow_categories()
        cat_to_main = {c[1]: c[2] for c in all_cats}
        
        for r, itm in enumerate(det):
            code, name, deb, cre, activity_name = itm
            self.table.setItem(r, 1, QTableWidgetItem(str(deb)))
            self.table.setItem(r, 2, QTableWidgetItem(str(cre)))
            self._setup_account_combo_widget(r).setCurrentText(f"{code} - {name}")
            
            main_combo, act_combo = self._setup_cf_widgets(r)
            if activity_name and activity_name in cat_to_main:
                main_combo.setCurrentText(cat_to_main[activity_name])
                act_combo.setCurrentText(activity_name)
            elif activity_name == "Tidak Berlaku":
                main_combo.setCurrentText("Tidak Berlaku")
                
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
            
            # Ambil aktivitas yang dipilih (kolom ke-5)
            act_combo = self.table.cellWidget(r, 4)
            activity = act_combo.currentText() if act_combo else None
            if activity == "": activity = None
            
            try:
                d = float(self.table.item(r, 1).text().replace(',', ''))
                c = float(self.table.item(r, 2).text().replace(',', ''))
                if d > 0 or c > 0:
                    details.append({'account_id': self.account_list[ac_txt], 'debit': d, 'credit': c, 'cash_flow_activity': activity})
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
