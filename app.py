import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปการส่งงาน", layout="wide")

# --- ส่วนหัว: จัดวางตามรูปภาพที่คุณส่งมา ---
# เราจะไม่ใช้ session_state สำหรับรูปภาพ เพื่อไม่ให้มีประวัติค้าง
col_logo, col_title, col_upload_profile = st.columns([1, 4, 2])

with col_logo:
    # แสดงรูปภาพโปรไฟล์จาก URL ตรงๆ (ไม่มีการเก็บประวัติการอัปโหลด)
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120)

with col_title:
    st.markdown("## 📋 ระบบสรุปการส่งงาน")
    st.markdown("#### โรงเรียนตระกาศประชาสามัคคี")
    st.caption("👨‍🏫 ผู้รับผิดชอบ: คุณครูตระกูล บุญชิต")
    st.caption("🧪 วิทยาศาสตร์และเทคโนโลยี (ชีววิทยา)")

with col_upload_profile:
    # ส่วนนี้มีไว้ตามดีไซน์ แต่จะไม่ทำการบันทึกภาพลงระบบถาวร
    with st.expander("🖼️ ตั้งค่ารูปโปรไฟล์"):
        st.file_uploader("เลือกรูปภาพใหม่", type=["jpg", "png"], key="temp_p_up")

st.markdown("---")

# --- ฟังก์ชันประมวลผล (ไม่มีการเก็บ State) ---
def process_data_instant(uploaded_file):
    try:
        file_bytes = uploaded_file.getvalue()
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(file_bytes), encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(file_bytes))
            
        df.columns = [str(c).strip() for c in df.columns]
        # กรองชื่อครูออก
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]
            
        temp_results = []
        for _, row in df.iterrows():
            txt = f"{row.get('เรื่อง', '')} {row.get('เนื้อหา', '')} {row.get('ผู้เขียน', '')}"
            
            # สกัดข้อมูล
            no_match = re.search(r'เลขที่\s*(\d+)', txt)
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', txt)
            
            temp_results.append({
                'เลขที่': int(no_match.group(1)) if no_match else 999,
                'ชื่อ': nm_match.group(2) if nm_match else "-",
                'นามสกุล': nm_match.group(3) if nm_match else "-",
                'ชื่อกลุ่ม': str(row.get('ส่วน', '')).replace('กลุ่มที่', '').strip(),
                'กิจกรรม': act_match.group(1) if act_match else None,
                'สถานะ': '✓'
            })
        return pd.DataFrame(temp_results)
    except:
        return None

# --- ส่วนอัปโหลดและแสดงผลทันที ---
st.markdown("### 📥 อัปโหลดไฟล์งานจาก Padlet (CSV หรือ Excel)")
# จุดสำคัญ: เราไม่เอา uploaded_file ไปเก็บใน session_state
main_file = st.file_uploader("Drag and drop files here", type=["csv", "xlsx", "xls"], label_visibility="collapsed")

if main_file:
    # แสดงสถานะกำลังประมวลผลเหมือนในรูป
    st.success(f"📍 กำลังแสดงผล: {main_file.name}")
    
    res_df = process_data_instant(main_file)
    
    if res_df is not None:
        st.markdown(f"### 📊 สรุปผลจากไฟล์: {main_file.name}")
        
        # แยกตารางกิจกรรม
        df_act = res_df[res_df['กิจกรรม'].notna()]
        if not df_act.empty:
            pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'กิจกรรม']).pivot(
                index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'],
                columns='กิจกรรม',
                values='สถานะ'
            ).fillna('-').reset_index()
            
            st.dataframe(pivot.sort_values('เลขที่'), use_container_width=True)
            
            # ปุ่มดาวน์โหลด
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pivot.to_excel(writer, index=False)
            st.download_button("📥 ดาวน์โหลดสรุป Excel", output.getvalue(), f"Summary.xlsx")

        # ตารางคนลืมระบุกิจกรรม
        df_no_act = res_df[res_df['กิจกรรม'].isna()]
        if not df_no_act.empty:
            st.markdown("---")
            st.markdown("### ⚠️ ตรวจสอบรายชื่อลืมระบุเลขกิจกรรม")
            st.table(df_no_act[['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม']].sort_values('เลขที่'))
