import pandas as pd
import sqlite3 # Added import
from .database_manager import DatabaseManager

class ReportGenerator:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_isak35_financial_position(self):
        """Menghasilkan Laporan Posisi Keuangan ISAK 35."""
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)
        
        # Fungsi bantu untuk mencocokkan kategori secara fleksibel
        def filter_category(d, cat_type):
            if cat_type == 'without':
                return d[d['category'].str.lower() == 'tanpa pembatasan']
            elif cat_type == 'with':
                return d[d['category'].str.lower() == 'dengan pembatasan']
            return pd.DataFrame()

        # 1. Aset
        assets_df = df[df['type'] == 'Asset']
        contra_assets_df = df[df['type'] == 'Asset (Contra)']
        
        total_assets = assets_df['balance'].sum() - contra_assets_df['balance'].sum()
        
        # 2. Liabilitas
        liabilities = df[df['type'] == 'Liability'][['code', 'name', 'balance']]
        total_liabilities = liabilities['balance'].sum()
        
        # 3. Aset Neto (ISAK 35 Core)
        net_assets_without_initial = filter_category(df[df['type'] == 'Asset Net'], 'without')['balance'].sum()
        net_assets_with_initial = filter_category(df[df['type'] == 'Asset Net'], 'with')['balance'].sum()
        
        surplus_without = filter_category(df[df['type'] == 'Revenue'], 'without')['balance'].sum() - \
                          df[(df['type'] == 'Expense')]['balance'].sum()
        
        surplus_with = filter_category(df[df['type'] == 'Revenue'], 'with')['balance'].sum()
        
        final_net_without = net_assets_without_initial + surplus_without
        final_net_with = net_assets_with_initial + surplus_with
        total_net_assets = final_net_without + final_net_with
        
        # 4. Verifikasi Persamaan Akuntansi
        total_liabilities_and_net_assets = total_liabilities + total_net_assets
        
        # Gabungkan Aset untuk tampilan
        assets_for_display = pd.concat([assets_df[['code', 'name', 'balance']], contra_assets_df[['code', 'name', 'balance']]]).sort_values(by='code')

        return {
            'assets': assets_for_display.to_dict('records'),
            'total_assets': total_assets,
            'liabilities': liabilities.to_dict('records'),
            'total_liabilities': total_liabilities,
            'net_assets_without': final_net_without,
            'net_assets_with': final_net_with,
            'total_net_assets': total_net_assets,
            'total_liabilities_and_net_assets': total_liabilities_and_net_assets
        }

    def get_comprehensive_income(self):
        """Menghasilkan Laporan Penghasilan Komprehensif ISAK 35."""
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)
        
        # Fungsi bantu untuk mencocokkan kategori secara fleksibel
        def filter_category(d, cat_type):
            if cat_type == 'without':
                return d[d['category'].str.lower() == 'tanpa pembatasan']
            elif cat_type == 'with':
                return d[d['category'].str.lower() == 'dengan pembatasan']
            return pd.DataFrame()

        # Pendapatan
        rev_without = filter_category(df[df['type'] == 'Revenue'], 'without')
        rev_with = filter_category(df[df['type'] == 'Revenue'], 'with')
        # Beban
        expenses = df[df['type'] == 'Expense']
        
        return {
            'revenue_without': rev_without.to_dict('records'),
            'revenue_with': rev_with.to_dict('records'),
            'expenses': expenses.to_dict('records'),
            'total_revenue': rev_without['balance'].sum() + rev_with['balance'].sum(),
            'total_expenses': expenses['balance'].sum()
        }

    def export_to_excel(self, file_path):
        """Mengekspor laporan keuangan ke file Excel."""
        pos_data = self.get_isak35_financial_position()
        income_data = self.get_comprehensive_income()
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # 1. Sheet Laporan Posisi Keuangan
            # Gabungkan Aset, Liabilitas, dan Aset Neto ke dalam satu DataFrame untuk diekspor
            pos_df_rows = []
            pos_df_rows.append({'Keterangan': 'ASET', 'Jumlah': ''})
            for asset in pos_data['assets']:
                pos_df_rows.append({'Keterangan': f"  {asset['name']}", 'Jumlah': asset['balance']})
            pos_df_rows.append({'Keterangan': 'TOTAL ASET', 'Jumlah': pos_data['total_assets']})
            pos_df_rows.append({'Keterangan': '', 'Jumlah': ''})
            
            pos_df_rows.append({'Keterangan': 'LIABILITAS', 'Jumlah': ''})
            for liability in pos_data['liabilities']:
                pos_df_rows.append({'Keterangan': f"  {liability['name']}", 'Jumlah': liability['balance']})
            pos_df_rows.append({'Keterangan': 'TOTAL LIABILITAS', 'Jumlah': pos_data['total_liabilities']})
            pos_df_rows.append({'Keterangan': '', 'Jumlah': ''})
            
            pos_df_rows.append({'Keterangan': 'ASET NETO', 'Jumlah': ''})
            pos_df_rows.append({'Keterangan': '  Tanpa Pembatasan dari Pemberi Sumber Daya', 'Jumlah': pos_data['net_assets_without']})
            pos_df_rows.append({'Keterangan': '  Dengan Pembatasan dari Pemberi Sumber Daya', 'Jumlah': pos_data['net_assets_with']})
            pos_df_rows.append({'Keterangan': 'TOTAL ASET NETO', 'Jumlah': pos_data['total_net_assets']})
            pos_df_rows.append({'Keterangan': '', 'Jumlah': ''})
            pos_df_rows.append({'Keterangan': 'TOTAL LIABILITAS DAN ASET NETO', 'Jumlah': pos_data['total_liabilities'] + pos_data['total_net_assets']})
            
            pd.DataFrame(pos_df_rows).to_excel(writer, sheet_name='Posisi Keuangan', index=False)
            
            # 2. Sheet Laporan Penghasilan Komprehensif
            inc_df_rows = []
            inc_df_rows.append({'Keterangan': 'PENDAPATAN', 'Jumlah': ''})
            inc_df_rows.append({'Keterangan': '  Tanpa Pembatasan:', 'Jumlah': ''})
            for rev in income_data['revenue_without']:
                inc_df_rows.append({'Keterangan': f"    {rev['name']}", 'Jumlah': rev['balance']})
            
            inc_df_rows.append({'Keterangan': '  Dengan Pembatasan:', 'Jumlah': ''})
            for rev in income_data['revenue_with']:
                inc_df_rows.append({'Keterangan': f"    {rev['name']}", 'Jumlah': rev['balance']})
            
            inc_df_rows.append({'Keterangan': 'TOTAL PENDAPATAN', 'Jumlah': income_data['total_revenue']})
            inc_df_rows.append({'Keterangan': '', 'Jumlah': ''})
            
            inc_df_rows.append({'Keterangan': 'BEBAN', 'Jumlah': ''})
            for exp in income_data['expenses']:
                inc_df_rows.append({'Keterangan': f"  {exp['name']}", 'Jumlah': exp['balance']})
            inc_df_rows.append({'Keterangan': 'TOTAL BEBAN', 'Jumlah': income_data['total_expenses']})
            inc_df_rows.append({'Keterangan': '', 'Jumlah': ''})
            
            surplus = income_data['total_revenue'] - income_data['total_expenses']
            inc_df_rows.append({'Keterangan': 'PENGHASILAN KOMPREHENSIF (SURPLUS/DEFISIT)', 'Jumlah': surplus})
            
            pd.DataFrame(inc_df_rows).to_excel(writer, sheet_name='Penghasilan Komprehensif', index=False)
            
        return True

    def get_trial_balance_report(self):
        """Menghasilkan data Neraca Saldo."""
        df = self.db.get_trial_balance()
        # Pastikan kolom debit dan credit tidak None
        df['debit'] = df['debit'].fillna(0)
        df['credit'] = df['credit'].fillna(0)

        # Hitung total debit dan kredit (dari saldo akhir setiap akun)
        total_debit_sum = df['debit'].sum()
        total_credit_sum = df['credit'].sum()

        # Tambahkan baris total ke DataFrame
        df_total = pd.DataFrame([{
            'code': '', 
            'name': 'TOTAL', 
            'type': '', 
            'category': '', 
            'debit': total_debit_sum, 
            'credit': total_credit_sum, 
            'balance': 0 
        }])
        df = pd.concat([df, df_total], ignore_index=True)
        
        return df.to_dict('records')

    def get_changes_in_net_assets_report(self):
        """Menghasilkan data Laporan Perubahan Aset Neto."""
        df = self.db.get_trial_balance()
        df['balance'] = df['balance'].fillna(0.0)

        # Fungsi bantu untuk mencocokkan kategori secara fleksibel
        def filter_category(d, cat_type):
            if cat_type == 'without':
                return d[d['category'].str.lower() == 'tanpa pembatasan']
            elif cat_type == 'with':
                return d[d['category'].str.lower() == 'dengan pembatasan']
            return pd.DataFrame()

        # Saldo Aset Neto Awal (dari akun Aset Neto)
        net_assets_without_initial = filter_category(df[df['type'] == 'Asset Net'], 'without')['balance'].sum()
        net_assets_with_initial = filter_category(df[df['type'] == 'Asset Net'], 'with')['balance'].sum()

        # Perubahan Aset Neto dari Penghasilan Komprehensif (Surplus/Defisit)
        surplus_without = filter_category(df[df['type'] == 'Revenue'], 'without')['balance'].sum() - \
                          df[(df['type'] == 'Expense')]['balance'].sum()
        surplus_with = filter_category(df[df['type'] == 'Revenue'], 'with')['balance'].sum()

        # Saldo Aset Neto Akhir
        final_net_without = net_assets_without_initial + surplus_without
        final_net_with = net_assets_with_initial + surplus_with
        
        total_initial_net_assets = net_assets_without_initial + net_assets_with_initial
        total_surplus = surplus_without + surplus_with
        total_final_net_assets = final_net_without + final_net_with

        report_data = [
            {"description": "Aset Neto Awal Periode", "without_restriction": net_assets_without_initial, "with_restriction": net_assets_with_initial, "total": total_initial_net_assets},
            {"description": "Kenaikan (Penurunan) Aset Neto dari Penghasilan Komprehensif", "without_restriction": surplus_without, "with_restriction": surplus_with, "total": total_surplus},
            {"description": "Aset Neto Akhir Periode", "without_restriction": final_net_without, "with_restriction": final_net_with, "total": total_final_net_assets},
        ]
        return report_data

    def get_cash_flow_report(self):
        """Menghasilkan data Laporan Arus Kas yang lebih terperinci."""
        # Dapatkan ID akun Kas dan Setara Kas
        cash_account_ids = self.db.get_cash_and_cash_equivalents_account_ids()
        print(f"DEBUG: cash_account_ids = {cash_account_ids}")

        if not cash_account_ids:
            return {"error": "Akun 'Kas' atau 'Bank' tidak ditemukan. Laporan Arus Kas tidak dapat dibuat.", "report_data": []}

        # Ambil semua detail jurnal
        conn = sqlite3.connect(self.db.db_path)
        query = """
        SELECT 
            jd.journal_id,
            jd.account_id,
            a.name as account_name,
            a.type as account_type,
            jd.debit,
            jd.credit,
            jd.cash_flow_activity,
            je.date,
            je.description as journal_description
        FROM journal_details jd
        JOIN accounts a ON jd.account_id = a.id
        JOIN journal_entries je ON jd.journal_id = je.id
        ORDER BY je.date ASC, je.id ASC
        """
        all_journal_details_df = pd.read_sql_query(query, conn)
        conn.close()

        # Filter transaksi yang melibatkan akun kas atau setara kas
        cash_transactions = all_journal_details_df[all_journal_details_df['account_id'].isin(cash_account_ids)]
        print(f"DEBUG: cash_transactions = \n{cash_transactions.to_string()}")

        # Kamus untuk menyimpan total per sub-kategori
        cash_flow_data = {
            "ARUS KAS DARI AKTIVITAS OPERASI": {},
            "ARUS KAS DARI AKTIVITAS INVESTASI": {},
            "ARUS KAS DARI AKTIVITAS PENDANAAN": {}
        }

        # Ambil pemetaan aktivitas arus kas dari database
        activity_mapping = self.db.get_cash_flow_activity_mapping()
        print(f"DEBUG: activity_mapping = {activity_mapping}")

        # Proses setiap transaksi kas
        for index, cash_row in cash_transactions.iterrows():
            journal_id = cash_row['journal_id']
            
            # Ambil cash_flow_activity langsung dari baris kas
            activity_description = cash_row['cash_flow_activity']
            
            if activity_description and activity_description in activity_mapping:
                main_activity = activity_mapping[activity_description]
                
                # Tentukan apakah ini arus kas masuk atau keluar
                # Jika kas didebit, berarti kas masuk (kredit di akun lain)
                # Jika kas dikredit, berarti kas keluar (debit di akun lain)
                amount = 0
                if cash_row['debit'] > 0: # Kas masuk
                    amount = cash_row['debit']
                elif cash_row['credit'] > 0: # Kas keluar
                    amount = -cash_row['credit'] # Negatif untuk arus kas keluar

                if activity_description not in cash_flow_data[main_activity]:
                    cash_flow_data[main_activity][activity_description] = 0
                cash_flow_data[main_activity][activity_description] += amount

        # Hitung total untuk setiap aktivitas utama
        total_operating_cash_flow = sum(cash_flow_data["ARUS KAS DARI AKTIVITAS OPERASI"].values()) if cash_flow_data["ARUS KAS DARI AKTIVITAS OPERASI"] else 0
        total_investing_cash_flow = sum(cash_flow_data["ARUS KAS DARI AKTIVITAS INVESTASI"].values()) if cash_flow_data["ARUS KAS DARI AKTIVITAS INVESTASI"] else 0
        total_financing_cash_flow = sum(cash_flow_data["ARUS KAS DARI AKTIVITAS PENDANAAN"].values()) if cash_flow_data["ARUS KAS DARI AKTIVITAS PENDANAAN"] else 0

        net_increase_decrease_in_cash = total_operating_cash_flow + total_investing_cash_flow + total_financing_cash_flow

        # Format laporan
        report_output = []

        # Aktivitas Operasi
        report_output.append({"Keterangan": "ARUS KAS DARI AKTIVITAS OPERASI", "Jumlah (Rp)": ""})
        for desc, amount in cash_flow_data["ARUS KAS DARI AKTIVITAS OPERASI"].items():
            report_output.append({"Keterangan": f"  {desc}", "Jumlah (Rp)": amount})
        report_output.append({"Keterangan": "Arus Kas Bersih dari Aktivitas Operasi", "Jumlah (Rp)": total_operating_cash_flow})
        report_output.append({"Keterangan": "", "Jumlah (Rp)": ""})

        # Aktivitas Investasi
        report_output.append({"Keterangan": "ARUS KAS DARI AKTIVITAS INVESTASI", "Jumlah (Rp)": ""})
        for desc, amount in cash_flow_data["ARUS KAS DARI AKTIVITAS INVESTASI"].items():
            report_output.append({"Keterangan": f"  {desc}", "Jumlah (Rp)": amount})
        report_output.append({"Keterangan": "Arus Kas Bersih dari Aktivitas Investasi", "Jumlah (Rp)": total_investing_cash_flow})
        report_output.append({"Keterangan": "", "Jumlah (Rp)": ""})

        # Aktivitas Pendanaan
        report_output.append({"Keterangan": "ARUS KAS DARI AKTIVITAS PENDANAAN", "Jumlah (Rp)": ""})
        for desc, amount in cash_flow_data["ARUS KAS DARI AKTIVITAS PENDANAAN"].items():
            report_output.append({"Keterangan": f"  {desc}", "Jumlah (Rp)": amount})
        report_output.append({"Keterangan": "Arus Kas Bersih dari Aktivitas Pendanaan", "Jumlah (Rp)": total_financing_cash_flow})
        report_output.append({"Keterangan": "", "Jumlah (Rp)": ""})

        # Ringkasan
        report_output.append({"Keterangan": "Kenaikan (Penurunan) Bersih Kas", "Jumlah (Rp)": net_increase_decrease_in_cash})
        # Saldo Kas Awal dan Akhir perlu data tambahan, mungkin dari saldo awal atau dari periode sebelumnya
        # Untuk saat ini, saya akan meninggalkan ini sebagai placeholder atau mengandalkan UI untuk menanganinya.
        # report_output.append({"Keterangan": "Kas dan Setara Kas pada Awal Tahun", "Jumlah (Rp)": "TODO"})
        # report_output.append({"Keterangan": "Kas dan Setara Kas pada Akhir Tahun", "Jumlah (Rp)": "TODO"})

        return {"report_data": report_output}

    def export_all_reports_to_excel(self, file_path):
        try:
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                # 1. Neraca
                df_neraca = self.db.get_trial_balance()
                df_neraca.to_excel(writer, sheet_name="Trial Balance", index=False)
                
                # 2. Arus Kas
                cf_data = self.db.get_all_journal_details_with_cash_flow()
                df_cf = pd.DataFrame(cf_data, columns=["ID", "Tanggal", "Keterangan", "Akun", "Debit", "Kredit", "Aktivitas"])
                df_cf.to_excel(writer, sheet_name="Detail Transaksi Kas", index=False)
            return True
        except: return False

