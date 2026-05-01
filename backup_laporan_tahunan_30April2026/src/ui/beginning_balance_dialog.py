from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLabel, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
                             QPushButton, QDialogButtonBox, QMessageBox, QHeaderView, QDateEdit, QFrame)
from PySide6.QtCore import Qt, QDate
from ..database_manager import DatabaseManager

class BeginningBalanceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Input Saldo Awal")
        self.setMinimumSize(600, 400)
        self.db = DatabaseManager()
        self.accounts = self.db.get_accounts() # (id, code, name, type, category)
        self.account_map = {f"{acc[1]} - {acc[2]}": acc[0] for acc in self.accounts}
        self.init_ui()

    def init_ui(self):
        # Set Dark Theme Stylesheet for the whole dialog
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: white;
            }
            QLabel {
                color: white;
            }
            QFrame {
                border: 1px solid #34495e;
                border-radius: 5px;
                background-color: #34495e;
            }
            QTableWidget {
                background-color: #ecf0f1;
                color: #2c3e50;
                gridline-color: #bdc3c7;
            }
            QHeaderView::section {
                background-color: #4b6584;
                color: white;
                padding: 5px;
                font-weight: bold;
            }
            QDateEdit, QComboBox, QLineEdit {
                background-color: white;
                color: #2c3e50;
                padding: 4px;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #4b6584;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5d7799;
            }
        """)

        layout = QVBoxLayout(self)

        # Header Section
        header_frame = QFrame()
        header_layout = QFormLayout(header_frame)
        
        self.date_edit = QDateEdit(self)
        self.date_edit.setDate(QDate(QDate.currentDate().year(), 1, 1))
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setMinimumWidth(120)
        
        lbl_tanggal = QLabel("<b>Tanggal Saldo Awal:</b>")
        header_layout.addRow(lbl_tanggal, self.date_edit)
        layout.addWidget(header_frame)

        # Table for Balance Entries
        self.table_balances = QTableWidget(0, 3) # Account, Debit, Credit
        self.table_balances.setHorizontalHeaderLabels(["Akun", "Debet (Rp)", "Kredit (Rp)"])
        self.table_balances.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_balances.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_balances.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table_balances)

        # Add/Remove Row Buttons
        row_button_layout = QHBoxLayout()
        self.btn_add_row = QPushButton("+ Tambah Baris")
        self.btn_add_row.clicked.connect(self.add_balance_row)
        self.btn_remove_row = QPushButton("🗑️ Hapus Baris")
        self.btn_remove_row.clicked.connect(self.remove_balance_row)
        row_button_layout.addWidget(self.btn_add_row)
        row_button_layout.addWidget(self.btn_remove_row)
        row_button_layout.addStretch()
        layout.addLayout(row_button_layout)

        # Total Debit/Credit Display
        self.lbl_balance_check = QLabel("Total Debet: Rp 0 | Total Kredit: Rp 0 | Selisih: Rp 0")
        self.lbl_balance_check.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(self.lbl_balance_check)
        self.table_balances.itemChanged.connect(self.update_balance_check)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept_entry)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.add_balance_row() # Add an initial row

    def add_balance_row(self):
        row_idx = self.table_balances.rowCount()
        self.table_balances.insertRow(row_idx)

        # Account ComboBox
        combo_account = QComboBox()
        combo_account.addItems(list(self.account_map.keys()))
        self.table_balances.setCellWidget(row_idx, 0, combo_account)

        # Debit and Credit LineEdits
        le_debit = QLineEdit("0")
        le_debit.setAlignment(Qt.AlignmentFlag.AlignRight)
        le_debit.textChanged.connect(self.update_balance_check)
        self.table_balances.setCellWidget(row_idx, 1, le_debit)

        le_credit = QLineEdit("0")
        le_credit.setAlignment(Qt.AlignmentFlag.AlignRight)
        le_credit.textChanged.connect(self.update_balance_check)
        self.table_balances.setCellWidget(row_idx, 2, le_credit)

    def remove_balance_row(self):
        selected_rows = self.table_balances.selectionModel().selectedRows()
        if selected_rows:
            for row in sorted(selected_rows, reverse=True):
                self.table_balances.removeRow(row.row())
            self.update_balance_check()
        else:
            QMessageBox.warning(self, "Peringatan", "Pilih baris yang ingin dihapus.")

    def update_balance_check(self):
        total_debit = 0.0
        total_credit = 0.0

        for row_idx in range(self.table_balances.rowCount()):
            debit_widget = self.table_balances.cellWidget(row_idx, 1)
            credit_widget = self.table_balances.cellWidget(row_idx, 2)

            try:
                debit_text = debit_widget.text().replace('.', '').replace(',', '.') if debit_widget else "0"
                credit_text = credit_widget.text().replace('.', '').replace(',', '.') if credit_widget else "0"
                total_debit += float(debit_text)
                total_credit += float(credit_text)
            except ValueError:
                pass # Ignore invalid number formats for now, validation will catch it later

        difference = total_debit - total_credit
        self.lbl_balance_check.setText(
            f"Total Debet: Rp {total_debit:,.0f} | Total Kredit: Rp {total_credit:,.0f} | Selisih: Rp {difference:,.0f}"
        )
        if abs(difference) > 0.01: # Allow for minor floating point inaccuracies
            self.lbl_balance_check.setStyleSheet("font-weight: bold; color: red;")
        else:
            self.lbl_balance_check.setStyleSheet("font-weight: bold; color: green;")

    def accept_entry(self):
        date = self.date_edit.date().toString("yyyy-MM-dd")
        year = self.date_edit.date().year()
        
        details = []
        total_debit = 0.0
        total_credit = 0.0

        for row_idx in range(self.table_balances.rowCount()):
            combo_account = self.table_balances.cellWidget(row_idx, 0)
            le_debit = self.table_balances.cellWidget(row_idx, 1)
            le_credit = self.table_balances.cellWidget(row_idx, 2)

            account_name_code = combo_account.currentText()
            account_id = self.account_map.get(account_name_code)

            if not account_id:
                QMessageBox.warning(self, "Validasi", f"Akun tidak valid pada baris {row_idx + 1}.")
                return

            try:
                debit_val = float(le_debit.text().replace('.', '').replace(',', '.'))
                credit_val = float(le_credit.text().replace('.', '').replace(',', '.'))
            except ValueError:
                QMessageBox.warning(self, "Validasi", f"Jumlah Debet/Kredit tidak valid pada baris {row_idx + 1}.")
                return
            
            if debit_val < 0 or credit_val < 0:
                QMessageBox.warning(self, "Validasi", f"Jumlah Debet/Kredit tidak boleh negatif pada baris {row_idx + 1}.")
                return

            if debit_val > 0 and credit_val > 0:
                QMessageBox.warning(self, "Validasi", f"Akun pada baris {row_idx + 1} tidak boleh memiliki Debet dan Kredit secara bersamaan.")
                return

            if debit_val == 0 and credit_val == 0:
                continue # Skip rows with zero debit and credit

            details.append({
                'account_id': account_id,
                'debit': debit_val,
                'credit': credit_val,
                'cash_flow_activity': None # Saldo awal tidak memiliki aktivitas arus kas
            })
            total_debit += debit_val
            total_credit += credit_val

        if not details:
            QMessageBox.warning(self, "Validasi", "Tidak ada entri saldo awal yang valid.")
            return

        if abs(total_debit - total_credit) > 0.01:
            QMessageBox.warning(self, "Validasi", "Total Debet dan Kredit harus seimbang.")
            return

        try:
            self.db.add_beginning_balance_entry(date, year, details)
            QMessageBox.information(self, "Sukses", "Saldo awal berhasil dicatat.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal mencatat saldo awal: {e}")
