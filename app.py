import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปงานชีววิทยา ม.3", layout="wide")

st.title("📋 ระบบสรุปการส่งงานวิชาชีววิทยา ม.3")
st.write("ตารางที่ 1: สรุปงานรายกิจกรรม | ตารางที่ 2: นับจำนวนงานที่ส่ง (กรณีไม่ระบุเลขกิจกรรม)")
st.markdown("---")

# ฟังก์ชันจัดการชื่อ (ตัดคำนำหน้า และแยกชื่อ-นามสกุล)
def clean_name_parts(raw_name):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    s = str(raw_name).strip()
    is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
    for p in prefixes:
        s = re.sub(p, '', s).strip()
    parts = s.split(maxsplit=1)
    fname = parts[0] if len(parts) > 0 else "-"
    lname = parts[1] if len(parts) > 1 else "-"
    is_unk = not is_valid_thai or lname == "-"
    return fname, lname, is_unk

# ฟังก์ชันดึงชื่อกลุ่ม (กลุ่มที่... + ชื่อกลุ่ม)
def get_group_full_name(section_text):
    text = str(section_text)
    num_match = re.search(r'(กลุ่มที่\s*\d+)', text)
    name_match = re.search(r'\)\s*(.*)', text)
    g_num = num_match.group(1) if num_match else ""
    g_name = name_match.group(1).strip() if name_match else ""
    if g_num and g_name:
        return f"{g_num} {g_name}"
    return g_num or g_name or text

# ส่วนอัปโหลดไฟล์
uploaded_file = st.file_uploader("อัปโหลดไฟล์จาก Padlet (CSV หรือ Excel)", type=["csv", "xlsx", "xls"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        else:
            df = pd.read_excel(uploaded_file)
            
        df.columns = [str(c).strip() for c in df.columns]
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]

        all_results = []
        for _, row in df.iterrows():
            sub = str(row.get('เรื่อง', ''))
            con = str(row.get('เนื้อหา', ''))
            full_txt = sub + " " + con
            
            n_match = re.search(r'เลขที่\s*(\d+)', full_txt)
            st_no = n_match.group(1) if n_match else "-"
            
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', full_txt)
            raw_name = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
            
            fname, lname, is_unk = clean_name_parts(raw_name)
            group_display = get_group_full_name(row.get('ส่วน', ''))
            
            a_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', full_txt)
            act_id = a_match.group(1) if a_match else None
            
            all_results.append({
                'เลขที่': st_no, 'ชื่อ': fname, 'นามสกุล': lname,
                'ชื่อกลุ่ม': group_display, 'กิจกรรม': act_id,
                'สถานะ': '✓', 'is_unknown': is_unk
            })
            
        res_df = pd.DataFrame(all_results)

        # --- ส่วนที่ 1: ตารางสรุปรายกิจกรรม ---
        st.subheader("✅ 1. ตารางสรุปการส่งงาน ม.3 (ระบุกิจกรรม)")
        df_act = res_df[res_df['กิจกรรม'].notna()].copy()
        if not df_act.empty:
            df_act = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม'])
            pivot = df_act.pivot(index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
            
            def sort_logic(row):
                no = int(row['เลขที่']) if str(row['เลขที่']).isdigit() else 999
                return (row['is_unknown'], no, row['ชื่อ'])

            pivot['sort_key'] = pivot.apply(sort_logic, axis=1)
            pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
            st.dataframe(pivot, use_container_width=True)
        else:
            st.warning("ไม่มีข้อมูลการระบุเลขกิจกรรม")

        # --- ส่วนที่ 2: ตารางคนไม่ระบุกิจกรรม (นับจำนวนงาน) ---
        st.markdown("---")
        st.subheader("⚠️ 2. ตารางตรวจสอบ: ส่งงานแล้วแต่ไม่ระบุเลขกิจกรรม")
        st.write("ตารางนี้จะ 'นับจำนวนครั้ง' ที่นักเรียนโพสต์งานแต่ไม่ได้เขียนว่า กิจกรรมที่เท่าไหร่")
        
        df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
        
        if not df_no_act.empty:
            # รวมกลุ่มเพื่อนับจำนวนโพสต์
            summary_no_act = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงานที่ส่ง')
            
            # เรียงลำดับ เลขที่ > ชื่อ > นามสกุล และคนชื่อไม่ชัดไว้ท้าย
            summary_no_act['sort_key'] = summary_no_act.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
            summary_no_act = summary_no_act.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
            
            st.table(summary_no_act)
        else:
            st.success("นักเรียนทุกคนระบุเลขกิจกรรมครบถ้วน!")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
