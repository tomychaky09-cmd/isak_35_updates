import sys
from PySide6.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QStackedWidget, 
                             QStatusBar, QFrame, QMessageBox, QDialog, QListWidget,
                             QLineEdit, QDialogButtonBox, QDateEdit, QFormLayout, QLayout)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QColor, QPalette
from .journal_entry import JournalEntryView
from .report_view import ReportView
from .coa_view import CoaView
from .journal_list_view import JournalListView
from .journal_detail_dialog import JournalDetailDialog
from .cash_flow_view import CashFlowView
from .settings_view import SettingsView
from .asset_view import AssetView
from .donor_view import DonorView
from src.database_manager import DatabaseManager
from src.updater import VERSION, UpdateChecker, DownloadWorker, apply_update
import json
import os
from PySide6.QtWidgets import QProgressDialog

class ClearAllDataDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Konfirmasi Hapus Semua Data")
        self.setModal(True); self.setMinimumWidth(400)
        layout = QVBoxLayout(self)
        warning_label = QLabel("PERINGATAN: Anda akan menghapus SEMUA data pengguna.\nTindakan ini TIDAK DAPAT DIBATALKAN.\nUntuk melanjutkan, ketik 'HAPUS SEMUA' di bawah ini:")
        warning_label.setWordWrap(True); layout.addWidget(warning_label)
        self.line_edit = QLineEdit(); self.line_edit.setPlaceholderText("Ketik 'HAPUS SEMUA' di sini"); layout.addWidget(self.line_edit)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Hapus Sekarang"); self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        self.button_box.accepted.connect(self.accept); self.button_box.rejected.connect(self.reject); layout.addWidget(self.button_box)
        self.line_edit.textChanged.connect(self._check_input)
    def _check_input(self, text): self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(text == "HAPUS SEMUA")
    def get_input_text(self): return self.line_edit.text()

class MainWindow(QMainWindow):
    CONFIG_FILE = "user_settings.json"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistem Pelaporan Keuangan Yayasan - ISAK 35")
        self.resize(1200, 800)
        
        config = self.load_config()
        self.nav_position = config.get("nav_position", "left")
        self.current_theme = config.get("theme", "standard")
        self.db_type = config.get("db_type", "sqlite")
        self.mysql_config = config.get("mysql_config", {})
        self.sqlserver_config = config.get("sqlserver_config", {})

        self.db = DatabaseManager()

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.root_layout = None 
        
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar_layout = None 
        
        self.label_title = QLabel("YAYASAN FINANCE")
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_title.setStyleSheet("font-size: 18px; margin-bottom: 20px; font-weight: bold; color: white; letter-spacing: 1px;")
        
        self.btn_dashboard = QPushButton("📊 Dashboard")
        self.btn_coa = QPushButton("📂 Bagan Akun (COA)")
        self.btn_journal = QPushButton("📝 Jurnal Umum")
        self.btn_reports = QPushButton("📑 Laporan Keuangan")
        self.btn_cash_flow = QPushButton("🌊 Arus Kas")
        self.btn_assets = QPushButton("📦 Aset Inventaris")
        self.btn_donors = QPushButton("🤝 Daftar Donatur")
        self.btn_closing_entries = QPushButton("🔒 Jurnal Penutup")
        self.btn_clear_data = QPushButton("🧹 Hapus/Reset Data")
        self.btn_settings = QPushButton("⚙️ Pengaturan")
        self.btn_update = QPushButton(f"🚀 Update (v{VERSION})")
        
        self.nav_buttons = [self.btn_dashboard, self.btn_coa, self.btn_journal, self.btn_reports, self.btn_cash_flow, self.btn_assets, self.btn_donors, self.btn_closing_entries, self.btn_clear_data, self.btn_settings, self.btn_update]
        
        self.content_area = QStackedWidget()
        self.setup_dashboard_ui() # 0
        self.coa_view = CoaView(); self.content_area.addWidget(self.coa_view) # 1
        self.journal_list_view = JournalListView(); self.content_area.addWidget(self.journal_list_view) # 2
        self.journal_entry_view = JournalEntryView(); self.content_area.addWidget(self.journal_entry_view) # 3
        self.report_view = ReportView(); self.content_area.addWidget(self.report_view) # 4
        self.cash_flow_view = CashFlowView(); self.content_area.addWidget(self.cash_flow_view) # 5
        self.asset_view = AssetView(); self.content_area.addWidget(self.asset_view) # 6
        self.donor_view = DonorView(); self.content_area.addWidget(self.donor_view) # 7
        self.settings_view = SettingsView(); self.content_area.addWidget(self.settings_view) # 8
        
        self.settings_view.set_current_settings(self.nav_position, self.current_theme, self.db_type, self.mysql_config, self.sqlserver_config)
        self.apply_navigation_layout(self.nav_position)
        self.apply_theme(self.current_theme)
        self.apply_sidebar_style()
        
        self.btn_dashboard.clicked.connect(lambda: self.switch_view(0))
        self.btn_coa.clicked.connect(lambda: self.switch_view(1))
        self.btn_journal.clicked.connect(self.show_journal_list)
        self.btn_reports.clicked.connect(self.show_reports)
        self.btn_cash_flow.clicked.connect(lambda: self.switch_view(5))
        self.btn_assets.clicked.connect(lambda: self.switch_view(6))
        self.btn_donors.clicked.connect(lambda: self.switch_view(7))
        self.btn_clear_data.clicked.connect(self.open_clear_data_dialog)
        self.btn_closing_entries.clicked.connect(self.open_closing_entries_dialog)
        self.btn_settings.clicked.connect(lambda: self.switch_view(8))
        self.btn_update.clicked.connect(self.check_for_updates)
        
        self.settings_view.position_changed.connect(self.on_nav_position_changed)
        self.settings_view.theme_changed.connect(self.on_theme_changed)
        self.settings_view.db_config_changed.connect(self.on_db_config_changed)
        
        self.journal_list_view.journal_selected.connect(self.open_journal_detail)
        self.journal_list_view.new_journal_requested.connect(self.open_new_journal_form)
        self.journal_list_view.edit_journal_requested.connect(self.open_journal_for_edit)
        self.journal_list_view.back_to_dashboard_requested.connect(lambda: self.switch_view(0))
        self.cash_flow_view.back_to_dashboard_requested.connect(lambda: self.switch_view(0))
        self.journal_entry_view.back_requested.connect(self.show_journal_list)
        
        self.setStatusBar(QStatusBar(self)); self.switch_view(0)

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f: return json.load(f)
            except: pass
        return {"nav_position": "left", "theme": "standard", "db_type": "sqlite", "mysql_config": {}, "sqlserver_config": {}}

    def save_config(self):
        config = {"nav_position": self.nav_position, "theme": self.current_theme, "db_type": self.db_type, "mysql_config": self.mysql_config, "sqlserver_config": self.sqlserver_config}
        with open(self.CONFIG_FILE, 'w') as f: json.dump(config, f)

    def on_nav_position_changed(self, position):
        self.nav_position = position; self.save_config(); self.apply_navigation_layout(position); self.apply_sidebar_style()

    def on_theme_changed(self, theme):
        self.current_theme = theme; self.save_config(); self.apply_theme(theme); self.apply_sidebar_style()

    def on_db_config_changed(self, db_config):
        self.db_type = db_config["db_type"]
        self.mysql_config = db_config["mysql_config"]
        self.sqlserver_config = db_config.get("sqlserver_config", {})
        self.save_config()
        QMessageBox.warning(self, "Informasi", "Konfigurasi database disimpan. Harap restart aplikasi untuk menerapkan koneksi baru.")

    def apply_theme(self, theme):
        app = QApplication.instance()
        if theme == "classic":
            app.setStyle("Fusion"); app.setPalette(app.style().standardPalette()); self.content_area.setStyleSheet("background-color: #f0f0f0;"); self.setStyleSheet("")
        elif theme == "dark":
            app.setStyle("Fusion"); self.set_dark_palette(app); self.content_area.setStyleSheet("background-color: #2d3436;"); self.setStyleSheet("QMainWindow { background-color: #2d3436; }")
        else: # standard
            app.setStyle("Windows"); app.setPalette(app.style().standardPalette()); self.content_area.setStyleSheet("background-color: #d1d8e0;"); self.setStyleSheet("")

    def set_dark_palette(self, app):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 52, 54)); palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30)); palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 52, 54))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white); palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white); palette.setColor(QPalette.ColorRole.Button, QColor(45, 52, 54))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white); palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218)); palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black); app.setPalette(palette)

    def apply_navigation_layout(self, position):
        # 1. Lepaskan widget utama dari root_layout agar tidak ikut terhapus
        self.sidebar.setParent(None)
        self.content_area.setParent(None)
        
        # 2. Hapus root_layout lama jika ada
        if self.main_widget.layout():
            # Trik aman untuk menghapus layout tanpa menghapus widget
            old_layout = self.main_widget.layout()
            # Pindahkan layout ke widget dummy yang segera dibuang
            QWidget().setLayout(old_layout)

        # 3. Lepaskan widget dalam sidebar dari sidebar_layout agar tidak terhapus
        self.label_title.setParent(None)
        for btn in self.nav_buttons:
            btn.setParent(None)

        if self.sidebar.layout():
            QWidget().setLayout(self.sidebar.layout())

        # 4. Buat Layout Baru
        if position in ["left", "right"]:
            self.root_layout = QHBoxLayout(self.main_widget)
            self.sidebar.setFixedWidth(230); self.sidebar.setFixedHeight(16777215)
            self.sidebar_layout = QVBoxLayout(self.sidebar)
            self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
            self.sidebar_layout.setContentsMargins(0, 20, 0, 20)
            self.label_title.setVisible(True)
            self.sidebar_layout.addWidget(self.label_title)
            for btn in self.nav_buttons: btn.setFixedWidth(16777215); self.sidebar_layout.addWidget(btn)
        else: # top, bottom
            self.root_layout = QVBoxLayout(self.main_widget)
            self.sidebar.setFixedHeight(80); self.sidebar.setFixedWidth(16777215)
            self.sidebar_layout = QHBoxLayout(self.sidebar)
            self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            self.sidebar_layout.setContentsMargins(20, 0, 20, 0)
            self.label_title.setVisible(False)
            for btn in self.nav_buttons: btn.setFixedWidth(140); self.sidebar_layout.addWidget(btn)

        self.root_layout.setContentsMargins(0, 0, 0, 0); self.root_layout.setSpacing(0)

        # 5. Pasang kembali ke Root Layout
        if position == "left":
            self.root_layout.addWidget(self.sidebar); self.root_layout.addWidget(self.content_area)
        elif position == "right":
            self.root_layout.addWidget(self.content_area); self.root_layout.addWidget(self.sidebar)
        elif position == "top":
            self.root_layout.addWidget(self.sidebar); self.root_layout.addWidget(self.content_area)
        elif position == "bottom":
            self.root_layout.addWidget(self.content_area); self.root_layout.addWidget(self.sidebar)

    def apply_sidebar_style(self):
        padding = "12px 20px" if self.nav_position in ["left", "right"] else "5px 10px"
        font_size = "14px" if self.nav_position in ["left", "right"] else "12px"
        margin = "2px 10px" if self.nav_position in ["left", "right"] else "2px 5px"
        text_align = "left" if self.nav_position in ["left", "right"] else "center"
        self.sidebar.setStyleSheet(f"""
            QFrame#sidebar {{ background-color: #2c3e50; color: white; border: none; }}
            QPushButton {{ text-align: {text_align}; padding: {padding}; background: transparent; border: none; font-size: {font_size}; color: #bdc3c7; border-radius: 5px; margin: {margin}; }}
            QPushButton:hover {{ background-color: #34495e; color: white; }}
            QPushButton[active="true"] {{ background-color: #3498db; color: white; font-weight: bold; }}
        """)

    def setup_dashboard_ui(self):
        self.dashboard_widget = QWidget(); layout = QVBoxLayout(self.dashboard_widget); layout.setContentsMargins(40, 40, 40, 40); layout.setSpacing(30)
        header = QHBoxLayout(); title = QLabel("📊 DASHBOARD KEUANGAN QUDWAH AS SUNNAH LAMANDAU"); title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2d3436;"); header.addWidget(title); header.addStretch(); self.lbl_balance_status = QLabel(); header.addWidget(self.lbl_balance_status); layout.addLayout(header)
        self.cards_layout = QHBoxLayout()
        self.card_asset = self.create_summary_card("TOTAL ASET", "Rp 0", "#3498db"); self.card_revenue = self.create_summary_card("TOTAL PENDAPATAN", "Rp 0", "#2ecc71"); self.card_surplus = self.create_summary_card("SURPLUS/DEFISIT", "Rp 0", "#27ae60"); self.card_expense = self.create_summary_card("TOTAL PENGELUARAN", "Rp 0", "#e74c3c")
        for c in [self.card_asset, self.card_revenue, self.card_surplus, self.card_expense]: self.cards_layout.addWidget(c)
        layout.addLayout(self.cards_layout)
        info_box = QFrame(); info_box.setStyleSheet("background-color: #ffffff; border-radius: 8px; border: 1px solid #a5b1c2; padding: 20px;"); info_layout = QVBoxLayout(info_box); info_title = QLabel("SYSTEM STATUS"); info_title.setStyleSheet("color: #000000; font-weight: bold; font-size: 16px;"); info_desc = QLabel("Seluruh data laporan disinkronkan secara otomatis sesuai dengan standar ISAK 35."); info_desc.setStyleSheet("color: #000000; font-size: 14px;"); info_layout.addWidget(info_title); info_layout.addWidget(info_desc); layout.addWidget(info_box); layout.addStretch(); self.content_area.addWidget(self.dashboard_widget); self.refresh_dashboard_data()

    def refresh_dashboard_data(self):
        try:
            df = self.db.get_trial_balance()
            total_debit = df['total_debit'].sum(); total_credit = df['total_credit'].sum(); is_balanced = abs(total_debit - total_credit) < 0.01
            if is_balanced: self.lbl_balance_status.setText("✔️ SISTEM SEIMBANG"); self.lbl_balance_status.setStyleSheet("background-color: #2ecc71; color: white; padding: 8px 15px; border-radius: 20px; font-weight: bold;")
            else: self.lbl_balance_status.setText(f"⚠️ TIDAK SEIMBANG: Rp {abs(total_debit-total_credit):,.0f}"); self.lbl_balance_status.setStyleSheet("background-color: #e74c3c; color: white; padding: 8px 15px; border-radius: 20px; font-weight: bold;")
            total_asset = df[df['type'] == 'Asset']['balance'].sum() - df[df['type'] == 'Asset (Contra)']['balance'].sum()
            total_revenue = df[df['type'] == 'Revenue']['balance'].sum(); total_expense = df[df['type'] == 'Expense']['balance'].sum(); surplus = total_revenue - total_expense
            self.update_card(self.card_asset, f"Rp {total_asset:,.0f}"); self.update_card(self.card_revenue, f"Rp {total_revenue:,.0f}"); self.update_card(self.card_expense, f"Rp {total_expense:,.0f}")
            surplus_title = "SURPLUS BERJALAN" if surplus >= 0 else "DEFISIT BERJALAN"; surplus_color = "#27ae60" if surplus >= 0 else "#e67e22"
            self.update_card(self.card_surplus, f"Rp {abs(surplus):,.0f}", surplus_title, surplus_color)
        except Exception as e: print(f"Refresh Dashboard Error: {e}")

    def create_summary_card(self, title, value, color):
        card = QFrame(); card.setStyleSheet(f"background-color: #ffffff; border-radius: 12px; border-left: 6px solid {color};")
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(); shadow.setBlurRadius(15); shadow.setXOffset(0); shadow.setYOffset(4); shadow.setColor(QColor(0, 0, 0, 40)); card.setGraphicsEffect(shadow)
        layout = QVBoxLayout(card); layout.setContentsMargins(25, 25, 25, 25); lbl_title = QLabel(title); lbl_title.setStyleSheet("color: #000000; font-size: 13px; font-weight: bold;"); lbl_value = QLabel(value); lbl_value.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; margin-top: 8px;"); layout.addWidget(lbl_title); layout.addWidget(lbl_value); return card

    def update_card(self, card, value, title=None, color=None):
        labels = card.findChildren(QLabel)
        if len(labels) >= 2:
            if title: labels[0].setText(title)
            labels[1].setText(value)
            if color: card.setStyleSheet(f"background-color: #ffffff; border-radius: 12px; border-left: 6px solid {color};"); labels[1].setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold; margin-top: 8px;")

    def switch_view(self, index):
        self.content_area.setCurrentIndex(index)
        view_to_btn_map = {0: 0, 1: 1, 2: 2, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 9} # Fixed mapping
        active_btn_idx = view_to_btn_map.get(index, -1)
        for i, btn in enumerate(self.nav_buttons):
            is_active = (i == active_btn_idx); btn.setProperty("active", is_active); btn.style().unpolish(btn); btn.style().polish(btn)
        if index == 0: self.refresh_dashboard_data()
        elif index == 1: self.coa_view.load_accounts()
        elif index == 2: self.journal_list_view.load_journals()
        elif index == 4: self.report_view.load_all()
        elif index == 5: self.cash_flow_view.load_categories()
        elif index == 6: self.asset_view.load_assets()
        elif index == 7: self.donor_view.load_donors()

    def show_journal_list(self): self.switch_view(2)
    def show_reports(self): self.switch_view(4)
    def open_new_journal_form(self): self.journal_entry_view._populate_account_list(); self.journal_entry_view.reset_form(); self.switch_view(3)
    def open_journal_for_edit(self, j_id): self.journal_entry_view._populate_account_list(); self.journal_entry_view.load_journal_for_edit(j_id); self.switch_view(3)
    def open_clear_data_dialog(self): 
        msg = QMessageBox(); msg.setWindowTitle("Reset Data"); msg.setText("Pilih opsi penghapusan data:"); b1 = msg.addButton("Hapus Tabel", QMessageBox.ButtonRole.ActionRole); b2 = msg.addButton("Hapus Semua", QMessageBox.ButtonRole.DestructiveRole); msg.addButton("Batal", QMessageBox.ButtonRole.RejectRole); msg.exec()
        if msg.clickedButton() == b1: self._show_clear_specific_table_dialog()
        elif msg.clickedButton() == b2: self._confirm_clear_all_data()
    def _show_clear_specific_table_dialog(self):
        d = QDialog(self); d.setWindowTitle("Hapus Tabel"); l = QVBoxLayout(d); lw = QListWidget(); lw.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for t in self.db.get_all_data_table_names(): lw.addItem(t)
        l.addWidget(lw); b = QPushButton("Hapus"); b.clicked.connect(lambda: self._clear_selected_tables(lw, d)); l.addWidget(b); d.exec()
    def _clear_selected_tables(self, lw, d):
        sel = [i.text() for i in lw.selectedItems()]
        if sel and QMessageBox.question(self, "Konfirmasi", f"Hapus {', '.join(sel)}?") == QMessageBox.StandardButton.Yes:
            for t in sel: self.db.clear_table_data(t)
            d.accept(); self._refresh_all_views()
    def _confirm_clear_all_data(self):
        d = ClearAllDataDialog(self); 
        if d.exec() == QDialog.DialogCode.Accepted: self.db.clear_all_data(); self._refresh_all_views()
    def open_closing_entries_dialog(self):
        d = QDialog(self); d.setWindowTitle("Jurnal Penutup"); l = QVBoxLayout(d); f = QFormLayout(); dt = QDateEdit(calendarPopup=True); dt.setDate(QDate.currentDate()); y = QLineEdit(str(QDate.currentDate().year())); f.addRow("Tanggal:", dt); f.addRow("Tahun:", y); l.addLayout(f); bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel); l.addWidget(bb); bb.accepted.connect(d.accept); bb.rejected.connect(d.reject)
        if d.exec() == QDialog.DialogCode.Accepted:
            if self.db.create_closing_entries(dt.date().toString("yyyy-MM-dd"), int(y.text())): self._refresh_all_views()
    def _refresh_all_views(self): self.refresh_dashboard_data(); self.coa_view.load_accounts(); self.journal_list_view.load_journals(); self.report_view.load_all(); self.journal_entry_view._populate_account_list()
    def open_journal_detail(self, j_id): JournalDetailDialog(j_id, self).exec()

    def check_for_updates(self):
        self.statusBar().showMessage("Memeriksa update...")
        self.checker = UpdateChecker()
        self.checker.update_available.connect(self.on_update_available)
        self.checker.no_update.connect(lambda: QMessageBox.information(self, "Update", "Aplikasi sudah versi terbaru."))
        self.checker.error.connect(lambda e: QMessageBox.warning(self, "Update Error", f"Gagal memeriksa update: {e}"))
        self.checker.start()

    def on_update_available(self, data):
        v = data.get("version")
        c = data.get("changelog", "Tidak ada catatan perubahan.")
        url = data.get("url")
        if QMessageBox.question(self, "Update Tersedia", f"Versi {v} tersedia!\n\nChangelog:\n{c}\n\nIngin update sekarang?") == QMessageBox.StandardButton.Yes:
            self.start_download(url)

    def start_download(self, url):
        self.progress = QProgressDialog("Downloading update...", "Batal", 0, 100, self)
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.show()
        
        self.downloader = DownloadWorker(url)
        self.downloader.progress.connect(self.progress.setValue)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.error.connect(lambda e: (self.progress.close(), QMessageBox.critical(self, "Download Error", f"Gagal download: {e}")))
        self.downloader.start()

    def on_download_finished(self, path):
        self.progress.close()
        if QMessageBox.question(self, "Download Selesai", "Update siap dipasang. Aplikasi akan restart otomatis. Lanjutkan?") == QMessageBox.StandardButton.Yes:
            apply_update(path)

if __name__ == "__main__":
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec())
