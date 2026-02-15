import streamlit as st
import pandas as pd
import re

st.set_page_config(page_title="ระบบสรุปงาน Padlet", layout="wide")

st.title("📋 ระบบสรุปการส่งงานชีววิทยา (แยกรายกิจกรรม)")
st.write("อัปโหลดไฟล์ 'โพสต์.csv' จาก Padlet เพื่อสรุปผล")

# ฟังก์ชันสำหรับจัดการชื่อและนามสกุล
def clean_student_data(full_name_text):
    # นำคำนำหน้าออก
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง']
    cleaned = full_name_text.strip()
    for p in prefixes:
        cleaned = re.sub(p, '', cleaned).strip()
    
    parts = cleaned.split(maxsplit=1)
    first = parts[0] if len(parts) > 0 else "-"
    last = parts[1] if len(parts) > 1 else "-"
    return first, last

# ฟังก์ชันดึงเลขกิจกรรม
def extract_act(text):
    match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', str(text))
    return match.group(1) if match else None

# ฟังก์ชันดึงชื่อกลุ่ม
def extract_group_name(part_text):
    num_match = re.search(r'(กลุ่มที่\s*\d+)', str(part_text))
    name_match = re.search(r'\).*(.*)', str(part_text))
    g_num = num_match.group(1) if num_match else "ไม่ระบุกลุ่ม"
    g_name = name_match.group(0).replace(')', '').strip() if name_match else ""
    return f"{g_num} {g_name}".strip()

uploaded_file = st.file_uploader("เลือกไฟล์ CSV", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # กรองโพสต์ของคุณครูออก
    df = df[~df['ผู้เขียน'].str.contains("ตระกูล บุญชิต", na=False)]
    
    results = []
    for _, row in df.iterrows():
        content_text = f"{row['เรื่อง']} {row['เนื้อหา']}"
        
        # ดึงเลขที่
        no_match = re.search(r'เลขที่\s*(\d+)', content_text)
        no = no_match.group(1) if no_match else "-"
        
        # ดึงชื่อ
        name_in_post = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.)\s*([^\s\d]+)\s+([^\s\d]+)', content_text)
        full_name = name_in_post.group(0) if name_in_post else str(row['ผู้เขียน']).split('(')[0].strip()
        first, last = clean_student_data(full_name)
        
        group = extract_group_name(row['ส่วน'])
        act = extract_act(content_text)
        
        results.append({
            'เลขที่': no, 'ชื่อ': first, 'นามสกุล': last, 
            'ชื่อกลุ่ม': group, 'กิจกรรม': act, 'สถานะ': '✓'
        })

    df_res = pd.DataFrame(results)
    
    # --- ตารางที่ 1: คนที่ระบุกิจกรรมชัดเจน ---
    st.subheader("1. สรุปผลการส่งงาน (ระบุกิจกรรมชัดเจน)")
    df_act = df_res[df_res['กิจกรรม'].notna()]
    if not df_act.empty:
        pivot = df_act.pivot_table(
