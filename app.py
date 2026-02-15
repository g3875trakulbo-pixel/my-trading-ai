import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

# 1. ตั้งค่าหน้าแอปให้กว้างและปิด Sidebar
st.set_page_config(page_title="ระบบสรุปงานชีววิทยา ม.3", layout="wide", initial_sidebar_state="collapsed")

# ระบบหน่วยความจำ (Session State)
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.title("📋 ระบบสรุปการส่งงานวิชาชีววิทยา ม.3")
st.write("จัดการงาน Padlet: อัปเดตไฟล์ล่าสุดได้ที่นี่ (แสดงประวัติย้อนหลัง 10 รายการ)")
st.markdown("---")

# --- ฟังก์ชันจัดการข้อมูล ---
def clean_name_parts(raw_name):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    s = str(raw_name).strip()
    is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
    for p in prefixes: s = re.sub(p, '', s).strip()
    parts = s.split(maxsplit=1)
    fname = parts[0] if len(parts) > 0 else "-"
    lname = parts[1] if len(parts) > 1 else "-"
    return fname, lname, (not is_valid_thai or lname == "-")

def get_group_info(section_text):
    text = str(section_text)
    g_num = re.search(r'(กลุ่มที่\s*\d+)', text)
    g_name = re.search(r'\)\s*(.*)', text)
    res_num = g_num.group(1) if g_num else ""
    res_name = g_name.group(1).strip() if g_name else ""
    return f"{res_num} {res_name}".strip() if res_num and res_name else (res_num or res_name or text)

# --- ส่วนอัปโหลดไฟล์ (แสดงเดี่ยวๆ เพื่อความคลีน) ---
uploaded_file = st.file_uploader("📥 อัปโหลดไฟล์เพื่อ Update ข้อมูลล่าสุด (CSV หรือ Excel)", type=["csv", "xlsx", "xls"])

# ประมวลผลเมื่อมีการอัปโหลด
if uploaded_file:
    try:
        raw_bytes = uploaded_file.getvalue()
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(raw_bytes))
            
        df.columns = [str(c).strip() for c in df.columns]
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]

        temp_results = []
        for _, row in df.iterrows():
            txt = f"{row.get('เรื่อง', '')} {row.get('เนื้อหา', '')}"
            st_no = re.search(r'เลขที่\s*(\d+)', txt)
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', txt)
            raw_name = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
            fname, lname, is_unk = clean_name_parts(raw_name)
            act = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            
            temp_results.append({
                'เลขที่': st_no.group(1) if st_no else "-",
                'ชื่อ': fname, 'นามสกุล': lname,
                'ชื่อกลุ่ม': get_group_info(row.get('ส่วน', '')),
                'กิจกรรม': act.group(1) if act else None,
                'สถานะ': '✓', 'is_unknown': is_unk
            })
        
        new_df = pd.DataFrame(temp_results)
        st.session_state['processed_data'] = new_df
        
        # บันทึกประวัติ (10 รายการล่าสุด)
        current_time = datetime.now().strftime("%H:%M:%S (%d/%m)")
        st.session_state['history'].append({
            "file": uploaded_file.name,
            "time": current_time,
            "raw_file": raw_bytes
        })
        
        if len(st.session_state['history']) > 10:
            st.session_state['history'] = st.session_state['history'][-10:]
            
        st.success(f"อัปเดตข้อมูลสำเร็จจากไฟล์ {uploaded_file.name}")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- ส่วนประวัติการอัปโหลด (อยู่ใต้ช่องอัปโหลดทันที) ---
if st.session_state['history']:
    with st.expander(f"📜 ประวัติการอัปโหลด ({len(st.session_state['history'])} รายการล่าสุด)", expanded=True):
        for idx, item in enumerate(reversed(st.session_state['history'])):
            h_col1, h_col2, h_col3 = st.columns([3, 2, 1])
            with h_col1:
                st.write(f"📄 {item['file']}")
            with h_col2:
                st.caption(f"🕒 {item['time']}")
            with h_col3:
                st.download_button(
                    label="📥 โหลดต้นฉบับ",
                    data=item['raw_file'],
                    file_name=item['file'],
                    key=f"hist_{idx}"
                )

# --- ส่วนตารางสรุปผล ---
if st.session_state['processed_data'] is not None:
    res_df = st.session_state['processed_data']
    st.markdown("---")
    
    st.subheader("✅ 1. ตารางสรุปการส่งงาน ม.3 (ล่าสุด)")
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม']).pivot(
            index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
            columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
        
        def sort_logic(row):
            no = int(row['เลขที่']) if str(row['เลขที่']).isdigit() else 999
            return (row['is_unknown'], no, row['ชื่อ'])

        pivot['sort_key'] = pivot.apply(sort_logic, axis=1)
        pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
        st.dataframe(pivot, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pivot.to_excel(writer, index=False)
        st.download_button(label="📥 ดาวน์โหลดตารางสรุปเป็น Excel", data=output.getvalue(), file_name="สรุปงาน_ม3.xlsx")

    # ตารางตรวจสอบงานที่ไม่ได้ระบุกิจกรรม
    st.markdown("---")
    st.subheader("⚠️ 2. ตารางตรวจสอบ (ลืมระบุเลขกิจกรรม)")
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงาน')
        summ_no['sort_key'] = summ_no.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        st.table(summ_no.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key']))
