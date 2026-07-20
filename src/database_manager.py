import sqlite3
import os
import json
from werkzeug.security import check_password_hash, generate_password_hash

class DatabaseManager:
    CONFIG_FILE = "user_settings.json"

    def __init__(self, db_path='database/foundation_finance.db'):
        self.db_path = db_path
        self.db_type = "sqlite"  # Variabel yang hilang ini sekarang sudah ada
        self._ensure_database_exists()
        self._update_schema()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def _execute_query(self, query, params=(), fetch=False, commit=False):
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            res = cursor.fetchall() if fetch else True
            if commit: conn.commit()
            return res
        except Exception as e: 
            print(f"DB Error: {e}")
            return None
        finally: conn.close()

    def _ensure_database_exists(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _update_schema(self):
        tables = [
            "CREATE TABLE IF NOT EXISTS accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE, name TEXT, type TEXT, category TEXT, notes TEXT)",
            "CREATE TABLE IF NOT EXISTS journal_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, description TEXT, reference_no TEXT UNIQUE)",
            "CREATE TABLE IF NOT EXISTS journal_details (id INTEGER PRIMARY KEY AUTOINCREMENT, journal_id INTEGER, account_id INTEGER, debit REAL, credit REAL, cash_flow_activity TEXT)",
            "CREATE TABLE IF NOT EXISTS donors (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, address TEXT, donor_type TEXT, description TEXT)",
            "CREATE TABLE IF NOT EXISTS assets_inventory (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, code TEXT, name TEXT, location TEXT, estimated_value REAL, quantity INTEGER, description TEXT)",
            "CREATE TABLE IF NOT EXISTS cash_flow_categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, main_category TEXT)",
            "CREATE TABLE IF NOT EXISTS foundation_profile (id INTEGER PRIMARY KEY CHECK (id = 1), name TEXT, address TEXT, leader_name TEXT, pembina_name TEXT, pengawas_name TEXT, logo_path TEXT, phone TEXT, email TEXT)",
            "CREATE TABLE IF NOT EXISTS annual_report_settings (year INTEGER PRIMARY KEY, vision TEXT, mission TEXT, program_summary TEXT, program_detail_edu TEXT, program_detail_social TEXT, organizational_structure TEXT, evaluation_constraints TEXT, future_plans TEXT)",
            "CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, role TEXT)",
            "CREATE TABLE IF NOT EXISTS app_pages (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, route_name TEXT, category TEXT)",
            "CREATE TABLE IF NOT EXISTS role_permissions (role TEXT, page_id INTEGER, can_view INTEGER DEFAULT 0, can_edit INTEGER DEFAULT 0, can_delete INTEGER DEFAULT 0, PRIMARY KEY (role, page_id))",
            "CREATE TABLE IF NOT EXISTS calk_notes (id INTEGER PRIMARY KEY AUTOINCREMENT, section_title TEXT UNIQUE, content TEXT, updated_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_by INTEGER)"
        ]
        for q in tables: self._execute_query(q)

        # Migrate role_permissions columns if they don't match the new schema
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(role_permissions)")
            columns = [col[1] for col in cursor.fetchall()]
            conn.close()
            
            if 'is_allowed' in columns and 'can_view' not in columns:
                self._execute_query("ALTER TABLE role_permissions ADD COLUMN can_view INTEGER DEFAULT 0", commit=True)
                self._execute_query("UPDATE role_permissions SET can_view = is_allowed", commit=True)
            if 'can_edit' not in columns:
                self._execute_query("ALTER TABLE role_permissions ADD COLUMN can_edit INTEGER DEFAULT 0", commit=True)
            if 'can_delete' not in columns:
                self._execute_query("ALTER TABLE role_permissions ADD COLUMN can_delete INTEGER DEFAULT 0", commit=True)
        except Exception as e:
            print(f"Migration Error on role_permissions: {e}")

        # Seed all standard app_pages if they don't exist
        default_pages = [
            (1, 'Dashboard', 'dashboard', 'Utama'),
            (2, 'Chart of Accounts', 'coa_page', 'Master'),
            (3, 'Kategori Arus Kas', 'cf_cats_page', 'Master'),
            (4, 'Donatur', 'donors_page', 'Master'),
            (5, 'Inventaris Aset', 'assets_page', 'Master'),
            (6, 'Jurnal Umum', 'journals_page', 'Transaksi'),
            (7, 'Buku Besar', 'ledger_page', 'Laporan'),
            (8, 'Neraca Saldo', 'trial_balance', 'Laporan'),
            (9, 'Laporan Aktivitas', 'report_activities', 'Laporan'),
            (10, 'Laporan Posisi Keuangan', 'report_position', 'Laporan'),
            (11, 'Laporan Perubahan Aset', 'report_net_assets', 'Laporan'),
            (12, 'Laporan Arus Kas', 'report_cash_flow', 'Laporan'),
            (13, 'Laporan Tahunan', 'annual_report_page', 'Laporan'),
            (14, 'Ekspor Excel', 'export_excel', 'Sistem'),
            (15, 'Aksi Entri Jurnal (Dashboard)', 'dash_add_journal', 'Dashboard'),
            (16, 'Aksi Ekspor (Dashboard)', 'dash_export_excel', 'Dashboard'),
            (17, 'Link Daftar Akun (Dashboard)', 'dash_link_coa', 'Dashboard'),
            (18, 'Link Donatur (Dashboard)', 'dash_link_donors', 'Dashboard'),
            (19, 'Panel Super Admin', 'super_admin_panel', 'Sistem'),
            (20, 'Laporan CALK', 'report_calk', 'Laporan')
        ]
        for p_id, name, route_name, category in default_pages:
            self._execute_query("INSERT OR IGNORE INTO app_pages (id, name, route_name, category) VALUES (?, ?, ?, ?)", (p_id, name, route_name, category), commit=True)
        
        # Seed default role permissions for Laporan CALK
        for role in ['admin', 'pembina', 'bendahara', 'ketua', 'pengawas']:
            self._execute_query("INSERT OR IGNORE INTO role_permissions (role, page_id, can_view) VALUES (?, 20, 1)", (role,), commit=True)
            
        # Seed default CALK Notes if empty
        check_notes = self._execute_query("SELECT COUNT(*) FROM calk_notes", fetch=True)
        if check_notes and check_notes[0][0] == 0:
            calk_data = [
                ('1. Gambaran Umum Entitas', 'Yayasan ISAK 35 didirikan untuk bergerak dalam bidang sosial, kemanusiaan, dan keagamaan. Fokus utama yayasan adalah pelayanan masyarakat, bantuan sosial, dan pendidikan keagamaan.'),
                ('2. Ikhtisar Kebijakan Akuntansi', 'Laporan keuangan disusun berdasarkan Standar Akuntansi Keuangan Entitas Berorientasi Nonlaba (ISAK 35). Pengukuran menggunakan biaya historis. Kas mencakup kas tunai di brankas dan saldo di rekening bank.'),
                ('3. Kas dan Setara Kas', 'Kas dan setara kas per tanggal pelaporan terdiri atas Kas Tunai Operasional Yayasan dan saldo rekening bank operasional untuk donasi terikat maupun bebas.'),
                ('4. Aset Neto Tanpa Pembatasan', 'Aset neto tanpa pembatasan merupakan akumulasi surplus atau defisit aktivitas operasional yayasan yang berasal dari donatur umum/bebas.'),
                ('5. Aset Neto Dengan Pembatasan', 'Aset neto dengan pembatasan merupakan dana sumbangan terikat yang disalurkan oleh donatur untuk pelaksanaan program kerja atau proyek spesifik tertentu.')
            ]
            for title, content in calk_data:
                self._execute_query("INSERT OR IGNORE INTO calk_notes (section_title, content) VALUES (?, ?)", (title, content), commit=True)

    # --- ACCOUNTS (COA) ---
    def get_accounts(self): return self._execute_query("SELECT id, code, name, type, category, notes FROM accounts ORDER BY code", fetch=True)
    def add_account(self, code, name, t, cat, n=""): return self._execute_query("INSERT INTO accounts (code, name, type, category, notes) VALUES (?, ?, ?, ?, ?)", (code, name, t, cat, n), commit=True)
    def update_account(self, aid, code, name, t, cat, n=""): return self._execute_query("UPDATE accounts SET code=?, name=?, type=?, category=?, notes=? WHERE id=?", (code, name, t, cat, n, aid), commit=True)
    def delete_account(self, aid):
        # Prevent deletion if the account has transactions (to avoid orphaned journal details)
        in_use = self._execute_query("SELECT 1 FROM journal_details WHERE account_id=? LIMIT 1", (aid,), fetch=True)
        if in_use:
            return False
        return self._execute_query("DELETE FROM accounts WHERE id=?", (aid,), commit=True)

    # --- JOURNALS ---
    def get_journal_summaries(self): return self._execute_query("SELECT id, date, description, reference_no FROM journal_entries ORDER BY date DESC, id DESC", fetch=True)
    def get_journal_details(self, jid):
        h = self._execute_query("SELECT date, description, reference_no FROM journal_entries WHERE id=?", (jid,), fetch=True)
        d = self._execute_query("SELECT a.code, a.name, jd.debit, jd.credit, jd.cash_flow_activity, jd.account_id FROM journal_details jd JOIN accounts a ON jd.account_id=a.id WHERE jd.journal_id=? ORDER BY jd.id", (jid,), fetch=True)
        return {'header': h[0], 'details': d} if h else None
    def add_journal_entry(self, date, desc, ref, details):
        conn = self.get_connection(); cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO journal_entries (date, description, reference_no) VALUES (?, ?, ?)", (date, desc, ref))
            jid = cursor.lastrowid
            for d in details: cursor.execute("INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)", (jid, d['account_id'], d['debit'], d['credit'], d.get('cash_flow_activity')))
            conn.commit(); return True
        except: return False
        finally: conn.close()
    def update_journal_entry(self, jid, date, desc, ref, details):
        self._execute_query("UPDATE journal_entries SET date=?, description=?, reference_no=? WHERE id=?", (date, desc, ref, jid), commit=True)
        self._execute_query("DELETE FROM journal_details WHERE journal_id=?", (jid,), commit=True)
        for d in details: self._execute_query("INSERT INTO journal_details (journal_id, account_id, debit, credit, cash_flow_activity) VALUES (?, ?, ?, ?, ?)", (jid, d['account_id'], d['debit'], d['credit'], d.get('cash_flow_activity')), commit=True)
        return True
    def delete_journal_entry(self, jid):
        self._execute_query("DELETE FROM journal_details WHERE journal_id=?", (jid,), commit=True)
        self._execute_query("DELETE FROM journal_entries WHERE id=?", (jid,), commit=True)
        return True

    # --- REPORTS & SETTINGS ---
    def get_trial_balance(self):
        res = self._execute_query("SELECT a.id, a.code, a.name, a.type, a.category, SUM(COALESCE(jd.debit, 0)), SUM(COALESCE(jd.credit, 0)) FROM accounts a LEFT JOIN journal_details jd ON a.id = jd.account_id GROUP BY a.id", fetch=True)
        data = []
        for r in res:
            is_debit_normal = str(r[3]).lower() in ['asset', 'expense', 'aset', 'beban', 'harta', 'biaya']
            debit_sum = r[5] or 0
            credit_sum = r[6] or 0
            net_bal = debit_sum - credit_sum
            
            if is_debit_normal:
                debit_val = net_bal if net_bal > 0 else 0
                credit_val = abs(net_bal) if net_bal < 0 else 0
                balance_val = net_bal
            else:
                credit_val = abs(net_bal) if net_bal < 0 else 0
                debit_val = net_bal if net_bal > 0 else 0
                balance_val = -net_bal
                
            data.append({
                'id': r[0], 
                'code': r[1], 
                'name': r[2], 
                'type': r[3], 
                'category': r[4], 
                'debit': debit_val, 
                'credit': credit_val, 
                'balance': balance_val
            })
        return data
    def get_ledger_entries(self, aid): 
        res = self._execute_query("SELECT je.date, je.description, je.reference_no, jd.debit, jd.credit FROM journal_details jd JOIN journal_entries je ON jd.journal_id=je.id WHERE jd.account_id=? ORDER BY je.date", (aid,), fetch=True)
        return [{'date': r[0], 'description': r[1], 'reference_no': r[2], 'debit': r[3], 'credit': r[4]} for r in res] if res else []
    def get_annual_report_settings(self, year):
        res = self._execute_query(
            "SELECT year, vision, mission, program_summary, program_detail_edu, program_detail_social, organizational_structure, evaluation_constraints, future_plans FROM annual_report_settings WHERE year=?", 
            (year,), 
            fetch=True
        )
        if res and len(res) > 0:
            cols = ['year','vision','mission','program_summary','program_detail_edu','program_detail_social','organizational_structure','evaluation_constraints','future_plans']
            return dict(zip(cols, res[0]))
        return None

    def save_annual_report_settings(self, year, data):
        # Check if row for this year already exists
        res = self._execute_query("SELECT 1 FROM annual_report_settings WHERE year=?", (year,), fetch=True)
        if res:
            return self._execute_query(
                "UPDATE annual_report_settings SET vision=?, mission=?, program_summary=?, program_detail_edu=?, program_detail_social=?, organizational_structure=?, evaluation_constraints=?, future_plans=? WHERE year=?",
                (data['vision'], data['mission'], data['program_summary'], data['program_detail_edu'], data['program_detail_social'], data['organizational_structure'], data['evaluation_constraints'], data['future_plans'], year),
                commit=True
            )
        else:
            return self._execute_query(
                "INSERT INTO annual_report_settings (year, vision, mission, program_summary, program_detail_edu, program_detail_social, organizational_structure, evaluation_constraints, future_plans) VALUES (?,?,?,?,?,?,?,?,?)",
                (year, data['vision'], data['mission'], data['program_summary'], data['program_detail_edu'], data['program_detail_social'], data['organizational_structure'], data['evaluation_constraints'], data['future_plans']),
                commit=True
            )

    # --- RBAC, USERS & HELPERS ---
    def get_permissions_dict(self, role):
        if role == 'super_admin': return {p[2]: True for p in self.get_app_pages()}
        res = self._execute_query("SELECT p.route_name FROM role_permissions rp JOIN app_pages p ON rp.page_id = p.id WHERE rp.role=? AND rp.can_view=1", (role,), fetch=True)
        return {r[0]: True for r in res} if res else {}
    def get_app_pages(self): return self._execute_query("SELECT id, name, route_name, category FROM app_pages", fetch=True)
    def get_role_permissions(self, role): return self._execute_query("SELECT p.id, p.name, p.category, COALESCE(rp.can_view, 0), COALESCE(rp.can_edit, 0), COALESCE(rp.can_delete, 0) FROM app_pages p LEFT JOIN role_permissions rp ON p.id = rp.page_id AND rp.role = ? ORDER BY p.category, p.name", (role,), fetch=True)
    def update_role_permission(self, role, page_id, action, is_allowed):
        exists = self._execute_query("SELECT 1 FROM role_permissions WHERE role=? AND page_id=?", (role, page_id), fetch=True)
        if exists:
            return self._execute_query(f"UPDATE role_permissions SET {action}=? WHERE role=? AND page_id=?", (is_allowed, role, page_id), commit=True)
        else:
            can_v = is_allowed if action == 'can_view' else 0
            can_e = is_allowed if action == 'can_edit' else 0
            can_d = is_allowed if action == 'can_delete' else 0
            return self._execute_query("INSERT INTO role_permissions (role, page_id, can_view, can_edit, can_delete) VALUES (?, ?, ?, ?, ?)", (role, page_id, can_v, can_e, can_d), commit=True)
    def get_users(self): return self._execute_query("SELECT id, username, role FROM users ORDER BY role", fetch=True)
    def add_user(self, u, p, r):
        hashed_p = generate_password_hash(p)
        return self._execute_query("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, hashed_p, r), commit=True)
    def update_user(self, uid, u, p, r):
        if p:
            hashed_p = generate_password_hash(p)
            return self._execute_query("UPDATE users SET username=?, password=?, role=? WHERE id=?", (u, hashed_p, r, uid), commit=True)
        return self._execute_query("UPDATE users SET username=?, role=? WHERE id=?", (u, r, uid), commit=True)
    def change_password(self, uid, new_p):
        hashed_p = generate_password_hash(new_p)
        return self._execute_query("UPDATE users SET password=? WHERE id=?", (hashed_p, uid), commit=True)
    def delete_user(self, uid):
        return self._execute_query("DELETE FROM users WHERE id=?", (uid,), commit=True)
    def verify_login(self, u, p):
        res = self._execute_query("SELECT id, username, role, password FROM users WHERE username=?", (u,), fetch=True)
        return {'id': res[0][0], 'username': res[0][1], 'role': res[0][2]} if res and (check_password_hash(res[0][3], p) or res[0][3] == p) else None
    def get_foundation_profile(self):
        res = self._execute_query("SELECT name, address, leader_name, pembina_name, pengawas_name, logo_path, phone, email FROM foundation_profile WHERE id=1", fetch=True)
        if res:
            r = res[0]
            return {
                'name': r[0] or 'Yayasan ISAK 35',
                'address': r[1] or '',
                'leader_name': r[2] or '',
                'pembina_name': r[3] or '',
                'pengawas_name': r[4] or '',
                'logo_path': r[5] or '',
                'phone': r[6] or '',
                'email': r[7] or ''
            }
        return {
            'name': 'Yayasan ISAK 35',
            'address': '',
            'leader_name': '',
            'pembina_name': '',
            'pengawas_name': '',
            'logo_path': '',
            'phone': '',
            'email': ''
        }
    def update_foundation_profile(self, name, addr, leader, pembina, pengawas, phone, email):
        return self._execute_query("UPDATE foundation_profile SET name=?, address=?, leader_name=?, pembina_name=?, pengawas_name=?, phone=?, email=? WHERE id=1", (name, addr, leader, pembina, pengawas, phone, email), commit=True)

    # --- KATEGORI ARUS KAS ---
    def get_cash_flow_categories(self): return self._execute_query("SELECT id, name, main_category FROM cash_flow_categories ORDER BY main_category, name", fetch=True)
    def add_cash_flow_category(self, name, main_cat):
        return self._execute_query("INSERT OR IGNORE INTO cash_flow_categories (name, main_category) VALUES (?, ?)" if self.db_type == "sqlite" else "INSERT IGNORE INTO cash_flow_categories (name, main_category) VALUES (?, ?)", (name, main_cat), commit=True)
    def update_cash_flow_category(self, cid, name, main_cat):
        return self._execute_query("UPDATE cash_flow_categories SET name=?, main_category=? WHERE id=?", (name, main_cat, cid), commit=True)
    def delete_cash_flow_category(self, name):
        return self._execute_query("DELETE FROM cash_flow_categories WHERE name=? OR id=?", (name, name), commit=True)

    # --- DONORS ---
    def get_donors(self): return self._execute_query("SELECT id, name, phone, address, donor_type, description FROM donors ORDER BY name", fetch=True)
    def add_donor(self, name, phone, address, t, desc):
        return self._execute_query("INSERT INTO donors (name, phone, address, donor_type, description) VALUES (?, ?, ?, ?, ?)", (name, phone, address, t, desc), commit=True)
    def update_donor(self, did, name, phone, address, t, desc):
        return self._execute_query("UPDATE donors SET name=?, phone=?, address=?, donor_type=?, description=? WHERE id=?", (name, phone, address, t, desc, did), commit=True)
    def delete_donor(self, did):
        return self._execute_query("DELETE FROM donors WHERE id=?", (did,), commit=True)

    # --- ASSETS INVENTORY ---
    def get_assets_inventory(self): return self._execute_query("SELECT id, date, code, name, location, estimated_value, quantity, description FROM assets_inventory ORDER BY date DESC", fetch=True)
    def add_asset_inventory(self, date, code, name, loc, val, qty, desc):
        return self._execute_query("INSERT INTO assets_inventory (date, code, name, location, estimated_value, quantity, description) VALUES (?, ?, ?, ?, ?, ?, ?)", (date, code, name, loc, val, qty, desc), commit=True)
    def update_asset_inventory(self, aid, date, code, name, loc, val, qty, desc):
        return self._execute_query("UPDATE assets_inventory SET date=?, code=?, name=?, location=?, estimated_value=?, quantity=?, description=? WHERE id=?", (date, code, name, loc, val, qty, desc, aid), commit=True)
    def delete_asset_inventory(self, aid):
        return self._execute_query("DELETE FROM assets_inventory WHERE id=?", (aid,), commit=True)

    def get_journal_data_for_export(self): return self._execute_query("SELECT je.date, je.description, je.reference_no, a.code, a.name, jd.debit, jd.credit, jd.cash_flow_activity FROM journal_details jd JOIN journal_entries je ON jd.journal_id=je.id JOIN accounts a ON jd.account_id=a.id", fetch=True)

    # --- CALK NOTES ---
    def get_calk_notes(self):
        return self._execute_query("SELECT id, section_title, content, updated_at FROM calk_notes ORDER BY id", fetch=True)
    def update_calk_note(self, note_id, content):
        return self._execute_query("UPDATE calk_notes SET content=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (content, note_id), commit=True)