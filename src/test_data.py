try:
    from .database_manager import DatabaseManager
except ImportError:
    from database_manager import DatabaseManager
import datetime

def add_sample_transactions():
    db = DatabaseManager('database/foundation_finance.db')
    
    # Ambil ID Akun yang Dibutuhkan
    accounts_raw = db.get_accounts()
    if not accounts_raw:
        print("Error: Tidak ada akun (COA) di database. Pastikan database_init.py sudah dijalankan.")
        return
        
    accounts = {row[1]: row[0] for row in accounts_raw}
    
    # Pastikan akun yang dibutuhkan ada
    required_codes = ['1000', '4000', '4100', '5200']
    for code in required_codes:
        if code not in accounts:
            print(f"Error: Akun dengan kode {code} tidak ditemukan di database.")
            return

    # 1. Transaksi: Penerimaan Donasi Umum (Tanpa Pembatasan)
    db.add_journal_entry(
        date=str(datetime.date.today()),
        description="Penerimaan Donasi Umum",
        ref_no="J-001",
        details=[
            {'account_id': accounts['1000'], 'debit': 10000000, 'credit': 0},
            {'account_id': accounts['4000'], 'debit': 0, 'credit': 10000000, 'cash_flow_activity': 'Operasi'}
        ]
    )
    
    # 2. Transaksi: Penerimaan Donasi Terikat (Dengan Pembatasan)
    db.add_journal_entry(
        date=str(datetime.date.today()),
        description="Penerimaan Donasi Pembangunan Gedung",
        ref_no="J-002",
        details=[
            {'account_id': accounts['1000'], 'debit': 5000000, 'credit': 0},
            {'account_id': accounts['4100'], 'debit': 0, 'credit': 5000000, 'cash_flow_activity': 'Pendanaan'}
        ]
    )
    
    # 3. Transaksi: Pembayaran Gaji
    db.add_journal_entry(
        date=str(datetime.date.today()),
        description="Pembayaran Gaji Karyawan",
        ref_no="J-003",
        details=[
            {'account_id': accounts['5200'], 'debit': 2000000, 'credit': 0, 'cash_flow_activity': 'Operasi'},
            {'account_id': accounts['1000'], 'debit': 0, 'credit': 2000000}
        ]
    )
    
    print("Sample transactions added successfully.")

if __name__ == "__main__":
    add_sample_transactions()
