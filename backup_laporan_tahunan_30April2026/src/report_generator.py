import pandas as pd
import sqlite3
import os
from .database_manager import DatabaseManager

class ReportGenerator:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_isak35_financial_position(self):
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)

        def filter_category(d, cat_type):
            if cat_type == 'without':
                return d[d['category'].str.lower() == 'tanpa pembatasan']
            elif cat_type == 'with':
                return d[d['category'].str.lower() == 'dengan pembatasan']
            return pd.DataFrame()

        assets_df = df[df['type'] == 'Asset']
        contra_assets_df = df[df['type'] == 'Asset (Contra)']
        total_assets = assets_df['balance'].sum() - contra_assets_df['balance'].sum()

        liabilities = df[df['type'] == 'Liability'][['code', 'name', 'balance']]
        total_liabilities = liabilities['balance'].sum()

        net_assets_without_initial = filter_category(df[df['type'] == 'Asset Net'], 'without')['balance'].sum()
        net_assets_with_initial = filter_category(df[df['type'] == 'Asset Net'], 'with')['balance'].sum()

        surplus_without = filter_category(df[df['type'] == 'Revenue'], 'without')['balance'].sum() - df[(df['type'] == 'Expense')]['balance'].sum()
        surplus_with = filter_category(df[df['type'] == 'Revenue'], 'with')['balance'].sum()

        final_net_without = net_assets_without_initial + surplus_without
        final_net_with = net_assets_with_initial + surplus_with
        total_net_assets = final_net_without + final_net_with

        assets_for_display = pd.concat([assets_df[['code', 'name', 'balance']], contra_assets_df[['code', 'name', 'balance']]]).sort_values(by='code')

        return {
            'assets': assets_for_display.to_dict('records'),
            'total_assets': total_assets,
            'liabilities': liabilities.to_dict('records'),
            'total_liabilities': total_liabilities,
            'net_assets_without': final_net_without,
            'net_assets_with': final_net_with,
            'total_net_assets': total_net_assets,
            'total_liabilities_and_net_assets': total_liabilities + total_net_assets
        }

    def get_comprehensive_income(self):
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)

        def filter_category(d, cat_type):
            if cat_type == 'without': return d[d['category'].str.lower() == 'tanpa pembatasan']
            elif cat_type == 'with': return d[d['category'].str.lower() == 'dengan pembatasan']
            return pd.DataFrame()

        rev_without = filter_category(df[df['type'] == 'Revenue'], 'without')
        rev_with = filter_category(df[df['type'] == 'Revenue'], 'with')
        expenses = df[df['type'] == 'Expense']

        return {
            'revenue_without': rev_without.to_dict('records'),
            'revenue_with': rev_with.to_dict('records'),
            'expenses': expenses.to_dict('records'),
            'total_revenue': rev_without['balance'].sum() + rev_with['balance'].sum(),
            'total_expenses': expenses['balance'].sum()
        }

    def get_trial_balance_report(self):
        df = self.db.get_trial_balance()
        df['debit'] = df['debit'].fillna(0)
        df['credit'] = df['credit'].fillna(0)
        
        total_debit = df['debit'].sum()
        total_credit = df['credit'].sum()
        
        records = df.to_dict('records')
        
        # Tambahkan baris TOTAL
        records.append({
            'code': '',
            'name': 'TOTAL',
            'debit': total_debit,
            'credit': total_credit
        })
        
        # Tambahkan info Balance/Unbalanced untuk visual tambahan di UI jika perlu
        # Namun untuk saat ini kita ikuti struktur yang diharapkan UI
        
        return records

    def get_statement_of_activities(self):
        data = self.get_comprehensive_income()
        rev_without_df = pd.DataFrame(data['revenue_without'])
        rev_with_df = pd.DataFrame(data['revenue_with'])
        
        rev_combined = []
        all_rev_names = set(rev_without_df['name'].tolist() if not rev_without_df.empty else []) | \
                          set(rev_with_df['name'].tolist() if not rev_with_df.empty else [])
        
        for name in all_rev_names:
            wout = rev_without_df[rev_without_df['name'] == name]['balance'].sum() if not rev_without_df.empty else 0
            with_r = rev_with_df[rev_with_df['name'] == name]['balance'].sum() if not rev_with_df.empty else 0
            rev_combined.append({'name': name, 'without_restriction': wout, 'with_restriction': with_r, 'total': wout + with_r})

        exp_df = pd.DataFrame(data['expenses'])
        total_rev_without = rev_without_df['balance'].sum() if not rev_without_df.empty else 0
        total_rev_with = rev_with_df['balance'].sum() if not rev_with_df.empty else 0
        total_exp = exp_df['balance'].sum() if not exp_df.empty else 0

        return {
            'revenue': pd.DataFrame(rev_combined),
            'expense': exp_df,
            'total_rev_without': total_rev_without,
            'total_rev_with': total_rev_with,
            'total_rev': total_rev_without + total_rev_with,
            'total_exp': total_exp,
            'change_without': total_rev_without - total_exp,
            'change_with': total_rev_with,
            'total_change': (total_rev_without + total_rev_with) - total_exp
        }

    def get_changes_in_net_assets_report(self):
        pos = self.get_isak35_financial_position()
        akt = self.get_statement_of_activities()
        
        # SINKRONISASI KUNCI DENGAN UI (report_view.py)
        return [
            {
                "description": "Aset Neto Awal Periode", 
                "without_restriction": pos['net_assets_without'] - akt['change_without'], 
                "with_restriction": pos['net_assets_with'] - akt['change_with'],
                "total": pos['total_net_assets'] - akt['total_change']
            },
            {
                "description": "Perubahan Periode Berjalan", 
                "without_restriction": akt['change_without'], 
                "with_restriction": akt['change_with'],
                "total": akt['total_change']
            },
            {
                "description": "Aset Neto Akhir Periode", 
                "without_restriction": pos['net_assets_without'], 
                "with_restriction": pos['net_assets_with'],
                "total": pos['total_net_assets']
            }
        ]

    def get_cash_flow_statement(self):
        query = "SELECT jd.cash_flow_activity as activity, jd.debit, jd.credit, cfc.main_category FROM journal_details jd JOIN cash_flow_categories cfc ON jd.cash_flow_activity = cfc.name"
        conn = self.db.get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['amount'] = df['debit'] - df['credit']
            summary = df.groupby(['main_category', 'activity'])['amount'].sum().reset_index()
        else:
            summary = pd.DataFrame(columns=['main_category', 'activity', 'amount'])
        return summary

    def get_cash_flow_report(self):
        df = self.get_cash_flow_statement()
        report_data = []
        total_all_activities = 0
        for cat in ["ARUS KAS DARI AKTIVITAS OPERASI", "ARUS KAS DARI AKTIVITAS INVESTASI", "ARUS KAS DARI AKTIVITAS PENDANAAN"]:
            cat_df = df[df['main_category'] == cat]
            cat_total = cat_df['amount'].sum() if not cat_df.empty else 0
            total_all_activities += cat_total
            
            report_data.append({"Keterangan": cat, "Jumlah (Rp)": ""})
            for _, r in cat_df.iterrows():
                report_data.append({"Keterangan": f"  {r['activity']}", "Jumlah (Rp)": r['amount']})
            report_data.append({"Keterangan": f"Total {cat}", "Jumlah (Rp)": cat_total})
            report_data.append({"Keterangan": "", "Jumlah (Rp)": ""})
            
        report_data.append({"Keterangan": "KENAIKAN (PENURUNAN) BERSIH KAS", "Jumlah (Rp)": total_all_activities})
        return {"report_data": report_data}

    def export_all_reports_to_excel(self, file_path):
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                # 1. Posisi Keuangan
                pos = self.get_isak35_financial_position()
                rows_pos = [["LAPORAN POSISI KEUANGAN"], [""]]
                rows_pos.append(["ASET", ""])
                for a in pos["assets"]: rows_pos.append([a['name'], a["balance"]])
                rows_pos.append(["TOTAL ASET", pos["total_assets"]])
                rows_pos.append(["", ""])
                rows_pos.append(["LIABILITAS", ""])
                for l in pos["liabilities"]: rows_pos.append([l['name'], l["balance"]])
                rows_pos.append(["TOTAL LIABILITAS", pos["total_liabilities"]])
                rows_pos.append(["", ""])
                rows_pos.append(["ASET NETO", ""])
                rows_pos.append(["  Tanpa Pembatasan", pos["net_assets_without"]])
                rows_pos.append(["  Dengan Pembatasan", pos["net_assets_with"]])
                rows_pos.append(["TOTAL ASET NETO", pos["total_net_assets"]])
                pd.DataFrame(rows_pos, columns=["Keterangan", "Nilai"]).to_excel(writer, sheet_name="Posisi Keuangan", index=False)

                # 2. Aktivitas
                akt = self.get_statement_of_activities()
                rows_akt = [["LAPORAN AKTIVITAS"], [""]]
                rows_akt.append(["PENDAPATAN", ""])
                for _, r in akt["revenue"].iterrows(): rows_akt.append([r['name'], r["total"]])
                rows_akt.append(["TOTAL PENDAPATAN", akt["total_rev"]])
                rows_akt.append(["", ""])
                rows_akt.append(["BEBAN", ""])
                for _, r in akt["expense"].iterrows(): rows_akt.append([r['name'], r["balance"]])
                rows_akt.append(["TOTAL BEBAN", akt["total_exp"]])
                rows_akt.append(["", ""])
                rows_akt.append(["PERUBAHAN ASET NETO", akt["total_change"]])
                pd.DataFrame(rows_akt, columns=["Keterangan", "Nilai"]).to_excel(writer, sheet_name="Laporan Aktivitas", index=False)

                # 3. Perubahan Aset Neto
                p_data = self.get_changes_in_net_assets_report()
                pd.DataFrame(p_data).to_excel(writer, sheet_name="Perubahan Aset Neto", index=False)

                # 4. Arus Kas
                cf_data = self.get_cash_flow_report()
                df_cf = pd.DataFrame(cf_data["report_data"])
                df_cf.to_excel(writer, sheet_name="Arus Kas", index=False)
            return True
        except Exception as e:
            print(f"Export Error: {e}")
            return False
