import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
from fpdf import FPDF

class ReportGenerator:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_trial_balance_report(self):
        data = self.db.get_trial_balance()
        if not data: return []
        
        total_debit = sum(x.get('debit', 0) for x in data)
        total_credit = sum(x.get('credit', 0) for x in data)
        data.append({'code': '', 'name': 'TOTAL', 'debit': total_debit, 'credit': total_credit})
        return data

    def get_isak35_financial_position(self):
        data = self.db.get_trial_balance()
        if not data: return {}

        def is_type_exact(actual, target_list):
            if not actual: return False
            return str(actual).lower().strip() in [t.lower() for t in target_list]

        def is_type_contains(actual, target_list):
            if not actual: return False
            return any(t in str(actual).lower().strip() for t in target_list)

        # Filter ASET
        assets = [x for x in data if is_type_exact(x.get('type'), ['asset', 'aset', 'harta'])]
        contra_assets = [x for x in data if is_type_contains(x.get('type'), ['contra', 'kontra', 'akumulasi'])]
        total_assets = sum(x.get('balance', 0) for x in assets) - sum(x.get('balance', 0) for x in contra_assets)
        
        # LIABILITAS
        liabilities = [x for x in data if is_type_exact(x.get('type'), ['liability', 'liabilitas', 'hutang', 'kewajiban'])]
        total_liabilities = sum(x.get('balance', 0) for x in liabilities)
        
        # ASET NETO (Ekuitas)
        net_assets_without = sum(x.get('balance', 0) for x in data if is_type_contains(x.get('type'), ['asset net', 'aset neto']) and str(x.get('category','')).lower() == 'tanpa pembatasan')
        net_assets_with = sum(x.get('balance', 0) for x in data if is_type_contains(x.get('type'), ['asset net', 'aset neto']) and str(x.get('category','')).lower() == 'dengan pembatasan')
        
        # PENDAPATAN & BEBAN
        rev_without = sum(x.get('balance', 0) for x in data if is_type_exact(x.get('type'), ['revenue', 'pendapatan', 'penerimaan']) and str(x.get('category','')).lower() == 'tanpa pembatasan')
        rev_with = sum(x.get('balance', 0) for x in data if is_type_exact(x.get('type'), ['revenue', 'pendapatan', 'penerimaan']) and str(x.get('category','')).lower() == 'dengan pembatasan')
        
        exp_without = sum(x.get('balance', 0) for x in data if is_type_exact(x.get('type'), ['expense', 'beban', 'biaya', 'pengeluaran']) and str(x.get('category','')).lower() == 'tanpa pembatasan')
        exp_with = sum(x.get('balance', 0) for x in data if is_type_exact(x.get('type'), ['expense', 'beban', 'biaya', 'pengeluaran']) and str(x.get('category','')).lower() == 'dengan pembatasan')
        
        surplus_without = rev_without - exp_without
        surplus_with = rev_with - exp_with
        
        final_net_without = net_assets_without + surplus_without
        final_net_with = net_assets_with + surplus_with
        
        return {
            'assets': [{'name': x['name'], 'balance': x['balance']} for x in assets + contra_assets],
            'total_assets': total_assets,
            'liabilities': [{'name': x['name'], 'balance': x['balance']} for x in liabilities],
            'total_liabilities': total_liabilities,
            'net_assets_without': final_net_without,
            'net_assets_with': final_net_with,
            'total_net_assets': final_net_without + final_net_with,
            'total_liabilities_and_net_assets': total_liabilities + final_net_without + final_net_with,
            'surplus_without': surplus_without,
            'surplus_with': surplus_with
        }

    def get_comprehensive_income(self):
        data = self.db.get_trial_balance()
        if not data: return {}
            
        def is_type_exact(actual, targets):
            if not actual: return False
            return str(actual).lower().strip() in [t.lower() for t in targets]

        rev = [x for x in data if is_type_exact(x.get('type'), ['revenue', 'pendapatan', 'penerimaan'])]
        exp = [x for x in data if is_type_exact(x.get('type'), ['expense', 'beban', 'biaya', 'pengeluaran'])]
        
        rev_without = [x for x in rev if str(x.get('category','')).lower() == 'tanpa pembatasan']
        rev_with = [x for x in rev if str(x.get('category','')).lower() == 'dengan pembatasan']
        
        total_rev = sum(x.get('balance', 0) for x in rev)
        total_exp = sum(x.get('balance', 0) for x in exp)
        
        return {
            'revenue_without': rev_without,
            'revenue_with': rev_with,
            'expenses': exp,
            'total_revenue': total_rev,
            'total_expenses': total_exp
        }

    def get_statement_of_activities(self):
        data = self.get_comprehensive_income()
        if not data: return {'revenue': [], 'total_rev': 0, 'expenses': [], 'total_exp': 0, 'total_change': 0}
        return {
            'revenue': data['revenue_without'] + data['revenue_with'],
            'total_rev': data['total_revenue'],
            'expenses': data['expenses'],
            'total_exp': data['total_expenses'],
            'total_change': data['total_revenue'] - data['total_expenses']
        }

    def get_changes_in_net_assets_report(self):
        pos = self.get_isak35_financial_position()
        akt = self.get_statement_of_activities()
        if not pos or not akt: return []
        return [
            {"description": "Aset Neto Awal Periode", "without_restriction": pos['net_assets_without'] - pos['surplus_without'], "with_restriction": pos['net_assets_with'] - pos['surplus_with'], "total": pos['total_net_assets'] - akt['total_change']},
            {"description": "Perubahan Periode Berjalan", "without_restriction": pos['surplus_without'], "with_restriction": pos['surplus_with'], "total": akt['total_change']},
            {"description": "Aset Neto Akhir Periode", "without_restriction": pos['net_assets_without'], "with_restriction": pos['net_assets_with'], "total": pos['total_net_assets']}
        ]

    def get_cash_flow_report(self):
        query = "SELECT jd.cash_flow_activity as activity, jd.debit, jd.credit, cfc.main_category FROM journal_details jd JOIN cash_flow_categories cfc ON jd.cash_flow_activity = cfc.name"
        conn = self.db.get_connection(); cursor = conn.cursor()
        cursor.execute(query); rows = cursor.fetchall(); conn.close()
        
        report_data = []
        if rows:
            # Manual aggregation
            summary = {} # (main_category, activity) -> total_amount
            for row in rows:
                key = (row[3], row[0])
                amount = float(row[1] or 0) - float(row[2] or 0)
                summary[key] = summary.get(key, 0) + amount
            
            total_all = 0
            for cat in ["ARUS KAS DARI AKTIVITAS OPERASI", "ARUS KAS DARI AKTIVITAS INVESTASI", "ARUS KAS DARI AKTIVITAS PENDANAAN"]:
                cat_total = 0
                cat_items = {k[1]: v for k, v in summary.items() if k[0] == cat}
                
                report_data.append({"Keterangan": cat, "Jumlah (Rp)": ""})
                for act, amt in cat_items.items():
                    report_data.append({"Keterangan": f"  {act}", "Jumlah (Rp)": amt})
                    cat_total += amt
                
                total_all += cat_total
                report_data.append({"Keterangan": f"Total {cat}", "Jumlah (Rp)": cat_total})
                report_data.append({"Keterangan": "", "Jumlah (Rp)": ""})
            
            report_data.append({"Keterangan": "KENAIKAN (PENURUNAN) BERSIH KAS", "Jumlah (Rp)": total_all})
        return {"report_data": report_data}

    def export_journals_to_excel(self, file_path):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Jurnal Umum"
            
            # Header
            headers = ['Tanggal', 'Keterangan', 'Referensi', 'Kode Akun', 'Nama Akun', 'Debit', 'Kredit', 'Aktivitas Arus Kas']
            ws.append(headers)
            
            # Data
            data = self.db.get_journal_data_for_export()
            for r in data:
                ws.append([
                    r.get('Tanggal'),
                    r.get('Keterangan'),
                    r.get('Referensi'),
                    r.get('Kode Akun'),
                    r.get('Nama Akun'),
                    r.get('Debit'),
                    r.get('Kredit'),
                    r.get('Aktivitas Arus Kas')
                ])
            
            # Styling sederhana
            for cell in ws[1]:
                cell.font = Font(bold=True)
                cell.alignment = Alignment(horizontal='center')

            wb.save(file_path)
            return True
        except Exception as e:
            print(f"Export Journal Error: {e}")
            return False

    def export_all_reports_to_excel(self, file_path):
        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Posisi Keuangan"
            pos = self.get_isak35_financial_position()
            
            ws.append(["Nama Akun", "Saldo"])
            for item in pos.get('assets', []):
                ws.append([item['name'], item['balance']])
            
            wb.save(file_path)
            return True
        except: return False

    def export_annual_report_to_pdf(self, file_path, year):
        try:
            settings = self.db.get_annual_report_settings(year)
            if not settings: return False
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, f"Laporan Tahunan {year}", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", '', 12)
            
            sections = [
                ("Visi", settings.get('vision', '')),
                ("Misi", settings.get('mission', '')),
                ("Ringkasan Program", settings.get('program_summary', '')),
                ("Program Pendidikan", settings.get('program_detail_edu', '')),
                ("Program Sosial", settings.get('program_detail_social', '')),
                ("Struktur Organisasi", settings.get('organizational_structure', '')),
                ("Kendala Evaluasi", settings.get('evaluation_constraints', '')),
                ("Rencana Masa Depan", settings.get('future_plans', ''))
            ]
            
            for title, content in sections:
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, title, ln=True)
                pdf.set_font("Arial", '', 11)
                pdf.multi_cell(0, 7, str(content))
                pdf.ln(5)
            
            pdf.output(file_path)
            return True
        except Exception as e:
            print(f"PDF Error: {e}")
            return False
