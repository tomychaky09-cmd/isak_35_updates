import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side

class ReportGenerator:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_trial_balance_report(self):
        data = self.db.get_trial_balance()
        total_debit = sum(x['debit'] for x in data)
        total_credit = sum(x['credit'] for x in data)
        data.append({'code': '', 'name': 'TOTAL', 'debit': total_debit, 'credit': total_credit})
        return data

    def get_isak35_financial_position(self):
        data = self.db.get_trial_balance()
        
        assets = [x for x in data if x['type'] == 'Asset']
        contra_assets = [x for x in data if x['type'] == 'Asset (Contra)']
        total_assets = sum(x['balance'] for x in assets) - sum(x['balance'] for x in contra_assets)
        
        liabilities = [x for x in data if x['type'] == 'Liability']
        total_liabilities = sum(x['balance'] for x in liabilities)
        
        # Aset Neto
        net_assets_without = sum(x['balance'] for x in data if x['type'] == 'Asset Net' and x['category'].lower() == 'tanpa pembatasan')
        net_assets_with = sum(x['balance'] for x in data if x['type'] == 'Asset Net' and x['category'].lower() == 'dengan pembatasan')
        
        # Surplus/Defisit
        rev_without = sum(x['balance'] for x in data if x['type'] == 'Revenue' and x['category'].lower() == 'tanpa pembatasan')
        rev_with = sum(x['balance'] for x in data if x['type'] == 'Revenue' and x['category'].lower() == 'dengan pembatasan')
        
        exp_without = sum(x['balance'] for x in data if x['type'] == 'Expense' and x['category'].lower() == 'tanpa pembatasan')
        exp_with = sum(x['balance'] for x in data if x['type'] == 'Expense' and x['category'].lower() == 'dengan pembatasan')
        
        # Handle uncategorized expenses
        total_exp_real = sum(x['balance'] for x in data if x['type'] == 'Expense')
        exp_uncategorized = total_exp_real - (exp_without + exp_with)
        exp_without += exp_uncategorized
        
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

    def get_statement_of_activities(self):
        data = self.db.get_trial_balance()
        
        rev = [x for x in data if x['type'] == 'Revenue']
        exp = [x for x in data if x['type'] == 'Expense']
        
        total_rev = sum(x['balance'] for x in rev)
        total_exp = sum(x['balance'] for x in exp)
        
        return {
            'revenue': [{'name': x['name'], 'balance': x['balance']} for x in rev],
            'total_rev': total_rev,
            'expenses': [{'name': x['name'], 'balance': x['balance']} for x in exp],
            'total_exp': total_exp,
            'total_change': total_rev - total_exp
        }

    def get_cash_flow_report(self):
        data = self.db.get_trial_balance()
        cash_accounts = [x for x in data if 'kas' in x['name'].lower() or 'bank' in x['name'].lower() or 'cash' in x['name'].lower()]
        total_cash_end = sum(x['balance'] for x in cash_accounts)
        report_data = [{"Keterangan": "SALDO KAS PADA AKHIR PERIODE", "Jumlah (Rp)": total_cash_end}]
        return {"report_data": report_data}

    def export_all_reports_to_excel(self, file_path):
        try:
            wb = Workbook()
            ws1 = wb.active
            ws1.title = "Posisi Keuangan"
            profile = self.db.get_foundation_profile()
            pos = self.get_isak35_financial_position()
            ws1.append([profile['name'].upper()])
            ws1.append(["LAPORAN POSISI KEUANGAN"])
            ws1.append([""])
            ws1.append(["ASET", "Jumlah (Rp)"])
            for a in pos['assets']: ws1.append([a['name'], a['balance']])
            ws1.append(["TOTAL ASET", pos['total_assets']])
            ws2 = wb.create_sheet("Aktivitas")
            akt = self.get_statement_of_activities()
            ws2.append(["LAPORAN AKTIVITAS"])
            ws2.append(["PENDAPATAN"])
            for r in akt['revenue']: ws2.append([r['name'], r['balance']])
            ws2.append(["TOTAL PENDAPATAN", akt['total_rev']])
            wb.save(file_path)
            return True
        except: return False
