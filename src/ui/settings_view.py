from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QFrame, QPushButton, QMessageBox, QLineEdit, QFormLayout, QScrollArea)
from PySide6.QtCore import Qt, Signal
import json
import os
from datetime import datetime

class SettingsView(QWidget):
    position_changed = Signal(str)
    theme_changed = Signal(str)
    config_updated = Signal(dict) # Sinyal gabungan untuk semua config

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # Title
        title = QLabel("⚙️ PENGATURAN SISTEM")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #2d3436; margin-bottom: 5px;")
        self.layout.addWidget(title)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.layout.addWidget(self.scroll)

        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(15, 15, 15, 15)
        self.container_layout.setSpacing(15)
        self.scroll.setWidget(self.container)

        input_style = """
            QLineEdit {
                padding: 6px; border: 1px solid #ced4da; border-radius: 4px; background-color: #ffffff; color: #2c3e50; font-size: 13px;
            }
            QComboBox {
                padding: 6px; border: 1px solid #3498db; border-radius: 4px; background-color: #ffffff; color: #2c3e50; font-size: 13px;
            }
        """

        # --- Section: Profil Yayasan ---
        profile_box = QFrame()
        profile_box.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;")
        profile_layout = QVBoxLayout(profile_box)
        
        lbl_prof = QLabel("🏢 PROFIL YAYASAN")
        lbl_prof.setStyleSheet("font-weight: bold; color: #2c3e50; border: none;")
        profile_layout.addWidget(lbl_prof)
        
        self.f_form = QFormLayout()
        self.f_form.setSpacing(8)
        self.f_name = QLineEdit(); self.f_address = QLineEdit()
        self.f_phone = QLineEdit(); self.f_email = QLineEdit()
        self.f_leader = QLineEdit(); self.f_pembina = QLineEdit(); self.f_pengawas = QLineEdit()
        
        for le in [self.f_name, self.f_address, self.f_phone, self.f_email, self.f_leader, self.f_pembina, self.f_pengawas]: 
            le.setStyleSheet(input_style)
        
        self.f_form.addRow("Nama Yayasan:", self.f_name)
        self.f_form.addRow("Alamat:", self.f_address)
        self.f_form.addRow("Telepon/WA:", self.f_phone)
        self.f_form.addRow("Email:", self.f_email)
        self.f_form.addRow("Ketua Pengurus:", self.f_leader)
        self.f_form.addRow("Ketua Pembina:", self.f_pembina)
        self.f_form.addRow("Ketua Pengawas:", self.f_pengawas)
        profile_layout.addLayout(self.f_form)
        self.container_layout.addWidget(profile_box)

        # --- Section: Tampilan & UI ---
        ui_box = QFrame()
        ui_box.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;")
        ui_layout = QVBoxLayout(ui_box)
        lbl_ui = QLabel("🎨 TAMPILAN ANTARMUKA")
        lbl_ui.setStyleSheet("font-weight: bold; color: #2c3e50; border: none;")
        ui_layout.addWidget(lbl_ui)
        
        ui_form = QFormLayout()
        self.combo_pos = QComboBox(); self.combo_pos.addItems(["Kiri (Default)", "Kanan", "Atas", "Bawah"])
        self.combo_theme = QComboBox(); self.combo_theme.addItems(["Standard (Modern Blue)", "Dark Mode", "Classic C++ Style"])
        
        for c in [self.combo_pos, self.combo_theme]: c.setStyleSheet(input_style); c.setFixedWidth(200)
        
        ui_form.addRow("Posisi Navigasi:", self.combo_pos)
        ui_form.addRow("Tema Warna:", self.combo_theme)
        ui_layout.addLayout(ui_form)
        self.container_layout.addWidget(ui_box)

        # --- Section: AI Assistant ---
        ai_box = QFrame()
        ai_box.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;")
        ai_layout = QVBoxLayout(ai_box)
        lbl_ai = QLabel("🤖 ASISTEN AI (GEMINI)")
        lbl_ai.setStyleSheet("font-weight: bold; color: #2c3e50; border: none;")
        ai_layout.addWidget(lbl_ai)
        
        ai_form = QFormLayout()
        self.gemini_key = QLineEdit()
        self.gemini_key.setEchoMode(QLineEdit.Password)
        self.gemini_key.setPlaceholderText("Masukkan API Key Gemini...")
        self.gemini_key.setStyleSheet(input_style)
        ai_form.addRow("API Key Gemini:", self.gemini_key)
        ai_layout.addLayout(ai_form)
        self.container_layout.addWidget(ai_box)

        # --- Section: Database ---
        db_box = QFrame()
        db_box.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;")
        db_layout = QVBoxLayout(db_box)
        lbl_db = QLabel("🛡️ KONFIGURASI DATABASE")
        lbl_db.setStyleSheet("font-weight: bold; color: #2c3e50; border: none;")
        db_layout.addWidget(lbl_db)
        
        self.combo_db_type = QComboBox()
        self.combo_db_type.addItems(["SQLite (Lokal)", "MySQL (Server)", "SQL Server (Server)"])
        self.combo_db_type.setStyleSheet(input_style); self.combo_db_type.setFixedWidth(200)
        self.combo_db_type.currentTextChanged.connect(self.toggle_db_inputs)
        db_layout.addWidget(self.combo_db_type)

        # MySQL
        self.mysql_group = QFrame(); self.mysql_layout = QFormLayout(self.mysql_group)
        self.db_host = QLineEdit("localhost"); self.db_user = QLineEdit("root")
        self.db_pass = QLineEdit(); self.db_pass.setEchoMode(QLineEdit.Password)
        self.db_name = QLineEdit("foundation_finance")
        for le in [self.db_host, self.db_user, self.db_pass, self.db_name]: le.setStyleSheet(input_style)
        self.mysql_layout.addRow("Host:", self.db_host); self.mysql_layout.addRow("User:", self.db_user)
        self.mysql_layout.addRow("Password:", self.db_pass); self.mysql_layout.addRow("Database:", self.db_name)
        db_layout.addWidget(self.mysql_group); self.mysql_group.setVisible(False)

        # SQL Server
        self.mssql_group = QFrame(); self.mssql_layout = QFormLayout(self.mssql_group)
        self.ms_host = QLineEdit("localhost"); self.ms_user = QLineEdit("sa")
        self.ms_pass = QLineEdit(); self.ms_pass.setEchoMode(QLineEdit.Password)
        self.ms_name = QLineEdit("foundation_finance")
        self.ms_driver = QComboBox(); self.ms_driver.addItems(["ODBC Driver 17 for SQL Server", "SQL Server"])
        self.ms_driver.setEditable(True)
        for le in [self.ms_host, self.ms_user, self.ms_pass, self.ms_name, self.ms_driver]: le.setStyleSheet(input_style)
        self.mssql_layout.addRow("Server:", self.ms_host); self.mssql_layout.addRow("UID:", self.ms_user)
        self.mssql_layout.addRow("PWD:", self.ms_pass); self.mssql_layout.addRow("Database:", self.ms_name)
        self.mssql_layout.addRow("Driver:", self.ms_driver)
        db_layout.addWidget(self.mssql_group); self.mssql_group.setVisible(False)
        self.container_layout.addWidget(db_box)

        # --- Section: Backup ---
        back_box = QFrame(); back_box.setStyleSheet("background-color: #f8f9fa; border-radius: 8px; border: 1px solid #e9ecef;")
        back_layout = QVBoxLayout(back_box)
        lbl_back = QLabel("💾 BACKUP & RESTORE")
        lbl_back.setStyleSheet("font-weight: bold; color: #2c3e50; border: none;")
        back_layout.addWidget(lbl_back)
        
        btn_lay = QHBoxLayout()
        self.btn_backup = QPushButton("📤 Export JSON"); self.btn_restore = QPushButton("📥 Import JSON")
        self.btn_backup.setStyleSheet("background-color: #34495e; color: white; padding: 8px; font-weight: bold; border: none;")
        self.btn_restore.setStyleSheet("background-color: #7f8c8d; color: white; padding: 8px; font-weight: bold; border: none;")
        self.btn_backup.clicked.connect(self.run_backup); self.btn_restore.clicked.connect(self.run_restore)
        btn_lay.addWidget(self.btn_backup); btn_lay.addWidget(self.btn_restore)
        back_layout.addLayout(btn_lay)
        self.container_layout.addWidget(back_box)

        # Save Button
        self.btn_save = QPushButton("💾 SIMPAN SEMUA PENGATURAN")
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 12px; font-size: 15px; font-weight: bold; border-radius: 6px; margin-top: 10px; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.btn_save.clicked.connect(self.save_settings)
        self.container_layout.addWidget(self.btn_save)
        
        self.container_layout.addStretch()

    def toggle_db_inputs(self, text):
        self.mysql_group.setVisible(text == "MySQL (Server)")
        self.mssql_group.setVisible(text == "SQL Server (Server)")

    def run_backup(self):
        from src.database_manager import DatabaseManager
        db = DatabaseManager()
        data = db.generate_full_backup()
        if data:
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getSaveFileName(self, "Simpan Backup", f"backup_isak35_{datetime.now().strftime('%Y%m%d')}.json", "JSON (*.json)")
            if path:
                with open(path, 'w') as f: json.dump(data, f)
                QMessageBox.information(self, "Sukses", "Backup berhasil disimpan.")

    def run_restore(self):
        from src.database_manager import DatabaseManager
        if QMessageBox.warning(self, "Peringatan", "Ini akan MENGHAPUS SEMUA DATA. Lanjut?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            from PySide6.QtWidgets import QFileDialog
            path, _ = QFileDialog.getOpenFileName(self, "Pilih Backup", "", "JSON (*.json)")
            if path:
                with open(path, 'r') as f: data = json.load(f)
                db = DatabaseManager()
                ok, msg = db.restore_full_backup(data)
                if ok: QMessageBox.information(self, "Sukses", "Data berhasil dipulihkan. Silakan restart aplikasi.")
                else: QMessageBox.critical(self, "Gagal", msg)

    def save_settings(self):
        from src.database_manager import DatabaseManager
        db = DatabaseManager()
        
        # Bug Fix: Include all names
        profile_data = {
            "name": self.f_name.text(), "address": self.f_address.text(),
            "phone": self.f_phone.text(), "email": self.f_email.text(),
            "leader_name": self.f_leader.text(),
            "pembina_name": self.f_pembina.text(),
            "pengawas_name": self.f_pengawas.text()
        }
        db.save_foundation_profile(profile_data)

        pos_map = {"Kiri (Default)": "left", "Kanan": "right", "Atas": "top", "Bawah": "bottom"}
        theme_map = {"Standard (Modern Blue)": "standard", "Dark Mode": "dark", "Classic C++ Style": "classic"}
        
        db_text = self.combo_db_type.currentText()
        db_type = "sqlite"
        if db_text == "MySQL (Server)": db_type = "mysql"
        elif db_text == "SQL Server (Server)": db_type = "sqlserver"

        # Emit all changes
        self.config_updated.emit({
            "nav_position": pos_map.get(self.combo_pos.currentText()),
            "theme": theme_map.get(self.combo_theme.currentText()),
            "db_type": db_type,
            "mysql_config": {"host": self.db_host.text(), "user": self.db_user.text(), "password": self.db_pass.text(), "database": self.db_name.text()},
            "sqlserver_config": {"host": self.ms_host.text(), "user": self.ms_user.text(), "password": self.ms_pass.text(), "database": self.ms_name.text(), "driver": self.ms_driver.currentText()},
            "gemini_config": {"api_key": self.gemini_key.text()}
        })
        
        QMessageBox.information(self, "Sukses", "Pengaturan telah disimpan.")

    def set_current_settings(self, pos, theme, db_type="sqlite", mysql_config=None, sqlserver_config=None, gemini_config=None):
        from src.database_manager import DatabaseManager
        db = DatabaseManager()
        
        prof = db.get_foundation_profile()
        self.f_name.setText(prof.get('name', ''))
        self.f_address.setText(prof.get('address', ''))
        self.f_phone.setText(prof.get('phone', ''))
        self.f_email.setText(prof.get('email', ''))
        self.f_leader.setText(prof.get('leader_name', ''))
        self.f_pembina.setText(prof.get('pembina_name', ''))
        self.f_pengawas.setText(prof.get('pengawas_name', ''))

        pos_inv = {"left": "Kiri (Default)", "right": "Kanan", "top": "Atas", "bottom": "Bawah"}
        theme_inv = {"standard": "Standard (Modern Blue)", "dark": "Dark Mode", "classic": "Classic C++ Style"}
        
        self.combo_pos.setCurrentText(pos_inv.get(pos, "Kiri (Default)"))
        self.combo_theme.setCurrentText(theme_inv.get(theme, "Standard (Modern Blue)"))
        
        if db_type == "mysql": self.combo_db_type.setCurrentText("MySQL (Server)")
        elif db_type == "sqlserver": self.combo_db_type.setCurrentText("SQL Server (Server)")
        else: self.combo_db_type.setCurrentText("SQLite (Lokal)")
        
        if mysql_config:
            self.db_host.setText(mysql_config.get("host", "localhost"))
            self.db_user.setText(mysql_config.get("user", "root"))
            self.db_pass.setText(mysql_config.get("password", ""))
            self.db_name.setText(mysql_config.get("database", "foundation_finance"))
            
        if sqlserver_config:
            self.ms_host.setText(sqlserver_config.get("host", "localhost"))
            self.ms_user.setText(sqlserver_config.get("user", "sa"))
            self.ms_pass.setText(sqlserver_config.get("password", ""))
            self.ms_name.setText(sqlserver_config.get("database", "foundation_finance"))
            self.ms_driver.setCurrentText(sqlserver_config.get("driver", "ODBC Driver 17 for SQL Server"))

        if gemini_config:
            self.gemini_key.setText(gemini_config.get("api_key", ""))

        self.toggle_db_inputs(self.combo_db_type.currentText())
