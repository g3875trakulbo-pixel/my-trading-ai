import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปการส่งงาน", layout="wide")

# --- ระบบหน่วยความจำ (จำเฉพาะไฟล์งาน ไม่จำรูปโปรไฟล์) ---
if 'file_storage' not in st.session_state:
    st.session_state['file_storage'] = {}  # เก็บ {ชื่อไฟล์: ข้อมูล bytes}
if 'selected_file' not in st.session_state:
    st.session_state['selected_file'] = ""

# --- ส่วนหัว: (ใช้รูป Default เสมอ ไม่เก็บประวัติภาพ) ---
head_col1, head_col2 = st.columns([1, 5])
with head_col1:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=140)
with head_col2:
    st.title("📋 ระบบสรุปการส่งงาน")
    st.subheader("โรงเรียนตระกาศประชาสามัคคี")
    st.write("👨‍🏫 **คุณครูตระกูล บุญชิต**")

st.markdown("---")

# --- ฟังก์ชันประมวลผลข้อมูล ---
def process_data(raw_bytes, file_name):
    try:
        data_io = io.BytesIO(raw_bytes)
        df = pd.read_csv(data_io, encoding='utf-8-sig') if file_name.endswith('.csv') else pd.read_excel(data_io)
        df.columns = [str(c).strip() for c in df.columns]
        
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]
            
        results = []
        for _, row in df.iterrows():
            txt = f"{row.get('เรื่อง', '')} {row.get('เนื้อหา', '')} {row.get('ผู้เขียน', '')}"
            no_match = re.search(r'เลขที่\s*(\d+)', txt)
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง|ดช\.|ดญ\.)\s*([^\s\d]+)\s+([^\s\d]+)', txt)
            
            results.append({
                'เลขที่': int(no_match.group(1)) if no_match else 999,
                'ชื่อ': nm_match.group(2) if nm_match else "-",
                'นามสกุล': nm_match.group(3) if nm_match else "-",
                'ชื่อกลุ่ม': str(row.get('ส่วน', '')).replace('กลุ่มที่', '').strip(),
                'กิจกรรม': act_match.group(1) if act_match else None,
                'สถานะ': '✓'
            })
        return pd.DataFrame(results)
    except: return None

# --- ส่วนอัปโหลดงาน (เพิ่มเข้าหน่วยความจำ) ---
st.markdown("### 📥 อัปโหลดไฟล์ใหม่")
new_uploads = st.file_uploader("ลากไฟล์ CSV หรือ Excel มาวางที่นี่", type=["csv", "xlsx"], accept_multiple_files=True)

if new_uploads:
    for f in new_uploads:
        st.session_state['file_storage'][f.name] = f.getvalue()
    # ถ้ายังไม่มีไฟล์ที่เลือก ให้เลือกไฟล์แรกที่อัปโหลดขึ้นมา
    if not st.session_state['selected_file']:
        st.session_state['selected_file'] = new_uploads[0].name

# --- ส่วนจัดการไฟล์ที่เคยอัปโหลดไว้ (จำไว้ใช้ต่อได้) ---
if st.session_state['file_storage']:
    st.markdown("### 📂 รายการไฟล์ที่พร้อมใช้งาน:")
    for f_name in list(st.session_state['file_storage'].keys()):
        c1, c2, c3 = st.columns([5, 1, 1])
        with c1:
            if f_name == st.session_state['selected_file']:
                st.success(f"📍 กำลังแสดงผล: {f_name}")
            else: st.write(f"📄 {f_name}")
        with c2:
            if st.button("เลือกใช้", key=f"use_{f_name}"):
                st.session_state['selected_file'] = f_name
                st.rerun()
        with c3:
            if st.button("🗑️ ลบ", key=f"del_{f_name}"):
                del st.session_state['file_storage'][f_name]
                if st.session_state['selected_file'] == f_name:
                    st.session_state['selected_file'] = ""
                st.rerun()
    st.markdown("---")

# --- แสดงผลตารางจากไฟล์ที่เลือก ---
if st.session_state['selected_file']:
    active_name = st.session_state['selected_file']
    active_bytes = st.session_state['file_storage'][active_name]
    df_res = process_data(active_bytes, active_name)
    
    if df_res is not None:
        st.subheader(f"📊 ผลสรุปจาก: {active_name}")
        df_act = df_res[df_res['กิจกรรม'].notna()]
        if not df_act.empty:
            pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'กิจกรรม']).pivot(
                index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'],
                columns='กิจกรรม', values='สถานะ'
            ).fillna('-').reset_index().sort_values('เลขที่')
            
            st.dataframe(pivot, use_container_width=True)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pivot.to_excel(writer, index=False)
            st.download_button("📥 ดาวน์โหลดสรุป Excel", output.getvalue(), f"Summary_{active_name}.xlsx")
