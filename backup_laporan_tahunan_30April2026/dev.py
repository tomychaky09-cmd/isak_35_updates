import sys
import time
import os
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class RestartHandler(FileSystemEventHandler):
    def __init__(self, command):
        self.command = command
        self.process = None
        self.restart()

    def restart(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        print(f"\n[DEV] File berubah. Menjalankan ulang aplikasi...")
        self.process = subprocess.Popen([sys.executable] + self.command)

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            self.restart()

if __name__ == "__main__":
    path = "."
    command = ["run.py"]
    event_handler = RestartHandler(command)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print(f"--- Dev Mode: Aktif (Memantau perubahan file .py) ---")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
