from src.database_manager import DatabaseManager
from src.report_generator import ReportGenerator

def verify():
    db = DatabaseManager('database/foundation_finance.db')
    report = ReportGenerator(db)
    
    print("=== VERIFIKASI LAPORAN ISAK 35 ===\n")
    
    # 1. Laporan Posisi Keuangan
    pos = report.get_isak35_financial_position()
    print("--- LAPORAN POSISI KEUANGAN ---")
    print(f"Total Aset: Rp {pos['total_assets']:,.0f}")
    print(f"Total Liabilitas: Rp {pos['total_liabilities']:,.0f}")
    print(f"Aset Neto Tanpa Pembatasan: Rp {pos['net_assets_without']:,.0f}")
    print(f"Aset Neto Dengan Pembatasan: Rp {pos['net_assets_with']:,.0f}")
    print(f"Total Aset Neto: Rp {pos['total_net_assets']:,.0f}")
    print("-" * 30)
    
    # 2. Laporan Penghasilan Komprehensif
    inc = report.get_comprehensive_income()
    print("\n--- LAPORAN PENGHASILAN KOMPREHENSIF ---")
    print(f"Total Pendapatan: Rp {inc['total_revenue']:,.0f}")
    print(f"Total Beban: Rp {inc['total_expenses']:,.0f}")
    surplus = inc['total_revenue'] - inc['total_expenses']
    print(f"Surplus/Defisit: Rp {surplus:,.0f}")
    print("-" * 30)

if __name__ == "__main__":
    verify()
