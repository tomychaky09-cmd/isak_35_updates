import sqlite3
import pandas as pd
import os
import sys
import json

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

try:
    import pyodbc
    SQLSERVER_AVAILABLE = True
except ImportError:
    SQLSERVER_AVAILABLE = False

class DatabaseManager:
    CONFIG_FILE = "user_settings.json"

    def __init__(self, db_path='database/foundation_finance.db'):
        # Load Config for Database Type
        self.config = self.load_config()
        self.db_type = self.config.get("db_type", "sqlite") # sqlite, mysql, or sqlserver
        self.mysql_config = self.config.get("mysql_config", {})
        self.sqlserver_config = self.config.get("sqlserver_config", {})

        if hasattr(sys, '_MEIPASS'):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.db_path = os.path.join(base_dir, db_path)
        
        if self.db_type == "sqlite":
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                try: os.makedirs(db_dir)
                except: self.db_path = os.path.basename(db_path)
            print(f"[*] Menggunakan SQLite: {self.db_path}")
        else:
            print(f"[*] Menggunakan MySQL: {self.mysql_config.get('host')}")
            
        self._update_schema()

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except: pass
        return {}

    def get_connection(self):
        if self.db_type == "mysql" and MYSQL_AVAILABLE:
            try:
                conn = mysql.connector.connect(
                    host=self.mysql_config.get("host"),
                    user=self.mysql_config.get("user"),
                    password=self.mysql_config.get("password"),
                    database=self.mysql_config.get("database")
                )
                return conn
            except Exception as e:
                print(f"Gagal koneksi MySQL, fallback ke SQLite: {e}")
                self.db_type = "sqlite"
        elif self.db_type == "sqlserver" and SQLSERVER_AVAILABLE:
            try:
                # Driver example: 'ODBC Driver 17 for SQL Server'
                driver = self.sqlserver_config.get("driver", "ODBC Driver 17 for SQL Server")
                server = self.sqlserver_config.get("host")
                database = self.sqlserver_config.get("database")
                uid = self.sqlserver_config.get("user")
                pwd = self.sqlserver_config.get("password")
                
                conn_str = f'DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={uid};PWD={pwd}'
                conn = pyodbc.connect(conn_str)
                return conn
            except Exception as e:
                print(f"Gagal koneksi SQL Server, fallback ke SQLite: {e}")
                self.db_type = "sqlite"
        
        return sqlite3.connect(self.db_path)

    def _execute_query(self, query, params=(), fetch=False):
        # MySQL uses %s as placeholder, SQLite and SQL Server use ?
        if self.db_type == "mysql":
            query = query.replace("?", "%s")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = None
        if fetch:
            result = cursor.fetchall()
        conn.commit()
        conn.close()
        return result

    def _update_schema(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Dialect differences: 
        # SQLite: INTEGER PRIMARY KEY AUTOINCREMENT
        # MySQL: INTEGER PRIMARY KEY AUTO_INCREMENT
        # SQL Server: INTEGER PRIMARY KEY IDENTITY(1,1)
        if self.db_type == "mysql":
            pk_type = "INTEGER PRIMARY KEY AUTO_INCREMENT"
            real_type = "DOUBLE"
        elif self.db_type == "sqlserver":
            pk_type = "INTEGER PRIMARY KEY IDENTITY(1,1)"
            real_type = "FLOAT"
        else: # sqlite
            pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"
            real_type = "REAL"

        tables = {
            "accounts": f"""
                CREATE TABLE IF NOT EXISTS accounts (
                    id {pk_type},
                    code VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    type VARCHAR(50) NOT NULL,
                    category VARCHAR(100) NOT NULL
                )
            """,
            "journal_entries": f"""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id {pk_type},
                    date VARCHAR(20) NOT NULL,
                    description TEXT NOT NULL,
                    reference_no VARCHAR(100)
                )
            """,
            "journal_details": f"""
                CREATE TABLE IF NOT EXISTS journal_details (
                    id {pk_type},
                    journal_id INTEGER NOT NULL,
                    account_id INTEGER NOT NULL,
                    debit {real_type} DEFAULT 0,
                    credit {real_type} DEFAULT 0,
                    cash_flow_activity TEXT
                )
            """,
            "cash_flow_categories": f"""
                CREATE TABLE IF NOT EXISTS cash_flow_categories (
                    id {pk_type},
                    name VARCHAR(255) NOT NULL UNIQUE,
                    main_category VARCHAR(255) NOT NULL
                )
            """,
            "assets_inventory": f"""
                CREATE TABLE IF NOT EXISTS assets_inventory (
                    id {pk_type},
                    date VARCHAR(20) NOT NULL,
                    code VARCHAR(50) NOT NULL UNIQUE,
                    name VARCHAR(255) NOT NULL,
                    location VARCHAR(255),
                    estimated_value {real_type} DEFAULT 0,
                    quantity INTEGER DEFAULT 1,
                    description TEXT
                )
            """,
            "donors": f"""
                CREATE TABLE IF NOT EXISTS donors (
                    id {pk_type},
                    name VARCHAR(255) NOT NULL,
                    phone VARCHAR(50),
                    address TEXT,
                    donor_type VARCHAR(50),
                    description TEXT
                )
            """
        }

        for table_name, create_query in tables.items():
            try:
                cursor.execute(create_query)
                conn.commit()
            except Exception as e:
                print(f"Error creating table {table_name}: {e}")

        # Check if cash_flow_categories is empty to add defaults
        cursor.execute("SELECT COUNT(*) FROM cash_flow_categories")
        if cursor.fetchone()[0] == 0:
            default_categories = [
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
            q = "INSERT INTO cash_flow_categories (name, main_category) VALUES (%s, %s)" if self.db_type == "mysql" else "INSERT INTO cash_flow_categories (name, main_category) VALUES (?, ?)"
            cursor.executemany(q, default_categories)
            conn.commit()

        conn.close()

    def get_accounts(self):
        query = "SELECT id, code, name, type, category FROM accounts ORDER BY code"
        return self._execute_query(query, fetch=True)

    def add_account(self, code, name, type, category):
        query = "INSERT INTO accounts (code, name, type, category) VALUES (?, ?, ?, ?)"
        self._execute_query(query, (code, name, type, category))

    def update_account(self, account_id, code, name, type, category):
        query = "UPDATE accounts SET code = ?, name = ?, type = ?, category = ? WHERE id = ?"
        self._execute_query(query, (code, name, type, category, account_id))

    def delete_account(self, account_id):
        query = "DELETE FROM accounts WHERE id = ?"
        self._execute_query(query, (account_id,))

    def bulk_add_accounts(self, accounts_data):
        conn = self.get_connection()
        cursor = conn.cursor()
        success_count = 0; fail_count = 0; errors = []
        try:
            for account in accounts_data:
                code = account.get('code'); name = account.get('name'); acc_type = account.get('type'); category = account.get('category', "")
                if not all([code, name, acc_type]): continue
                
                q_check = "SELECT id FROM accounts WHERE code = %s" if self.db_type == "mysql" else "SELECT id FROM accounts WHERE code = ?"
                cursor.execute(q_check, (code,))
                existing = cursor.fetchone()
                if existing:
                    q_up = "UPDATE accounts SET name = %s, type = %s, category = %s WHERE id = %s" if self.db_type == "mysql" else "UPDATE accounts SET name = ?, type = ?, category = ? WHERE id = ?"
                    cursor.execute(q_up, (name, acc_type, category, existing[0]))
                else:
                    q_in = "INSERT INTO accounts (code, name, type, category) VALUES (%s, %s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO accounts (code, name, type, category) VALUES (?, ?, ?, ?)"
                    cursor.execute(q_in, (code, name, acc_type, category))
                success_count += 1
            conn.commit()
        except Exception as e:
            conn.rollback(); errors.append(str(e)); fail_count = len(accounts_data)
        finally: conn.close()
        return success_count, fail_count, errors

    def add_journal_entry(self, date, description, ref_no, details):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            q_in = "INSERT INTO journal_entries (date, description, reference_no) VALUES (%s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO journal_entries (date, description, reference_no) VALUES (?, ?, ?)"
            cursor.execute(q_in, (date, description, ref_no))
            journal_id = cursor.lastrowid
            
            q_det = "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (%s, %s, %s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)"
            for item in details:
                cursor.execute(q_det, (journal_id, item['account_id'], item['debit'], item['credit'], item.get('cash_flow_activity')))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error: {e}"); conn.rollback(); return False
        finally: conn.close()

    def update_journal_entry(self, journal_id, date, description, ref_no, details):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            q_up = "UPDATE journal_entries SET date = %s, description = %s, reference_no = %s WHERE id = %s" if self.db_type == "mysql" else "UPDATE journal_entries SET date = ?, description = ?, reference_no = ? WHERE id = ?"
            cursor.execute(q_up, (date, description, ref_no, journal_id))
            q_del = "DELETE FROM journal_details WHERE journal_id = %s" if self.db_type == "mysql" else "DELETE FROM journal_details WHERE journal_id = ?"
            cursor.execute(q_del, (journal_id,))
            q_det = "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (%s, %s, %s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)"
            for item in details:
                cursor.execute(q_det, (journal_id, item['account_id'], item['debit'], item['credit'], item.get('cash_flow_activity')))
            conn.commit(); return True
        except Exception as e:
            print(f"Error: {e}"); conn.rollback(); return False
        finally: conn.close()

    def get_journal_summaries(self):
        query = "SELECT id, date, description, reference_no FROM journal_entries ORDER BY date DESC, id DESC"
        return self._execute_query(query, fetch=True)

    def get_journal_details(self, journal_id):
        header_query = "SELECT date, description, reference_no FROM journal_entries WHERE id = ?"
        header_result = self._execute_query(header_query, (journal_id,), fetch=True)
        if not header_result: return None
        details_query = """
        SELECT a.code, a.name, jd.debit, jd.credit, jd.cash_flow_activity
        FROM journal_details jd
        JOIN accounts a ON jd.account_id = a.id
        WHERE jd.journal_id = ?
        ORDER BY jd.id ASC
        """
        details_result = self._execute_query(details_query, (journal_id,), fetch=True)
        return {'header': header_result[0], 'details': details_result}

    def delete_journal_entry(self, journal_id):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            q1 = "DELETE FROM journal_details WHERE journal_id = %s" if self.db_type == "mysql" else "DELETE FROM journal_details WHERE journal_id = ?"
            cursor.execute(q1, (journal_id,))
            q2 = "DELETE FROM journal_entries WHERE id = %s" if self.db_type == "mysql" else "DELETE FROM journal_entries WHERE id = ?"
            cursor.execute(q2, (journal_id,))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

    def get_trial_balance(self):
        query = """
        SELECT a.code, a.name, a.type, a.category,
               SUM(jd.debit) as total_debit, SUM(jd.credit) as total_credit
        FROM accounts a
        LEFT JOIN journal_details jd ON a.id = jd.account_id
        GROUP BY a.id, a.code, a.name, a.type, a.category
        """
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        df['total_debit'] = pd.to_numeric(df['total_debit'].fillna(0), errors='coerce').fillna(0)
        df['total_credit'] = pd.to_numeric(df['total_credit'].fillna(0), errors='coerce').fillna(0)
        df['debit'] = 0.0; df['credit'] = 0.0; df['balance'] = 0.0
        for index, row in df.iterrows():
            if row['type'] in ['Asset', 'Expense']:
                balance = row['total_debit'] - row['total_credit']
                df.at[index, 'balance'] = balance
                if balance >= 0: df.at[index, 'debit'] = balance
                else: df.at[index, 'credit'] = abs(balance)
            else:
                balance = row['total_credit'] - row['total_debit']
                df.at[index, 'balance'] = balance
                if balance >= 0: df.at[index, 'credit'] = balance
                else: df.at[index, 'debit'] = abs(balance)
        return df

    def get_ledger_entries(self, account_id):
        query = """
        SELECT je.date, je.description, je.reference_no, jd.debit, jd.credit
        FROM journal_details jd
        JOIN journal_entries je ON jd.journal_id = je.id
        WHERE jd.account_id = ?
        ORDER BY je.date ASC, je.id ASC
        """
        if self.db_type == "mysql": query = query.replace("?", "%s")
        conn = self.get_connection()
        df = pd.read_sql_query(query, conn, params=(account_id,))
        conn.close(); return df

    def get_cash_flow_categories(self):
        query = "SELECT id, name, main_category FROM cash_flow_categories ORDER BY name"
        return self._execute_query(query, fetch=True)

    def get_cash_flow_activity_mapping(self):
        categories = self.get_cash_flow_categories()
        return {name: main_cat for _, name, main_cat in categories}

    def get_account_id_by_code(self, account_code):
        query = "SELECT id FROM accounts WHERE code = ?"
        result = self._execute_query(query, (account_code,), fetch=True)
        return result[0][0] if result else None

    def get_cash_and_cash_equivalents_account_ids(self):
        query = "SELECT id FROM accounts WHERE name LIKE '%Kas%' OR name LIKE '%Bank%'"
        result = self._execute_query(query, fetch=True)
        return [row[0] for row in result] if result else []

    def get_cash_account_id(self):
        query = "SELECT id FROM accounts WHERE name = 'Kas' OR name = 'Cash' OR name = 'Kas dan Setara Kas' LIMIT 1"
        result = self._execute_query(query, fetch=True)
        return result[0][0] if result else None

    def get_all_journal_details_with_cash_flow(self):
        query = """
        SELECT je.id, je.date, je.description, a.name, jd.debit, jd.credit, jd.cash_flow_activity
        FROM journal_details jd
        JOIN journal_entries je ON jd.journal_id = je.id
        JOIN accounts a ON jd.account_id = a.id
        ORDER BY je.date ASC, je.id ASC
        """
        return self._execute_query(query, fetch=True)

    def get_journal_details_for_account(self, account_id):
        query = """
        SELECT je.date, je.description, je.reference_no, jd.debit, jd.credit
        FROM journal_details jd
        JOIN journal_entries je ON jd.journal_id = je.id
        WHERE jd.account_id = ?
        ORDER BY je.date ASC, je.id ASC
        """
        return self._execute_query(query, (account_id,), fetch=True)

    def add_cash_flow_category(self, name, main_category):
        query = "INSERT INTO cash_flow_categories (name, main_category) VALUES (?, ?)"
        self._execute_query(query, (name, main_category))

    def update_cash_flow_category(self, category_id, name, main_category):
        query = "UPDATE cash_flow_categories SET name = ?, main_category = ? WHERE id = ?"
        self._execute_query(query, (name, main_category, category_id))

    def delete_cash_flow_category(self, category_id):
        query = "DELETE FROM cash_flow_categories WHERE id = ?"
        self._execute_query(query, (category_id,))

    # --- Assets Inventory ---
    def get_assets_inventory(self):
        query = "SELECT id, date, code, name, location, estimated_value, quantity, description FROM assets_inventory ORDER BY date DESC"
        return self._execute_query(query, fetch=True)

    def add_asset_inventory(self, date, code, name, location, value, qty, desc):
        query = "INSERT INTO assets_inventory (date, code, name, location, estimated_value, quantity, description) VALUES (?, ?, ?, ?, ?, ?, ?)"
        self._execute_query(query, (date, code, name, location, value, qty, desc))

    def update_asset_inventory(self, asset_id, date, code, name, location, value, qty, desc):
        query = "UPDATE assets_inventory SET date = ?, code = ?, name = ?, location = ?, estimated_value = ?, quantity = ?, description = ? WHERE id = ?"
        self._execute_query(query, (date, code, name, location, value, qty, desc, asset_id))

    def delete_asset_inventory(self, asset_id):
        query = "DELETE FROM assets_inventory WHERE id = ?"
        self._execute_query(query, (asset_id,))

    def bulk_add_assets(self, assets_data):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            for item in assets_data:
                q = "INSERT INTO assets_inventory (date, code, name, location, estimated_value, quantity, description) VALUES (?, ?, ?, ?, ?, ?, ?)"
                if self.db_type == "mysql": q = q.replace("?", "%s")
                cursor.execute(q, (item['date'], item['code'], item['name'], item['location'], item['estimated_value'], item['quantity'], item.get('description', "")))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

    # --- Donors ---
    def get_donors(self):
        query = "SELECT id, name, phone, address, donor_type, description FROM donors ORDER BY name"
        return self._execute_query(query, fetch=True)

    def add_donor(self, name, phone, address, donor_type, desc):
        query = "INSERT INTO donors (name, phone, address, donor_type, description) VALUES (?, ?, ?, ?, ?)"
        self._execute_query(query, (name, phone, address, donor_type, desc))

    def update_donor(self, donor_id, name, phone, address, donor_type, desc):
        query = "UPDATE donors SET name = ?, phone = ?, address = ?, donor_type = ?, description = ? WHERE id = ?"
        self._execute_query(query, (name, phone, address, donor_type, desc, donor_id))

    def delete_donor(self, donor_id):
        query = "DELETE FROM donors WHERE id = ?"
        self._execute_query(query, (donor_id,))

    def get_all_data_table_names(self):
        return ['journal_details', 'journal_entries', 'accounts', 'cash_flow_categories', 'assets_inventory', 'donors']

    def clear_table_data(self, table_name):
        query = f"DELETE FROM {table_name}"
        self._execute_query(query)

    def clear_all_data(self):
        for t in self.get_all_data_table_names(): self.clear_table_data(t)

    def get_account_balance_at_date(self, account_id, end_date):
        conn = self.get_connection(); cursor = conn.cursor()
        q_type = "SELECT type FROM accounts WHERE id = %s" if self.db_type == "mysql" else "SELECT type FROM accounts WHERE id = ?"
        cursor.execute(q_type, (account_id,))
        res = cursor.fetchone()
        if not res: conn.close(); return 0.0
        acc_type = res[0]
        q_bal = """
        SELECT SUM(jd.debit) as td, SUM(jd.credit) as tc
        FROM journal_details jd
        JOIN journal_entries je ON jd.journal_id = je.id
        WHERE jd.account_id = %s AND je.date <= %s
        """ if self.db_type == "mysql" else """
        SELECT SUM(jd.debit) as td, SUM(jd.credit) as tc
        FROM journal_details jd
        JOIN journal_entries je ON jd.journal_id = je.id
        WHERE jd.account_id = ? AND je.date <= ?
        """
        cursor.execute(q_bal, (account_id, end_date))
        r = cursor.fetchone()
        conn.close()
        td = r[0] if r[0] else 0.0; tc = r[1] if r[1] else 0.0
        return (td - tc) if acc_type in ['Asset', 'Expense'] else (tc - td)

    def get_account_by_name_or_create(self, name, code, type, category):
        conn = self.get_connection(); cursor = conn.cursor()
        q_sel = "SELECT id FROM accounts WHERE name = %s" if self.db_type == "mysql" else "SELECT id FROM accounts WHERE name = ?"
        cursor.execute(q_sel, (name,))
        res = cursor.fetchone()
        if res: conn.close(); return res[0]
        q_in = "INSERT INTO accounts (code, name, type, category) VALUES (%s, %s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO accounts (code, name, type, category) VALUES (?, ?, ?, ?)"
        cursor.execute(q_in, (code, name, type, category))
        aid = cursor.lastrowid; conn.commit(); conn.close(); return aid

    def create_closing_entries(self, date, year):
        try:
            ism_id = self.get_account_by_name_or_create("Ikhtisar Laba Rugi", "3999", "Asset Net", "Ekuitas")
            conn = self.get_connection(); cursor = conn.cursor()
            q_eq = "SELECT id FROM accounts WHERE name LIKE '%Modal%' OR name LIKE '%Ekuitas%' LIMIT 1"
            cursor.execute(q_eq); eq_res = cursor.fetchone()
            if not eq_res: return False
            eq_id = eq_res[0]
            cursor.execute("SELECT id, name, type FROM accounts WHERE type IN ('Revenue', 'Expense')")
            accs = cursor.fetchall()
            details = []; total_ism = 0.0
            for aid, aname, atype in accs:
                bal = self.get_account_balance_at_date(aid, date)
                if bal != 0:
                    if atype == 'Revenue':
                        details.append({'account_id': aid, 'debit': bal, 'credit': 0.0})
                        details.append({'account_id': ism_id, 'debit': 0.0, 'credit': bal})
                        total_ism += bal
                    else:
                        details.append({'account_id': aid, 'debit': 0.0, 'credit': bal})
                        details.append({'account_id': ism_id, 'debit': bal, 'credit': 0.0})
                        total_ism -= bal
            if details: self.add_journal_entry(date, f"Penutup IE {year}", f"JP-IE-{year}", details)
            ism_bal = self.get_account_balance_at_date(ism_id, date)
            if ism_bal != 0:
                re_dets = []
                if ism_bal > 0:
                    re_dets.append({'account_id': ism_id, 'debit': ism_bal, 'credit': 0.0})
                    re_dets.append({'account_id': eq_id, 'debit': 0.0, 'credit': ism_bal})
                else:
                    re_dets.append({'account_id': eq_id, 'debit': abs(ism_bal), 'credit': 0.0})
                    re_dets.append({'account_id': ism_id, 'debit': 0.0, 'credit': abs(ism_bal)})
                self.add_journal_entry(date, f"Penutup ISM {year}", f"JP-IS-{year}", re_dets)
            return True
        except: return False
