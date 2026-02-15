import streamlit as st
import pandas as pd
import re

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบเช็กงาน Padlet ม.3", layout="wide")

st.title("📋 ระบบสรุปการส่งงานจาก Padlet (ม.3)")
st.write("อัปโหลดไฟล์ 'โพสต์.csv' เพื่อดูสรุปรายคนและรายกลุ่ม")

# ฟังก์ชันจัดการชื่อ (เอาคำนำหน้าออก)
def clean_name(text):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง']
    cleaned = str(text).strip()
    for p in prefixes:
        cleaned = re.sub(p, '', cleaned).strip()
    
    parts = cleaned.split(maxsplit=1)
    first = parts[0] if len(parts) > 0 else "-"
    last = parts[1] if len(parts) > 1 else "-"
    return first, last

# ฟังก์ชันดึงชื่อกลุ่มจากคอลัมน์ 'ส่วน'
def get_group(text):
    text = str(text)
    match_num = re.search(r'(กลุ่มที่\s*\d+)', text)
    match_name = re.search(r'\).*(.*)', text)
    g_num = match_num.group(1) if match_num else "ไม่ระบุกลุ่ม"
    g_name = match_name.group(0).replace(')', '').strip() if match_name else ""
    return f"{g_num} {g_name}".strip()

# ส่วนอัปโหลดไฟล์
uploaded_file = st.file_uploader("เลือกไฟล์ CSV ที่ได้จาก Padlet", type=["csv"])

if uploaded_file:
    try:
        # อ่านไฟล์ CSV (รองรับภาษาไทย)
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        
        # กรองเอาโพสต์ของคุณครูออก (ถ้ามี)
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล บุญชิต", na=False)]
        
        results = []
        for _, row in df.iterrows():
            # รวมเนื้อหาเพื่อค้นหา เลขที่ และ กิจกรรม
            subject = str(row.get('เรื่อง', ''))
            content = str(row.get('เนื้อหา', ''))
            full_text = f"{subject} {content}"
            
            # 1. ดึงเลขที่
            no_match = re.search(r'เลขที่\s*(\d+)', full_text)
            no = no_match.group(1) if no_match else "-"
            
            # 2. ดึงชื่อ-นามสกุล
            name_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.)\s*([^\s\d]+)\s+([^\s\d]+)', full_text)
            if name_match:
                fname, lname = clean_name(name_match.group(0))
            else:
                author_name = str(row.get('ผู้เขียน', 'Unknown')).split('(')[0]
                fname, lname = clean_name(author_name)
            
            # 3. ดึงกลุ่มและกิจกรรม
            group = get_group(row.get('ส่วน', ''))
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', full_text)
            act = act_match.group(1) if act_match else None
            
            results.append({
                'เลขที่': no, 'ชื่อ': fname, 'นามสกุล': lname, 
                'กลุ่ม': group, 'กิจกรรม': act, 'สถานะ': '✓'
            })

        res_df = pd.DataFrame(results)

        # --- ตารางที่ 1: คนที่ระบุกิจกรรม (มีเครื่องหมาย ✓) ---
        st.subheader("✅ ตารางสรุปการส่งงาน (ระบุกิจกรรมชัดเจน)")
        df_with_act = res_df[res_df['กิจกรรม'].notna()]
        
        if not df_with_act.empty:
            pivot = df_with_act.pivot_table(
                index=['เลขที่', 'ชื่อ', 'นามสกุล', 'กลุ่ม'],
                columns='กิจกรรม', 
                values='สถานะ', 
                aggfunc='first'
            ).fillna('-')
            st.dataframe
