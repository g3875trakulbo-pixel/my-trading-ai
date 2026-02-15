import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปงานชีววิทยา ม.3", layout="wide")

# ระบบหน่วยความจำ (Session State)
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None
if 'history' not in st.session_state:
    st.session_state['history'] = []

st.title("📋 ระบบสรุปการส่งงานวิชาชีววิทยา ม.3")
st.write("จัดการสรุปงาน Padlet: เรียงเลขที่ แยกกลุ่ม และเก็บประวัติการอัปเดต")
st.markdown("---")

# --- ฟังก์ชันจัดการข้อมูล (เสถียรและแม่นยำ) ---
def clean_name_parts(raw_name):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    s = str(raw_name).strip()
    is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
    for p in prefixes: 
        s = re.sub(p, '', s).strip()
    parts = s.split(maxsplit=1)
    fname = parts[0] if len(parts) > 0 else "-"
    lname = parts[1] if len(parts) > 1 else "-"
    # ถ้าไม่มีนามสกุลหรือชื่อไม่ใช่ภาษาไทย ให้ถือว่าระบุตัวตนยาก
    is_unk = not is_valid_thai or lname == "-"
    return fname, lname, is_unk

def get_group_info(section_text):
    text = str(section_text)
    g_num = re.search(r'(กลุ่มที่\s*\d+)', text)
    g_name = re.search(r'\)\s*(.*)', text)
    res_num = g_num.group(1) if g_num else ""
    res_name = g_name.group(1).strip() if g_name else ""
    if res_num and res_name:
        return f"{res_num} {res_name}"
    return res_num or res_name or text

# --- Sidebar: ส่วนควบคุมและแสดงประวัติไล่ลำดับ ---
with st.sidebar:
    st.header("⚙️ เมนูจัดการ")
    if st.button("🗑️ ล้างประวัติและข้อมูลทั้งหมด"):
        st.session_state['processed_data'] = None
        st.session_state['history'] = []
        st.rerun()
    
    st.markdown("---")
    st.subheader("📜 ประวัติการอัปเดต")
    if st.session_state['history']:
        # เรียงประวัติจากใหม่ไปเก่า
        for item in reversed(st.session_state['history']):
            with st.expander(f"📄 {item['file']}"):
                st.caption(f"🕒 เวลา: {item['time']}")
                st.caption(f"📊 ตรวจพบ: {item['count']} รายการ")
    else:
        st.write("ยังไม่มีประวัติการอัปเดต")

# --- ส่วนอัปโหลดไฟล์ (คงไว้ตลอดเวลาเพื่อการ Update) ---
uploaded_file = st.file_uploader("📥 อัปโหลดไฟล์เพื่ออัปเดตข้อมูล (CSV หรือ Excel)", type=["csv", "xlsx", "xls"])

if uploaded_file:
    try:
        # อ่านไฟล์
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        else:
            df = pd.read_excel(uploaded_file)
            
        df.columns = [str(c).strip() for c in df.columns]
        
        # กรองโพสต์คุณครูออก
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]

        temp_results = []
        for _, row in df.iterrows():
            sub = str(row.get('เรื่อง', ''))
            con = str(row.get('เนื้อหา', ''))
            txt = f"{sub} {con}"
            
            # ดึงเลขที่
            n_match = re.search(r'เลขที่\s*(\d+)', txt)
            st_no = n_match.group(1) if n_match else "-"
            
            # ดึงชื่อ
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', txt)
            raw_name = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
            fname, lname, is_unk = clean_name_parts(raw_name)
            
            # ดึงเลขกิจกรรม
            a_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            act_id = a_match.group(1) if a_match else None
            
            temp_results.append({
                'เลขที่': st_no, 
                'ชื่อ': fname, 
                'นามสกุล': lname,
                'ชื่อกลุ่ม': get_group_info(row.get('ส่วน', '')),
                'กิจกรรม': act_id,
                'สถานะ': '✓', 
                'is_unknown': is_unk
            })
        
        # บันทึกข้อมูลล่าสุดลง Session
        new_df = pd.DataFrame(temp_results)
        st.session_state['processed_data'] = new_df
        
        # บันทึกประวัติ
        current_time = datetime.now().strftime("%H:%M:%S (%d/%m)")
        # ตรวจสอบเพื่อไม่ให้บันทึกซ้ำซ้อนกันมากเกินไป
        if not st.session_state['history'] or st.session_state['history'][-1]['time'] != current_time:
            st.session_state['history'].append({
                "file": uploaded_file.name, 
                "time": current_time,
                "count": len(new_df)
            })
        
        st.success(f"อัปเดตข้อมูลจากไฟล์ {uploaded_file.name} เรียบร้อยแล้ว!")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")

# --- ส่วนแสดงผลตาราง (จากหน่วยความจำล่าสุด) ---
if st.session_state['processed_data'] is not None:
    res_df = st.session_state['processed_data']
    st.markdown("---")
    
    # 1. ตารางสรุปรายกิจกรรม
    st.subheader("✅ 1. ตารางสรุปการส่งงาน ม.3 (ล่าสุด)")
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        df_act = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม'])
        pivot = df_act.pivot(index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
                            columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
        
        # เรียงลำดับ: คนปกติขึ้นก่อน > เลขที่ > ชื่อ
        def sort_logic(row):
            no = int(row['เลขที่']) if str(row['เลขที่']).isdigit() else 999
            return (row['is_unknown'], no, row['ชื่อ'])

        pivot['sort_key'] = pivot.apply(sort_logic, axis=1)
        pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
        
        st.dataframe(pivot, use_container_width=True)

        # ปุ่มดาวน์โหลด Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pivot.to_excel(writer, index=False, sheet_name='Summary_M3')
        st.download_button(label="📥 ดาวน์โหลดไฟล์สรุปเป็น Excel", data=output.getvalue(), file_name="สรุปส่งงาน_ม3_ล่าสุด.xlsx")

    # 2. ตารางคนไม่ระบุกิจกรรม
    st.markdown("---")
    st.subheader("⚠️ 2. ตารางตรวจสอบ (นับจำนวนงานที่ไม่ระบุเลขกิจกรรม)")
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงาน')
        
        summ_no['sort_key'] = summ_no.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        st.table(summ_no.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key']))
