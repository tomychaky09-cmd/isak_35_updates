import pandas as pd
import sqlite3
import os
from .database_manager import DatabaseManager
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from datetime import datetime

class ReportGenerator:
    def __init__(self, db_manager):
        self.db = db_manager

    def get_trial_balance_report(self):
        df = self.db.get_trial_balance()
        df['debit'] = df['debit'].fillna(0); df['credit'] = df['credit'].fillna(0)
        total_debit = df['debit'].sum(); total_credit = df['credit'].sum()
        records = df.to_dict('records')
        records.append({'code': '', 'name': 'TOTAL', 'debit': total_debit, 'credit': total_credit})
        return records

    def get_isak35_financial_position(self):
        df = self.db.get_trial_balance()
        if 'balance' not in df.columns:
            df['balance'] = 0.0
        df['balance'] = df['balance'].fillna(0.0)
        
        def filter_category(d, cat_type):
            if d.empty: return pd.DataFrame(columns=d.columns)
            if cat_type == 'without': return d[d['category'].str.lower() == 'tanpa pembatasan']
            elif cat_type == 'with': return d[d['category'].str.lower() == 'dengan pembatasan']
            return pd.DataFrame(columns=d.columns)
        
        assets_df = df[df['type'] == 'Asset']
        contra_assets_df = df[df['type'] == 'Asset (Contra)']
        total_assets = assets_df['balance'].sum() - contra_assets_df['balance'].sum()
        liabilities_df = df[df['type'] == 'Liability']
        total_liabilities = liabilities_df['balance'].sum()
        
        # Aset Neto Awal (dari COA Tipe Asset Net)
        net_assets_without = filter_category(df[df['type'] == 'Asset Net'], 'without')['balance'].sum()
        net_assets_with = filter_category(df[df['type'] == 'Asset Net'], 'with')['balance'].sum()
        
        # Surplus/Defisit Berjalan (Revenue - Expense) per Kategori
        rev_without = filter_category(df[df['type'] == 'Revenue'], 'without')['balance'].sum()
        rev_with = filter_category(df[df['type'] == 'Revenue'], 'with')['balance'].sum()
        
        # Perbaikan: Beban sekarang dipisahkan berdasarkan kategori COA-nya
        exp_without = filter_category(df[df['type'] == 'Expense'], 'without')['balance'].sum()
        exp_with = filter_category(df[df['type'] == 'Expense'], 'with')['balance'].sum()
        
        # Jika ada beban yang tidak memiliki kategori di COA, masukkan ke Tanpa Pembatasan
        total_exp_real = df[df['type'] == 'Expense']['balance'].sum()
        exp_uncategorized = total_exp_real - (exp_without + exp_with)
        exp_without += exp_uncategorized
        
        surplus_without = rev_without - exp_without
        surplus_with = rev_with - exp_with
        
        final_net_without = net_assets_without + surplus_without
        final_net_with = net_assets_with + surplus_with
        
        return {
            'assets': pd.concat([assets_df[['name', 'balance']], contra_assets_df[['name', 'balance']]]).to_dict('records') if not assets_df.empty or not contra_assets_df.empty else [],
            'total_assets': total_assets,
            'liabilities': liabilities_df[['name', 'balance']].to_dict('records') if not liabilities_df.empty else [],
            'total_liabilities': total_liabilities,
            'net_assets_without': final_net_without,
            'net_assets_with': final_net_with,
            'total_net_assets': final_net_without + final_net_with,
            'total_liabilities_and_net_assets': total_liabilities + final_net_without + final_net_with,
            'surplus_without': surplus_without,
            'surplus_with': surplus_with
        }

    def get_comprehensive_income(self):
        df = self.db.get_trial_balance()
        if 'balance' not in df.columns:
            df['balance'] = 0.0
        df['balance'] = df['balance'].fillna(0.0)
        
        def filter_cat(d, c):
            if d.empty: return pd.DataFrame(columns=d.columns)
            return d[d['category'].str.lower() == c]
            
        rev = df[df['type'] == 'Revenue']; exp = df[df['type'] == 'Expense']
        return {
            'revenue_without': filter_cat(rev, 'tanpa pembatasan').to_dict('records'),
            'revenue_with': filter_cat(rev, 'dengan pembatasan').to_dict('records'),
            'expenses': exp.to_dict('records'),
            'total_revenue': rev['balance'].sum() if not rev.empty else 0,
            'total_expenses': exp['balance'].sum() if not exp.empty else 0,
            'total_rev_without': filter_cat(rev, 'tanpa pembatasan')['balance'].sum(),
            'total_rev_with': filter_cat(rev, 'dengan pembatasan')['balance'].sum(),
            'total_exp_without': filter_cat(exp, 'tanpa pembatasan')['balance'].sum(),
            'total_exp_with': filter_cat(exp, 'dengan pembatasan')['balance'].sum()
        }

    def get_statement_of_activities(self):
        data = self.get_comprehensive_income()
        return {
            'revenue': data['revenue_without'] + data['revenue_with'],
            'total_rev': data['total_revenue'],
            'expenses': data['expenses'],
            'total_exp': data['total_expenses'],
            'total_change': data['total_revenue'] - data['total_expenses'],
            # Perubahan neto per kategori
            'change_without': data['total_rev_without'] - (data['total_expenses'] - data['total_exp_with']),
            'change_with': data['total_rev_with'] - data['total_exp_with']
        }

    def get_changes_in_net_assets_report(self):
        pos = self.get_isak35_financial_position(); akt = self.get_statement_of_activities()
        # Perubahan Periode Berjalan harus diambil dari Laporan Aktivitas (akt)
        change_without = akt['change_without']
        change_with = akt['change_with']
        
        # Aset Neto Awal = Akhir - Perubahan
        start_without = pos['net_assets_without'] - change_without
        start_with = pos['net_assets_with'] - change_with
        
        return [
            {"description": "Aset Neto Awal Periode", "without_restriction": start_without, "with_restriction": start_with, "total": start_without + start_with},
            {"description": "Perubahan Periode Berjalan", "without_restriction": change_without, "with_restriction": change_with, "total": change_without + change_with},
            {"description": "Aset Neto Akhir Periode", "without_restriction": pos['net_assets_without'], "with_restriction": pos['net_assets_with'], "total": pos['total_net_assets']}
        ]

    def get_cash_flow_report(self):
        # 1. Identifikasi Akun Kas & Bank
        df_tb = self.db.get_trial_balance()
        if 'balance' not in df_tb.columns:
            df_tb['balance'] = 0.0
            
        def is_cash_account(row):
            name = str(row['name']).lower()
            return 'kas' in name or 'bank' in name or 'cash' in name
            
        cash_accounts = df_tb[df_tb.apply(is_cash_account, axis=1)]
        
        # 2. Ambil Pergerakan (Movements) dari Jurnal (EXCLUDE Saldo Awal SA-)
        query = """
            SELECT jd.cash_flow_activity as activity, jd.debit, jd.credit, cfc.main_category 
            FROM journal_details jd 
            JOIN cash_flow_categories cfc ON jd.cash_flow_activity = cfc.name
            JOIN journal_entries je ON jd.journal_id = je.id
            WHERE jd.cash_flow_activity IS NOT NULL
            AND je.reference_no NOT LIKE 'SA-%'
        """
        conn = self.db.get_connection()
        df_movements = pd.read_sql_query(query, conn)
        
        # 3. Ambil Saldo Awal Khusus (dari entri SA-)
        query_sa = """
            SELECT jd.account_id, SUM(jd.debit - jd.credit) as sa_amount
            FROM journal_details jd
            JOIN journal_entries je ON jd.journal_id = je.id
            WHERE je.reference_no LIKE 'SA-%'
            GROUP BY jd.account_id
        """
        df_sa = pd.read_sql_query(query_sa, conn)
        conn.close()
        
        report_data = []
        
        # --- Bagian A: Arus Kas dari Aktivitas ---
        total_net_change = 0
        if not df_movements.empty:
            df_movements['amount'] = df_movements['debit'] - df_movements['credit']
            summary = df_movements.groupby(['main_category', 'activity'])['amount'].sum().reset_index()
            
            for cat in ["ARUS KAS DARI AKTIVITAS OPERASI", "ARUS KAS DARI AKTIVITAS INVESTASI", "ARUS KAS DARI AKTIVITAS PENDANAAN"]:
                cat_df = summary[summary['main_category'] == cat]
                cat_total = cat_df['amount'].sum() if not cat_df.empty else 0
                total_net_change += cat_total
                
                report_data.append({"Keterangan": cat, "Jumlah (Rp)": ""})
                for _, r in cat_df.iterrows():
                    report_data.append({"Keterangan": f"  {r['activity']}", "Jumlah (Rp)": r['amount']})
                report_data.append({"Keterangan": f"Total {cat}", "Jumlah (Rp)": cat_total})
                report_data.append({"Keterangan": "", "Jumlah (Rp)": ""})
        
        report_data.append({"Keterangan": "KENAIKAN (PENURUNAN) BERSIH KAS", "Jumlah (Rp)": total_net_change})
        report_data.append({"Keterangan": "", "Jumlah (Rp)": ""})
        
        # --- Bagian B: Rekonsiliasi Saldo Kas ---
        # Hitung Saldo Awal dari DF_SA
        sa_map = df_sa.set_index('account_id')['sa_amount'].to_dict()
        
        cash_with_start = 0
        cash_without_start = 0
        
        for _, acc in cash_accounts.iterrows():
            aid = acc['id']
            sa_val = sa_map.get(aid, 0)
            if 'dengan pembatasan' in str(acc['category']).lower() or 'dengan pembatasan' in str(acc['name']).lower():
                cash_with_start += sa_val
            else:
                cash_without_start += sa_val
        
        total_cash_start = cash_with_start + cash_without_start
        total_cash_end = cash_accounts['balance'].sum()
        
        # Identifikasi Kas Akhir per Kategori
        mask_with = (cash_accounts['category'].str.contains('dengan pembatasan', case=False, na=False)) | \
                    (cash_accounts['name'].str.contains('dengan pembatasan', case=False, na=False))
        cash_with_end = cash_accounts[mask_with]['balance'].sum()
        cash_without_end = total_cash_end - cash_with_end

        report_data.append({"Keterangan": "SALDO KAS PADA AWAL PERIODE", "Jumlah (Rp)": total_cash_start})
        report_data.append({"Keterangan": "  Kas Tanpa Pembatasan (Awal)", "Jumlah (Rp)": cash_without_start})
        report_data.append({"Keterangan": "  Kas Dengan Pembatasan (Awal)", "Jumlah (Rp)": cash_with_start})
        
        report_data.append({"Keterangan": "", "Jumlah (Rp)": ""})
        report_data.append({"Keterangan": "SALDO KAS PADA AKHIR PERIODE", "Jumlah (Rp)": total_cash_end})
        report_data.append({"Keterangan": "  Kas Tanpa Pembatasan (Akhir)", "Jumlah (Rp)": cash_without_end})
        report_data.append({"Keterangan": "  Kas Dengan Pembatasan (Akhir)", "Jumlah (Rp)": cash_with_end})
        
        return {"report_data": report_data}

    def _extract_names(self, structure_text, profile):
        names = {'pembina': profile.get('pembina_name', '-'), 'pengawas': profile.get('pengawas_name', '-'), 'ketua': profile.get('leader_name', '-'), 'bendahara': '............................'}
        for line in (structure_text or "").split('\n'):
            lc = line.lower(); val = ""
            if ':' in line: val = line.split(':', 1)[1].strip()
            elif '-' in line: val = line.split('-', 1)[1].strip()
            if not val: continue
            if 'pembina' in lc: names['pembina'] = val
            elif 'pengawas' in lc: names['pengawas'] = val
            elif 'bendahara' in lc: names['bendahara'] = val
            elif 'ketua' in lc or 'umum' in lc: names['ketua'] = val
        return names

    def export_all_reports_to_excel(self, file_path):
        try:
            profile = self.db.get_foundation_profile()
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                pos = self.get_isak35_financial_position()
                pd.DataFrame([[profile['name'].upper()], ["LAPORAN POSISI KEUANGAN"], [""]] + [[a['name'], a['balance']] for a in pos['assets']]).to_excel(writer, sheet_name="Posisi Keuangan", index=False, header=False)
            return True
        except Exception as e: print(f"Excel Error: {e}"); return False

    def export_annual_report_to_excel(self, file_path, year):
        try:
            profile = self.db.get_foundation_profile(); settings = self.db.get_annual_report_settings(year)
            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                pd.DataFrame([[profile['name'].upper()], [f"LAPORAN TAHUNAN {year}"]]).to_excel(writer, sheet_name="Profil", index=False, header=False)
                pos = self.get_isak35_financial_position(); akt = self.get_statement_of_activities(); cf = self.get_cash_flow_report()
                pd.DataFrame([[a['name'], a['balance']] for a in pos['assets']]).to_excel(writer, sheet_name="Neraca", index=False, header=False)
                pd.DataFrame([[r['name'], r['balance']] for r in akt['revenue']]).to_excel(writer, sheet_name="Aktivitas", index=False, header=False)
                pd.DataFrame([[r['Keterangan'], r['Jumlah (Rp)']] for r in cf['report_data']]).to_excel(writer, sheet_name="Arus Kas", index=False, header=False)
            return True
        except Exception as e: print(f"Annual Excel Error: {e}"); return False

    def export_annual_report_to_pdf(self, file_path, year):
        try:
            profile = self.db.get_foundation_profile(); settings = self.db.get_annual_report_settings(year)
            extracted = self._extract_names(settings['organizational_structure'], profile)
            doc = SimpleDocTemplate(file_path, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=40, bottomMargin=40)
            styles = getSampleStyleSheet()
            n_style = styles['Normal']; n_style.fontSize = 9; n_style.alignment = 0 
            
            elements = []
            # HALAMAN 1: KOP & NARASI AWAL
            elements.append(Paragraph(f"<b>{profile['name'].upper()}</b>", ParagraphStyle('H', alignment=1, fontSize=14)))
            elements.append(Paragraph(profile['address'], ParagraphStyle('SH', alignment=1, fontSize=10)))
            elements.append(Spacer(1, 5)); elements.append(Table([[""]], colWidths=[6.5*inch], style=[('LINEBELOW', (0,0), (-1,-1), 1, colors.black)]))
            elements.append(Paragraph(f"LAPORAN TAHUNAN {year}", ParagraphStyle('T', alignment=1, fontSize=16, spaceBefore=10, spaceAfter=20)))
            
            # I. VISI MISI
            elements.append(Paragraph("<b>I. VISI & MISI</b>", styles['Heading2']))
            vm_rows = [["Visi", Paragraph(settings['vision'] or "-", n_style)], ["Misi", Paragraph((settings['mission'] or "-").replace('\n','<br/>'), n_style)]]
            t_vm = Table(vm_rows, colWidths=[1*inch, 5.2*inch]); t_vm.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.5,colors.grey), ('BACKGROUND',(0,0),(0,-1),colors.lightgrey), ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'), ('VALIGN',(0,0),(-1,-1),'TOP')])); elements.append(t_vm)

            # II. STRUKTUR
            elements.append(Paragraph("<b>II. STRUKTUR ORGANISASI</b>", styles['Heading2']))
            data_org = [["Jabatan / Posisi", "Nama Pengurus"]]
            for line in (settings['organizational_structure'] or "").split('\n'):
                if ':' in line: p = line.split(':', 1); data_org.append([p[0].strip(), p[1].strip()])
                elif line.strip(): data_org.append(["-", line.strip()])
            t_org = Table(data_org, colWidths=[2.5*inch, 3.7*inch]); t_org.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey)])); elements.append(t_org)

            # III. KINERJA BIDANG
            elements.append(Paragraph("<b>III. LAPORAN KINERJA PROGRAM BIDANG</b>", styles['Heading2']))
            data_kinerja = [["Bidang / Kategori", "Penjelasan Realisasi Kegiatan"]]
            data_kinerja.append(["Umum / Utama", Paragraph((settings['program_summary'] or "-").replace('\n','<br/>'), n_style)])
            data_kinerja.append(["Pendidikan", Paragraph((settings['program_detail_edu'] or "-").replace('\n','<br/>'), n_style)])
            data_kinerja.append(["Dakwah & Sosial", Paragraph((settings['program_detail_social'] or "-").replace('\n','<br/>'), n_style)])
            t_kin = Table(data_kinerja, colWidths=[1.5*inch, 4.7*inch]); t_kin.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey), ('VALIGN',(0,0),(-1,-1),'TOP')])); elements.append(t_kin)

            # HALAMAN 2-4: KEUANGAN (Tetap sama desainnya)
            elements.append(PageBreak()); elements.append(Paragraph("<b>IV. LAPORAN KEUANGAN</b>", styles['Heading2']))
            elements.append(Paragraph("A. Laporan Posisi Keuangan", styles['Heading3']))
            pos = self.get_isak35_financial_position(); rows = [["Keterangan", "Jumlah (Rp)"], ["ASET", ""]]
            for a in pos['assets']: rows.append([Paragraph(a['name'], n_style), f"{a['balance']:,.0f}"])
            rows += [["TOTAL ASET", f"{pos['total_assets']:,.0f}"], ["", ""], ["LIABILITAS", ""]]
            for l in pos['liabilities']: rows.append([Paragraph(l['name'], n_style), f"{l['balance']:,.0f}"])
            rows += [["TOTAL LIABILITAS", f"{pos['total_liabilities']:,.0f}"], ["", ""], ["ASET NETO", ""], ["  Tanpa Pembatasan", f"{pos['net_assets_without']:,.0f}"], ["  Dengan Pembatasan", f"{pos['net_assets_with']:,.0f}"], ["TOTAL ASET NETO", f"{pos['total_net_assets']:,.0f}"]]
            t_p = Table(rows, colWidths=[4.7*inch, 1.5*inch]); t_p.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey), ('ALIGN',(1,1),(-1,-1),'RIGHT')]))
            for i, r in enumerate(rows):
                if r[0] in ["ASET", "TOTAL ASET", "LIABILITAS", "TOTAL LIABILITAS", "ASET NETO", "TOTAL ASET NETO"]: t_p.setStyle(TableStyle([('FONTNAME',(0,i),(-1,i),'Helvetica-Bold')]))
            elements.append(t_p)

            elements.append(PageBreak()); elements.append(Paragraph("B. Laporan Aktivitas", styles['Heading3']))
            akt = self.get_statement_of_activities(); rows = [["Keterangan", "Jumlah (Rp)"], ["PENDAPATAN", ""]]
            for r in akt['revenue']: rows.append([Paragraph(r['name'], n_style), f"{r['balance']:,.0f}"])
            rows += [["TOTAL PENDAPATAN", f"{akt['total_rev']:,.0f}"], ["", ""], ["BEBAN", ""]]
            for e in akt['expenses']: rows.append([Paragraph(e['name'], n_style), f"{e['balance']:,.0f}"])
            rows += [["TOTAL BEBAN", f"{akt['total_exp']:,.0f}"], ["PERUBAHAN ASET NETO", f"{akt['total_change']:,.0f}"]]
            t_a = Table(rows, colWidths=[4.7*inch, 1.5*inch]); t_a.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey), ('ALIGN',(1,1),(-1,-1),'RIGHT')]))
            for i, r in enumerate(rows):
                if r[0] in ["PENDAPATAN", "TOTAL PENDAPATAN", "BEBAN", "TOTAL BEBAN", "PERUBAHAN ASET NETO"]: t_a.setStyle(TableStyle([('FONTNAME',(0,i),(-1,i),'Helvetica-Bold')]))
            elements.append(t_a)

            elements.append(PageBreak()); elements.append(Paragraph("C. Laporan Perubahan Aset Neto", styles['Heading3']))
            per = self.get_changes_in_net_assets_report(); p_rows = [["Uraian", "Tanpa Pembatasan", "Dengan", "Total"]]
            for r in per: p_rows.append([Paragraph(r['description'], n_style), f"{r['without_restriction']:,.0f}", f"{r['with_restriction']:,.0f}", f"{r['total']:,.0f}"])
            tp = Table(p_rows, colWidths=[3.2*inch, 1.0*inch, 1.0*inch, 1.0*inch]); tp.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey), ('ALIGN',(1,1),(-1,-1),'RIGHT'), ('FONTSIZE',(0,0),(-1,-1),8)])); elements.append(tp)
            elements.append(Spacer(1, 20)); elements.append(Paragraph("D. Laporan Arus Kas", styles['Heading3']))
            cf = self.get_cash_flow_report(); c_rows = [["Keterangan", "Jumlah (Rp)"]]
            for r in cf['report_data']: c_rows.append([Paragraph(r['Keterangan'].replace('\n',''), n_style), f"{r['Jumlah (Rp)']:,.0f}" if isinstance(r['Jumlah (Rp)'], (int, float)) else ""])
            tc = Table(c_rows, colWidths=[4.7*inch, 1.5*inch]); tc.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey), ('ALIGN',(1,1),(-1,-1),'RIGHT')])); elements.append(tc)

            # HALAMAN 5: EVALUASI LENGKAP (Termasuk Pendidikan & Dakwah)
            elements.append(PageBreak()); elements.append(Paragraph("<b>V. EVALUASI, KENDALA & RENCANA STRATEGIS</b>", styles['Heading2']))
            ev_table_data = [["No", "Evaluasi", "Kendala", "Rencana Strategis ke depan"]]
            
            # Gabungkan sumber Evaluasi: Ringkasan Umum + Pendidikan + Dakwah/Sosial
            eval_l = (settings['program_summary'] or "").split('\n')
            if settings.get('program_detail_edu'): eval_l.append(f"PENDIDIKAN: {settings['program_detail_edu']}")
            if settings.get('program_detail_social'): eval_l.append(f"DAKWAH/SOSIAL: {settings['program_detail_social']}")
            
            kend_l = (settings['evaluation_constraints'] or "").split('\n')
            renc_l = (settings['future_plans'] or "").split('\n')
            
            for i in range(max(len(eval_l), len(kend_l), len(renc_l))):
                ev_table_data.append([str(i+1), Paragraph(eval_l[i].strip("- ") if i<len(eval_l) else "-", n_style), Paragraph(kend_l[i].strip("- ") if i<len(kend_l) else "-", n_style), Paragraph(renc_l[i].strip("- ") if i<len(renc_l) else "-", n_style)])
            
            t_ev = Table(ev_table_data, colWidths=[0.4*inch, 1.9*inch, 2.0*inch, 1.9*inch]); t_ev.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.navy), ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.5,colors.grey), ('VALIGN',(0,0),(-1,-1),'TOP'), ('FONTSIZE',(0,0),(-1,-1),8)])); elements.append(t_ev)
            
            # TANDA TANGAN (Lebih lega untuk tanda tangan basah & stempel)
            elements.append(Spacer(1, 40))
            elements.append(Paragraph(f"Dicetak pada: {datetime.now().strftime('%d %B %Y')}", n_style))
            elements.append(Spacer(1, 15))
            
            # Baris 1: Pembina & Pengawas
            sig_data1 = [
                ["Menyetujui,", "Meninjau,"],
                ["Ketua Pembina", "Ketua Pengawas"],
                ["", ""], # Ruang Tanda Tangan
                [f"( {extracted['pembina']} )", f"( {extracted['pengawas']} )"]
            ]
            t_sig1 = Table(sig_data1, colWidths=[3.2*inch, 3.2*inch], rowHeights=[20, 20, 60, 20])
            t_sig1.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
            ]))
            elements.append(t_sig1)
            
            elements.append(Spacer(1, 35)) # Jarak antar baris tanda tangan
            
            # Baris 2: Ketua & Bendahara
            sig_data2 = [
                ["Mengetahui,", "Dibuat Oleh,"],
                ["Ketua Pengurus", "Bendahara"],
                ["", ""], # Ruang Tanda Tangan
                [f"( {extracted['ketua']} )", f"( {extracted['bendahara']} )"]
            ]
            t_sig2 = Table(sig_data2, colWidths=[3.2*inch, 3.2*inch], rowHeights=[20, 20, 60, 20])
            t_sig2.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('FONTNAME', (0,1), (-1,1), 'Helvetica-Bold'),
            ]))
            elements.append(t_sig2)

            doc.build(elements); return True
        except Exception as e: print(f"PDF Final Error: {e}"); return False
