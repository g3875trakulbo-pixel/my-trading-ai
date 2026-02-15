import streamlit as st
import pandas as pd
import re

# ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปงาน Padlet ม.3", layout="wide")

st.title("📋 ระบบสรุปการส่งงานชีววิทยา (Padlet)")
st.write("อัปโหลดไฟล์ 'โพสต์.csv' เพื่อดูสรุปรายคน")

# 1. ฟังก์ชันจัดการชื่อ (ตัดคำนำหน้าและแยกชื่อ-นามสกุล)
def clean_student_name(full_text):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    cleaned = str(full_text).strip()
    for p in prefixes:
        cleaned = re.sub(p, '', cleaned).strip()
    
    parts = cleaned.split(maxsplit=1)
    fname = parts[0] if len(parts) > 0 else "-"
    lname = parts[1] if len(parts) > 1 else "-"
    return fname, lname

# 2. ฟังก์ชันดึงชื่อกลุ่ม
def get_group_info(section_text):
    text = str(section_text)
    num_match = re.search(r'(กลุ่มที่\s*\d+)', text)
    name_match = re.search(r'\)\s*(.*)', text)
    g_num = num_match.group(1) if num_match else "ไม่ระบุกลุ่ม"
    g_name = name_match.group(1).strip() if name_match else ""
    return f"{g_num} {g_name}".strip()

# ส่วนอัปโหลด
uploaded_file = st.file_uploader("เลือกไฟล์ CSV จาก Padlet", type=["csv"])

if uploaded_file:
    try:
        # อ่านไฟล์รองรับภาษาไทย
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        
        # กรองโพสต์ครูออก
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]
        
        data_list = []
        for _, row in df.iterrows():
            subject = str(row.get('เรื่อง', ''))
            content = str(row.get('เนื้อหา', ''))
            full_text = f"{subject} {content}"
            
            # ดึงเลขที่
            no_match = re.search(r'เลขที่\s*(\d+)', full_text)
            st_no = no_match.group(1) if no_match else "-"
            
            # ดึงชื่อ-นามสกุล
            name_re = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.)\s*([^\s\d]+)\s+([^\s\d]+)', full_text)
            if name_re:
                raw_name = name_re.group(0)
            else:
                raw_name = str(row.get('ผู้เขียน', 'Unknown')).split('(')[0].strip()
            
            fname, lname = clean_student_name(raw_name)
            
            # ดึงกลุ่มและกิจกรรม
            group = get_group_info(row.get('ส่วน', ''))
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', full_text)
            act_id = act_match.group(1) if act_match else None
            
            # เก็บข้อมูลลง List (จุดที่เคย Error ถูกแก้แล้ว)
            data_list.append({
                'เลขที่': st_no,
                'ชื่อ': fname,
                'นามสกุล': lname,
                'ชื่อกลุ่ม': group,
                'กิจกรรม': act_id,
                'สถานะ': '✓'
            })
            
        final_df = pd.DataFrame(data_list)

        # --- ตารางที่ 1: รู้กิจกรรม ---
        st.subheader("✅ ตารางสรุปการส่งงาน (1.1 - 1.10)")
        df_act = final_df[final_df['กิจกรรม'].notna()]
        if not df_act.empty:
            df_act = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม'])
            pivot = df_act.pivot(index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'], columns='กิจกรรม', values='สถานะ').fillna('-')
            st.dataframe(pivot, use_container_width=True)
        else:
            st.warning("ไม่พบการระบุเลขกิจกรรม")

        # --- ตารางที่ 2: ไม่ระบุกิจกรรม (ขีดไว้ท้ายตาราง) ---
        st.markdown("---")
        st.subheader("❓ ตารางสุดท้าย (ส่งงานแล้วแต่ไม่ระบุเลขกิจกรรม)")
        df_no_act = final_df[final_df['กิจกรรม'].isna()].drop(columns=['กิจกรรม', 'สถานะ'])
        df_no_act = df_no_act.drop_duplicates(subset=['ชื่อ', 'นามสกุล'])
        
        # จัดเรียงเลขที่
        def sort_func(x):
            try: return int(x)
            except: return 999
        df_no_act['sort'] = df_no_act['เลขที่'].apply(sort_func)
        df_no_act = df_no_act.sort_values('sort').drop(columns='sort')
        
        st.table(df_no_act)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
