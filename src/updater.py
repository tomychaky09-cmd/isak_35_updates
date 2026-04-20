import requests
import json
import os
import sys
import subprocess
import shutil
from PySide6.QtCore import QThread, Signal

VERSION = "1.0.0"
# Ganti 'main' dengan nama branch Anda (biasanya 'main' atau 'master')
# Ganti 'nama_repo' dengan nama repository tempat Anda menyimpan version.json
UPDATE_URL = "https://raw.githubusercontent.com/tomychaky09-cmd/isak_35_updates/master/version.json"

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
                if latest_version > VERSION:
                    self.update_available.emit(data)
                else:
                    self.no_update.emit()
            else:
                self.error.emit(f"Server returned status {response.status_code}")
        except Exception as e:
            self.error.emit(str(e))

class DownloadWorker(QThread):
    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            response = requests.get(self.download_url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            
            save_path = os.path.join(os.environ.get("TEMP", "."), "isak35_update.exe")
            
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
    Creates a batch script to swap the executable and restarts the app.
    """
    current_exe = sys.argv[0]
    if not current_exe.endswith(".exe"):
        # For development mode, just print info
        print(f"Bukan mode EXE. Simulasi update dari {new_exe_path} ke {current_exe}")
        return

    # Create updater batch script
    batch_content = f"""
@echo off
taskkill /f /im {os.path.basename(current_exe)}
timeout /t 2 /nobreak
del "{current_exe}"
move "{new_exe_path}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
"""
    batch_path = os.path.join(os.path.dirname(current_exe), "updater.bat")
    with open(batch_path, "w") as f:
        f.write(batch_content)
    
    # Run the batch script and exit current process
    subprocess.Popen([batch_path], shell=True)
    sys.exit(0)
