import requests
import json
import os
import sys
import subprocess
import shutil
from PySide6.QtCore import QThread, Signal

VERSION = "1.1.0"
# Ganti 'main' dengan nama branch Anda (biasanya 'main' atau 'master')
UPDATE_URL = "https://raw.githubusercontent.com/tomychaky09-cmd/isak_35_updates/master/version.json"

def get_app_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_exe_path():
    return sys.executable

class UpdateChecker(QThread):
    update_available = Signal(dict)
    no_update = Signal()
    error = Signal(str)

    def run(self):
        try:
            response = requests.get(UPDATE_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("version", "1.0.0")
                
                # Hanya izinkan update jika versi server benar-benar lebih tinggi
                if latest_version > VERSION:
                    print(f"[UPDATER] Versi baru ditemukan: {latest_version} (Lokal: {VERSION})")
                    self.update_available.emit(data)
                else:
                    print(f"[UPDATER] Aplikasi sudah versi terbaru ({VERSION})")
                    self.no_update.emit()
            else:
                self.error.emit(f"Server returned status {response.status_code}")
        except Exception as e:
            self.error.emit(str(e))

class DownloadWorker(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, download_url, target_version):
        super().__init__()
        self.download_url = download_url
        self.target_version = target_version

    def run(self):
        try:
            # Validasi ulang sebelum download (double check)
            if self.target_version <= VERSION:
                self.error.emit("Versi target tidak lebih baru dari versi saat ini.")
                return

            response = requests.get(self.download_url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            
            # Gunakan folder AppData untuk penyimpanan sementara yang lebih aman
            temp_dir = os.path.join(os.environ.get("LOCALAPPDATA", os.environ.get("TEMP")), "ISAK35_Updates")
            if not os.path.exists(temp_dir):
                os.makedirs(temp_dir)
            
            save_path = os.path.join(temp_dir, f"isak35_{self.target_version}.exe")
            
            downloaded_size = 0
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            self.progress.emit(percent)
            
            self.finished.emit(save_path)
        except Exception as e:
            self.error.emit(str(e))

def apply_update(new_exe_path):
    """
    Membuat skrip batch untuk menukar executable dan merestart aplikasi.
    """
    current_exe = get_exe_path()
    
    # Jangan lakukan update jika tidak dijalankan sebagai EXE (mode dev)
    if not current_exe.lower().endswith(".exe"):
        print(f"[SIMULASI] Mode Development: Mengganti {current_exe} dengan {new_exe_path}")
        return

    # Folder EXE asli
    exe_dir = os.path.dirname(current_exe)
    batch_path = os.path.join(exe_dir, "finish_update.bat")
    
    # Skrip batch yang lebih robust
    batch_content = f"""
@echo off
title Updating ISAK 35...
taskkill /f /im "{os.path.basename(current_exe)}" >nul 2>&1
timeout /t 2 /nobreak >nul
del /f /q "{current_exe}"
move /y "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    try:
        with open(batch_path, "w") as f:
            f.write(batch_content)
        
        subprocess.Popen([batch_path], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        sys.exit(0)
    except Exception as e:
        print(f"Gagal menerapkan update: {e}")
