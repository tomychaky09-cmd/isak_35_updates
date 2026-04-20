import openpyxl
import os

template_dir = "/home/tomychaky/aplikasi-yayasan-isak35/src/templates"
os.makedirs(template_dir, exist_ok=True)

# Create COA Template
coa_wb = openpyxl.Workbook()
coa_ws = coa_wb.active
coa_ws.title = "Bagan Akun"
coa_ws.append(["Kode", "Nama Akun", "Tipe", "Kategori"])
coa_wb.save(os.path.join(template_dir, "coa_template.xlsx"))
print(f"Created coa_template.xlsx in {template_dir}")

# Create Journal Template
journal_wb = openpyxl.Workbook()
journal_ws = journal_wb.active
journal_ws.title = "Jurnal Umum"
journal_ws.append(["Tanggal", "Deskripsi", "No. Referensi", "Kode Akun", "Debit", "Kredit", "Aktivitas Arus Kas"])
journal_wb.save(os.path.join(template_dir, "journal_template.xlsx"))
print(f"Created journal_template.xlsx in {template_dir}")
