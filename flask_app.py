from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash, send_file
from src.database_manager import DatabaseManager
from src.report_generator import ReportGenerator
import os
from functools import wraps
from datetime import datetime
import tempfile

# SETTING TEMPLATE: Mengarah langsung ke folder 'web'
app = Flask(__name__, 
            template_folder='templates/web',
            static_folder='static')
app.secret_key = 'isak35_secret_key'

# Inisialisasi Database
base_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(base_dir, 'database', 'foundation_finance.db')
if not os.path.exists(os.path.dirname(db_path)):
    os.makedirs(os.path.dirname(db_path))

db = DatabaseManager(db_path)
rg = ReportGenerator(db)
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
        u = request.form.get('username'); p = request.form.get('password')
        user = db.verify_login(u, p)
        if user: session['user'] = user; return redirect(url_for('dashboard'))
        flash('Username/Password salah!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None); return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    profile = db.get_foundation_profile()
    try:
        accounts = db.get_accounts()
        journals = db.get_journal_summaries()
        donors = db.get_donors()
        tb = db.get_trial_balance()
        total_asset = sum(x['balance'] for x in tb if x['type'] == 'Asset') - sum(x['balance'] for x in tb if x['type'] == 'Asset (Contra)')
        total_rev = sum(x['balance'] for x in tb if x['type'] == 'Revenue')
        total_exp = sum(x['balance'] for x in tb if x['type'] == 'Expense')
        return render_template('dashboard.html', profile=profile, total_accounts=len(accounts), total_journals=len(journals), total_donors=len(donors), total_asset=total_asset, total_revenue=total_rev, total_expense=total_exp, surplus=total_rev - total_exp)
    except: return render_template('dashboard.html', profile=profile, total_accounts=0, total_journals=0, total_donors=0, total_asset=0, total_revenue=0, total_expense=0, surplus=0)

# --- COA ---
@app.route('/coa')
@login_required
def coa_page():
    return render_template('coa.html', accounts=db.get_accounts())

@app.route('/coa/add', methods=['GET', 'POST'])
@login_required
def add_coa():
    if request.method == 'POST':
        db.add_account(request.form.get('code'), request.form.get('name'), request.form.get('type'), request.form.get('category'), request.form.get('notes'))
        flash('Akun ditambahkan!', 'success'); return redirect(url_for('coa_page'))
    return render_template('coa_form.html')

@app.route('/coa/edit/<int:aid>', methods=['GET', 'POST'])
@login_required
def edit_coa(aid):
    if request.method == 'POST':
        db.update_account(aid, request.form.get('code'), request.form.get('name'), request.form.get('type'), request.form.get('category'), request.form.get('notes'))
        flash('Akun diperbarui!', 'success'); return redirect(url_for('coa_page'))
    accs = db.get_accounts()
    acc = next((x for x in accs if x[0] == aid), None)
    return render_template('coa_form.html', account=acc)

@app.route('/coa/delete/<int:aid>')
@login_required
def delete_coa(aid):
    db.delete_account(aid); flash('Akun dihapus.', 'success'); return redirect(url_for('coa_page'))

# --- JOURNALS ---
@app.route('/journals/')
@app.route('/journals')
@login_required
def journals_page():
    return render_template('journals.html', journals=db.get_journal_summaries())

@app.route('/journals/add', methods=['GET', 'POST'])
@login_required
def add_journal():
    if request.method == 'POST':
        try:
            date = request.form.get('date'); ref = request.form.get('ref_no'); desc = request.form.get('description')
            ids = request.form.getlist('account_id[]'); dbt = request.form.getlist('debit[]'); crd = request.form.getlist('credit[]'); cf = request.form.getlist('cf_activity[]')
            dets = []
            for i in range(len(ids)):
                if ids[i]: dets.append({'account_id': int(ids[i]), 'debit': float(dbt[i] or 0), 'credit': float(crd[i] or 0), 'cash_flow_activity': cf[i] if i < len(cf) else None})
            if db.add_journal_entry(date, desc, ref, dets): flash('Jurnal disimpan!', 'success'); return redirect(url_for('journals_page'))
        except Exception as e: flash(f'Error: {e}', 'danger')
    return render_template('journal_form.html', accounts=db.get_accounts(), cf_cats=db.get_cash_flow_categories())

@app.route('/journals/edit/<int:jid>', methods=['GET', 'POST'])
@login_required
def edit_journal(jid):
    if request.method == 'POST':
        try:
            date = request.form.get('date'); ref = request.form.get('ref_no'); desc = request.form.get('description')
            ids = request.form.getlist('account_id[]'); dbt = request.form.getlist('debit[]'); crd = request.form.getlist('credit[]'); cf = request.form.getlist('cf_activity[]')
            dets = []
            for i in range(len(ids)):
                if ids[i]: dets.append({'account_id': int(ids[i]), 'debit': float(dbt[i] or 0), 'credit': float(crd[i] or 0), 'cash_flow_activity': cf[i] if i < len(cf) else None})
            if db.update_journal_entry(jid, date, desc, ref, dets): flash('Jurnal diperbarui!', 'success'); return redirect(url_for('journals_page'))
        except Exception as e: flash(f'Error: {e}', 'danger')
    data = db.get_journal_details(jid)
    return render_template('journal_form.html', data=data, journal_id=jid, accounts=db.get_accounts(), cf_cats=db.get_cash_flow_categories())

@app.route('/journals/<int:jid>')
@login_required
def journal_detail(jid):
    data = db.get_journal_details(jid)
    return render_template('journal_detail.html', data=data) if data else ("Bukan Jurnal", 404)

@app.route('/journals/delete/<int:jid>')
@login_required
def delete_journal(jid):
    db.delete_journal_entry(jid); flash('Jurnal dihapus.', 'success'); return redirect(url_for('journals_page'))

# --- ASSETS ---
@app.route('/assets')
@login_required
def assets_page():
    return render_template('assets.html', assets=db.get_assets_inventory())

@app.route('/assets/add', methods=['GET', 'POST'])
@login_required
def add_asset():
    if request.method == 'POST':
        db.add_asset_inventory(request.form.get('date'), request.form.get('code'), request.form.get('name'), request.form.get('location'), float(request.form.get('estimated_value') or 0), int(request.form.get('quantity') or 1), request.form.get('description'))
        flash('Aset ditambahkan!', 'success'); return redirect(url_for('assets_page'))
    return render_template('asset_form.html')

@app.route('/assets/edit/<int:aid>', methods=['GET', 'POST'])
@login_required
def edit_asset(aid):
    if request.method == 'POST':
        db.update_asset_inventory(aid, request.form.get('date'), request.form.get('code'), request.form.get('name'), request.form.get('location'), float(request.form.get('estimated_value') or 0), int(request.form.get('quantity') or 1), request.form.get('description'))
        flash('Aset diperbarui!', 'success'); return redirect(url_for('assets_page'))
    assets = db.get_assets_inventory()
    asset = next((x for x in assets if x[0] == aid), None)
    return render_template('asset_form.html', asset=asset)

@app.route('/assets/delete/<int:aid>')
@login_required
def delete_asset(aid):
    db.delete_asset_inventory(aid); flash('Aset dihapus.', 'success'); return redirect(url_for('assets_page'))

# --- DONORS ---
@app.route('/donors')
@login_required
def donors_page():
    return render_template('donors.html', donors=db.get_donors())

@app.route('/donors/add', methods=['GET', 'POST'])
@login_required
def add_donor():
    if request.method == 'POST':
        db.add_donor(request.form.get('name'), request.form.get('phone'), request.form.get('address'), request.form.get('type'), request.form.get('description'))
        flash('Donatur ditambahkan!', 'success'); return redirect(url_for('donors_page'))
    return render_template('donor_form.html')

@app.route('/donors/edit/<int:did>', methods=['GET', 'POST'])
@login_required
def edit_donor(did):
    if request.method == 'POST':
        db.update_donor(did, request.form.get('name'), request.form.get('phone'), request.form.get('address'), request.form.get('type'), request.form.get('description'))
        flash('Donatur diperbarui!', 'success'); return redirect(url_for('donors_page'))
    donors = db.get_donors()
    donor = next((x for x in donors if x[0] == did), None)
    return render_template('donor_form.html', donor=donor)

@app.route('/donors/delete/<int:did>')
@login_required
def delete_donor(did):
    db.delete_donor(did); flash('Donatur dihapus.', 'success'); return redirect(url_for('donors_page'))

# --- LEDGER ---
@app.route('/ledger')
@login_required
def ledger_page():
    return render_template('ledger_select.html', accounts=db.get_accounts())

@app.route('/ledger/<int:aid>')
@login_required
def ledger_detail(aid):
    accs = db.get_accounts()
    curr = next((x for x in accs if x[0] == aid), None)
    if not curr: return "Akun tidak ada", 404
    ents = db.get_ledger_entries(aid)
    bal = 0; res = []
    for e in ents:
        d = e['debit'] or 0; c = e['credit'] or 0
        if curr[3] in ['Asset', 'Expense']: bal += (d - c)
        else: bal += (c - d)
        e['running_balance'] = bal; res.append(e)
    return render_template('ledger_detail.html', account=curr, entries=res, final_balance=bal)

# --- REPORTS ---
@app.route('/reports/trial-balance')
@login_required
def trial_balance():
    data = db.get_trial_balance()
    totals = {'debit': sum(x['debit'] for x in data), 'credit': sum(x['credit'] for x in data)}
    return render_template('report_trial_balance.html', data=data, totals=totals)

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

@app.route('/export/excel')
@login_required
def export_excel():
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        file_path = tmp.name
    if rg.export_all_reports_to_excel(file_path):
        return send_file(file_path, as_attachment=True, download_name=f"Laporan_ISAK35_{datetime.now().strftime('%Y%m%d')}.xlsx")
    return "Gagal", 500

@app.route('/api/dashboard-stats')
@login_required
def dashboard_stats_api():
    try:
        data = db.get_journal_data_for_export()
        if not data: return jsonify({"labels": [], "income": [], "expense": []})
        stats = {}
        accs = {a[1]: a[3] for a in db.get_accounts()}
        for r in data:
            m = r['Tanggal'][:7]
            if m not in stats: stats[m] = {'i': 0, 'e': 0}
            t = accs.get(r['Kode Akun'])
            if t == 'Revenue': stats[m]['i'] += (r['Kredit'] - r['Debit'])
            elif t == 'Expense': stats[m]['e'] += (r['Debit'] - r['Kredit'])
        labels = sorted(stats.keys())[-6:]
        return jsonify({"labels": labels, "income": [stats[l]['i'] for l in labels], "expense": [stats[l]['e'] for l in labels]})
    except: return jsonify({"labels": [], "income": [], "expense": []})

# --- SYNC ---
@app.route('/api/sync/pull', methods=['GET'])
def api_pull():
    if request.headers.get('Authorization') != SYNC_TOKEN: return jsonify({"error": "No"}), 401
    return jsonify(db.generate_full_backup())

@app.route('/api/sync/push', methods=['POST'])
def api_push():
    if request.headers.get('Authorization') != SYNC_TOKEN: return jsonify({"error": "No"}), 401
    ok, msg = db.restore_full_backup(request.json)
    return jsonify({"status": "success"}) if ok else jsonify({"error": msg}), 500

if __name__ == '__main__':
    app.run(debug=True)
