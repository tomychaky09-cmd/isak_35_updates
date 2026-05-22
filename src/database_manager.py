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
        if hasattr(sys, '_MEIPASS'): base_dir = os.path.dirname(sys.executable)
        else: base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not os.path.isabs(db_path): self.db_path = os.path.join(base_dir, db_path)
        else: self.db_path = db_path
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
                conn = mysql.connector.connect(host=self.mysql_config.get("host"), user=self.mysql_config.get("user"), password=self.mysql_config.get("password"))
                cursor = conn.cursor()
                db_name = self.mysql_config.get("database")
                if db_name: cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
                conn.close()
            except: pass

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f: return json.load(f)
            except: return {}
        return {}

    def get_connection(self):
        if self.db_type == "mysql" and MYSQL_AVAILABLE:
            try: return mysql.connector.connect(**self.mysql_config)
            except: return sqlite3.connect(self.db_path)
        return sqlite3.connect(self.db_path)

    def _execute_query(self, query, params=(), fetch=False, commit=False):
        conn = self.get_connection()
        if self.db_type == "mysql":
            query = query.replace("?", "%s")
            cursor = conn.cursor(buffered=True)
        else: cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit: conn.commit()
            if fetch: return cursor.fetchall()
            return True
        except: return None
        finally: conn.close()

    def _update_schema(self):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            pk = "INTEGER PRIMARY KEY AUTO_INCREMENT" if self.db_type == "mysql" else "INTEGER PRIMARY KEY AUTOINCREMENT"
            cursor.execute(f"CREATE TABLE IF NOT EXISTS accounts (id {pk}, code VARCHAR(50) UNIQUE, name VARCHAR(255), type VARCHAR(50), category VARCHAR(100), notes TEXT)")
            cursor.execute(f"CREATE TABLE IF NOT EXISTS journal_entries (id {pk}, date VARCHAR(20), description TEXT, reference_no VARCHAR(100) UNIQUE)")
            cursor.execute(f"CREATE TABLE IF NOT EXISTS journal_details (id {pk}, journal_id INTEGER, account_id INTEGER, debit DOUBLE DEFAULT 0, credit DOUBLE DEFAULT 0, cash_flow_activity TEXT)")
            cursor.execute(f"CREATE TABLE IF NOT EXISTS donors (id {pk}, name VARCHAR(255), phone VARCHAR(50), address TEXT, donor_type VARCHAR(50), description TEXT)")
            cursor.execute(f"CREATE TABLE IF NOT EXISTS assets_inventory (id {pk}, date VARCHAR(20), code VARCHAR(50) UNIQUE, name VARCHAR(255), location VARCHAR(255), estimated_value DOUBLE DEFAULT 0, quantity INTEGER DEFAULT 1, description TEXT)")
            cursor.execute(f"CREATE TABLE IF NOT EXISTS cash_flow_categories (id {pk}, name VARCHAR(255) UNIQUE, main_category VARCHAR(255))")
            cursor.execute("CREATE TABLE IF NOT EXISTS foundation_profile (id INTEGER PRIMARY KEY CHECK (id = 1), name VARCHAR(255), address TEXT, leader_name VARCHAR(255), pembina_name VARCHAR(255), pengawas_name VARCHAR(255), logo_path TEXT, phone VARCHAR(50), email VARCHAR(100))")
            cursor.execute("CREATE TABLE IF NOT EXISTS annual_report_settings (year INTEGER PRIMARY KEY, vision TEXT, mission TEXT, program_summary TEXT, program_detail_edu TEXT, program_detail_social TEXT, organizational_structure TEXT, evaluation_constraints TEXT, future_plans TEXT)")
            cursor.execute("SELECT COUNT(*) FROM foundation_profile")
            if cursor.fetchone()[0] == 0: cursor.execute("INSERT INTO foundation_profile (id, name) VALUES (1, 'Yayasan ISAK 35')")
            cursor.execute("SELECT COUNT(*) FROM cash_flow_categories")
            if cursor.fetchone()[0] == 0:
                cats = [('Penerimaan Donasi / Infaq', 'ARUS KAS DARI AKTIVITAS OPERASI'),('Pembelian Aset Tetap', 'ARUS KAS DARI AKTIVITAS INVESTASI'),('Penerimaan Pinjaman', 'ARUS KAS DARI AKTIVITAS PENDANAAN')]
                q = "INSERT INTO cash_flow_categories (name, main_category) VALUES (%s, %s)" if self.db_type == "mysql" else "INSERT INTO cash_flow_categories (name, main_category) VALUES (?, ?)"
                cursor.executemany(q, cats)
            conn.commit()
        except: pass
        finally: conn.close()

    # --- ACCOUNTS ---
    def get_accounts(self):
        r = self._execute_query("SELECT id, code, name, type, category, notes FROM accounts ORDER BY code", fetch=True)
        return [{'id': x[0], 'code': x[1], 'name': x[2], 'type': x[3], 'category': x[4], 'notes': x[5]} for x in r] if r else []

    def add_account(self, code, name, t, cat, n=""):
        return self._execute_query("INSERT INTO accounts (code, name, type, category, notes) VALUES (?, ?, ?, ?, ?)", (code, name, t, cat, n), commit=True)

    def update_account(self, aid, code, name, t, cat, n=""):
        return self._execute_query("UPDATE accounts SET code=?, name=?, type=?, category=?, notes=? WHERE id=?", (code, name, t, cat, n, aid), commit=True)

    def delete_account(self, aid):
        return self._execute_query("DELETE FROM accounts WHERE id=?", (aid,), commit=True)

    # --- JOURNALS ---
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
            q1 = "UPDATE journal_entries SET date=?, description=?, reference_no=? WHERE id=?"
            if self.db_type == "mysql": q1 = q1.replace("?", "%s")
            cursor.execute(q1, (date, desc, ref, jid))
            q2 = "DELETE FROM journal_details WHERE journal_id=?"
            if self.db_type == "mysql": q2 = q2.replace("?", "%s")
            cursor.execute(q2, (jid,))
            q3 = "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (%s, %s, %s, %s, %s)" if self.db_type == "mysql" else "INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)"
            for d in details: cursor.execute(q3, (jid, d['account_id'], d['debit'], d['credit'], d.get('cash_flow_activity')))
            conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

    def get_journal_summaries(self):
        r = self._execute_query("SELECT id, date, description, reference_no FROM journal_entries ORDER BY date DESC, id DESC", fetch=True)
        return [{'id': x[0], 'date': x[1], 'description': x[2], 'reference_no': x[3]} for x in r] if r else []

    def get_journal_details(self, jid):
        h = self._execute_query("SELECT date, description, reference_no FROM journal_entries WHERE id=?", (jid,), fetch=True)
        if not h: return None
        d = self._execute_query("SELECT a.code, a.name, jd.debit, jd.credit, jd.cash_flow_activity, a.id FROM journal_details jd JOIN accounts a ON jd.account_id=a.id WHERE jd.journal_id=? ORDER BY jd.id", (jid,), fetch=True)
        return {'header': {'date': h[0][0], 'description': h[0][1], 'reference_no': h[0][2]}, 'details': [{'code': x[0], 'name': x[1], 'debit': x[2], 'credit': x[3], 'cash_flow_activity': x[4], 'account_id': x[5]} for x in d]}

    def delete_journal_entry(self, jid):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            q1 = "DELETE FROM journal_details WHERE journal_id=?"; q2 = "DELETE FROM journal_entries WHERE id=?"
            if self.db_type == "mysql": q1 = q1.replace("?", "%s"); q2 = q2.replace("?", "%s")
            cursor.execute(q1, (jid,)); cursor.execute(q2, (jid,)); conn.commit(); return True
        except: conn.rollback(); return False
        finally: conn.close()

    # --- REPORTS & LEDGER ---
    def get_trial_balance(self):
        query = "SELECT a.id, a.code, a.name, a.type, a.category, SUM(COALESCE(jd.debit, 0)), SUM(COALESCE(jd.credit, 0)) FROM accounts a LEFT JOIN journal_details jd ON a.id = jd.account_id GROUP BY a.id, a.code, a.name, a.type, a.category ORDER BY a.code"
        r = self._execute_query(query, fetch=True)
        res = []
        for x in r:
            aid, code, name, t, cat, td, tc = x
            td = td or 0.0; tc = tc or 0.0
            item = {'id': aid, 'code': code, 'name': name, 'type': t, 'category': cat, 'total_debit': td, 'total_credit': tc, 'debit': 0.0, 'credit': 0.0, 'balance': 0.0}
            if t in ['Asset', 'Expense']:
                bal = td - tc; item['balance'] = bal
                if bal >= 0: item['debit'] = bal
                else: item['credit'] = abs(bal)
            else:
                bal = tc - td; item['balance'] = bal
                if bal >= 0: item['credit'] = bal
                else: item['debit'] = abs(bal)
            res.append(item)
        return res

    def get_ledger_entries(self, aid):
        r = self._execute_query("SELECT je.date, je.description, je.reference_no, jd.debit, jd.credit FROM journal_details jd JOIN journal_entries je ON jd.journal_id=je.id WHERE jd.account_id=? ORDER BY je.date, je.id", (aid,), fetch=True)
        return [{'date': x[0], 'description': x[1], 'reference_no': x[2], 'debit': x[3], 'credit': x[4]} for x in r] if r else []

    # --- DONORS ---
    def get_donors(self):
        r = self._execute_query("SELECT id, name, phone, address, donor_type, description FROM donors ORDER BY name", fetch=True)
        return [{'id': x[0], 'name': x[1], 'phone': x[2], 'address': x[3], 'type': x[4], 'description': x[5]} for x in r] if r else []

    def add_donor(self, name, phone, address, t, desc):
        return self._execute_query("INSERT INTO donors (name, phone, address, donor_type, description) VALUES (?, ?, ?, ?, ?)", (name, phone, address, t, desc), commit=True)

    def update_donor(self, did, name, phone, address, t, desc):
        return self._execute_query("UPDATE donors SET name=?, phone=?, address=?, donor_type=?, description=? WHERE id=?", (name, phone, address, t, desc, did), commit=True)

    def delete_donor(self, did):
        return self._execute_query("DELETE FROM donors WHERE id=?", (did,), commit=True)

    # --- ASSETS ---
    def get_assets_inventory(self):
        r = self._execute_query("SELECT id, date, code, name, location, estimated_value, quantity, description FROM assets_inventory ORDER BY date DESC", fetch=True)
        return [{'id': x[0], 'date': x[1], 'code': x[2], 'name': x[3], 'location': x[4], 'estimated_value': x[5], 'quantity': x[6], 'description': x[7]} for x in r] if r else []

    def add_asset_inventory(self, date, code, name, loc, val, qty, desc):
        return self._execute_query("INSERT INTO assets_inventory (date, code, name, location, estimated_value, quantity, description) VALUES (?, ?, ?, ?, ?, ?, ?)", (date, code, name, loc, val, qty, desc), commit=True)

    def update_asset_inventory(self, aid, date, code, name, loc, val, qty, desc):
        return self._execute_query("UPDATE assets_inventory SET date=?, code=?, name=?, location=?, estimated_value=?, quantity=?, description=? WHERE id=?", (date, code, name, loc, val, qty, desc, aid), commit=True)

    def delete_asset_inventory(self, aid):
        return self._execute_query("DELETE FROM assets_inventory WHERE id=?", (aid,), commit=True)

    # --- OTHER ---
    def get_foundation_profile(self):
        r = self._execute_query("SELECT name, address, leader_name, pembina_name, pengawas_name, logo_path, phone, email FROM foundation_profile WHERE id=1", fetch=True)
        if r: return {'name': r[0][0], 'address': r[0][1], 'leader_name': r[0][2], 'pembina_name': r[0][3], 'pengawas_name': r[0][4], 'logo_path': r[0][5], 'phone': r[0][6], 'email': r[0][7]}
        return {'name': 'Yayasan ISAK 35'}

    def update_foundation_profile(self, name, addr, leader, pembina, pengawas, phone, email):
        return self._execute_query("UPDATE foundation_profile SET name=?, address=?, leader_name=?, pembina_name=?, pengawas_name=?, phone=?, email=? WHERE id=1", (name, addr, leader, pembina, pengawas, phone, email), commit=True)

    def get_cash_flow_categories(self):
        r = self._execute_query("SELECT name, main_category FROM cash_flow_categories ORDER BY main_category, name", fetch=True)
        return [{'name': x[0], 'main_category': x[1]} for x in r] if r else []

    def get_annual_report_settings(self, year):
        r = self._execute_query("SELECT vision, mission, program_summary, program_detail_edu, program_detail_social, organizational_structure, evaluation_constraints, future_plans FROM annual_report_settings WHERE year=?", (year,), fetch=True)
        keys = ['vision', 'mission', 'program_summary', 'program_detail_edu', 'program_detail_social', 'organizational_structure', 'evaluation_constraints', 'future_plans']
        return {keys[i]: r[0][i] for i in range(len(keys))} if r else {k: "" for k in keys}

    def verify_login(self, u, p):
        if u == 'admin' and p == 'admin123': return {'username': u, 'role': 'admin'}
        return None

    def get_journal_data_for_export(self):
        q = "SELECT je.date, je.reference_no, je.description, a.code, a.name, jd.debit, jd.credit FROM journal_details jd JOIN journal_entries je ON jd.journal_id=je.id JOIN accounts a ON jd.account_id=a.id ORDER BY je.date, je.id"
        r = self._execute_query(q, fetch=True)
        return [{'Tanggal': x[0], 'Referensi': x[1], 'Keterangan': x[2], 'Kode Akun': x[3], 'Nama Akun': x[4], 'Debit': x[5], 'Kredit': x[6]} for x in r] if r else []

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
