# src/ui/journal_detail_dialog.py

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QDialogButtonBox, QHeaderView, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from ..database_manager import DatabaseManager

class JournalDetailDialog(QDialog):
    """
    Dialog untuk menampilkan detail lengkap dari satu entri jurnal dengan info Arus Kas lengkap.
    """
    def __init__(self, journal_id, parent=None):
        super().__init__(parent)
        self.journal_id = journal_id
        self.db = DatabaseManager()

        self.setWindowTitle(f"Detail Jurnal #{self.journal_id}")
        self.setMinimumSize(800, 500) # Perlebar dialog untuk mengakomodasi kolom baru

        self.init_ui()
        self.load_details()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header Jurnal
        header_frame = QFrame()
        header_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QFormLayout(header_frame)
        
        self.lbl_date = QLabel("N/A")
        self.lbl_desc = QLabel("N/A")
        self.lbl_ref = QLabel("N/A")
        
        header_layout.addRow(QLabel("<b>Tanggal:</b>"), self.lbl_date)
        header_layout.addRow(QLabel("<b>Deskripsi:</b>"), self.lbl_desc)
        header_layout.addRow(QLabel("<b>No. Ref:</b>"), self.lbl_ref)
        
        layout.addWidget(header_frame)

        # Table Section (6 Columns now)
        self.table_details = QTableWidget(0, 6) 
        self.table_details.setHorizontalHeaderLabels([
            "Kode Akun", "Nama Akun", "Debet (Rp)", "Kredit (Rp)", 
            "Kategori Arus Kas", "Aktivitas Arus Kas"
        ])
        
        h = self.table_details.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table_details.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table_details)

        # Footer Total
        total_layout = QHBoxLayout()
        self.lbl_total_debit = QLabel("<b>Total Debit:</b> Rp 0")
        self.lbl_total_credit = QLabel("<b>Total Kredit:</b> Rp 0")
        total_layout.addStretch()
        total_layout.addWidget(self.lbl_total_debit)
        total_layout.addSpacing(20)
        total_layout.addWidget(self.lbl_total_credit)
        layout.addLayout(total_layout)

        # Tombol
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def load_details(self):
        data = self.db.get_journal_details(self.journal_id)
        if not data:
            self.lbl_desc.setText("<font color='red'>Error: Jurnal tidak ditemukan.</font>")
            return

        # Ambil pemetaan arus kas untuk lookup Kategori Utama
        all_cats = self.db.get_cash_flow_categories()
        act_to_main = {c[1]: c[2] for c in all_cats}

        # Isi Header
        header_data = data['header']
        self.lbl_date.setText(header_data[0])
        self.lbl_desc.setText(header_data[1])
        self.lbl_ref.setText(header_data[2] if header_data[2] else "-")

        # Isi Tabel
        details_data = data['details']
        self.table_details.setRowCount(len(details_data))
        
        total_debit = 0
        total_credit = 0

        for row, item in enumerate(details_data):
            code, name, debit, credit, activity_name = item
            
            self.table_details.setItem(row, 0, QTableWidgetItem(code))
            self.table_details.setItem(row, 1, QTableWidgetItem(name))
            
            debit_item = QTableWidgetItem(f"{debit:,.0f}" if debit != 0 else "")
            debit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_details.setItem(row, 2, debit_item)
            
            credit_item = QTableWidgetItem(f"{credit:,.0f}" if credit != 0 else "")
            credit_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_details.setItem(row, 3, credit_item)

            # Determine Main Category and Activity
            main_cat = act_to_main.get(activity_name, "Tidak Berlaku") if activity_name else "Tidak Berlaku"
            self.table_details.setItem(row, 4, QTableWidgetItem(main_cat))
            self.table_details.setItem(row, 5, QTableWidgetItem(activity_name if activity_name else "-"))
            
            total_debit += debit
            total_credit += credit

        # Update Total
        self.lbl_total_debit.setText(f"<b>Total Debit:</b> Rp {total_debit:,.0f}")
        self.lbl_total_credit.setText(f"<b>Total Kredit:</b> Rp {total_credit:,.0f}")
