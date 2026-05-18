from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash, send_file
from src.database_manager import DatabaseManager
from src.report_generator import ReportGenerator
import os
import json
from functools import wraps
from datetime import datetime
import pandas as pd
import tempfile

app = Flask(__name__, 
            template_folder='templates/web',
            static_folder='static')
app.secret_key = 'isak35_secret_key'

# Inisialisasi Database Manager & Report Generator
# Pada PythonAnywhere, pastikan path database absolut
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'database', 'foundation_finance.db')
if not os.path.exists(os.path.dirname(db_path)):
    os.makedirs(os.path.dirname(db_path))

db = DatabaseManager(db_path)
rg = ReportGenerator(db)

# Token Keamanan (Wajib disamakan dengan di Desktop)
SYNC_TOKEN = "qudwah_secret_token_2026"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_db_info():
    return dict(db_type=db.db_type, now=datetime.now().strftime('%Y-%m-%d'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.verify_login(username, password)
        if user:
            session['user'] = user
            return redirect(url_for('dashboard'))
        else:
            flash('Username atau Password salah!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """Halaman Dashboard Utama"""
    profile = db.get_foundation_profile()
    try:
        accounts = db.get_accounts()
        total_accounts = len(accounts)
        journals = db.get_journal_summaries()
        total_journals = len(journals)
        donors = db.get_donors()
        total_donors = len(donors)
        
        df_tb = db.get_trial_balance()
        total_asset = 0; total_rev = 0; total_exp = 0
        if not df_tb.empty:
            total_asset = df_tb[df_tb['type'] == 'Asset']['balance'].sum() - df_tb[df_tb['type'] == 'Asset (Contra)']['balance'].sum()
            total_rev = df_tb[df_tb['type'] == 'Revenue']['balance'].sum()
            total_exp = df_tb[df_tb['type'] == 'Expense']['balance'].sum()
            
    except Exception as e:
        print(f"Error fetching stats: {e}")
        total_accounts = total_journals = total_donors = total_asset = total_rev = total_exp = 0

    return render_template('dashboard.html', 
                           profile=profile,
                           total_accounts=total_accounts,
                           total_journals=total_journals,
                           total_donors=total_donors,
                           total_asset=total_asset,
                           total_revenue=total_rev,
                           total_expense=total_exp,
                           surplus=total_rev - total_exp)

@app.route('/api/dashboard-stats')
@login_required
def dashboard_stats_api():
    """API untuk grafik dashboard"""
    try:
        df_journals = db.get_journal_data_for_export()
        if df_journals.empty: return jsonify({"labels": [], "income": [], "expense": []})
        df_journals['Tanggal'] = pd.to_datetime(df_journals['Tanggal'])
        df_journals['Bulan'] = df_journals['Tanggal'].dt.strftime('%Y-%m')
        months = sorted(df_journals['Bulan'].unique())[-6:]
        labels = []; income = []; expense = []
        accounts = db.get_accounts()
        acc_types = {acc[1]: acc[3] for acc in accounts}
        for m in months:
            labels.append(m); df_month = df_journals[df_journals['Bulan'] == m]
            inc_val = 0; exp_val = 0
            for _, row in df_month.iterrows():
                a_type = acc_types.get(row['Kode Akun'])
                if a_type == 'Revenue': inc_val += (row['Kredit'] - row['Debit'])
                elif a_type == 'Expense': exp_val += (row['Debit'] - row['Kredit'])
            income.append(float(inc_val)); expense.append(float(exp_val))
        return jsonify({"labels": labels, "income": income, "expense": expense})
    except Exception as e: return jsonify({"labels": [], "income": [], "expense": []})

# --- CRUD ROUTES (COA, Journals, Assets, Donors) ---
@app.route('/coa')
@login_required
def coa_page():
    return render_template('coa.html', accounts=db.get_accounts())

@app.route('/coa/add', methods=['GET', 'POST'])
@login_required
def add_coa():
    if request.method == 'POST':
        try:
            db.add_account(request.form.get('code'), request.form.get('name'), request.form.get('type'), request.form.get('category'), request.form.get('notes'))
            flash(f"Akun berhasil ditambahkan!", 'success')
            return redirect(url_for('coa_page'))
        except Exception as e: flash(f'Error: {e}', 'danger')
    return render_template('coa_form.html')

@app.route('/journals')
@login_required
def journals_page():
    return render_template('journals.html', journals=db.get_journal_summaries())

@app.route('/journals/add', methods=['GET', 'POST'])
@login_required
def add_journal():
    if request.method == 'POST':
        try:
            date = request.form.get('date'); ref_no = request.form.get('ref_no'); desc = request.form.get('description')
            account_ids = request.form.getlist('account_id[]'); debits = request.form.getlist('debit[]'); credits = request.form.getlist('credit[]'); cf_activities = request.form.getlist('cf_activity[]')
            details = []
            for i in range(len(account_ids)):
                if account_ids[i]: details.append({'account_id': int(account_ids[i]), 'debit': float(debits[i] or 0), 'credit': float(credits[i] or 0), 'cash_flow_activity': cf_activities[i] if i < len(cf_activities) else None})
            if db.add_journal_entry(date, desc, ref_no, details): flash('Jurnal berhasil disimpan!', 'success'); return redirect(url_for('journals_page'))
            else: flash('Gagal menyimpan jurnal.', 'danger')
        except Exception as e: flash(f'Error: {e}', 'danger')
    return render_template('journal_form.html', accounts=db.get_accounts(), cf_cats=db.get_cash_flow_categories())

# --- REPORTS ---
@app.route('/reports/trial-balance')
@login_required
def trial_balance():
    df = db.get_trial_balance(); totals = {'debit': df['debit'].sum(), 'credit': df['credit'].sum()}
    return render_template('report_trial_balance.html', data=df.to_dict('records'), totals=totals)

@app.route('/reports/activities')
@login_required
def report_activities():
    return render_template('report_activities.html', data=rg.get_statement_of_activities())

@app.route('/reports/position')
@login_required
def report_position():
    return render_template('report_position.html', data=rg.get_isak35_financial_position())

@app.route('/reports/cash-flow')
@login_required
def report_cash_flow():
    return render_template('report_cash_flow.html', data=rg.get_cash_flow_report()['report_data'])

# --- API SINKRONISASI ---

@app.route('/api/sync/pull', methods=['GET'])
def api_pull():
    """Mengirim seluruh data database ke Desktop (JSON)."""
    token = request.headers.get('Authorization')
    if token != SYNC_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify(db.generate_full_backup())

@app.route('/api/sync/push', methods=['POST'])
def api_push():
    """Menerima data dari Desktop dan mengganti database Web."""
    token = request.headers.get('Authorization')
    if token != SYNC_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    sync_data = request.json
    if not sync_data: return jsonify({"error": "No data"}), 400
    ok, msg = db.restore_full_backup(sync_data)
    if ok: return jsonify({"status": "success"})
    return jsonify({"error": msg}), 500

if __name__ == '__main__':
    app.run(debug=True)
