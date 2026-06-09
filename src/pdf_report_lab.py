from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

class AnnualReportPDF:
    def __init__(self, data):
        self.data = data
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        def add_or_replace_style(style):
            if style.name in self.styles:
                self.styles.byName[style.name] = style
            else:
                self.styles.add(style)

        add_or_replace_style(ParagraphStyle(name='TitleBold', fontSize=16, alignment=TA_CENTER, spaceAfter=2, fontName='Helvetica-Bold'))
        add_or_replace_style(ParagraphStyle(name='SubTitle', fontSize=10, alignment=TA_CENTER, spaceAfter=10, fontName='Helvetica'))
        add_or_replace_style(ParagraphStyle(name='Heading2', fontSize=12, spaceBefore=15, spaceAfter=10, fontName='Helvetica-Bold', color=colors.HexColor("#2C3E50")))
        add_or_replace_style(ParagraphStyle(name='BodyTextIndent', fontSize=10, leftIndent=20, spaceAfter=5))
        add_or_replace_style(ParagraphStyle(name='TableCell', fontSize=9, fontName='Helvetica'))
        add_or_replace_style(ParagraphStyle(name='TableCellBold', fontSize=9, fontName='Helvetica-Bold'))
        add_or_replace_style(ParagraphStyle(name='TableNumber', fontSize=9, alignment=TA_RIGHT, fontName='Helvetica'))
        add_or_replace_style(ParagraphStyle(name='TableNumberBold', fontSize=9, alignment=TA_RIGHT, fontName='Helvetica-Bold'))

    def format_idr(self, value):
        if value is None: return "0"
        return "{:,.0f}".format(value).replace(",", ".")

    def generate(self, output_path):
        doc = SimpleDocTemplate(output_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        elements = []

        # 1. Header & Profil
        profile = self.data['profile']
        elements.append(Paragraph(profile['name'], self.styles['TitleBold']))
        elements.append(Paragraph(profile['address'], self.styles['SubTitle']))
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph(f"LAPORAN TAHUNAN {profile['year']}", self.styles['TitleBold']))
        elements.append(Spacer(1, 1*cm))

        elements.append(Paragraph("I. VISI & MISI", self.styles['Heading2']))
        elements.append(Paragraph(f"<b>Visi:</b> {profile['vision']}", self.styles['Normal']))
        elements.append(Spacer(1, 0.2*cm))
        elements.append(Paragraph("<b>Misi:</b>", self.styles['Normal']))
        
        mission_items = profile.get('mission', '')
        if mission_items:
            # Menangani newline dari berbagai OS (\r\n atau \n)
            lines = [l.strip() for l in mission_items.replace('\r\n', '\n').split('\n') if l.strip()]
            misi_list = [ListItem(Paragraph(m, self.styles['Normal'])) for m in lines]
            elements.append(ListFlowable(misi_list, bulletType='bullet', leftIndent=20))
        else:
            elements.append(Paragraph("-", self.styles['Normal']))

        # 2. Struktur Organisasi
        elements.append(Paragraph("II. STRUKTUR ORGANISASI", self.styles['Heading2']))
        org_data = [["Posisi", "Nama"]]
        for member in self.data['organization']:
            org_data.append([member['position'], member['name']])
        
        t_org = Table(org_data, colWidths=[6*cm, 10*cm])
        t_org.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#ECF0F1")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        elements.append(t_org)

        # 3. Kinerja Program
        elements.append(Paragraph("III. KINERJA PROGRAM", self.styles['Heading2']))
        
        # Ringkasan Umum
        perf_summary = self.data.get('performance', "")
        if perf_summary:
            elements.append(Paragraph(perf_summary, self.styles['Normal']))
            elements.append(Spacer(1, 0.3*cm))

        # Detail Program
        for title, key in [("Bidang Pendidikan", "program_edu"), ("Bidang Sosial & Keagamaan", "program_social")]:
            detail = self.data.get(key, "")
            if detail:
                elements.append(Paragraph(f"<b>{title}:</b>", self.styles['Normal']))
                lines = [l.strip() for l in detail.split('\n') if l.strip()]
                items = [ListItem(Paragraph(l, self.styles['Normal'])) for l in lines]
                elements.append(ListFlowable(items, bulletType='bullet', leftIndent=25))
                elements.append(Spacer(1, 0.2*cm))

        elements.append(PageBreak())

        # 4. Laporan Keuangan (ISAK 35)
        elements.append(Paragraph("IV. LAPORAN KEUANGAN", self.styles['Heading2']))
        
        # --- A. Posisi Keuangan ---
        elements.append(Paragraph("A. Laporan Posisi Keuangan", self.styles['Normal']))
        elements.append(Spacer(1, 0.2*cm))
        
        pos = self.data['financials']['position']
        pos_data = [[Paragraph("<b>AKUN</b>", self.styles['TableCellBold']), Paragraph("<b>SALDO (RP)</b>", self.styles['TableCellBold'])]]
        
        # Assets
        pos_data.append([Paragraph("<b>ASET</b>", self.styles['TableCellBold']), ""])
        for a in pos.get('assets', []):
            pos_data.append([Paragraph(a['name'], self.styles['TableCell']), Paragraph(self.format_idr(a['balance']), self.styles['TableNumber'])])
        pos_data.append([Paragraph("TOTAL ASET", self.styles['TableCellBold']), Paragraph(self.format_idr(pos.get('total_assets', 0)), self.styles['TableNumberBold'])])
        
        # Liabilities
        pos_data.append([Paragraph("<b>LIABILITAS</b>", self.styles['TableCellBold']), ""])
        for l in pos.get('liabilities', []):
            pos_data.append([Paragraph(l['name'], self.styles['TableCell']), Paragraph(self.format_idr(l['balance']), self.styles['TableNumber'])])
        pos_data.append([Paragraph("TOTAL LIABILITAS", self.styles['TableCellBold']), Paragraph(self.format_idr(pos.get('total_liabilities', 0)), self.styles['TableNumberBold'])])
        
        # Net Assets
        pos_data.append([Paragraph("<b>ASET NETO</b>", self.styles['TableCellBold']), ""])
        pos_data.append([Paragraph("Tanpa Pembatasan", self.styles['TableCell']), Paragraph(self.format_idr(pos.get('net_assets_without', 0)), self.styles['TableNumber'])])
        pos_data.append([Paragraph("Dengan Pembatasan", self.styles['TableCell']), Paragraph(self.format_idr(pos.get('net_assets_with', 0)), self.styles['TableNumber'])])
        pos_data.append([Paragraph("TOTAL ASET NETO", self.styles['TableCellBold']), Paragraph(self.format_idr(pos.get('total_net_assets', 0)), self.styles['TableNumberBold'])])

        t_pos = Table(pos_data, colWidths=[11*cm, 5*cm])
        t_pos.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('BACKGROUND', (0,0), (1,0), colors.HexColor("#F9F9F9")),
        ]))
        elements.append(t_pos)
        elements.append(Spacer(1, 0.5*cm))

        # --- B. Laporan Aktivitas ---
        elements.append(Paragraph("B. Laporan Aktivitas", self.styles['Normal']))
        act = self.data['financials']['activities']
        act_data = [[Paragraph("<b>KETERANGAN</b>", self.styles['TableCellBold']), Paragraph("<b>JUMLAH (RP)</b>", self.styles['TableCellBold'])]]
        act_data.append([Paragraph("TOTAL PENDAPATAN", self.styles['TableCellBold']), Paragraph(self.format_idr(act.get('total_rev', 0)), self.styles['TableNumberBold'])])
        act_data.append([Paragraph("TOTAL BEBAN", self.styles['TableCellBold']), Paragraph(self.format_idr(act.get('total_exp', 0)), self.styles['TableNumberBold'])])
        act_data.append([Paragraph("SURPLUS / (DEFISIT)", self.styles['TableCellBold']), Paragraph(self.format_idr(act.get('total_change', 0)), self.styles['TableNumberBold'])])
        
        t_act = Table(act_data, colWidths=[11*cm, 5*cm])
        t_act.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ]))
        elements.append(t_act)
        elements.append(Spacer(1, 0.5*cm))

        # --- C. Laporan Arus Kas ---
        elements.append(Paragraph("C. Laporan Arus Kas", self.styles['Normal']))
        cf = self.data['financials']['cash_flow']
        cf_data = [[Paragraph("<b>AKTIVITAS</b>", self.styles['TableCellBold']), Paragraph("<b>JUMLAH (RP)</b>", self.styles['TableCellBold'])]]
        for row in cf:
            if row['Jumlah (Rp)'] == "":
                cf_data.append([Paragraph(f"<b>{row['Keterangan']}</b>", self.styles['TableCellBold']), ""])
            else:
                cf_data.append([Paragraph(row['Keterangan'], self.styles['TableCell']), Paragraph(self.format_idr(row['Jumlah (Rp)']), self.styles['TableNumber'])])
        
        t_cf = Table(cf_data, colWidths=[11*cm, 5*cm])
        t_cf.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ]))
        elements.append(t_cf)

        # 5. Evaluasi & Kendala
        elements.append(Paragraph("V. EVALUASI & RENCANA TINDAK LANJUT", self.styles['Heading2']))
        eval_text = self.data.get('evaluation', "")
        future_plans = self.data.get('future_plans', "")
        
        eval_data = [["No", "Deskripsi Kendala / Rencana"]]
        
        # Gabungkan semua baris dari evaluasi dan rencana masa depan
        all_lines = []
        if eval_text:
            all_lines.extend([l.strip() for l in eval_text.replace('\r\n', '\n').split('\n') if l.strip()])
        if future_plans:
            all_lines.extend([l.strip() for l in future_plans.replace('\r\n', '\n').split('\n') if l.strip()])

        if all_lines:
            for i, line in enumerate(all_lines, 1):
                eval_data.append([str(i), Paragraph(line, self.styles['TableCell'])])
        else:
            eval_data.append(["-", "-"])
        
        t_eval = Table(eval_data, colWidths=[1*cm, 15*cm])
        t_eval.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#ECF0F1")),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('TOPPADDING', (0,1), (-1,-1), 5),
            ('BOTTOMPADDING', (0,1), (-1,-1), 5),
        ]))
        elements.append(t_eval)

        # 6. Signature Block
        elements.append(Spacer(1, 2*cm))
        
        def get_name(pos_name):
            for m in self.data['organization']:
                if pos_name.lower() in m['position'].lower():
                    return m['name']
            return "................"

        # Ambil nama yang diperlukan (Pembina dihapus sesuai permintaan)
        ketua_pengurus = get_name("Ketua Pengurus")
        if ketua_pengurus == "................":
            ketua_pengurus = get_name("Ketua Umum") # Support variasi nama jabatan
            
        ketua_pengawas = get_name("Ketua Pengawas")
        bendahara_name = get_name("Bendahara")

        # Susunan Tanda Tangan:
        # Atas: [Kosong, Pengawas]
        # Bawah: [Pengurus, Bendahara]
        sig_data = [
            ["", "Meninjau,"],
            ["", "Ketua Pengawas"],
            ["", ""],
            ["", ""],
            ["", f"( {ketua_pengawas} )"],
            ["", Spacer(1, 1*cm)], # Spasi pemisah baris atas dan bawah
            ["Mengetahui,", Paragraph(f"<font size='8'>Dibuat Oleh: {bendahara_name}</font>", self.styles['Normal'])],
            ["Ketua Pengurus", "Bendahara"],
            ["", ""],
            ["", ""],
            [f"( {ketua_pengurus} )", f"( {bendahara_name} )"]
        ]
        
        t_sig = Table(sig_data, colWidths=[8*cm, 8*cm])
        t_sig.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,2), (-1,2), 30), # Ruang tanda tangan baris atas
            ('BOTTOMPADDING', (0,8), (-1,8), 30), # Ruang tanda tangan baris bawah
        ]))
        elements.append(t_sig)

        doc.build(elements)
        return True
