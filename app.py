import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบส่งงาน", layout="wide")

# --- ส่วนหัว: Layout ตามที่คุณต้องการ (ไม่มีการบันทึกภาพลงเครื่อง) ---
head_col1, head_col2 = st.columns([1, 5])

with head_col1:
    # ใช้รูป Icon หรือ URL รูปประจำตัวแบบ Static
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=140)

with head_col2:
    st.title("ระบบส่งงาน")
    st.subheader("โรงเรียนตระกาศประชาสามัคคี")
    st.write("คุณครูตระกูล บุญชิต")

st.markdown("---")

# --- ฟังก์ชันจัดการข้อมูล (เน้นความแม่นยำในการสกัดชื่อและเลขกิจกรรม) ---
def process_data_logic(uploaded_file):
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
            txt = f"{row.get('เรื่อง', '')} {row.get('เนื้อหา', '')} {row.get('ผู้เขียน', '')}"
            
            # สกัดเลขที่ (เรียงลำดับได้ถูกต้อง)
            st_no_match = re.search(r'เลขที่\s*(\d+)', txt)
            st_no = st_no_match.group(1) if st_no_match else "999"
            
            # สกัดชื่อ-นามสกุล
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', txt)
            if nm_match:
                fname, lname = nm_match.group(2), nm_match.group(3)
            else:
                raw_name = str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
                prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
                for p in prefixes: raw_name = re.sub(p, '', raw_name).strip()
                parts = raw_name.split(maxsplit=1)
                fname = parts[0] if len(parts) > 0 else "-"
                lname = parts[1] if len(parts) > 1 else "-"
            
            # สกัดกลุ่ม
            sec_txt = str(row.get('ส่วน', ''))
            g_num = re.search(r'(กลุ่มที่\s*\d+)', sec_txt)
            g_name = re.search(r'\)\s*(.*)', sec_txt)
            group_display = f"{g_num.group(1) if g_num else ''} {g_name.group(1).strip() if g_name else sec_txt}".strip()
            
            # สกัดเลขกิจกรรม
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            
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
        st.error(f"เกิดข้อผิดพลาด: {e}")
        return None

# --- ส่วนอัปโหลดงาน (ไม่อัดประวัติลง Session State) ---
uploaded_file = st.file_uploader("อัปโหลดไฟล์จาก Padlet", type=["csv", "xlsx", "xls"])

if uploaded_file:
    # แสดงผลทันทีที่อัปโหลด โดยไม่เก็บเข้าประวัติย้อนหลัง
    st.success(f"📍 กำลังประมวลผลไฟล์: {uploaded_file.name}")
    
    df_res = process_data_logic(uploaded_file)
    
    if df_res is not None:
        # 1. แสดงตารางสรุป
        df_act = df_res[df_res['กิจกรรม'].notna()].copy()
        if not df_act.empty:
            st.subheader(f"📊 สรุปการส่งงานจากไฟล์ล่าสุด")
            pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'กิจกรรม']).pivot(
                index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'], 
                columns='กิจกรรม', 
                values='สถานะ'
            ).fillna('-').reset_index()
            
            # เรียงตามเลขที่จริง (1, 2, 3...)
            pivot = pivot.sort_values(by=['เลขที่', 'ชื่อ'])
            st.dataframe(pivot, use_container_width=True)
            
            # ปุ่มดาวน์โหลด
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pivot.to_excel(writer, index=False)
            st.download_button(label="📥 ดาวน์โหลดไฟล์สรุป (Excel)", data=output.getvalue(), file_name="Summary.xlsx")

        # 2. ตารางคนลืมระบุกิจกรรม
        df_no_act = df_res[df_res['กิจกรรม'].isna()].copy()
        if not df_no_act.empty:
            st.markdown("---")
            st.warning("⚠️ รายชื่อที่ระบบไม่พบเลขกิจกรรม")
            st.table(df_no_act[['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม']].sort_values('เลขที่'))
