import streamlit as st
import pandas as pd
import re
import io
import os
from PIL import Image

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปงาน", layout="wide")

# ระบบหน่วยความจำสำหรับเก็บข้อมูลต่างๆ
if 'files_storage' not in st.session_state:
    st.session_state['files_storage'] = {}
if 'active_file' not in st.session_state:
    st.session_state['active_file'] = ""
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None
if 'teacher_image' not in st.session_state:
    st.session_state['teacher_image'] = None

# --- ส่วนหัว: อัปโหลดและแสดงรูปภาพคุณครู + ข้อมูลโรงเรียน ---
st.markdown("### 🛠️ ตั้งค่าข้อมูลผู้ใช้งาน")
uploaded_photo = st.file_uploader("🖼️ อัปโหลดรูปภาพคุณครู (เพื่อใช้เป็นรูปโปรไฟล์)", type=["jpg", "jpeg", "png"])

if uploaded_photo:
    st.session_state['teacher_image'] = uploaded_photo.getvalue()

st.markdown("---")

# ส่วนแสดงผล Header
h_col1, h_col2 = st.columns([1, 5])

with h_col1:
    if st.session_state['teacher_image']:
        st.image(st.session_state['teacher_image'], width=150)
    else:
        # กรณีไม่มีการอัปโหลดรูป ให้แสดงไอคอนแทน
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)

with h_col2:
    st.title("📋 ระบบสรุปการส่งงาน")
    st.subheader("โรงเรียนขุนหาญวิทยาสรรค์")
    st.write("👨‍🏫 **ผู้รับผิดชอบ:** คุณครูตระกูล บุญชิต")
    st.write("🔬 วิทยาศาสตร์และเทคโนโลยี (ชีววิทยา)")

st.markdown("---")

# --- ฟังก์ชันจัดการข้อมูล (คงความแม่นยำสูงสุด) ---
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
            is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
            for p in prefixes: s = re.sub(p, '', s).strip()
            parts = s.split(maxsplit=1)
            fname = parts[0] if len(parts) > 0 else "-"
            lname = parts[1] if len(parts) > 1 else "-"
            
            sec_txt = str(row.get('ส่วน', ''))
            g_num = re.search(r'(กลุ่มที่\s*\d+)', sec_txt)
            g_name = re.search(r'\)\s*(.*)', sec_txt)
            group_display = f"{g_num.group(1) if g_num else ''} {g_name.group(1).strip() if g_name else sec_txt}".strip()
            
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
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
        return None

# --- ส่วนอัปโหลดไฟล์งาน (หลายไฟล์) ---
uploaded_files = st.file_uploader("📥 อัปโหลดไฟล์งานจาก Padlet (CSV หรือ Excel)", 
                                  type=["csv", "xlsx", "xls"], 
                                  accept_multiple_files=True)

if uploaded_files:
    for f in uploaded_files:
        st.session_state['files_storage'][f.name] = f.getvalue()
    
    if not st.session_state['active_file']:
        first_file = uploaded_files[0].name
        st.session_state['active_file'] = first_file
        st.session_state['processed_df'] = process_data(st.session_state['files_storage'][first_file], first_file)

# --- รายชื่อไฟล์ในระบบ (อยู่ใต้ปุ่มอัปโหลด) ---
if st.session_state['files_storage']:
    st.write("📂 **ไฟล์ที่พร้อมสรุปข้อมูล:**")
    for f_name in st.session_state['files_storage'].keys():
        col_txt, col_btn = st.columns([5, 1])
        with col_txt:
            if f_name == st.session_state['active_file']:
                st.success(f"📍 กำลังแสดงผลไฟล์: {f_name}")
            else:
                st.write(f"📄 {f_name}")
        with col_btn:
            if st.button("🔄 เลือก", key=f"btn_{f_name}"):
                st.session_state['active_file'] = f_name
                st.session_state['processed_df'] = process_data(st.session_state['files_storage'][f_name], f_name)
                st.rerun()
    st.markdown("---")

# --- ส่วนแสดงผลตารางสรุป ---
if st.session_state['processed_df'] is not None:
    res_df = st.session_state['processed_df']
    st.subheader(f"📊 ตารางสรุป: {st.session_state['active_file']}")
    
    # ตารางส่งงานหลัก
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม']).pivot(
            index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
            columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
        
        pivot['sort_key'] = pivot.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
        
        st.dataframe(pivot, use_container_width=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pivot.to_excel(writer, index=False)
        st.download_button(label="📥 ดาวน์โหลดสรุป Excel", data=output.getvalue(), file_name=f"สรุป_{st.session_state['active_file']}.xlsx")

    # ตารางคนลืมระบุเลขกิจกรรม
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        st.markdown("---")
        st.subheader("⚠️ รายชื่อที่ส่งงานแต่ไม่ได้ระบุเลขกิจกรรม")
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงาน')
        summ_no['sort_key'] = summ_no.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        st.table(summ_no.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key']))
