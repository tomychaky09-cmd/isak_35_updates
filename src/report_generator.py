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
            'total_net_assets': total_net_assets, 'total_liabilities_and_net_assets': total_liabilities + total_net_assets
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

    def get_changes_in_net_assets_report(self):
        pos = self.get_isak35_financial_position()
        inc = self.get_comprehensive_income()
        surplus_without = inc['total_revenue'] - inc['total_expenses'] # Simplified
        surplus_with = sum([r['balance'] for r in inc['revenue_with']])

        return [
            {"Keterangan": "Aset Neto Awal Periode", "Tanpa Pembatasan": pos['net_assets_without'] - surplus_without, "Dengan Pembatasan": pos['net_assets_with'] - surplus_with},
            {"Keterangan": "Perubahan Periode Berjalan", "Tanpa Pembatasan": surplus_without, "Dengan Pembatasan": surplus_with},
            {"Keterangan": "Aset Neto Akhir Periode", "Tanpa Pembatasan": pos['net_assets_without'], "Dengan Pembatasan": pos['net_assets_with']}
        ]

    def get_cash_flow_report(self):
        query = "SELECT jd.cash_flow_activity, jd.debit, jd.credit, cfc.main_category FROM journal_details jd JOIN cash_flow_categories cfc ON jd.cash_flow_activity = cfc.name"
        conn = self.db.get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        report_data = []
        for cat in ["ARUS KAS DARI AKTIVITAS OPERASI", "ARUS KAS DARI AKTIVITAS INVESTASI", "ARUS KAS DARI AKTIVITAS PENDANAAN"]:
            cat_df = df[df['main_category'] == cat]
            report_data.append({"Keterangan": cat, "Nilai": ""})
            for act in cat_df['cash_flow_activity'].unique():
                val = cat_df[cat_df['cash_flow_activity'] == act]['debit'].sum() - cat_df[cat_df['cash_flow_activity'] == act]['credit'].sum()
                report_data.append({"Keterangan": f"  {act}", "Nilai": val})
            report_data.append({"Keterangan": f"Total {cat}", "Nilai": cat_df['debit'].sum() - cat_df['credit'].sum()})
        return {"report_data": report_data}

    def export_all_reports_to_excel(self, file_path):
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                # 1
                pos = self.get_isak35_financial_position()
                rows_pos = [["LAPORAN POSISI KEUANGAN"], [""]]
                for a in pos["assets"]: rows_pos.append([a['name'], a["balance"]])
                rows_pos.append(["TOTAL ASET", pos["total_assets"]])
                pd.DataFrame(rows_pos).to_excel(writer, sheet_name="Posisi Keuangan", index=False)
                # 2
                inc = self.get_comprehensive_income()
                rows_inc = [["LAPORAN AKTIVITAS"], [""]]
                rows_inc.append(["TOTAL PENDAPATAN", inc["total_revenue"]])
                rows_inc.append(["TOTAL BEBAN", inc["total_expenses"]])
                pd.DataFrame(rows_inc).to_excel(writer, sheet_name="Laporan Aktivitas", index=False)
                # 3
                p_data = self.get_changes_in_net_assets_report()
                pd.DataFrame(p_data).to_excel(writer, sheet_name="Perubahan Aset Neto", index=False)
                # 4
                cf_data = self.get_cash_flow_report()
                pd.DataFrame(cf_data["report_data"]).to_excel(writer, sheet_name="Arus Kas", index=False)
            return True
        except: return False
