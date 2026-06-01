import sqlite3
import os

def initialize_database(db_path='database/foundation_finance.db'):
    # Pastikan direktori database ada
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Tabel Akun (Chart of Accounts)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL, -- Asset, Liability, Asset Net, Revenue, Expense
        category TEXT -- Without Restriction, With Restriction, None
    )
    ''')
    
    # 2. Tabel Jurnal Umum (Header)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS journal_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT,
        reference_no TEXT
    )
    ''')
    
    # 3. Tabel Detail Jurnal (Lines)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS journal_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        journal_id INTEGER,
        account_id INTEGER,
        debit REAL DEFAULT 0,
        credit REAL DEFAULT 0,
        FOREIGN KEY (journal_id) REFERENCES journal_entries(id),
        FOREIGN KEY (account_id) REFERENCES accounts(id)
    )
    ''')
    
    # Isi Data Awal: Bagan Akun Standar ISAK 35
    initial_accounts = [
        # Aset
        ('1000', 'Kas dan Setara Kas', 'Asset', 'None'),
        ('1100', 'Piutang', 'Asset', 'None'),
        ('1200', 'Aset Tetap', 'Asset', 'None'),
        ('1201', 'Akumulasi Penyusutan Aset Tetap', 'Asset', 'None'),
        
        # Liabilitas
        ('2000', 'Utang Usaha', 'Liability', 'None'),
        ('2100', 'Utang Gaji', 'Liability', 'None'),
        
        # Aset Neto (Ekuitas)
        ('3000', 'Aset Neto Tanpa Pembatasan', 'Asset Net', 'Without Restriction'),
        ('3100', 'Aset Neto Dengan Pembatasan', 'Asset Net', 'With Restriction'),
        
        # Pendapatan
        ('4000', 'Pendapatan Tanpa Pembatasan', 'Revenue', 'Without Restriction'),
        ('4100', 'Pendapatan Dengan Pembatasan', 'Revenue', 'With Restriction'),
        ('4200', 'Penghasilan Investasi', 'Revenue', 'Without Restriction'),
        
        # Beban
        ('5000', 'Beban Program', 'Expense', 'Without Restriction'),
        ('5100', 'Beban Umum dan Administrasi', 'Expense', 'Without Restriction'),
        ('5200', 'Beban Gaji', 'Expense', 'Without Restriction'),
        ('5300', 'Beban Penyusutan', 'Expense', 'Without Restriction')
    ]
    
    cursor.executemany('INSERT OR IGNORE INTO accounts (code, name, type, category) VALUES (?, ?, ?, ?)', initial_accounts)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {db_path}")

if __name__ == "__main__":
    initialize_database()
