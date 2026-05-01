import sys
import os
from PySide6.QtWidgets import QApplication

# Otomatis menambahkan direktori saat ini ke path Python
# agar folder 'src' bisa ditemukan sebagai modul
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    print("=== Aplikasi Yayasan ISAK 35 Berhasil Dijalankan ===")
    sys.exit(app.exec())
