import sqlite3
import os
import sys
import json

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

class DatabaseManager:
    CONFIG_FILE = "user_settings.json"

    def __init__(self, db_path='database/foundation_finance.db'):
        self.config = self.load_config()
        self.db_type = self.config.get("db_type", "sqlite")
        self.mysql_config = self.config.get("mysql_config", {})

        if hasattr(sys, '_MEIPASS'):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(base_dir, db_path)
        else:
            self.db_path = db_path
        
        if self.db_type == "sqlite":
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                try: os.makedirs(db_dir)
                except: self.db_path = os.path.basename(db_path)
            
        self._ensure_database_exists()
        self._update_schema()

    def _ensure_database_exists(self):
        if self.db_type == "mysql" and MYSQL_AVAILABLE:
            try:
                conn = mysql.connector.connect(
                    host=self.mysql_config.get("host"),
                    user=self.mysql_config.get("user"),
                    password=self.mysql_config.get("password")
                )
                cursor = conn.cursor()
                db_name = self.mysql_config.get("database")
                if db_name:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
                conn.close()
            except: pass

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
            except:
                self.db_type = "sqlite"
        return sqlite3.connect(self.db_path)

    def _execute_query(self, query, params=(), fetch=False, commit=False):
        if self.db_type == "mysql":
            query = query.replace("?", "%s")
        conn = self.get_connection()
        try:
            if self.db_type == "mysql":
                cursor = conn.cursor(buffered=True)
            else:
                cursor = conn.cursor()
            cursor.execute(query, params)
            res = cursor.fetchall() if fetch else None
            if commit: conn.commit()
            return res
        except Exception as e:
            print(f"DB Error: {e}")
            return None
        finally:
            conn.close()

    def _update_schema(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        pk = "INTEGER PRIMARY KEY AUTO_INCREMENT" if self.db_type == "mysql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
        real = "DOUBLE" if self.db_type == "mysql" else "REAL"

        tables = {
            "accounts": f"CREATE TABLE IF NOT EXISTS accounts (id {pk}, code VARCHAR(50) UNIQUE, name VARCHAR(255), type VARCHAR(50), category VARCHAR(100), notes TEXT)",
            "journal_entries": f"CREATE TABLE IF NOT EXISTS journal_entries (id {pk}, date VARCHAR(20), description TEXT, reference_no VARCHAR(100) UNIQUE)",
            "journal_details": f"CREATE TABLE IF NOT EXISTS journal_details (id {pk}, journal_id INTEGER, account_id INTEGER, debit {real} DEFAULT 0, credit {real} DEFAULT 0, cash_flow_activity TEXT)",
            "donors": f"CREATE TABLE IF NOT EXISTS donors (id {pk}, name VARCHAR(255), phone VARCHAR(50), address TEXT, donor_type VARCHAR(50), description TEXT)",
            "assets_inventory": f"CREATE TABLE IF NOT EXISTS assets_inventory (id {pk}, date VARCHAR(20), code VARCHAR(50) UNIQUE, name VARCHAR(255), location VARCHAR(255), estimated_value {real} DEFAULT 0, quantity INTEGER DEFAULT 1, description TEXT)",
            "cash_flow_categories": f"CREATE TABLE IF NOT EXISTS cash_flow_categories (id {pk}, name VARCHAR(255) UNIQUE, main_category VARCHAR(255))",
            "foundation_profile": f"CREATE TABLE IF NOT EXISTS foundation_profile (id INTEGER PRIMARY KEY CHECK (id = 1), name VARCHAR(255), address TEXT, leader_name VARCHAR(255), pembina_name VARCHAR(255), pengawas_name VARCHAR(255), logo_path TEXT, phone VARCHAR(50), email VARCHAR(100))",
            "annual_report_settings": f"CREATE TABLE IF NOT EXISTS annual_report_settings (year INTEGER PRIMARY KEY, vision TEXT, mission TEXT, program_summary TEXT, program_detail_edu TEXT, program_detail_social TEXT, organizational_structure TEXT, evaluation_constraints TEXT, future_plans TEXT)"
        }
        for _, q in tables.items():
            try: cursor.execute(q); conn.commit()
            except: pass
        
        for col in ['program_detail_edu', 'program_detail_social', 'evaluation_constraints', 'future_plans']:
            try: cursor.execute(f"ALTER TABLE annual_report_settings ADD COLUMN {col} TEXT"); conn.commit()
            except: pass
        for col in ['pembina_name', 'pengawas_name', 'logo_path']:
            try: cursor.execute(f"ALTER TABLE foundation_profile ADD COLUMN {col} TEXT"); conn.commit()
            except: pass
        conn.close()

    # --- ACCOUNTS ---
    def get_accounts(self): return self._execute_query("SELECT id, code, name, type, category, notes FROM accounts ORDER BY code", fetch=True)
    def add_account(self, code, name, t, cat, n=""): return self._execute_query("INSERT INTO accounts (code, name, type, category, notes) VALUES (?, ?, ?, ?, ?)", (code, name, t, cat, n), commit=True)
    def update_account(self, aid, code, name, t, cat, n=""): return self._execute_query("UPDATE accounts SET code=?, name=?, type=?, category=?, notes=? WHERE id=?", (code, name, t, cat, n, aid), commit=True)
    def delete_account(self, aid): return self._execute_query("DELETE FROM accounts WHERE id=?", (aid,), commit=True)

    # --- JOURNALS ---
    def get_journal_summaries(self): return self._execute_query("SELECT id, date, description, reference_no FROM journal_entries ORDER BY date DESC, id DESC", fetch=True)
    
    def get_journal_details(self, jid):
        h = self._execute_query("SELECT date, description, reference_no FROM journal_entries WHERE id=?", (jid,), fetch=True)
        if not h: return None
        d = self._execute_query("SELECT a.code, a.name, jd.debit, jd.credit, jd.cash_flow_activity, jd.account_id FROM journal_details jd JOIN accounts a ON jd.account_id=a.id WHERE jd.journal_id=? ORDER BY jd.id", (jid,), fetch=True)
        return {'header': h[0], 'details': d}

    def add_journal_entry(self, date, desc, ref, details):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            q1 = "INSERT INTO journal_entries (date, description, reference_no) VALUES (%s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO journal_entries (date, description, reference_no) VALUES (?, ?, ?)"
            cursor.execute(q1, (date, desc, ref)); jid = cursor.lastrowid
            q2 = "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (%s, %s, %s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)"
            for d in details: cursor.execute(q2, (jid, d['account_id'], d['debit'], d['credit'], d.get('cash_flow_activity')))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

    def update_journal_entry(self, jid, date, desc, ref, details):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            cursor.execute("UPDATE journal_entries SET date=%s, description=%s, reference_no=%s WHERE id=%s" if self.db_type == "mysql" else "UPDATE journal_entries SET date=?, description=?, reference_no=? WHERE id=?", (date, desc, ref, jid))
            cursor.execute("DELETE FROM journal_details WHERE journal_id=%s" if self.db_type == "mysql" else "DELETE FROM journal_details WHERE journal_id=?", (jid,))
            q = "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (%s, %s, %s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)"
            for d in details: cursor.execute(q, (jid, d['account_id'], d['debit'], d['credit'], d.get('cash_flow_activity')))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

    def delete_journal_entry(self, jid):
        self._execute_query("DELETE FROM journal_details WHERE journal_id=?", (jid,), commit=True)
        self._execute_query("DELETE FROM journal_entries WHERE id=?", (jid,), commit=True)
        return True

    def add_beginning_balance_entry(self, date, year, details):
        ref_no = f"SA-{year}"
        old_entry = self._execute_query("SELECT id FROM journal_entries WHERE reference_no=?", (ref_no,), fetch=True)
        if old_entry: self.delete_journal_entry(old_entry[0][0])
        return self.add_journal_entry(date, f"Saldo Awal Tahun {year}", ref_no, details)

    def get_journal_data_for_export(self):
        query = "SELECT je.date as Tanggal, je.description as Keterangan, je.reference_no as Referensi, a.code as 'Kode Akun', a.name as 'Nama Akun', jd.debit as Debit, jd.credit as Kredit, jd.cash_flow_activity as 'Aktivitas Arus Kas' FROM journal_details jd JOIN journal_entries je ON jd.journal_id = je.id JOIN accounts a ON jd.account_id = a.id ORDER BY je.date DESC, je.id DESC"
        res = self._execute_query(query, fetch=True)
        if not res: return []
        cols = ['Tanggal', 'Keterangan', 'Referensi', 'Kode Akun', 'Nama Akun', 'Debit', 'Kredit', 'Aktivitas Arus Kas']
        return [dict(zip(cols, row)) for row in res]

    # --- REPORTS ---
    def get_trial_balance(self):
        q = "SELECT a.id, a.code, a.name, a.type, a.category, SUM(COALESCE(jd.debit, 0)) as total_debit, SUM(COALESCE(jd.credit, 0)) as total_credit FROM accounts a LEFT JOIN journal_details jd ON a.id = jd.account_id GROUP BY a.id, a.code, a.name, a.type, a.category ORDER BY a.code"
        res = self._execute_query(q, fetch=True)
        if not res: return []
        
        data = []
        for row in res:
            r = dict(zip(['id', 'code', 'name', 'type', 'category', 'total_debit', 'total_credit'], row))
            r['total_debit'] = float(r['total_debit'] or 0)
            r['total_credit'] = float(r['total_credit'] or 0)
            r['debit'] = 0.0; r['credit'] = 0.0; r['balance'] = 0.0
            
            if r['type'] in ['Asset', 'Expense', 'aset', 'beban', 'harta', 'biaya']:
                bal = r['total_debit'] - r['total_credit']
                r['balance'] = bal
                if bal >= 0: r['debit'] = bal
                else: r['credit'] = abs(bal)
            else:
                bal = r['total_credit'] - r['total_debit']
                r['balance'] = bal
                if bal >= 0: r['credit'] = bal
                else: r['debit'] = abs(bal)
            data.append(r)
        return data

    def get_ledger_entries(self, aid):
        q = "SELECT je.date, je.description, je.reference_no, jd.debit, jd.credit FROM journal_details jd JOIN journal_entries je ON jd.journal_id=je.id WHERE jd.account_id=? ORDER BY je.date, je.id"
        res = self._execute_query(q, params=(aid,), fetch=True)
        if not res: return []
        cols = ['date', 'description', 'reference_no', 'debit', 'credit']
        return [dict(zip(cols, row)) for row in res]

    def get_cash_flow_categories(self): return self._execute_query("SELECT id, name, main_category FROM cash_flow_categories ORDER BY main_category, name", fetch=True)

    # --- DONORS & ASSETS ---
    def get_donors(self): return self._execute_query("SELECT id, name, phone, address, donor_type, description FROM donors ORDER BY name", fetch=True)
    def add_donor(self, name, phone, address, t, desc): return self._execute_query("INSERT INTO donors (name, phone, address, donor_type, description) VALUES (?, ?, ?, ?, ?)", (name, phone, address, t, desc), commit=True)
    def update_donor(self, did, name, phone, address, t, desc): return self._execute_query("UPDATE donors SET name=?, phone=?, address=?, donor_type=?, description=? WHERE id=?", (name, phone, address, t, desc, did), commit=True)
    def delete_donor(self, did): return self._execute_query("DELETE FROM donors WHERE id=?", (did,), commit=True)

    def get_assets_inventory(self): return self._execute_query("SELECT id, date, code, name, location, estimated_value, quantity, description FROM assets_inventory ORDER BY date DESC", fetch=True)
    def add_asset_inventory(self, date, code, name, loc, val, qty, desc): return self._execute_query("INSERT INTO assets_inventory (date, code, name, location, estimated_value, quantity, description) VALUES (?, ?, ?, ?, ?, ?, ?)", (date, code, name, loc, val, qty, desc), commit=True)
    def update_asset_inventory(self, aid, date, code, name, loc, val, qty, desc): return self._execute_query("UPDATE assets_inventory SET date=?, code=?, name=?, location=?, estimated_value=?, quantity=?, description=? WHERE id=?", (date, code, name, loc, val, qty, desc, aid), commit=True)
    def delete_asset_inventory(self, aid): return self._execute_query("DELETE FROM assets_inventory WHERE id=?", (aid,), commit=True)

    # --- PROFILE & SETTINGS ---
    def get_foundation_profile(self):
        r = self._execute_query("SELECT name, address, leader_name, pembina_name, pengawas_name, logo_path, phone, email FROM foundation_profile WHERE id=1", fetch=True)
        if r: return {'name': r[0][0], 'address': r[0][1], 'leader_name': r[0][2], 'pembina_name': r[0][3], 'pengawas_name': r[0][4], 'logo_path': r[0][5], 'phone': r[0][6], 'email': r[0][7]}
        return {'name': 'Yayasan ISAK 35'}

    def update_foundation_profile(self, name, addr, leader, pembina, pengawas, phone, email):
        return self._execute_query("UPDATE foundation_profile SET name=?, address=?, leader_name=?, pembina_name=?, pengawas_name=?, phone=?, email=? WHERE id=1", (name, addr, leader, pembina, pengawas, phone, email), commit=True)

    def verify_login(self, u, p):
        if u == 'admin' and p == 'admin123': return {'username': u, 'role': 'admin'}
        return None

    def get_all_data_table_names(self):
        return ['journal_entries', 'journal_details', 'accounts', 'donors', 'assets_inventory', 'cash_flow_categories', 'annual_report_settings']

    def clear_table_data(self, table_name):
        if table_name in self.get_all_data_table_names():
            return self._execute_query(f"DELETE FROM {table_name}", commit=True)
        return False

    # --- ANNUAL REPORT ---
    def get_annual_report_settings(self, year):
        res = self._execute_query("SELECT * FROM annual_report_settings WHERE year=?", (year,), fetch=True)
        if not res: return None
        cols = ['year', 'vision', 'mission', 'program_summary', 'program_detail_edu', 'program_detail_social', 'organizational_structure', 'evaluation_constraints', 'future_plans', 'pembina_name', 'pengawas_name', 'logo_path']
        return dict(zip(cols, res[0]))

    def save_annual_report_settings(self, year, data):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            # Check if exists
            cursor.execute("SELECT year FROM annual_report_settings WHERE year=?", (year,))
            if cursor.fetchone():
                q = "UPDATE annual_report_settings SET vision=?, mission=?, program_summary=?, program_detail_edu=?, program_detail_social=?, organizational_structure=?, evaluation_constraints=?, future_plans=? WHERE year=?"
                cursor.execute(q, (data['vision'], data['mission'], data['program_summary'], data['program_detail_edu'], data['program_detail_social'], data['organizational_structure'], data['evaluation_constraints'], data['future_plans'], year))
            else:
                q = "INSERT INTO annual_report_settings (year, vision, mission, program_summary, program_detail_edu, program_detail_social, organizational_structure, evaluation_constraints, future_plans) VALUES (?,?,?,?,?,?,?,?,?)"
                cursor.execute(q, (year, data['vision'], data['mission'], data['program_summary'], data['program_detail_edu'], data['program_detail_social'], data['organizational_structure'], data['evaluation_constraints'], data['future_plans']))
            conn.commit(); return True
        except Exception as e:
            print(f"Error saving report settings: {e}")
            return False
        finally: conn.close()

    def generate_full_backup(self):
        tables = ['accounts', 'journal_entries', 'journal_details', 'donors', 'assets_inventory', 'cash_flow_categories', 'foundation_profile', 'annual_report_settings']
        backup = {}
        conn = self.get_connection(); cursor = conn.cursor()
        for t in tables:
            cursor.execute(f"SELECT * FROM {t}"); rows = cursor.fetchall()
            if self.db_type == "mysql":
                cursor.execute(f"SHOW COLUMNS FROM {t}"); cols = [c[0] for c in cursor.fetchall()]
            else:
                cursor.execute(f"PRAGMA table_info({t})"); cols = [c[1] for c in cursor.fetchall()]
            backup[t] = [dict(zip(cols, row)) for row in rows]
        conn.close(); return backup

    def restore_full_backup(self, data):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            for t in ['journal_details', 'journal_entries', 'accounts', 'cash_flow_categories', 'assets_inventory', 'donors', 'foundation_profile', 'annual_report_settings']:
                try: cursor.execute(f"DELETE FROM {t}")
                except: pass
            for t, rows in data.items():
                if not rows: continue
                cols = list(rows[0].keys()); placeholders = ", ".join(["%s" if self.db_type == "mysql" else "?" for _ in cols])
                q = f"INSERT INTO {t} ({', '.join(cols)}) VALUES ({placeholders})"
                cursor.executemany(q, [tuple(r[c] for c in cols) for r in rows])
            conn.commit(); return True, "Success"
        except Exception as e: conn.rollback(); return False, str(e)
        finally: conn.close()
