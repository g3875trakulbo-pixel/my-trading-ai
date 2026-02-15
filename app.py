import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบส่งงาน", layout="wide")

# ระบบหน่วยความจำ
if 'current_files' not in st.session_state:
    st.session_state['current_files'] = {}
if 'active_file' not in st.session_state:
    st.session_state['active_file'] = ""
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None
if 'teacher_image' not in st.session_state:
    st.session_state['teacher_image'] = None

# --- ส่วนหัว: รูปภาพและชื่อ ---
head_col1, head_col2, head_col3 = st.columns([1, 3, 2])

with head_col1:
    if st.session_state['teacher_image']:
        st.image(st.session_state['teacher_image'], width=140)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=140)

with head_col2:
    st.title("ระบบส่งงาน")
    st.subheader("โรงเรียนตระกาศประชาสามัคคี")
    st.write(f"คุณครูตระกูล บุญชิต")

with head_col3:
    uploaded_photo = st.file_uploader("📷", type=["jpg", "jpeg", "png"], key="teacher_up")
    if uploaded_photo:
        st.session_state['teacher_image'] = uploaded_photo.getvalue()
        st.rerun()

st.markdown("---")

# --- ฟังก์ชันจัดการข้อมูลและการเรียงลำดับ ---
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
            
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            act_id = act_match.group(1) if act_match else None
            
            temp_results.append({
                'เลขที่': st_no.group(1) if st_no else "999", # ใส่ 999 เพื่อให้คนไม่มีเลขที่ไปอยู่ท้ายสุด
                'ชื่อ': fname, 
                'นามสกุล': lname,
                'ชื่อกลุ่ม': group_display,
                'กิจกรรม': act_id,
                'สถานะ': '✓'
            })
        return pd.DataFrame(temp_results)
    except Exception as e:
        st.error(f"Error: {e}")
        return None

# --- ส่วนอัปโหลด ---
uploaded_files = st.file_uploader("📥", type=["csv", "xlsx", "xls"], accept_multiple_files=True)

if uploaded_files:
    st.session_state['current_files'] = {f.name: f.getvalue() for f in uploaded_files}
    if st.session_state['active_file'] not in st.session_state['current_files']:
        first_file = list(st.session_state['current_files'].keys())[0]
        st.session_state['active_file'] = first_file
        st.session_state['processed_df'] = process_data(st.session_state['current_files'][first_file], first_file)

# --- รายชื่อไฟล์ ---
if st.session_state['current_files']:
    for f_name in st.session_state['current_files'].keys():
        f_col1, f_col2 = st.columns([5, 1])
        with f_col1:
            if f_name == st.session_state['active_file']:
                st.success(f"📍 {f_name}")
            else: st.write(f"📄 {f_name}")
        with f_col2:
            if st.button("🔄", key=f"sel_{f_name}"):
                st.session_state['active_file'] = f_name
                st.session_state['processed_df'] = process_data(st.session_state['current_files'][f_name], f_name)
                st.rerun()
    st.markdown("---")

# --- ส่วนแสดงผลตาราง (เน้นการ Sorting) ---
if st.session_state['processed_df'] is not None:
    res_df = st.session_state['processed_df']
    
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        # 1. จัดทำ Pivot Table
        pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม']).pivot(
            index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'], 
            columns='กิจกรรม', 
            values='สถานะ'
        ).fillna('-').reset_index()
        
        # 2. แปลงเลขที่ให้เป็นตัวเลขเพื่อการเรียงลำดับที่ถูกต้อง
        pivot['no_int'] = pd.to_numeric(pivot['เลขที่'], errors='coerce').fillna(999).astype(int)
        
        # 3. สั่งเรียงลำดับ: เลขที่ > ชื่อ > นามสกุล > กลุ่ม
        pivot = pivot.sort_values(by=['no_int', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'])
        
        # 4. ลบคอลัมน์ช่วยเรียงออกก่อนแสดงผล
        display_df = pivot.drop(columns=['no_int'])
        
        st.dataframe(display_df, use_container_width=True)
        
        # ปุ่มดาวน์โหลด
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            display_df.to_excel(writer, index=False)
        st.download_button(label="📥 Excel", data=output.getvalue(), file_name=f"สรุป_{st.session_state['active_file']}.xlsx")

    # ตารางลืมระบุเลขกิจกรรม
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        st.markdown("---")
        st.subheader("⚠️")
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม']).size().reset_index(name='N')
        summ_no['no_int'] = pd.to_numeric(summ_no['เลขที่'], errors='coerce').fillna(999).astype(int)
        summ_no = summ_no.sort_values(by=['no_int', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'])
        st.table(summ_no.drop(columns=['no_int']))
