import streamlit as st
import pandas as pd
import re
import io

# --- 1. Configuration & Constants ---
st.set_page_config(page_title="ระบบส่งงาน - โรงเรียนตระกาศประชาสามัคคี", layout="wide")

# กำหนดสไตล์ CSS เล็กน้อยเพื่อให้ตารางดูง่าย
st.markdown("""
    <style>
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. Helper Functions ---
def extract_student_info(text, default_name="ไม่ระบุ"):
    """ ฟังก์ชันสกัดข้อมูล เลขที่ และ ชื่อ-นามสกุล จากข้อความ """
    # ค้นหาเลขที่
    no_match = re.search(r'เลขที่\s*(\d+)', text)
    st_no = no_match.group(1) if no_match else "999"
    
    # ค้นหาชื่อ (รองรับคำนำหน้าหลายรูปแบบ)
    name_pattern = r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)'
    nm_match = re.search(name_pattern, text)
    
    if nm_match:
        return st_no, nm_match.group(2), nm_match.group(3)
    
    # กรณีหาชื่อด้วย Regex ไม่เจอ ให้ลบคำนำหน้าออกด้วยวิธีสะอาดๆ
    clean_name = re.sub(r'^(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง|ดช\.|ดญ\.)', '', text.strip()).strip()
    parts = clean_name.split(maxsplit=1)
    return st_no, parts[0] if parts else "-", parts[1] if len(parts) > 1 else "-"

@st.cache_data # เพิ่ม Cache เพื่อความเร็วในการประมวลผลไฟล์เดิม
def process_data(raw_bytes, file_name):
    try:
        data_io = io.BytesIO(raw_bytes)
        df = pd.read_csv(data_io, encoding='utf-8-sig') if file_name.endswith('.csv') else pd.read_excel(data_io)
        
        df.columns = df.columns.str.strip()
        
        # กรองผู้สอนออก (Case Insensitive)
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False, case=False)]
            
        temp_results = []
        for _, row in df.iterrows():
            content_text = f"{row.get('เรื่อง', '')} {row.get('เนื้อหา', '')} {row.get('ผู้เขียน', '')}"
            
            # สกัดข้อมูล
            st_no, fname, lname = extract_student_info(content_text)
            
            # จัดการเรื่อง "กลุ่ม"
            sec_txt = str(row.get('ส่วน', ''))
            g_num = re.search(r'(กลุ่มที่\s*\d+)', sec_txt)
            g_name = re.search(r'\)\s*(.*)', sec_txt)
            group_display = f"{g_num.group(1) if g_num else ''} {g_name.group(1).strip() if g_name else sec_txt}".strip()
            
            # เลขกิจกรรม
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', content_text)
            
            temp_results.append({
                'เลขที่': int(st_no) if st_no.isdigit() else 999,
                'ชื่อ': fname, 
                'นามสกุล': lname,
                'ชื่อกลุ่ม': group_display,
                'กิจกรรม': act_match.group(1) if act_match else None,
                'สถานะ': '✓'
            })
            
        return pd.DataFrame(temp_results)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ {file_name}: {e}")
        return None

# --- 3. UI logic ---
# (ใช้ Session State เดิมของคุณแต่จัดกลุ่มให้ดูง่าย)
for key in ['current_files', 'active_file', 'teacher_image']:
    if key not in st.session_state:
        st.session_state[key] = {} if key == 'current_files' else "" if key == 'active_file' else None

# Layout ส่วนหัว
head_col1, head_col2 = st.columns([1, 4])
with head_col1:
    img_url = st.session_state['teacher_image'] if st.session_state['teacher_image'] else "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    st.image(img_url, width=120)
    uploaded_photo = st.file_uploader("เปลี่ยนรูป", type=["jpg", "png"], key="teacher_up", label_visibility="collapsed")
    if uploaded_photo:
        st.session_state['teacher_image'] = uploaded_photo.getvalue()
        st.rerun()

with head_col2:
    st.title("🚀 ระบบสรุปการส่งงาน")
    st.info(f"📍 กำลังใช้งาน: {st.session_state['active_file'] if st.session_state['active_file'] else 'ยังไม่ได้เลือกไฟล์'}")

# อัปโหลดไฟล์
files = st.file_uploader("เลือกไฟล์งาน (CSV/Excel)", type=["csv", "xlsx"], accept_multiple_files=True)
if files:
    new_files = {f.name: f.getvalue() for f in files}
    st.session_state['current_files'] = new_files
    if not st.session_state['active_file']:
        st.session_state['active_file'] = list(new_files.keys())[0]

# แสดงรายการไฟล์ (Sidebar หรือ Column)
if st.session_state['current_files']:
    with st.expander("📂 รายการไฟล์ที่อัปโหลด", expanded=True):
        cols = st.columns(len(st.session_state['current_files']))
        for idx, (name, content) in enumerate(st.session_state['current_files'].items()):
            if cols[idx % 4].button(f"📄 {name[:15]}...", key=name):
                st.session_state['active_file'] = name
                st.rerun()

# --- 4. Main Processing & Display ---
if st.session_state['active_file']:
    active_name = st.session_state['active_file']
    raw_data = st.session_state['current_files'][active_name]
    res_df = process_data(raw_data, active_name)
    
    if res_df is not None:
        # แยกข้อมูลที่มีกิจกรรมและไม่มีกิจกรรม
        df_has_act = res_df[res_df['กิจกรรม'].notna()]
        df_no_act = res_df[res_df['กิจกรรม'].isna()]

        if not df_has_act.empty:
            # สร้าง Pivot Table
            pivot = df_has_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม']).pivot(
                index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'], 
                columns='กิจกรรม', 
                values='สถานะ'
            ).fillna('-').reset_index()
            
            pivot = pivot.sort_values(['เลขที่', 'ชื่อ'])
            st.subheader("📊 ตารางสรุปการส่งงาน")
            st.dataframe(pivot, use_container_width=True)
            
            # ปุ่มดาวน์โหลด
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pivot.to_excel(writer, index=False)
            st.download_button("📥 ดาวน์โหลดไฟล์สรุป (Excel)", output.getvalue(), f"Summary_{active_name}.xlsx")

        if not df_no_act.empty:
            st.warning("⚠️ รายการที่ไม่ได้ระบุชื่อกิจกรรม")
            st.table(df_no_act[['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม']].sort_values('เลขที่'))
