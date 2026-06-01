Write-Host "Mengaktifkan Virtual Environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1
Write-Host "Menjalankan Aplikasi Web..." -ForegroundColor Green
python flask_app.py
pause
