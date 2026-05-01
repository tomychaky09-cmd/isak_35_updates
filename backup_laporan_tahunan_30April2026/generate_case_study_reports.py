import sqlite3
import pandas as pd
import os
from datetime import datetime

# Mock DatabaseManager for in-memory database
class MockDatabaseManager:
    def __init__(self, db_path=':memory:'): # Use in-memory database
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path) # Maintain a single connection
        self._update_schema()

    def _execute_query(self, query, params=(), fetch=False):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query, params)
            result = None
            if fetch:
                result = cursor.fetchall()
            self.conn.commit()
            return result
        except Exception as e:
            self.conn.rollback()
            print(f"Error executing query: {query} with params {params} - {e}")
            raise

    def _update_schema(self):
        cursor = self.conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                reference_no TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                journal_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                debit REAL DEFAULT 0,
                credit REAL DEFAULT 0,
                cash_flow_activity TEXT,
                FOREIGN KEY (journal_id) REFERENCES journal_entries(id) ON DELETE CASCADE,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cash_flow_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                main_category TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def get_accounts(self):
        query = "SELECT id, code, name, type, category FROM accounts ORDER BY code"
        return self._execute_query(query, fetch=True)

    def add_account(self, code, name, type, category):
        query = "INSERT INTO accounts (code, name, type, category) VALUES (?, ?, ?, ?)"
        self._execute_query(query, (code, name, type, category))

    def bulk_add_accounts(self, accounts_data):
        cursor = self.conn.cursor()
        success_count = 0
        errors = []
        try:
            for account in accounts_data:
                code = account['code']
                name = account['name']
                acc_type = account['type']
                category = account['category']
                cursor.execute("INSERT INTO accounts (code, name, type, category) VALUES (?, ?, ?, ?)", 
                               (code, name, acc_type, category))
                success_count += 1
            self.conn.commit()
        except sqlite3.IntegrityError as e:
            errors.append(f"Account with code {code} already exists: {e}")
            self.conn.rollback()
        except Exception as e:
            errors.append(f"Error adding account {code}: {e}")
            self.conn.rollback()
        return success_count, len(accounts_data) - success_count, errors

    def bulk_add_cash_flow_categories(self, categories_data):
        cursor = self.conn.cursor()
        try:
            cursor.executemany("INSERT INTO cash_flow_categories (name, main_category) VALUES (?, ?)", categories_data)
            self.conn.commit()
        except sqlite3.IntegrityError:
            print("Cash flow categories already exist (expected in mock setup).")
        except Exception as e:
            print(f"Error adding cash flow categories: {e}")
            self.conn.rollback()

    def add_journal_entry(self, date, description, ref_no, details):
        cursor = self.conn.cursor()
        try:
            cursor.execute("INSERT INTO journal_entries (date, description, reference_no) VALUES (?, ?, ?)", 
                           (date, description, ref_no))
            journal_id = cursor.lastrowid
            
            for item in details:
                cursor.execute("INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)", 
                               (journal_id, item['account_id'], item['debit'], item['credit'], item.get('cash_flow_activity')))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding journal entry: {e}")
            self.conn.rollback()
            return False

    def get_account_id_by_code(self, account_code):
        query = "SELECT id FROM accounts WHERE code = ?"
        result = self._execute_query(query, (account_code,), fetch=True)
        if result:
            return result[0][0]
        return None

    def get_trial_balance(self):
        query = """
        SELECT a.id, a.code, a.name, a.type, a.category, 
               SUM(jd.debit) as total_debit, SUM(jd.credit) as total_credit
        FROM accounts a
        LEFT JOIN journal_details jd ON a.id = jd.account_id
        GROUP BY a.id, a.code, a.name, a.type, a.category
        ORDER BY a.code
        """
        df = pd.read_sql_query(query, self.conn)
        
        df['balance'] = 0.0
        df['total_debit'] = pd.to_numeric(df['total_debit'].fillna(0), errors='coerce').fillna(0)
        df['total_credit'] = pd.to_numeric(df['total_credit'].fillna(0), errors='coerce').fillna(0)

        mask_debit = df['type'].isin(['Asset', 'Expense'])
        df.loc[mask_debit, 'balance'] = df['total_debit'] - df['total_credit']
        
        mask_credit = df['type'].isin(['Liability', 'Asset Net', 'Revenue'])
        df.loc[mask_credit, 'balance'] = df['total_credit'] - df['total_debit']
        
        return df

    def get_cash_account_ids(self):
        query = "SELECT id FROM accounts WHERE name IN ('Kas', 'Bank - Mandiri', 'Cash', 'Kas dan Setara Kas')"
        result = self._execute_query(query, fetch=True)
        if result:
            return [row[0] for row in result]
        return []

    def get_cash_flow_categories(self):
        query = "SELECT id, name, main_category FROM cash_flow_categories ORDER BY name"
        return self._execute_query(query, fetch=True)

    def get_cash_flow_activity_mapping(self):
        categories = self.get_cash_flow_categories()
        mapping = {}
        for cat_id, name, main_cat in categories:
            mapping[name] = main_cat
        return mapping

# Mock ReportGenerator (simplified for summary)
class MockReportGenerator:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_isak35_financial_position(self):
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)
        
        total_assets = df[df['type'] == 'Asset']['balance'].sum()
        total_liabilities = df[df['type'] == 'Liability']['balance'].sum()
        
        # Get net assets balances from trial balance (before closing entries)
        net_assets_unrestricted_tb = df[(df['type'] == 'Asset Net') & (df['category'] == 'Tidak Terbatas')]['balance'].sum()
        net_assets_restricted_time_tb = df[(df['type'] == 'Asset Net') & (df['category'] == 'Terbatas Waktu')]['balance'].sum()
        net_assets_restricted_permanent_tb = df[(df['type'] == 'Asset Net') & (df['category'] == 'Terbatas Permanen')]['balance'].sum()

        # Get net income/loss from comprehensive income report
        ci_summary = self.get_comprehensive_income()
        net_income_loss = ci_summary['net_income_loss']

        # Adjust unrestricted net assets with net income/loss (simulating closing entry)
        final_net_unrestricted = net_assets_unrestricted_tb + net_income_loss
        final_net_restricted_time = net_assets_restricted_time_tb
        final_net_restricted_permanent = net_assets_restricted_permanent_tb
        
        total_net_assets = final_net_unrestricted + final_net_restricted_time + final_net_restricted_permanent
        
        return {
            'total_assets': total_assets,
            'total_liabilities': total_liabilities,
            'net_assets_unrestricted': final_net_unrestricted,
            'net_assets_restricted_time': final_net_restricted_time,
            'net_assets_restricted_permanent': final_net_restricted_permanent,
            'total_net_assets': total_net_assets
        }

    def get_comprehensive_income(self):
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)
        
        total_revenue_unrestricted = df[(df['type'] == 'Revenue') & (df['category'] == 'Tidak Terbatas')]['balance'].sum()
        total_revenue_restricted_time = df[(df['type'] == 'Revenue') & (df['category'] == 'Terbatas Waktu')]['balance'].sum()
        total_revenue_restricted_permanent = df[(df['type'] == 'Revenue') & (df['category'] == 'Terbatas Permanen')]['balance'].sum()
        
        total_expenses = df[df['type'] == 'Expense']['balance'].sum()

        total_revenue = total_revenue_unrestricted + total_revenue_restricted_time + total_revenue_restricted_permanent
        net_income_loss = total_revenue - total_expenses
        
        return {
            'total_revenue_unrestricted': total_revenue_unrestricted,
            'total_revenue_restricted_time': total_revenue_restricted_time,
            'total_revenue_restricted_permanent': total_revenue_restricted_permanent,
            'total_expenses': total_expenses,
            'net_income_loss': net_income_loss
        }

    def get_changes_in_net_assets_report(self):
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)

        # Initial Net Assets (from the beginning balance entry)
        # We need to query the initial balance entry specifically
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT a.code, a.name, jd.debit, jd.credit
            FROM journal_details jd
            JOIN journal_entries je ON jd.journal_id = je.id
            JOIN accounts a ON jd.account_id = a.id
            WHERE je.reference_no = 'SA-2025' AND a.type = 'Asset Net'
        """)
        initial_net_assets_raw = cursor.fetchall()

        initial_unrestricted = 0
        initial_restricted_time = 0
        initial_restricted_permanent = 0

        for code, name, debit, credit in initial_net_assets_raw:
            if code == '3000': # Aset Neto Tidak Terbatas
                initial_unrestricted += credit - debit
            elif code == '3010': # Aset Neto Terbatas Waktu
                initial_restricted_time += credit - debit
            elif code == '3020': # Aset Neto Terbatas Permanen
                initial_restricted_permanent += credit - debit
        
        # Changes from Comprehensive Income
        income_data = self.get_comprehensive_income()
        total_revenue_unrestricted = income_data['total_revenue_unrestricted']
        total_revenue_restricted_time = income_data['total_revenue_restricted_time']
        total_revenue_restricted_permanent = income_data['total_revenue_restricted_permanent']
        total_expenses = income_data['total_expenses']

        # Release from Restriction
        release_from_restriction_amount = 0
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT jd.debit FROM journal_details jd
            JOIN journal_entries je ON jd.journal_id = je.id
            JOIN accounts a ON jd.account_id = a.id
            WHERE je.reference_no = 'RLS-ANTW-001' AND a.code = '3010'
        """)
        result = cursor.fetchone()
        if result:
            release_from_restriction_amount = result[0]

        # Net Assets Changes
        change_unrestricted = total_revenue_unrestricted - total_expenses + release_from_restriction_amount
        change_restricted_time = total_revenue_restricted_time - release_from_restriction_amount
        change_restricted_permanent = total_revenue_restricted_permanent

        # Ending Net Assets
        ending_unrestricted = initial_unrestricted + change_unrestricted
        ending_restricted_time = initial_restricted_time + change_restricted_time
        ending_restricted_permanent = initial_restricted_permanent + change_restricted_permanent

        total_initial_net_assets = initial_unrestricted + initial_restricted_time + initial_restricted_permanent
        total_change_net_assets = change_unrestricted + change_restricted_time + change_restricted_permanent
        total_ending_net_assets = ending_unrestricted + ending_restricted_time + ending_restricted_permanent

        return {
            'initial_unrestricted': initial_unrestricted,
            'initial_restricted_time': initial_restricted_time,
            'initial_restricted_permanent': initial_restricted_permanent,
            'total_initial_net_assets': total_initial_net_assets,
            'change_unrestricted': change_unrestricted,
            'change_restricted_time': change_restricted_time,
            'change_restricted_permanent': change_restricted_permanent,
            'total_change_net_assets': total_change_net_assets,
            'ending_unrestricted': ending_unrestricted,
            'ending_restricted_time': ending_restricted_time,
            'ending_restricted_permanent': ending_restricted_permanent,
            'total_ending_net_assets': total_ending_net_assets
        }

    def get_cash_flow_report(self):
        cash_account_ids = self.db.get_cash_account_ids()
        if not cash_account_ids:
            return {"error": "Akun 'Kas' tidak ditemukan."}

        conn = self.db.conn
        all_journal_details_df = pd.read_sql_query("""
            SELECT 
                jd.journal_id, jd.account_id, a.name as account_name, a.type as account_type,
                jd.debit, jd.credit, jd.cash_flow_activity, je.date, je.description as journal_description
            FROM journal_details jd
            JOIN accounts a ON jd.account_id = a.id
            JOIN journal_entries je ON jd.journal_id = je.id
            ORDER BY je.date ASC, je.id ASC
        """, conn)

        cash_transactions = all_journal_details_df[all_journal_details_df['account_id'].isin(cash_account_ids)]
        activity_mapping = self.db.get_cash_flow_activity_mapping()

        cash_flow_data = {
            "ARUS KAS DARI AKTIVITAS OPERASI": {},
            "ARUS KAS DARI AKTIVITAS INVESTASI": {},
            "ARUS KAS DARI AKTIVITAS PENDANAAN": {}
        }

        for index, cash_row in cash_transactions.iterrows():
            activity_description = cash_row['cash_flow_activity']
            
            if activity_description and activity_description in activity_mapping:
                main_activity = activity_mapping[activity_description]
                amount = 0
                if cash_row['debit'] > 0:
                    amount = cash_row['debit']
                elif cash_row['credit'] > 0:
                    amount = -cash_row['credit']

                if activity_description not in cash_flow_data[main_activity]:
                    cash_flow_data[main_activity][activity_description] = 0
                cash_flow_data[main_activity][activity_description] += amount
        
        total_operating_cash_flow = sum(cash_flow_data["ARUS KAS DARI AKTIVITAS OPERASI"].values()) if cash_flow_data["ARUS KAS DARI AKTIVITAS OPERASI"] else 0
        total_investing_cash_flow = sum(cash_flow_data["ARUS KAS DARI AKTIVITAS INVESTASI"].values()) if cash_flow_data["ARUS KAS DARI AKTIVITAS INVESTASI"] else 0
        total_financing_cash_flow = sum(cash_flow_data["ARUS KAS DARI AKTIVITAS PENDANAAN"].values()) if cash_flow_data["ARUS KAS DARI AKTIVITAS PENDANAAN"] else 0

        net_increase_decrease_in_cash = total_operating_cash_flow + total_investing_cash_flow + total_financing_cash_flow

        # Get initial cash balance from SA-2025
        initial_cash_balance = 0
        cursor = self.db.conn.cursor()
        placeholders = ','.join('?' for _ in cash_account_ids)
        cursor.execute(f"""
            SELECT SUM(jd.debit), SUM(jd.credit) FROM journal_details jd
            JOIN journal_entries je ON jd.journal_id = je.id
            WHERE je.reference_no = 'SA-2025' AND jd.account_id IN ({placeholders})
        """, cash_account_ids)
        initial_cash_raw = cursor.fetchone()
        if initial_cash_raw and initial_cash_raw[0] is not None:
            initial_cash_balance = initial_cash_raw[0] - initial_cash_raw[1] # Debit - Credit for cash

        ending_cash_balance = initial_cash_balance + net_increase_decrease_in_cash

        return {
            'operating_activities': cash_flow_data["ARUS KAS DARI AKTIVITAS OPERASI"],
            'total_operating_cash_flow': total_operating_cash_flow,
            'investing_activities': cash_flow_data["ARUS KAS DARI AKTIVITAS INVESTASI"],
            'total_investing_cash_flow': total_investing_cash_flow,
            'financing_activities': cash_flow_data["ARUS KAS DARI AKTIVITAS PENDANAAN"],
            'total_financing_cash_flow': total_financing_cash_flow,
            'net_increase_decrease_in_cash': net_increase_decrease_in_cash,
            'initial_cash_balance': initial_cash_balance,
            'ending_cash_balance': ending_cash_balance
        }

    def get_trial_balance_report(self):
        df = self.db.get_trial_balance()
        df['total_debit'] = df['total_debit'].fillna(0)
        df['total_credit'] = df['total_credit'].fillna(0)
        
        total_debit_sum = df['total_debit'].sum()
        total_credit_sum = df['total_credit'].sum()
        
        report_data = df[['code', 'name', 'total_debit', 'total_credit']].to_dict('records')
        report_data.append({
            'code': '', 
            'name': 'TOTAL',
            'total_debit': total_debit_sum, 
            'total_credit': total_credit_sum
        })
        return report_data

# --- Case Study Data ---
COA_DATA = [
    {'code': '1000', 'name': 'Kas', 'type': 'Asset', 'category': 'Lancar'},
    {'code': '1010', 'name': 'Bank - Mandiri', 'type': 'Asset', 'category': 'Lancar'},
    {'code': '1020', 'name': 'Piutang Sumbangan', 'type': 'Asset', 'category': 'Lancar'},
    {'code': '1030', 'name': 'Persediaan Perlengkapan Kantor', 'type': 'Asset', 'category': 'Lancar'},
    {'code': '1100', 'name': 'Tanah', 'type': 'Asset', 'category': 'Tidak Lancar'},
    {'code': '1110', 'name': 'Bangunan', 'type': 'Asset', 'category': 'Tidak Lancar'},
    {'code': '1120', 'name': 'Akumulasi Penyusutan Bangunan', 'type': 'Asset', 'category': 'Tidak Lancar (Kontra)'},
    {'code': '1130', 'name': 'Peralatan Kantor', 'type': 'Asset', 'category': 'Tidak Lancar'},
    {'code': '1140', 'name': 'Akumulasi Penyusutan Peralatan', 'type': 'Asset', 'category': 'Tidak Lancar (Kontra)'},
    {'code': '2000', 'name': 'Utang Usaha', 'type': 'Liability', 'category': 'Lancar'},
    {'code': '2010', 'name': 'Utang Gaji', 'type': 'Liability', 'category': 'Lancar'},
    {'code': '2020', 'name': 'Pendapatan Diterima di Muka', 'type': 'Liability', 'category': 'Lancar'},
    {'code': '2100', 'name': 'Utang Bank Jangka Panjang', 'type': 'Liability', 'category': 'Tidak Lancar'},
    {'code': '3000', 'name': 'Aset Neto Tidak Terbatas', 'type': 'Asset Net', 'category': 'Tidak Terbatas'},
    {'code': '3010', 'name': 'Aset Neto Terbatas Waktu', 'type': 'Asset Net', 'category': 'Terbatas Waktu'},
    {'code': '3020', 'name': 'Aset Neto Terbatas Permanen', 'type': 'Asset Net', 'category': 'Terbatas Permanen'},
    {'code': '4000', 'name': 'Pendapatan Sumbangan Tidak Terbatas', 'type': 'Revenue', 'category': 'Tidak Terbatas'},
    {'code': '4010', 'name': 'Pendapatan Sumbangan Terbatas Waktu', 'type': 'Revenue', 'category': 'Terbatas Waktu'},
    {'code': '4020', 'name': 'Pendapatan Jasa Program', 'type': 'Revenue', 'category': 'Tidak Terbatas'},
    {'code': '5000', 'name': 'Beban Gaji & Tunjangan', 'type': 'Expense', 'category': 'Program'},
    {'code': '5010', 'name': 'Beban Program Pendidikan', 'type': 'Expense', 'category': 'Program'},
    {'code': '5020', 'name': 'Beban Program Kesehatan', 'type': 'Expense', 'category': 'Program'},
    {'code': '6000', 'name': 'Beban Administrasi & Umum', 'type': 'Expense', 'category': 'Administrasi & Umum'},
    {'code': '6010', 'name': 'Beban Sewa Kantor', 'type': 'Expense', 'category': 'Administrasi & Umum'},
    {'code': '6020', 'name': 'Beban Perlengkapan Kantor', 'type': 'Expense', 'category': 'Administrasi & Umum'},
    {'code': '6030', 'name': 'Beban Utilitas', 'type': 'Expense', 'category': 'Administrasi & Umum'},
    {'code': '6040', 'name': 'Beban Penyusutan Bangunan', 'type': 'Expense', 'category': 'Administrasi & Umum'},
    {'code': '6050', 'name': 'Beban Penyusutan Peralatan', 'type': 'Expense', 'category': 'Administrasi & Umum'},
    {'code': '7000', 'name': 'Beban Bunga Bank', 'type': 'Expense', 'category': 'Lain-lain'},
]

CASH_FLOW_CATEGORIES_DATA = [
    ("Penerimaan dari Sumbangan/Donasi", "ARUS KAS DARI AKTIVITAS OPERASI"),
    ("Penerimaan dari Jasa Layanan/Unit Bisnis", "ARUS KAS DARI AKTIVITAS OPERASI"),
    ("Penerimaan Hibah Pemerintah", "ARUS KAS DARI AKTIVITAS OPERASI"),
    ("Pembayaran Kas untuk Gaji dan Karyawan", "ARUS KAS DARI AKTIVITAS OPERASI"),
    ("Pembayaran Kas untuk Beban Program", "ARUS KAS DARI AKTIVITAS OPERASI"),
    ("Pembayaran Kas untuk Beban Administrasi", "ARUS KAS DARI AKTIVITAS OPERASI"),
    ("Pembayaran Kas untuk Sewa Gedung", "ARUS KAS DARI AKTIVITAS OPERASI"),
    ("Penjualan Aset Tetap (Kendaraan lama)", "ARUS KAS DARI AKTIVITAS INVESTASI"),
    ("Pembelian Peralatan Kantor Baru", "ARUS KAS DARI AKTIVITAS INVESTASI"),
    ("Perolehan Investasi Jangka Panjang", "ARUS KAS DARI AKTIVITAS INVESTASI"),
    ("Penerimaan dari Pinjaman Bank", "ARUS KAS DARI AKTIVITAS PENDANAAN"),
    ("Pembayaran Pokok Pinjaman", "ARUS KAS DARI AKTIVITAS PENDANAAN"),
    ("Penerimaan Sumbangan yang Dibatasi untuk Bangunan", "ARUS KAS DARI AKTIVITAS PENDANAAN")
]

INITIAL_BALANCES = [
    {'account_code': '1000', 'debit': 5000000, 'credit': 0},
    {'account_code': '1010', 'debit': 25000000, 'credit': 0},
    {'account_code': '1020', 'debit': 2000000, 'credit': 0},
    {'account_code': '1030', 'debit': 1000000, 'credit': 0},
    {'account_code': '1110', 'debit': 100000000, 'credit': 0},
    {'account_code': '1120', 'debit': 0, 'credit': 10000000},
    {'account_code': '1130', 'debit': 15000000, 'credit': 0},
    {'account_code': '1140', 'debit': 0, 'credit': 3000000},
    {'account_code': '2000', 'debit': 0, 'credit': 1500000},
    {'account_code': '2100', 'debit': 0, 'credit': 50000000},
    {'account_code': '3000', 'debit': 0, 'credit': 73500000},
    {'account_code': '3010', 'debit': 0, 'credit': 10000000},
]

TRANSACTIONS = [
    # Januari 2025
    {
        'date': '2025-01-05', 'description': 'Penerimaan sumbangan tunai dari donatur umum', 'ref_no': 'SUMB-001',
        'details': [
            {'account_code': '1000', 'debit': 10000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4000', 'debit': 0, 'credit': 10000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-01-25', 'description': 'Pembayaran gaji karyawan bulan Januari', 'ref_no': 'GJI-001',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    {
        'date': '2025-01-28', 'description': 'Pembelian perlengkapan kantor dari Toko ABC secara kredit', 'ref_no': 'BELI-001',
        'details': [
            {'account_code': '1030', 'debit': 1500000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '2000', 'debit': 0, 'credit': 1500000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-01-30', 'description': 'Penerimaan sumbangan terbatas waktu untuk program pendidikan', 'ref_no': 'SUMB-002',
        'details': [
            {'account_code': '1010', 'debit': 5000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4010', 'debit': 0, 'credit': 5000000, 'cash_flow_activity': None},
        ]
    },
    # Februari 2025
    {
        'date': '2025-02-10', 'description': 'Pembayaran utang kepada Toko ABC untuk pembelian perlengkapan', 'ref_no': 'BYR-UTG-001',
        'details': [
            {'account_code': '2000', 'debit': 1500000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 1500000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Administrasi'},
        ]
    },
    {
        'date': '2025-02-15', 'description': 'Penerimaan sumbangan tunai untuk pembelian tanah', 'ref_no': 'SUMB-003',
        'details': [
            {'account_code': '1010', 'debit': 20000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan Sumbangan yang Dibatasi untuk Bangunan'},
            {'account_code': '3020', 'debit': 0, 'credit': 20000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-02-20', 'description': 'Pembelian tanah menggunakan dana sumbangan terbatas permanen', 'ref_no': 'BELI-TNH-001',
        'details': [
            {'account_code': '1100', 'debit': 20000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 20000000, 'cash_flow_activity': 'Pembelian Peralatan Kantor Baru'},
        ]
    },
    {
        'date': '2025-02-28', 'description': 'Pembayaran sewa kantor bulan Februari', 'ref_no': 'SEWA-001',
        'details': [
            {'account_code': '6010', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': 'Pembayaran Kas untuk Sewa Gedung'},
        ]
    },
    # Maret 2025
    {
        'date': '2025-03-05', 'description': 'Penerimaan kas dari piutang sumbangan yang sebelumnya diakui', 'ref_no': 'PIUT-001',
        'details': [
            {'account_code': '1010', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '1020', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-03-10', 'description': 'Pembelian perlengkapan kantor secara tunai', 'ref_no': 'BELI-PLKP-002',
        'details': [
            {'account_code': '1030', 'debit': 750000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1000', 'debit': 0, 'credit': 750000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Administrasi'},
        ]
    },
    {
        'date': '2025-03-20', 'description': 'Pembayaran biaya operasional program pendidikan', 'ref_no': 'PROG-PEND-001',
        'details': [
            {'account_code': '5010', 'debit': 3000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 3000000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Program'},
        ]
    },
    {
        'date': '2025-03-25', 'description': 'Pengakuan pendapatan dari jasa program yang telah diselesaikan', 'ref_no': 'JASA-PROG-001',
        'details': [
            {'account_code': '1010', 'debit': 4000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Jasa Layanan/Unit Bisnis'},
            {'account_code': '4020', 'debit': 0, 'credit': 4000000, 'cash_flow_activity': None},
        ]
    },
    # April 2025
    {
        'date': '2025-04-05', 'description': 'Pembayaran tagihan listrik dan air bulan Maret', 'ref_no': 'UTIL-001',
        'details': [
            {'account_code': '6030', 'debit': 800000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 800000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Administrasi'},
        ]
    },
    {
        'date': '2025-04-15', 'description': 'Penerimaan sumbangan tunai dari donatur individu', 'ref_no': 'SUMB-004',
        'details': [
            {'account_code': '1000', 'debit': 3000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4000', 'debit': 0, 'credit': 3000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-04-20', 'description': 'Pembayaran biaya operasional program kesehatan', 'ref_no': 'PROG-KES-001',
        'details': [
            {'account_code': '5020', 'debit': 2500000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 2500000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Program'},
        ]
    },
    {
        'date': '2025-04-25', 'description': 'Pembayaran gaji karyawan bulan April', 'ref_no': 'GJI-002',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    # Mei 2025
    {
        'date': '2025-05-10', 'description': 'Penerimaan pendapatan dari jasa program yang telah diberikan', 'ref_no': 'JASA-PROG-002',
        'details': [
            {'account_code': '1010', 'debit': 3500000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Jasa Layanan/Unit Bisnis'},
            {'account_code': '4020', 'debit': 0, 'credit': 3500000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-05-18', 'description': 'Pembayaran berbagai beban administrasi dan umum (misal: ATK, kebersihan)', 'ref_no': 'ADM-001',
        'details': [
            {'account_code': '6000', 'debit': 1200000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1000', 'debit': 0, 'credit': 1200000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Administrasi'},
        ]
    },
    {
        'date': '2025-05-25', 'description': 'Pembayaran gaji karyawan bulan Mei', 'ref_no': 'GJI-003',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    {
        'date': '2025-05-30', 'description': 'Penerimaan sumbangan tunai akhir tahun dari donatur', 'ref_no': 'SUMB-005',
        'details': [
            {'account_code': '1000', 'debit': 8000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4000', 'debit': 0, 'credit': 8000000, 'cash_flow_activity': None},
        ]
    },
    # Juni 2025
    {
        'date': '2025-06-01', 'description': 'Pembayaran sewa kantor bulan Juni', 'ref_no': 'SEWA-002',
        'details': [
            {'account_code': '6010', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': 'Pembayaran Kas untuk Sewa Gedung'},
        ]
    },
    {
        'date': '2025-06-10', 'description': 'Penerimaan sumbangan tunai terbatas waktu untuk program kesehatan', 'ref_no': 'SUMB-006',
        'details': [
            {'account_code': '1010', 'debit': 6000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4010', 'debit': 0, 'credit': 6000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-06-20', 'description': 'Pembayaran biaya operasional program kesehatan', 'ref_no': 'PROG-KES-002',
        'details': [
            {'account_code': '5020', 'debit': 4000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 4000000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Program'},
        ]
    },
    {
        'date': '2025-06-25', 'description': 'Pembayaran gaji karyawan bulan Juni', 'ref_no': 'GJI-004',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    # Juli 2025
    {
        'date': '2025-07-05', 'description': 'Penerimaan sumbangan tunai dari donatur perusahaan', 'ref_no': 'SUMB-007',
        'details': [
            {'account_code': '1010', 'debit': 15000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4000', 'debit': 0, 'credit': 15000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-07-15', 'description': 'Pembayaran biaya operasional kantor (misal: internet, telepon)', 'ref_no': 'ADM-002',
        'details': [
            {'account_code': '6000', 'debit': 900000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 900000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Administrasi'},
        ]
    },
    {
        'date': '2025-07-25', 'description': 'Pembayaran gaji karyawan bulan Juli', 'ref_no': 'GJI-005',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    {
        'date': '2025-07-30', 'description': 'Penerimaan pendapatan dari jasa program (pelatihan)', 'ref_no': 'JASA-PROG-003',
        'details': [
            {'account_code': '1010', 'debit': 6000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Jasa Layanan/Unit Bisnis'},
            {'account_code': '4020', 'debit': 0, 'credit': 6000000, 'cash_flow_activity': None},
        ]
    },
    # Agustus 2025
    {
        'date': '2025-08-01', 'description': 'Pembayaran sewa kantor bulan Agustus', 'ref_no': 'SEWA-003',
        'details': [
            {'account_code': '6010', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': 'Pembayaran Kas untuk Sewa Gedung'},
        ]
    },
    {
        'date': '2025-08-10', 'description': 'Penerimaan sumbangan tunai dari donatur perorangan', 'ref_no': 'SUMB-008',
        'details': [
            {'account_code': '1000', 'debit': 4000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4000', 'debit': 0, 'credit': 4000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-08-20', 'description': 'Pembayaran biaya operasional program pendidikan', 'ref_no': 'PROG-PEND-002',
        'details': [
            {'account_code': '5010', 'debit': 3500000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 3500000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Program'},
        ]
    },
    {
        'date': '2025-08-25', 'description': 'Pembayaran gaji karyawan bulan Agustus', 'ref_no': 'GJI-006',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    # September 2025
    {
        'date': '2025-09-05', 'description': 'Pembayaran tagihan listrik dan air bulan Agustus', 'ref_no': 'UTIL-002',
        'details': [
            {'account_code': '6030', 'debit': 850000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 850000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Administrasi'},
        ]
    },
    {
        'date': '2025-09-15', 'description': 'Penerimaan sumbangan tunai terbatas waktu untuk program pengembangan', 'ref_no': 'SUMB-009',
        'details': [
            {'account_code': '1010', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-09-20', 'description': 'Pembayaran biaya operasional program pendidikan', 'ref_no': 'PROG-PEND-003',
        'details': [
            {'account_code': '5010', 'debit': 4000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 4000000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Program'},
        ]
    },
    {
        'date': '2025-09-25', 'description': 'Pembayaran gaji karyawan bulan September', 'ref_no': 'GJI-007',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    # Oktober 2025
    {
        'date': '2025-10-01', 'description': 'Pembayaran sewa kantor bulan Oktober', 'ref_no': 'SEWA-004',
        'details': [
            {'account_code': '6010', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': 'Pembayaran Kas untuk Sewa Gedung'},
        ]
    },
    {
        'date': '2025-10-10', 'description': 'Penerimaan sumbangan tunai dari donatur perorangan', 'ref_no': 'SUMB-010',
        'details': [
            {'account_code': '1000', 'debit': 5000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4000', 'debit': 0, 'credit': 5000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-10-20', 'description': 'Pembayaran biaya operasional program kesehatan', 'ref_no': 'PROG-KES-003',
        'details': [
            {'account_code': '5020', 'debit': 3000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 3000000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Program'},
        ]
    },
    {
        'date': '2025-10-25', 'description': 'Pembayaran gaji karyawan bulan Oktober', 'ref_no': 'GJI-008',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    # November 2025
    {
        'date': '2025-11-05', 'description': 'Penerimaan pendapatan dari jasa program (konsultasi)', 'ref_no': 'JASA-PROG-004',
        'details': [
            {'account_code': '1010', 'debit': 4500000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Jasa Layanan/Unit Bisnis'},
            {'account_code': '4020', 'debit': 0, 'credit': 4500000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-11-15', 'description': 'Pembayaran biaya operasional kantor (misal: perbaikan kecil)', 'ref_no': 'ADM-003',
        'details': [
            {'account_code': '6000', 'debit': 700000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1000', 'debit': 0, 'credit': 700000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Administrasi'},
        ]
    },
    {
        'date': '2025-11-25', 'description': 'Pembayaran gaji karyawan bulan November', 'ref_no': 'GJI-009',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    {
        'date': '2025-11-30', 'description': 'Penerimaan sumbangan tunai akhir tahun dari donatur', 'ref_no': 'SUMB-011',
        'details': [
            {'account_code': '1010', 'debit': 10000000, 'credit': 0, 'cash_flow_activity': 'Penerimaan dari Sumbangan/Donasi'},
            {'account_code': '4000', 'debit': 0, 'credit': 10000000, 'cash_flow_activity': None},
        ]
    },
    # Desember 2025
    {
        'date': '2025-12-01', 'description': 'Pembayaran sewa kantor bulan Desember', 'ref_no': 'SEWA-005',
        'details': [
            {'account_code': '6010', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': 'Pembayaran Kas untuk Sewa Gedung'},
        ]
    },
    {
        'date': '2025-12-15', 'description': 'Pembayaran biaya operasional program pendidikan akhir tahun', 'ref_no': 'PROG-PEND-004',
        'details': [
            {'account_code': '5010', 'debit': 5000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 5000000, 'cash_flow_activity': 'Pembayaran Kas untuk Beban Program'},
        ]
    },
    {
        'date': '2025-12-25', 'description': 'Pembayaran gaji karyawan bulan Desember', 'ref_no': 'GJI-010',
        'details': [
            {'account_code': '5000', 'debit': 7000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1010', 'debit': 0, 'credit': 7000000, 'cash_flow_activity': 'Pembayaran Kas untuk Gaji dan Karyawan'},
        ]
    },
    # Penyesuaian Akhir Tahun
    {
        'date': '2025-12-31', 'description': 'Penyesuaian penggunaan perlengkapan kantor selama tahun 2025', 'ref_no': 'ADJ-PLKP-001',
        'details': [
            {'account_code': '6020', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1030', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-12-31', 'description': 'Penyesuaian beban penyusutan bangunan tahun 2025', 'ref_no': 'ADJ-SUSUT-BGN-001',
        'details': [
            {'account_code': '6040', 'debit': 5000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1120', 'debit': 0, 'credit': 5000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-12-31', 'description': 'Penyesuaian beban penyusutan peralatan tahun 2025', 'ref_no': 'ADJ-SUSUT-PRL-001',
        'details': [
            {'account_code': '6050', 'debit': 2000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '1140', 'debit': 0, 'credit': 2000000, 'cash_flow_activity': None},
        ]
    },
    {
        'date': '2025-12-31', 'description': 'Pelepasan pembatasan aset neto terbatas waktu seiring dengan penggunaan dana untuk program pendidikan dan kesehatan', 'ref_no': 'RLS-ANTW-001',
        'details': [
            {'account_code': '3010', 'debit': 18000000, 'credit': 0, 'cash_flow_activity': None},
            {'account_code': '3000', 'debit': 0, 'credit': 18000000, 'cash_flow_activity': None},
        ]
    },
]

def generate_expected_reports():
    db_manager = MockDatabaseManager()
    report_generator = MockReportGenerator(db_manager)

    # 1. Add COA
    print("Adding COA...")
    db_manager.bulk_add_accounts(COA_DATA)
    
    # 2. Add Cash Flow Categories
    print("Adding Cash Flow Categories...")
    db_manager.bulk_add_cash_flow_categories(CASH_FLOW_CATEGORIES_DATA)

    # 3. Add Initial Balances
    print("Adding Initial Balances (SA-2025)...")
    initial_balance_details = []
    for item in INITIAL_BALANCES:
        account_id = db_manager.get_account_id_by_code(item['account_code'])
        if account_id:
            initial_balance_details.append({
                'account_id': account_id,
                'debit': item['debit'],
                'credit': item['credit'],
                'cash_flow_activity': None # Initial balances usually don't have direct cash flow activity
            })
    db_manager.add_journal_entry('2025-01-01', 'Saldo Awal Tahun Buku 2025', 'SA-2025', initial_balance_details)

    # 4. Add all Transactions
    print("Adding Monthly Transactions...")
    for transaction in TRANSACTIONS:
        details_with_ids = []
        for item in transaction['details']:
            account_id = db_manager.get_account_id_by_code(item['account_code'])
            if account_id:
                details_with_ids.append({
                    'account_id': account_id,
                    'debit': item['debit'],
                    'credit': item['credit'],
                    'cash_flow_activity': item['cash_flow_activity']
                })
        db_manager.add_journal_entry(transaction['date'], transaction['description'], transaction['ref_no'], details_with_ids)

    print("\n--- Expected Report Summaries (as of 2025-12-31) ---")

    # Laporan Posisi Keuangan
    fp_summary = report_generator.get_isak35_financial_position()
    print("\nLaporan Posisi Keuangan (Ringkasan):")
    print(f"  Total Aset: Rp {fp_summary['total_assets']:,.0f}")
    print(f"  Total Liabilitas: Rp {fp_summary['total_liabilities']:,.0f}")
    print(f"  Aset Neto Tidak Terbatas: Rp {fp_summary['net_assets_unrestricted']:,.0f}")
    print(f"  Aset Neto Terbatas Waktu: Rp {fp_summary['net_assets_restricted_time']:,.0f}")
    print(f"  Aset Neto Terbatas Permanen: Rp {fp_summary['net_assets_restricted_permanent']:,.0f}")
    print(f"  Total Aset Neto: Rp {fp_summary['total_net_assets']:,.0f}")
    print(f"  Total Liabilitas dan Aset Neto: Rp {fp_summary['total_liabilities'] + fp_summary['total_net_assets']:,.0f}")
    # Add a check for balance
    if abs(fp_summary['total_assets'] - (fp_summary['total_liabilities'] + fp_summary['total_net_assets'])) < 0.01:
        print("  (Persamaan Akuntansi Seimbang)")
    else:
        print("  (PERINGATAN: Persamaan Akuntansi TIDAK Seimbang!)")


    # Laporan Penghasilan Komprehensif
    ci_summary = report_generator.get_comprehensive_income()
    print("\nLaporan Penghasilan Komprehensif (Ringkasan):")
    print(f"  Total Pendapatan Tidak Terbatas: Rp {ci_summary['total_revenue_unrestricted']:,.0f}")
    print(f"  Total Pendapatan Terbatas Waktu: Rp {ci_summary['total_revenue_restricted_time']:,.0f}")
    print(f"  Total Pendapatan Terbatas Permanen: Rp {ci_summary['total_revenue_restricted_permanent']:,.0f}")
    print(f"  Total Beban: Rp {ci_summary['total_expenses']:,.0f}")
    print(f"  Penghasilan Komprehensif (Surplus/Defisit): Rp {ci_summary['net_income_loss']:,.0f}")

    # Laporan Perubahan Aset Neto
    cna_summary = report_generator.get_changes_in_net_assets_report()
    print("\nLaporan Perubahan Aset Neto (Ringkasan):")
    print(f"  Aset Neto Tidak Terbatas Awal: Rp {cna_summary['initial_unrestricted']:,.0f}")
    print(f"  Aset Neto Terbatas Waktu Awal: Rp {cna_summary['initial_restricted_time']:,.0f}")
    print(f"  Aset Neto Terbatas Permanen Awal: Rp {cna_summary['initial_restricted_permanent']:,.0f}")
    print(f"  Total Aset Neto Awal: Rp {cna_summary['total_initial_net_assets']:,.0f}")
    print(f"  Perubahan Aset Neto Tidak Terbatas: Rp {cna_summary['change_unrestricted']:,.0f}")
    print(f"  Perubahan Aset Neto Terbatas Waktu: Rp {cna_summary['change_restricted_time']:,.0f}")
    print(f"  Perubahan Aset Neto Terbatas Permanen: Rp {cna_summary['change_restricted_permanent']:,.0f}")
    print(f"  Total Perubahan Aset Neto: Rp {cna_summary['total_change_net_assets']:,.0f}")
    print(f"  Aset Neto Tidak Terbatas Akhir: Rp {cna_summary['ending_unrestricted']:,.0f}")
    print(f"  Aset Neto Terbatas Waktu Akhir: Rp {cna_summary['ending_restricted_time']:,.0f}")
    print(f"  Aset Neto Terbatas Permanen Akhir: Rp {cna_summary['ending_restricted_permanent']:,.0f}")
    print(f"  Total Aset Neto Akhir: Rp {cna_summary['total_ending_net_assets']:,.0f}")

    # Laporan Arus Kas
    cf_summary = report_generator.get_cash_flow_report()
    print("\nLaporan Arus Kas (Ringkasan):")
    if "error" in cf_summary:
        print(f"  Error: {cf_summary['error']}")
    else:
        print(f"  Arus Kas Bersih dari Aktivitas Operasi: Rp {cf_summary['total_operating_cash_flow']:,.0f}")
        print(f"  Arus Kas Bersih dari Aktivitas Investasi: Rp {cf_summary['total_investing_cash_flow']:,.0f}")
        print(f"  Arus Kas Bersih dari Aktivitas Pendanaan: Rp {cf_summary['total_financing_cash_flow']:,.0f}")
        print(f"  Kenaikan (Penurunan) Bersih Kas: Rp {cf_summary['net_increase_decrease_in_cash']:,.0f}")
        print(f"  Kas dan Setara Kas pada Awal Tahun: Rp {cf_summary['initial_cash_balance']:,.0f}")
        print(f"  Kas dan Setara Kas pada Akhir Tahun: Rp {cf_summary['ending_cash_balance']:,.0f}")
        # Add a check for balance
        if abs(cf_summary['initial_cash_balance'] + cf_summary['net_increase_decrease_in_cash'] - cf_summary['ending_cash_balance']) < 0.01:
            print("  (Arus Kas Seimbang)")
        else:
            print("  (PERINGATAN: Arus Kas TIDAK Seimbang!)")

    # Neraca Saldo
    tb_report = report_generator.get_trial_balance_report()
    print("\nNeraca Saldo (Ringkasan Total):")
    total_debit_tb = tb_report[-1]['total_debit']
    total_credit_tb = tb_report[-1]['total_credit']
    print(f"  Total Debit: Rp {total_debit_tb:,.0f}")
    print(f"  Total Kredit: Rp {total_credit_tb:,.0f}")
    if abs(total_debit_tb - total_credit_tb) < 0.01:
        print("  (Neraca Saldo Seimbang)")
    else:
        print("  (PERINGATAN: Neraca Saldo TIDAK Seimbang!)")


if __name__ == "__main__":
    generate_expected_reports()
