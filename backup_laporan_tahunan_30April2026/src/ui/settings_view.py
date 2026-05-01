from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QComboBox, QFrame, QPushButton, QMessageBox, QLineEdit, QFormLayout)
from PySide6.QtCore import Qt, Signal

class SettingsView(QWidget):
    position_changed = Signal(str)
    theme_changed = Signal(str)
    db_config_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        title = QLabel("⚙️ PENGATURAN SISTEM")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2d3436;")
        layout.addWidget(title)

        # Scroll area would be better, but we'll use a single layout for now
        main_container = QFrame()
        main_container.setStyleSheet("background-color: white; border-radius: 10px; padding: 20px;")
        container_layout = QVBoxLayout(main_container)

        combo_style = """
            QComboBox {
                padding: 8px; border: 2px solid #3498db; border-radius: 5px; background-color: #ffffff; color: #2c3e50; min-width: 250px; font-size: 14px;
            }
        """
        input_style = """
            QLineEdit {
                padding: 8px; border: 1px solid #ced4da; border-radius: 5px; background-color: #ffffff; color: #2c3e50; font-size: 14px;
            }
        """

        # --- Navigation Position ---
        container_layout.addWidget(QLabel("<b>Posisi Navigasi Menu:</b>"))
        self.combo_pos = QComboBox()
        self.combo_pos.addItems(["Kiri (Default)", "Kanan", "Atas", "Bawah"])
        self.combo_pos.setStyleSheet(combo_style)
        container_layout.addWidget(self.combo_pos)
        container_layout.addSpacing(10)

        # --- Theme ---
        container_layout.addWidget(QLabel("<b>Tema Tampilan:</b>"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Standard (Modern Blue)", "Dark Mode", "Classic C++ Style"])
        self.combo_theme.setStyleSheet(combo_style)
        container_layout.addWidget(self.combo_theme)
        container_layout.addSpacing(20)

        # --- Database Configuration ---
        db_title = QLabel("🛡️ KONFIGURASI DATABASE")
        db_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        container_layout.addWidget(db_title)
        
        self.combo_db_type = QComboBox()
        self.combo_db_type.addItems(["SQLite (Lokal)", "MySQL (Server)", "SQL Server (Server)"])
        self.combo_db_type.setStyleSheet(combo_style)
        self.combo_db_type.currentTextChanged.connect(self.toggle_db_inputs)
        container_layout.addWidget(self.combo_db_type)

        # MySQL Inputs
        self.mysql_group = QFrame()
        self.mysql_layout = QFormLayout(self.mysql_group)
        self.db_host = QLineEdit("localhost")
        self.db_user = QLineEdit("root")
        self.db_pass = QLineEdit()
        self.db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_name = QLineEdit("foundation_finance")
        
        for le in [self.db_host, self.db_user, self.db_pass, self.db_name]: le.setStyleSheet(input_style)
        
        self.mysql_layout.addRow("Host:", self.db_host)
        self.mysql_layout.addRow("User:", self.db_user)
        self.mysql_layout.addRow("Password:", self.db_pass)
        self.mysql_layout.addRow("Database Name:", self.db_name)
        container_layout.addWidget(self.mysql_group)
        self.mysql_group.setVisible(False)

        # SQL Server Inputs
        self.mssql_group = QFrame()
        self.mssql_layout = QFormLayout(self.mssql_group)
        self.ms_host = QLineEdit("localhost")
        self.ms_user = QLineEdit("sa")
        self.ms_pass = QLineEdit()
        self.ms_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ms_name = QLineEdit("foundation_finance")
        self.ms_driver = QComboBox()
        self.ms_driver.addItems(["ODBC Driver 17 for SQL Server", "SQL Server", "ODBC Driver 13 for SQL Server"])
        self.ms_driver.setEditable(True)
        self.ms_driver.setStyleSheet(combo_style)
        
        for le in [self.ms_host, self.ms_user, self.ms_pass, self.ms_name]: le.setStyleSheet(input_style)
        
        self.mssql_layout.addRow("Server:", self.ms_host)
        self.mssql_layout.addRow("UID:", self.ms_user)
        self.mssql_layout.addRow("PWD:", self.ms_pass)
        self.mssql_layout.addRow("Database:", self.ms_name)
        self.mssql_layout.addRow("Driver:", self.ms_driver)
        container_layout.addWidget(self.mssql_group)
        self.mssql_group.setVisible(False)

        container_layout.addSpacing(20)

        # --- Backup & Restore Section ---
        backup_title = QLabel("💾 MANAJEMEN CADANGAN DATA (BACKUP)")
        backup_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; margin-top: 10px;")
        container_layout.addWidget(backup_title)
        
        backup_btn_layout = QHBoxLayout()
        self.btn_backup = QPushButton("📤 Buat Backup Sistem")
        self.btn_restore = QPushButton("📥 Pulihkan dari Backup")
        
        btn_backup_style = """
            QPushButton { background-color: #34495e; color: white; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #2c3e50; }
        """
        btn_restore_style = """
            QPushButton { background-color: #e67e22; color: white; padding: 10px; border-radius: 5px; font-weight: bold; }
            QPushButton:hover { background-color: #d35400; }
        """
        
        self.btn_backup.setStyleSheet(btn_backup_style)
        self.btn_restore.setStyleSheet(btn_restore_style)
        
        self.btn_backup.clicked.connect(self.handle_backup)
        self.btn_restore.clicked.connect(self.handle_restore)
        
        backup_btn_layout.addWidget(self.btn_backup)
        backup_btn_layout.addWidget(self.btn_restore)
        container_layout.addLayout(backup_btn_layout)

        container_layout.addSpacing(30)

        # Save Button
        self.btn_save = QPushButton("💾 Simpan Semua Pengaturan")
        self.btn_save.setFixedWidth(250)
        self.btn_save.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; padding: 12px; border-radius: 5px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        self.btn_save.clicked.connect(self.save_settings)
        container_layout.addWidget(self.btn_save)

        layout.addWidget(main_container)
        layout.addStretch()

    def handle_backup(self):
        from PySide6.QtWidgets import QFileDialog
        from src.database_manager import DatabaseManager
        import json
        
        path, _ = QFileDialog.getSaveFileName(self, "Simpan Backup Sistem", "Backup_Yayasan_Full.json", "Backup Files (*.json)")
        if path:
            db = DatabaseManager()
            data = db.generate_full_backup()
            if data:
                try:
                    with open(path, 'w') as f:
                        json.dump(data, f, indent=4)
                    QMessageBox.information(self, "Sukses", f"Backup sistem berhasil disimpan ke:\n{path}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Gagal menulis file backup: {e}")
            else:
                QMessageBox.critical(self, "Error", "Gagal mengambil data dari database.")

    def handle_restore(self):
        from PySide6.QtWidgets import QFileDialog
        from src.database_manager import DatabaseManager
        import json
        
        reply = QMessageBox.warning(self, "Peringatan Serius", 
                                    "Proses pemulihan akan MENGHAPUS SELURUH DATA yang ada saat ini dan menggantinya dengan data dari file backup.\n\nApakah Anda yakin ingin melanjutkan?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            path, _ = QFileDialog.getOpenFileName(self, "Pilih File Backup", "", "Backup Files (*.json)")
            if path:
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                    
                    db = DatabaseManager()
                    success, msg = db.restore_full_backup(data)
                    if success:
                        QMessageBox.information(self, "Sukses", "Data berhasil dipulihkan. Aplikasi akan memerlukan restart untuk menyegarkan tampilan.")
                    else:
                        QMessageBox.critical(self, "Gagal", f"Gagal memulihkan data: {msg}")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Gagal membaca file backup: {e}")

    def toggle_db_inputs(self, text):
        self.mysql_group.setVisible(text == "MySQL (Server)")
        self.mssql_group.setVisible(text == "SQL Server (Server)")

    def save_settings(self):
        pos_map = {"Kiri (Default)": "left", "Kanan": "right", "Atas": "top", "Bawah": "bottom"}
        theme_map = {"Standard (Modern Blue)": "standard", "Dark Mode": "dark", "Classic C++ Style": "classic"}
        
        db_text = self.combo_db_type.currentText()
        db_type = "sqlite"
        if db_text == "MySQL (Server)": db_type = "mysql"
        elif db_text == "SQL Server (Server)": db_type = "sqlserver"

        mysql_config = {
            "host": self.db_host.text(),
            "user": self.db_user.text(),
            "password": self.db_pass.text(),
            "database": self.db_name.text()
        }

        sqlserver_config = {
            "host": self.ms_host.text(),
            "user": self.ms_user.text(),
            "password": self.ms_pass.text(),
            "database": self.ms_name.text(),
            "driver": self.ms_driver.currentText()
        }

        self.position_changed.emit(pos_map.get(self.combo_pos.currentText()))
        self.theme_changed.emit(theme_map.get(self.combo_theme.currentText()))
        self.db_config_changed.emit({
            "db_type": db_type, 
            "mysql_config": mysql_config,
            "sqlserver_config": sqlserver_config
        })
        
        QMessageBox.information(self, "Sukses", "Pengaturan telah disimpan. Beberapa perubahan mungkin memerlukan restart aplikasi.")

    def set_current_settings(self, pos, theme, db_type="sqlite", mysql_config=None, sqlserver_config=None):
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

        self.toggle_db_inputs(self.combo_db_type.currentText())
