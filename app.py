import streamlit as st
import pandas as pd
import re
import io
import os
from PIL import Image

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปการส่งงานงาน โรงเรียนตระกาศประชาสามัคคี", layout="wide")

# ระบบหน่วยความจำ
if 'files_storage' not in st.session_state:
    st.session_state['files_storage'] = {}
if 'active_file' not in st.session_state:
    st.session_state['active_file'] = ""
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None
if 'teacher_image' not in st.session_state:
    st.session_state['teacher_image'] = None

# --- ส่วนหัว: ข้อมูลโรงเรียน และ ปุ่มอัปโหลดภาพ (จัดวางแบบ 3 คอลัมน์) ---
head_col1, head_col2, head_col3 = st.columns([1, 3, 2])

with head_col1:
    # แสดงรูปภาพคุณครู
    if st.session_state['teacher_image']:
        st.image(st.session_state['teacher_image'], width=140)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=140)

with head_col2:
    # ข้อมูลโรงเรียนและชื่อครู
    st.title("📋 ระบบสรุปการส่งงาน")
    st.subheader("โรงเรียนตระกาศประชาสามัคคี")
    st.write("👨‍🏫 **ผู้รับผิดชอบ:** คุณครูตระกูล บุญชิต")
    st.write("🔬 วิทยาศาสตร์และเทคโนโลยี (ชีววิทยา)")

with head_col3:
    # ปุ่มอัปโหลดภาพอยู่ด้านข้างตรงนี้ครับ
    st.write("🖼️ **ตั้งค่ารูปโปรไฟล์**")
    uploaded_photo = st.file_uploader("เลือกรูปภาพใหม่", type=["jpg", "jpeg", "png"], key="photo_up")
    if uploaded_photo:
        st.session_state['teacher_image'] = uploaded_photo.getvalue()
        st.rerun()

st.markdown("---")

# --- ฟังก์ชันจัดการข้อมูล (แม่นยำสูงสุด) ---
def process_data(raw_bytes, file_name):
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
            
            raw_name = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
            prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
            s = raw_name
            for p in prefixes: s = re.sub(p, '', s).strip()
            parts = s.split(maxsplit=1)
            fname = parts[0] if len(parts) > 0 else "-"
            lname = parts[1] if len(parts) > 1 else "-"
            
            sec_txt = str(row.get('ส่วน', ''))
            g_num = re.search(r'(กลุ่มที่\s*\d+)', sec_txt)
            g_name = re.search(r'\)\s*(.*)', sec_txt)
            group_display = f"{g_num.group(1) if g_num else ''} {g_name.group(1).strip() if g_name else sec_txt}".strip()
            
            act_id = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            
            temp_results.append({
                'เลขที่': st_no.group(1) if st_no else "-",
                'ชื่อ': fname, 'นามสกุล': lname,
                'ชื่อกลุ่ม': group_display,
                'กิจกรรม': act_id.group(1) if act_id else None,
                'สถานะ': '✓', 'is_unknown': (lname == "-")
            })
        return pd.DataFrame(temp_results)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
        return None

# --- ส่วนอัปโหลดงาน (หลายไฟล์) ---
uploaded_files = st.file_uploader("📥 อัปโหลดไฟล์งานจาก Padlet (CSV หรือ Excel)", type=["csv", "xlsx", "xls"], accept_multiple_files=True)

if uploaded_files:
    for f in uploaded_files:
        st.session_state['files_storage'][f.name] = f.getvalue()
    if not st.session_state['active_file']:
        first_file = uploaded_files[0].name
        st.session_state['active_file'] = first_file
        st.session_state['processed_df'] = process_data(st.session_state['files_storage'][first_file], first_file)

# --- รายชื่อไฟล์ในระบบ (ใต้ปุ่มอัปโหลด) ---
if st.session_state['files_storage']:
    st.write("📂 **รายการไฟล์ที่เลือกดูได้:**")
    for f_name in st.session_state['files_storage'].keys():
        f_col1, f_col2 = st.columns([5, 1])
        with f_col1:
            if f_name == st.session_state['active_file']:
                st.success(f"📍 กำลังแสดงผล: {f_name}")
            else:
                st.write(f"📄 {f_name}")
        with f_col2:
            if st.button("🔄 เลือก", key=f"btn_{f_name}"):
                st.session_state['active_file'] = f_name
                st.session_state['processed_df'] = process_data(st.session_state['files_storage'][f_name], f_name)
                st.rerun()
    st.markdown("---")

# --- ตารางสรุปผล ---
if st.session_state['processed_df'] is not None:
    res_df = st.session_state['processed_df']
    st.subheader(f"📊 สรุปผลจากไฟล์: {st.session_state['active_file']}")
    
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม']).pivot(
            index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
            columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
        
        pivot['sort_key'] = pivot.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
        st.dataframe(pivot, use_container_width=True)
        
        # ปุ่มโหลด Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pivot.to_excel(writer, index=False)
        st.download_button(label="📥 ดาวน์โหลดสรุป Excel", data=output.getvalue(), file_name=f"สรุป_{st.session_state['active_file']}.xlsx")

    # ตารางตรวจสอบลืมระบุเลขกิจกรรม
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        st.markdown("---")
        st.subheader("⚠️ ตรวจสอบรายชื่อลืมระบุเลขกิจกรรม")
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงาน')
        summ_no['sort_key'] = summ_no.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        st.table(summ_no.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key']))
