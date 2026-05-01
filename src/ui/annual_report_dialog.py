from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QTextEdit, QPushButton, QMessageBox, 
                             QFormLayout, QTabWidget, QWidget)
from PySide6.QtCore import Qt

class AnnualReportDialog(QDialog):
    def __init__(self, db_manager, year):
        super().__init__()
        self.db = db_manager
        self.year = year
        self.init_ui()
        self.load_data()

    def init_ui(self):
        self.setWindowTitle(f"Penyusunan Laporan Tahunan Pengurus - {self.year}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setStyleSheet("background-color: #f5f6fa;")

        layout = QVBoxLayout(self)
        
        header = QLabel(f"📋 FORMAT LAPORAN TAHUNAN {self.year}")
        header.setStyleSheet("font-size: 20px; font-weight: bold; color: #2f3640; margin-bottom: 10px;")
        layout.addWidget(header)

        # Tabs for better organization
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab { padding: 10px 20px; font-weight: bold; }")
        
        # Tab 1: Profil & Organisasi
        self.tab_profile = QWidget()
        profile_layout = QFormLayout(self.tab_profile)
        self.txt_vision = QTextEdit()
        self.txt_mission = QTextEdit()
        self.txt_structure = QTextEdit()
        profile_layout.addRow("Visi Yayasan:", self.txt_vision)
        profile_layout.addRow("Misi Yayasan:", self.txt_mission)
        profile_layout.addRow("Struktur Pengurus:", self.txt_structure)
        
        # Tab 2: Laporan Bidang (Referensi Scribd)
        self.tab_fields = QWidget()
        fields_layout = QFormLayout(self.tab_fields)
        self.txt_programs = QTextEdit()
        self.txt_edu = QTextEdit()
        self.txt_social = QTextEdit()
        fields_layout.addRow("Ringkasan Umum:", self.txt_programs)
        fields_layout.addRow("Bidang Pendidikan:", self.txt_edu)
        fields_layout.addRow("Bidang Dakwah/Sosial:", self.txt_social)
        
        # Tab 3: Evaluasi & Rencana
        self.tab_eval = QWidget()
        eval_layout = QFormLayout(self.tab_eval)
        self.txt_constraints = QTextEdit()
        self.txt_plans = QTextEdit()
        eval_layout.addRow("Kendala & Hambatan:", self.txt_constraints)
        eval_layout.addRow("Rencana Strategis Ke Depan:", self.txt_plans)

        self.tabs.addTab(self.tab_profile, "1. Profil & Struktur")
        self.tabs.addTab(self.tab_fields, "2. Laporan Bidang")
        self.tabs.addTab(self.tab_eval, "3. Evaluasi & Rencana")
        
        layout.addWidget(self.tabs)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 Simpan Draf Laporan")
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 12px; border-radius: 6px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.btn_save.clicked.connect(self.save_data)
        
        self.btn_cancel = QPushButton("Batal")
        self.btn_cancel.setStyleSheet("padding: 10px; border-radius: 5px;")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def load_data(self):
        # Ambil data dari database (termasuk kolom baru)
        data = self.db.get_annual_report_settings(self.year)
        self.txt_vision.setPlainText(data.get('vision', ''))
        self.txt_mission.setPlainText(data.get('mission', ''))
        self.txt_structure.setPlainText(data.get('organizational_structure', ''))
        self.txt_programs.setPlainText(data.get('program_summary', ''))
        self.txt_edu.setPlainText(data.get('program_detail_edu', ''))
        self.txt_social.setPlainText(data.get('program_detail_social', ''))
        self.txt_constraints.setPlainText(data.get('evaluation_constraints', ''))
        self.txt_plans.setPlainText(data.get('future_plans', ''))

    def save_data(self):
        data = {
            'vision': self.txt_vision.toPlainText(),
            'mission': self.txt_mission.toPlainText(),
            'organizational_structure': self.txt_structure.toPlainText(),
            'program_summary': self.txt_programs.toPlainText(),
            'program_detail_edu': self.txt_edu.toPlainText(),
            'program_detail_social': self.txt_social.toPlainText(),
            'evaluation_constraints': self.txt_constraints.toPlainText(),
            'future_plans': self.txt_plans.toPlainText()
        }
        try:
            self.db.save_annual_report_settings(self.year, data)
            QMessageBox.information(self, "Berhasil", "Data Laporan Tahunan berhasil diperbarui.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Gagal", f"Terjadi kesalahan saat menyimpan: {e}")
