import google.generativeai as genai
import json
import os
import re

class AIManager:
    def __init__(self, config_file="user_settings.json"):
        self.config_file = config_file
        self.api_key = ""
        self.model_name = "gemini-1.5-flash"
        self.load_config()
        
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    full_config = json.load(f)
                    gemini_cfg = full_config.get("gemini_config", {})
                    self.api_key = gemini_cfg.get("api_key", "")
                    self.model_name = gemini_cfg.get("model", "gemini-1.5-flash")
            except:
                pass

    def get_accounting_suggestion(self, description, detailed_accounts, cf_mapping=None):
        """
        Mengirim deskripsi transaksi dan daftar akun ke Gemini API untuk mendapatkan saran jurnal.
        """
        if not self.api_key:
            return {"error": "API Key Gemini belum diatur di user_settings.json"}

        # Format daftar akun untuk prompt dengan info tipe yang lebih jelas
        account_context = "\n".join([
            f"- {acc['code']} {acc['name']} (Tipe: {acc['type']})"
            for acc in detailed_accounts
        ])

        # Format daftar aktivitas arus kas
        cf_context = ""
        if cf_mapping:
            for main_cat, activities in cf_mapping.items():
                cf_context += f"- {main_cat}: {', '.join(activities)}\n"

        prompt = f"""
        Role: Senior Accountant for Yayasan ISAK 35.
        Objective: Convert transaction description into a precise JSON journal entry.

        DAFTAR AKUN (COA):
        {account_context}

        DAFTAR AKTIVITAS ARUS KAS TERSEDIA:
        {cf_context}

        STRICT RULES:
        1. DEBET vs KREDIT HARUS BERBEDA.
        2. NOMINAL: Ekstrak angka dari teks (misal: 15000000).
        3. CASH FLOW PLACEMENT (CRITICAL):
           - Data "arus_kas_utama" dan "arus_kas_aktivitas" WAJIB diletakkan pada baris akun yang bertipe KAS atau BANK.
           - Baris akun lawan (seperti Beban atau Peralatan) harus dikosongkan ("").
        4. PILIHAN AKTIVITAS:
           - "arus_kas_utama" WAJIB dipilih dari: "ARUS KAS DARI AKTIVITAS OPERASI", "ARUS KAS DARI AKTIVITAS INVESTASI", atau "ARUS KAS DARI AKTIVITAS PENDANAAN".
           - "arus_kas_aktivitas" WAJIB dipilih dari DAFTAR AKTIVITAS ARUS KAS TERSEDIA di atas yang paling cocok.

        FORMAT OUTPUT (JSON ONLY):
        {{
            "nominal": 0,
            "saran": [
                {{
                    "akun": "KODE - NAMA", 
                    "posisi": "Debet", 
                    "arus_kas_utama": "", 
                    "arus_kas_aktivitas": ""
                }},
                {{
                    "akun": "KODE - NAMA", 
                    "posisi": "Kredit", 
                    "arus_kas_utama": "KATEGORI", 
                    "arus_kas_aktivitas": "NAMA_DARI_DAFTAR"
                }}
            ],
            "kesimpulan": "Analisis singkat"
        }}

        DESCRIPTION: "{description}"
        """

        # Daftar model yang akan dicoba jika terjadi 404
        models_to_try = [self.model_name, "gemini-1.5-flash", "gemini-flash-latest", "gemini-2.0-flash-lite-preview-02-05"]
        
        last_error = ""
        for m_name in models_to_try:
            try:
                # Pastikan format nama benar
                full_name = m_name if m_name.startswith("models/") else f"models/{m_name}"
                model = genai.GenerativeModel(full_name)
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        response_mime_type="application/json",
                    ),
                )
                
                if response.text:
                    return json.loads(response.text)
            except Exception as e:
                last_error = str(e)
                if "404" in last_error:
                    continue # Coba model berikutnya
                else:
                    return {"error": last_error} # Jika error lain (seperti 429), langsung stop
        
        return {"error": f"Semua model gagal. Error terakhir: {last_error}"}
