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
if 'current_file_name' not in st.session_state:
    st.session_state['current_file_name'] = ""

st.title("📋 ระบบสรุปการส่งงานวิชาชีววิทยา ม.3")
st.write("จัดการงาน Padlet: อัปเดตไฟล์ใหม่ หรือคลิกดึงไฟล์เก่าจากประวัติมาสรุปผลใหม่ได้ทันที")
st.markdown("---")

# --- ฟังก์ชันหลักในการประมวลผลข้อมูล ---
def process_padlet_file(raw_bytes, file_name):
    try:
        if file_name.endswith('.csv'):
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
            
            # จัดการชื่อ
            raw_name = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
            prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
            s = raw_name
            is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
            for p in prefixes: s = re.sub(p, '', s).strip()
            parts = s.split(maxsplit=1)
            fname = parts[0] if len(parts) > 0 else "-"
            lname = parts[1] if len(parts) > 1 else "-"
            
            # จัดการกลุ่ม
            sec_txt = str(row.get('ส่วน', ''))
            g_num = re.search(r'(กลุ่มที่\s*\d+)', sec_txt)
            g_name = re.search(r'\)\s*(.*)', sec_txt)
            group_display = f"{g_num.group(1) if g_num else ''} {g_name.group(1).strip() if g_name else sec_txt}".strip()
            
            # กิจกรรม
            act = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            
            temp_results.append({
                'เลขที่': st_no.group(1) if st_no else "-",
                'ชื่อ': fname, 'นามสกุล': lname,
                'ชื่อกลุ่ม': group_display,
                'กิจกรรม': act.group(1) if act else None,
                'สถานะ': '✓', 'is_unknown': (not is_valid_thai or lname == "-")
            })
        return pd.DataFrame(temp_results)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการประมวลผล: {e}")
        return None

# --- ส่วนอัปโหลดไฟล์ใหม่ ---
uploaded_file = st.file_uploader("📥 อัปโหลดไฟล์เพื่อ Update ข้อมูลล่าสุด (CSV หรือ Excel)", type=["csv", "xlsx", "xls"])

if uploaded_file:
    raw_bytes = uploaded_file.getvalue()
    result_df = process_padlet_file(raw_bytes, uploaded_file.name)
    if result_df is not None:
        st.session_state['processed_data'] = result_df
        st.session_state['current_file_name'] = uploaded_file.name
        current_time = datetime.now().strftime("%H:%M:%S (%d/%m)")
        
        # บันทึกเข้าประวัติ (กันการซ้ำซ้อนในวินาทีเดียวกัน)
        if not st.session_state['history'] or st.session_state['history'][-1]['file'] != uploaded_file.name:
            st.session_state['history'].append({
                "file": uploaded_file.name,
                "time": current_time,
                "raw_file": raw_bytes
            })
        if len(st.session_state['history']) > 10:
            st.session_state['history'] = st.session_state['history'][-10:]
        st.success(f"อัปเดตข้อมูลสำเร็จจากไฟล์ {uploaded_file.name}")

# --- ส่วนประวัติ 10 รายการล่าสุด (เหลือแค่ปุ่มดึงข้อมูลกลับมา) ---
if st.session_state['history']:
    with st.expander(f"📜 ประวัติการอัปโหลด ({len(st.session_state['history'])} รายการล่าสุด) - คลิกปุ่มเพื่อดึงข้อมูลไฟล์เก่ามาแสดง", expanded=True):
        for idx, item in enumerate(reversed(st.session_state['history'])):
            h_col1, h_col2, h_col3 = st.columns([5, 3, 2])
            with h_col1:
                st.write(f"📄 {item['file']}")
            with h_col2:
                st.caption(f"🕒 {item['time']}")
            with h_col3:
                if st.button("🔄 ดึงมาแสดง", key=f"restore_{idx}"):
                    st.session_state['processed_data'] = process_padlet_file(item['raw_file'], item['file'])
                    st.session_state['current_file_name'] = item['file']
                    st.rerun()

# --- ส่วนตารางสรุปผล ---
if st.session_state['processed_data'] is not None:
    res_df = st.session_state['processed_data']
    st.markdown("---")
    
    # แสดงชื่อไฟล์ที่กำลังประมวลผลอยู่เพื่อให้คุณครูไม่สับสน
    st.subheader(f"✅ 1. ตารางสรุปการส่งงาน ม.3 (จากไฟล์: {st.session_state['current_file_name']})")
    
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม']).pivot(
            index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
            columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
        
        # เรียงลำดับ: คนปกติขึ้นก่อน > เลขที่ > ชื่อ
        def sort_logic(row):
            no = int(row['เลขที่']) if str(row['เลขที่']).isdigit() else 999
            return (row['is_unknown'], no, row['ชื่อ'])

        pivot['sort_key'] = pivot.apply(sort_logic, axis=1)
        pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
        
        st.dataframe(pivot, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pivot.to_excel(writer, index=False)
        st.download_button(label="📥 ดาวน์โหลดตารางสรุปเป็น Excel", data=output.getvalue(), file_name=f"สรุปงาน_ม3_{st.session_state['current_file_name']}.xlsx")

    # ตารางตรวจสอบงานที่ไม่ได้ระบุกิจกรรม
    st.markdown("---")
    st.subheader("⚠️ 2. ตารางตรวจสอบ (ลืมระบุเลขกิจกรรม)")
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงาน')
        summ_no['sort_key'] = summ_no.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        st.table(summ_no.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key']))
