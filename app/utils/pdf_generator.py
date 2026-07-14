import os
from pathlib import Path
from fpdf import FPDF
from typing import List, Dict, Any
from datetime import datetime

def format_rupiah(amount: float) -> str:
    """Format number to Indonesian Rupiah standard."""
    # Handle decimals by rounding, then format with comma and dots
    return f"Rp {amount:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def format_indo_date(dt_str: str) -> str:
    """Parse ISO date string and format to Indonesian readable string."""
    try:
        dt = datetime.fromisoformat(dt_str)
        months = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", 
                  "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
        return f"{dt.day} {months[dt.month]} {dt.year}, {dt.strftime('%H:%M')} WIB"
    except Exception:
        return dt_str


def generate_liquidation_pdf(
    family_id: str,
    family_name: str,
    member_names: List[str],
    personal_assets: List[Dict[str, Any]],
    joint_assets: List[Dict[str, Any]],
    total_joint: float,
    claim_per_person: float,
    timestamp: str,
    doc_number: str
) -> str:
    """
    Generate PDF Berita Acara for family unlink/liquidation.
    
    Data should be passed as dictionaries (DTOs) to avoid DetachedInstanceError from SQLAlchemy.
    """
    # BASE_DIR calculation based on the location of this file
    # this file is at app/utils/pdf_generator.py
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    
    # Static reports directory
    static_dir = BASE_DIR / "app" / "static" / "reports"
    os.makedirs(static_dir, exist_ok=True)
    
    filename = f"berita-acara-{family_id}-{timestamp.replace(':', '').replace('-', '')}.pdf"
    file_path = static_dir / filename
    
    # Relative path to return (URL)
    relative_url = f"/static/reports/{filename}"
    
    pdf = FPDF()
    pdf.add_page()
    
    # Set title and general font
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "BERITA ACARA LIKUIDASI AKUN KELUARGA", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    
    pdf.set_font("helvetica", "", 11)
    
    # Document Info
    pdf.cell(50, 8, "Nomor Dokumen", border=0)
    pdf.cell(5, 8, ":", border=0)
    pdf.cell(0, 8, doc_number, border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(50, 8, "Tanggal Dihasilkan", border=0)
    pdf.cell(5, 8, ":", border=0)
    
    formatted_date = format_indo_date(timestamp)
    pdf.cell(0, 8, formatted_date, border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(50, 8, "Nama Keluarga", border=0)
    pdf.cell(5, 8, ":", border=0)
    pdf.cell(0, 8, family_name, border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(50, 8, "Anggota Keluarga", border=0)
    pdf.cell(5, 8, ":", border=0)
    pdf.cell(0, 8, ", ".join(member_names), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # Personal Assets
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "1. Aset Pribadi (Personal Assets)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    
    if personal_assets:
        # Group by owner in dictionary
        grouped_personal = {}
        for asset in personal_assets:
            owner = asset.get('owner_name', 'Unknown')
            if owner not in grouped_personal:
                grouped_personal[owner] = []
            grouped_personal[owner].append(asset)
            
        for owner, assets in grouped_personal.items():
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(0, 8, f"Pemilik: {owner}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 11)
            for asset in assets:
                pdf.cell(10, 6, "-", border=0)
                val_str = format_rupiah(float(asset.get('valuation', 0)))
                pdf.cell(0, 6, f"{asset.get('asset_name')} (Valuasi: {val_str})", border=0, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
    else:
        pdf.cell(0, 8, "Tidak ada aset pribadi terdaftar.", new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(3)
        
    # Joint Assets
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "2. Aset Bersama (Joint Assets)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    
    if joint_assets:
        for asset in joint_assets:
            pdf.cell(10, 6, "-", border=0)
            val_str = format_rupiah(float(asset.get('valuation', 0)))
            pdf.cell(0, 6, f"{asset.get('asset_name')} (Valuasi: {val_str})", border=0, new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 8, "Tidak ada aset bersama terdaftar.", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(5)
    
    # Financial Summary
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "3. Ringkasan Finansial Aset Bersama", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 11)
    
    pdf.cell(60, 8, "Total Valuasi Aset Bersama", border=0)
    pdf.cell(5, 8, ":", border=0)
    pdf.cell(0, 8, format_rupiah(total_joint), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.cell(60, 8, "Klaim Per Orang (50:50)", border=0)
    pdf.cell(5, 8, ":", border=0)
    pdf.cell(0, 8, format_rupiah(claim_per_person), border=0, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(10)
    
    # Liquidation Statement
    pdf.set_font("helvetica", "B", 11)
    pdf.multi_cell(0, 6, "Pernyataan Likuidasi:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "I", 10)
    statement = (
        "Dengan diterbitkannya dokumen Berita Acara ini, tautan akun keluarga pada aplikasi Seharta dinyatakan "
        "telah diputuskan secara resmi. Seluruh data entitas keluarga, serta data kepemilikan aset secara logis "
        "telah dihapus dari sistem dan tidak dapat dipulihkan. Rincian nilai dan distribusi aset seperti yang "
        "tercantum dalam dokumen ini adalah final sesuai dengan snapshot pada saat tautan diputuskan."
    )
    pdf.multi_cell(0, 6, statement, new_x="LMARGIN", new_y="NEXT")
    
    # Recommendations
    pdf.ln(5)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, "REKOMENDASI PENYELESAIAN (Merujuk UU No. 1 Tahun 1974)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 8)
    
    claim_rupiah = format_rupiah(claim_per_person)
    
    pdf.multi_cell(0, 5, "1. Harta Bawaan mutlak kembali pada penguasaan masing-masing pemilik asalnya.", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5, f"2. Untuk Harta Bersama, masing-masing pihak memiliki hak klaim senilai {claim_rupiah}.", new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(2)
    pdf.multi_cell(0, 5, "Penyelesaian hak untuk Harta Bersama dapat dilakukan melalui musyawarah dengan alternatif:", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5, "   - Aset bersama dilikuidasi (dijual) dan hasil tunai dibagi dua secara proporsional.", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 5, f"   - Salah satu pihak mengambil alih aset fisik dan membayarkan kompensasi tunai sebesar {claim_rupiah} kepada pihak lainnya.", new_x="LMARGIN", new_y="NEXT")
    
    # Reset styling
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 11)

    
    # Save the document
    pdf.output(str(file_path))
    
    return relative_url
