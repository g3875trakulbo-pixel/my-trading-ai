import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปงาน Padlet ม.3", layout="wide")

st.title("📋 ระบบสรุปการส่งงานชีววิทยา")
st.markdown("---")

# ฟังก์ชันล้างคำนำหน้าชื่อและแยก ชื่อ-นามสกุล
def clean_name(raw_text):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    s = str(raw_text).strip()
    for p in prefixes:
        s = re.sub(p, '', s).strip()
    
    parts = s.split(maxsplit=1)
    f_name = parts[0] if len(parts) > 0 else "-"
    l_name = parts[1] if len(parts) > 1 else "-"
    return f_name, l_name

# ส่วนการอัปโหลดไฟล์
file = st.file_uploader("อัปโหลดไฟล์ CSV จาก Padlet (ไฟล์โพสต์)", type=["csv"])

if file:
    try:
        # อ่านไฟล์รองรับภาษาไทย
        df = pd.read_csv(file, encoding='utf-8-sig')
        df.columns = [str(c).strip() for c in df.columns]

        # กรองโพสต์คุณครูออก
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]

        final_data = []
        for _, row in df.iterrows():
            subject = str(row.get('เรื่อง', ''))
            content = str(row.get('เนื้อหา', ''))
            txt = subject + " " + content
            
            # ดึงเลขที่
            n_match = re.search(r'เลขที่\s*(\d+)', txt)
            st_no = n_match.group(1) if n_match else "-"
            
            # ดึงชื่อ
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.)\s*([^\s\d]+)\s+([^\s\d]+)', txt)
            full_raw = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0]
            fname, lname = clean_name(full_raw)
            
            # ดึงกลุ่ม
            part_txt = str(row.get('ส่วน', ''))
            g_num = re.search(r'(กลุ่มที่\s*\d+)', part_txt)
            g_name = re.search(r'\)\s*(.*)', part_txt)
            g_full = f"{g_num.group(1) if g_num else ''} {g_name.group(1).strip() if g_name else part_txt}".strip()
            
            # ดึงกิจกรรม
            a_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            act_id = a_match.group(1) if a_match else None
            
            final_data.append({
                'เลขที่': st_no,
                'ชื่อ': fname,
                'นามสกุล': lname,
                'ชื่อกลุ่ม': g_full,
                'กิจกรรม': act_id,
                'สถานะ': '✓'
            })
            
        res_df = pd.DataFrame(final_data)

        # --- ตารางที่ 1: สรุปคนระบุกิจกรรม ---
        st.subheader("✅ 1. ตารางสรุปการส่งงาน (แยกกิจกรรม)")
        df_ok = res_df[res_df['กิจกรรม'].notna()]
        
        if not df_ok.empty:
            df_ok = df_ok.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม'])
            pivot = df_ok.pivot(
                index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'], 
                columns='กิจกรรม', 
                values='สถานะ'
            ).fillna('-')
            st.dataframe(pivot, use_container_width=True)
            
            # เตรียมไฟล์ Excel สำหรับดาวน์โหลด
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pivot.to_excel(writer, sheet_name='Summary')
            excel_data = output.getvalue()
            st.download_button(
                label="📥 ดาวน์โหลดตารางสรุปเป็น Excel",
                data=excel_data,
                file_name="สรุปส่งงาน_ชีววิทยา.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("ไม่พบการระบุกิจกรรมในไฟล์")

        # --- ตารางที่ 2: ส่งงานแต่ไม่รู้จักกิจกรรม ---
        st.markdown("---")
        st.subheader("❓ 2. ตารางท้ายสุด (ส่งงานแล้วแต่ไม่ได้พิมพ์เลขกิจกรรม)")
        df_unk = res_df[res_df['กิจกรรม'].isna()].drop(columns=['กิจกรรม', 'สถานะ'])
        df_unk = df_unk.drop_duplicates(subset=['ชื่อ', 'นามสกุล'])
        
        def sort_key(v):
            try: return int(v)
            except: return 999
        df_unk['sort'] = df_unk['เลขที่'].apply(sort_key)
        df_unk = df_unk.sort_values('sort').drop(columns='sort')
        
        st.table(df_unk)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
