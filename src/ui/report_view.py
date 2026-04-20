from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView, 
                             QTabWidget, QComboBox, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from ..database_manager import DatabaseManager
from ..report_generator import ReportGenerator

class ReportView(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager('database/foundation_finance.db')
        self.report_gen = ReportGenerator(self.db)
        self.init_ui()

    def init_ui(self):
        # Set Page Background
        self.setStyleSheet("background-color: #d1d8e0;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header Container
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("📑 LAPORAN KEUANGAN YAYASAN")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #2d3436;")
        
        btn_refresh = QPushButton("🔄 Perbarui Data")
        btn_refresh.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        btn_refresh.clicked.connect(self.load_all)
                
        self.btn_export = QPushButton("📤 Ekspor Excel")
        self.btn_export.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 10px 15px; border-radius: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.btn_export.clicked.connect(self.handle_export)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(btn_refresh)
        header_layout.addWidget(self.btn_export)
        layout.addWidget(header_widget)

        # Tabs Styling
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #a5b1c2;
                background-color: #ffffff;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #b2bec3;
                color: #2d3436;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                font-weight: bold;
            }
        """)
        
        self.tab_posisi_keuangan = QWidget()
        self.tab_penghasilan = QWidget()
        self.tab_perubahan_aset_neto = QWidget()
        self.tab_arus_kas = QWidget()
        self.tab_neraca_saldo = QWidget()
        self.tab_buku_besar = QWidget()
        
        self.tabs.addTab(self.tab_posisi_keuangan, "Posisi Keuangan")
        self.tabs.addTab(self.tab_penghasilan, "Penghasilan")
        self.tabs.addTab(self.tab_perubahan_aset_neto, "Perubahan Aset")
        self.tabs.addTab(self.tab_arus_kas, "Arus Kas")
        self.tabs.addTab(self.tab_neraca_saldo, "Neraca Saldo")
        self.tabs.addTab(self.tab_buku_besar, "Buku Besar")
        
        layout.addWidget(self.tabs)
        
        self.setup_posisi_keuangan_ui()
        self.setup_penghasilan_ui()
        self.setup_buku_besar_ui()
        self.setup_neraca_saldo_ui()
        self.setup_perubahan_aset_neto_ui()
        self.setup_cash_flow_ui()
        
        self.load_all()

    def style_table(self, table):
        table.setStyleSheet("""
            QTableWidget {
                background-color: #ffffff;
                color: #000000;
                gridline-color: #d1d8e0;
                border: none;
                font-size: 13px;
            }
            QHeaderView::section {
                background-color: #4b6584;
                color: white;
                padding: 8px;
                font-weight: bold;
                border: none;
            }
        """)

    def setup_posisi_keuangan_ui(self):
        layout = QVBoxLayout(self.tab_posisi_keuangan)
        self.table_posisi = QTableWidget(0, 2)
        self.table_posisi.setHorizontalHeaderLabels(["Uraian", "Jumlah (Rp)"])
        self.table_posisi.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.style_table(self.table_posisi)
        layout.addWidget(self.table_posisi)

    def setup_penghasilan_ui(self):
        layout = QVBoxLayout(self.tab_penghasilan)
        self.table_penghasilan = QTableWidget(0, 2)
        self.table_penghasilan.setHorizontalHeaderLabels(["Uraian", "Jumlah (Rp)"])
        self.table_penghasilan.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.style_table(self.table_penghasilan)
        layout.addWidget(self.table_penghasilan)

    def setup_buku_besar_ui(self):
        layout = QVBoxLayout(self.tab_buku_besar)
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Pilih Akun:"))
        self.combo_ledger_account = QComboBox()
        self.combo_ledger_account.setStyleSheet("background-color: white; color: black; padding: 5px;")
        self.combo_ledger_account.currentIndexChanged.connect(self.load_ledger)
        control_layout.addWidget(self.combo_ledger_account)
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        self.table_ledger = QTableWidget(0, 5)
        self.table_ledger.setHorizontalHeaderLabels(["Tanggal", "Keterangan", "Debet", "Kredit", "Saldo"])
        self.table_ledger.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.style_table(self.table_ledger)
        layout.addWidget(self.table_ledger)

    def setup_neraca_saldo_ui(self):
        layout = QVBoxLayout(self.tab_neraca_saldo)
        self.table_neraca_saldo = QTableWidget(0, 4)
        self.table_neraca_saldo.setHorizontalHeaderLabels(["Kode", "Nama Akun", "Debet", "Kredit"])
        self.table_neraca_saldo.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.style_table(self.table_neraca_saldo)
        layout.addWidget(self.table_neraca_saldo)

    def setup_perubahan_aset_neto_ui(self):
        layout = QVBoxLayout(self.tab_perubahan_aset_neto)
        self.table_perubahan_aset_neto = QTableWidget(0, 4)
        self.table_perubahan_aset_neto.setHorizontalHeaderLabels(["Uraian", "Tanpa Pembatasan", "Dengan Pembatasan", "Total"])
        self.table_perubahan_aset_neto.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.style_table(self.table_perubahan_aset_neto)
        layout.addWidget(self.table_perubahan_aset_neto)

    def setup_cash_flow_ui(self):
        layout = QVBoxLayout(self.tab_arus_kas)
        self.table_arus_kas = QTableWidget(0, 2)
        self.table_arus_kas.setHorizontalHeaderLabels(["Uraian", "Jumlah (Rp)"])
        self.table_arus_kas.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.style_table(self.table_arus_kas)
        layout.addWidget(self.table_arus_kas)

    def add_row(self, table, label, value="", is_bold=False, is_indent=False, is_sub_indent=False, is_error=False):
        row = table.rowCount()
        table.insertRow(row)
        label_text = f"{'        ' if is_sub_indent else '    ' if is_indent else ''}{label}"
        label_item = QTableWidgetItem(label_text)
        label_item.setForeground(Qt.GlobalColor.black)
        
        val_text = f"{value:,.0f}" if isinstance(value, (int, float)) else str(value)
        value_item = QTableWidgetItem(val_text)
        value_item.setForeground(Qt.GlobalColor.black)
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        if is_bold:
            font = label_item.font()
            font.setBold(True)
            label_item.setFont(font)
            value_item.setFont(font)
        if is_error:
            label_item.setBackground(QColor("#ffcccc"))
            value_item.setBackground(QColor("#ffcccc"))
            
        table.setItem(row, 0, label_item)
        table.setItem(row, 1, value_item)

    def load_all(self):
        self.load_posisi_keuangan()
        self.load_penghasilan()
        self.refresh_ledger_accounts()
        self.load_trial_balance()
        self.load_changes_in_net_assets()
        self.load_cash_flow_statement()

    def load_posisi_keuangan(self):
        self.table_posisi.setRowCount(0)
        data = self.report_gen.get_isak35_financial_position()
        self.add_row(self.table_posisi, "ASET", is_bold=True)
        for item in data['assets']: self.add_row(self.table_posisi, item['name'], item['balance'], is_indent=True)
        self.add_row(self.table_posisi, "TOTAL ASET", data['total_assets'], is_bold=True)
        self.add_row(self.table_posisi, "", "")
        self.add_row(self.table_posisi, "LIABILITAS", is_bold=True)
        for item in data['liabilities']: self.add_row(self.table_posisi, item['name'], item['balance'], is_indent=True)
        self.add_row(self.table_posisi, "TOTAL LIABILITAS", data['total_liabilities'], is_bold=True)
        self.add_row(self.table_posisi, "", "")
        self.add_row(self.table_posisi, "ASET NETO", is_bold=True)
        self.add_row(self.table_posisi, "Tanpa Pembatasan", data['net_assets_without'], is_indent=True)
        self.add_row(self.table_posisi, "Dengan Pembatasan", data['net_assets_with'], is_indent=True)
        self.add_row(self.table_posisi, "TOTAL ASET NETO", data['total_net_assets'], is_bold=True)
        self.add_row(self.table_posisi, "TOTAL LIABILITAS DAN ASET NETO", data['total_liabilities_and_net_assets'], is_bold=True)

    def load_penghasilan(self):
        self.table_penghasilan.setRowCount(0)
        data = self.report_gen.get_comprehensive_income()
        self.add_row(self.table_penghasilan, "PENDAPATAN", is_bold=True)
        self.add_row(self.table_penghasilan, "Tanpa Pembatasan:", is_indent=True)
        for item in data['revenue_without']: self.add_row(self.table_penghasilan, item['name'], item['balance'], is_indent=True, is_sub_indent=True)
        self.add_row(self.table_penghasilan, "Dengan Pembatasan:", is_indent=True)
        for item in data['revenue_with']: self.add_row(self.table_penghasilan, item['name'], item['balance'], is_indent=True, is_sub_indent=True)
        self.add_row(self.table_penghasilan, "TOTAL PENDAPATAN", data['total_revenue'], is_bold=True)
        self.add_row(self.table_penghasilan, "", "")
        self.add_row(self.table_penghasilan, "BEBAN", is_bold=True)
        for item in data['expenses']: self.add_row(self.table_penghasilan, item['name'], item['balance'], is_indent=True)
        self.add_row(self.table_penghasilan, "TOTAL BEBAN", data['total_expenses'], is_bold=True)
        surplus = data['total_revenue'] - data['total_expenses']
        self.add_row(self.table_penghasilan, "KENAIKAN (PENURUNAN) ASET NETO", surplus, is_bold=True)
    def load_trial_balance(self):
        self.table_neraca_saldo.setRowCount(0)
        data = self.report_gen.get_trial_balance_report()
        for row_data in data:
            row_idx = self.table_neraca_saldo.rowCount()
            self.table_neraca_saldo.insertRow(row_idx)
            cols = [
                str(row_data['code']), 
                str(row_data['name']), 
                f"{row_data['debit']:,.0f}" if row_data['debit'] != 0 else "", 
                f"{row_data['credit']:,.0f}" if row_data['credit'] != 0 else ""
            ]
            for col_idx, text in enumerate(cols):
                item = QTableWidgetItem(text)
                item.setForeground(Qt.GlobalColor.black)
                if col_idx >= 2: 
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                if row_data['name'] == 'TOTAL':
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                    item.setBackground(QColor("#f1f2f6"))

                self.table_neraca_saldo.setItem(row_idx, col_idx, item)

    def load_changes_in_net_assets(self):
        self.table_perubahan_aset_neto.setRowCount(0)
        data = self.report_gen.get_changes_in_net_assets_report()
        for row_data in data:
            row_idx = self.table_perubahan_aset_neto.rowCount()
            self.table_perubahan_aset_neto.insertRow(row_idx)
            cols = [str(row_data['description']), f"{row_data['without_restriction']:,.0f}", f"{row_data['with_restriction']:,.0f}", f"{row_data['total']:,.0f}"]
            for col_idx, text in enumerate(cols):
                item = QTableWidgetItem(text)
                item.setForeground(Qt.GlobalColor.black)
                if col_idx >= 1: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if "Periode" in row_data['description']:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table_perubahan_aset_neto.setItem(row_idx, col_idx, item)

    def load_cash_flow_statement(self):
        self.table_arus_kas.setRowCount(0)
        result = self.report_gen.get_cash_flow_report()
        if "error" in result: return
        for row_data in result['report_data']:
            row_idx = self.table_arus_kas.rowCount()
            self.table_arus_kas.insertRow(row_idx)
            desc_item = QTableWidgetItem(str(row_data['Keterangan']))
            desc_item.setForeground(Qt.GlobalColor.black)
            val = row_data['Jumlah (Rp)']
            amount_item = QTableWidgetItem(f"{val:,.0f}" if isinstance(val, (int, float)) else "")
            amount_item.setForeground(Qt.GlobalColor.black)
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if "Total" in str(row_data['Keterangan']) or "Bersih" in str(row_data['Keterangan']):
                font = desc_item.font()
                font.setBold(True)
                desc_item.setFont(font)
                amount_item.setFont(font)
            self.table_arus_kas.setItem(row_idx, 0, desc_item)
            self.table_arus_kas.setItem(row_idx, 1, amount_item)

    def refresh_ledger_accounts(self):
        self.combo_ledger_account.blockSignals(True)
        self.combo_ledger_account.clear()
        accounts = self.db.get_accounts()
        self.ledger_account_map = {f"{acc[1]} - {acc[2]}": (acc[0], acc[3]) for acc in accounts}
        self.combo_ledger_account.addItems(["-- Pilih Akun --"] + list(self.ledger_account_map.keys()))
        self.combo_ledger_account.blockSignals(False)

    def load_ledger(self):
        self.table_ledger.setRowCount(0)
        text = self.combo_ledger_account.currentText()
        if text == "-- Pilih Akun --": return
        acc_id, acc_type = self.ledger_account_map[text]
        df = self.db.get_ledger_entries(acc_id)
        bal = 0
        is_debit = acc_type in ['Asset', 'Expense']
        for _, row in df.iterrows():
            row_idx = self.table_ledger.rowCount()
            self.table_ledger.insertRow(row_idx)
            bal += (row['debit'] - row['credit']) if is_debit else (row['credit'] - row['debit'])
            cols = [row['date'], row['description'], f"{row['debit']:,.0f}" if row['debit'] != 0 else "", f"{row['credit']:,.0f}" if row['credit'] != 0 else "", f"{bal:,.0f}"]
            for col_idx, txt in enumerate(cols):
                item = QTableWidgetItem(txt)
                item.setForeground(Qt.GlobalColor.black)
                if col_idx >= 2: item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table_ledger.setItem(row_idx, col_idx, item)

    def handle_export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Laporan", "Laporan_Yayasan.xlsx", "Excel Files (*.xlsx)")
        if path:
            if self.report_gen.export_to_excel(path):
                QMessageBox.information(self, "Berhasil", f"Laporan disimpan di:\n{path}")
