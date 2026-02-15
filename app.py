import streamlit as st
import pandas as pd
import re

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="ระบบสรุปงาน Padlet", layout="wide")

st.title("📋 ระบบสรุปการส่งงาน (ม.3)")
st.write("อัปโหลดไฟล์ 'โพสต์.csv' เพื่อสรุปรายคนรายกลุ่ม")

# ฟังก์ชันจัดการชื่อ (ตัดคำนำหน้าและแยกชื่อ-นามสกุล)
def clean_student_name(full_text):
    # รายการคำนำหน้าที่จะตัดออก
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    cleaned = str(full_text).strip()
    for p in prefixes:
        cleaned = re.sub(p, '', cleaned).strip()
    
    # แยกชื่อกับนามสกุลด้วยช่องว่าง
    parts = cleaned.split(maxsplit=1)
    fname = parts[0] if len(parts) > 0 else "-"
    lname = parts[1] if len(parts) > 1 else "-"
    return fname, lname

# ฟังก์ชันดึงชื่อกลุ่ม (กลุ่มที่ X [ชื่อกลุ่ม])
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
        
        # กรองโพสต์ของคุณครูตระกูลออก
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]
        
        data_list = []
        for _, row in df.iterrows():
            subject = str(row.get('เรื่อง', ''))
            content = str(row.get('เนื้อหา', ''))
            full_text = f"{subject} {content}"
            
            # 1. ดึงเลขที่
            no_match = re.search(r'เลขที่\s*(\d+)', full_text)
            st_no = no_match.group(1) if no_match else "-"
            
            # 2. ดึงชื่อ-นามสกุล
            name_re = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.)\s*([^\s\d]+)\s+([^\s\d]+)', full_text)
            if name_re:
                raw_name = name_re.group(0)
            else:
                raw_name = str(row.get('ผู้เขียน', 'Unknown')).split('(')[0].strip()
            
            fname, lname = clean_student_name(raw_name)
            
            # 3. ดึงกลุ่มและกิจกรรม
            group = get_group_info(row.get('ส่วน', ''))
            act_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', full_text)
            act_id = act_match.group(1) if act_match else None
            
            # รวบรวมข้อมูล
            data_list.append({
                'เลขที่': st_no,
                'ชื่อ': fname,
                'นามสกุล': lname,
                'ชื่อกลุ่ม': group,
                'กิจกรรม': act_id,
                'สถานะ': '✓'
            })
            
        final_df = pd.DataFrame(data_list)

        # --- ตารางที่ 1: ตารางสรุปงานที่มีเลขกิจกรรม ---
        st.subheader("✅ ตารางสรุปการส่งงาน (แยกกิจกรรม 1.1 - 1.10)")
        df_act = final_df[final_df['กิจกรรม'].notna()]
        if not df_act.empty:
            df_act = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม'])
            pivot = df_act.pivot(index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม'], columns='กิจกรรม', values='สถานะ').fillna('-')
            st.dataframe(pivot, use_container_width=True)
        else:
            st.warning("ไม่พบการระบุเลขกิจกรรมที่ชัดเจนในไฟล์นี้")

        # --- ตารางที่ 2: ตารางสุดท้าย (ส่งงานแล้วแต่ไม่ระบุกิจกรรม) ---
        st.markdown("---")
        st.subheader("❓ ตารางสุดท้าย (รายชื่อผู้ส่งงานแต่ไม่ระบุเลขกิจกรรม)")
        df_no_act = final_df[final_df['กิจกรรม'].isna()].drop(columns=['กิจกรรม', 'สถานะ'])
        df_no_act = df_no_act.drop_duplicates(subset=['ชื่อ', 'นามสกุล'])
        
        # จัดเรียงตามเลขที่
        def sort_func(x):
            try: return int(x)
            except: return 999
        df_no_act['sort'] = df_no_act['เลขที่'].apply(sort_func)
        df_no_act = df_no_act.sort_values('sort').drop(columns='sort')
        
        st.table(df_no_act)
        
        # ปุ่มดาวน์โหลด
        csv_out = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 ดาวน์โหลดไฟล์สรุป (CSV)", data=csv_out, file_name="summary.csv", mime="text/csv")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
