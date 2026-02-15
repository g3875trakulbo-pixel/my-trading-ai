import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปงานชีววิทยา ม.3", layout="wide")

# ระบบหน่วยความจำชั่วคราว (Session State)
if 'processed_data' not in st.session_state:
    st.session_state['processed_data'] = None  # เก็บ DataFrame ที่ประมวลผลแล้ว
if 'history' not in st.session_state:
    st.session_state['history'] = []           # เก็บประวัติชื่อไฟล์

st.title("📋 ระบบสรุปการส่งงานวิชาชีววิทยา ม.3")
st.write("ระบบจะจดจำข้อมูลที่อัปโหลดไว้แล้ว คุณครูไม่ต้องอัปโหลดใหม่จนกว่าจะปิดเบราว์เซอร์")

# --- Sidebar: ส่วนควบคุมและประวัติ ---
with st.sidebar:
    st.header("⚙️ การจัดการข้อมูล")
    if st.button("🗑️ ล้างข้อมูลทั้งหมดเพื่อเริ่มใหม่"):
        st.session_state['processed_data'] = None
        st.session_state['history'] = []
        st.rerun()
    
    st.markdown("---")
    st.subheader("📜 ประวัติไฟล์ที่เคยอัปโหลด")
    if st.session_state['history']:
        for item in reversed(st.session_state['history']):
            st.info(f"📄 {item['file']}\n\n🕒 {item['time']}")
    else:
        st.write("ยังไม่มีประวัติ")

# ฟังก์ชันจัดการชื่อและกลุ่ม (เหมือนเดิมที่เสถียรที่สุด)
def clean_name_parts(raw_name):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    s = str(raw_name).strip()
    is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
    for p in prefixes: s = re.sub(p, '', s).strip()
    parts = s.split(maxsplit=1)
    fname = parts[0] if len(parts) > 0 else "-"
    lname = parts[1] if len(parts) > 1 else "-"
    return fname, lname, (not is_valid_thai or lname == "-")

def get_group_info(section_text):
    text = str(section_text)
    g_num = re.search(r'(กลุ่มที่\s*\d+)', text)
    g_name = re.search(r'\)\s*(.*)', text)
    res_num = g_num.group(1) if g_num else ""
    res_name = g_name.group(1).strip() if g_name else ""
    return f"{res_num} {res_name}".strip() if res_num and res_name else (res_num or res_name or text)

# --- ส่วนการรับไฟล์ ---
# แสดงช่องอัปโหลดเฉพาะเมื่อยังไม่มีข้อมูลในระบบ
if st.session_state['processed_data'] is None:
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

            temp_results = []
            for _, row in df.iterrows():
                full_text = f"{row.get('เรื่อง', '')} {row.get('เนื้อหา', '')}"
                st_no = re.search(r'เลขที่\s*(\d+)', full_text)
                no = st_no.group(1) if st_no else "-"
                
                nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', full_text)
                raw_name = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
                
                fname, lname, is_unk = clean_name_parts(raw_name)
                all_act = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', full_text)
                
                temp_results.append({
                    'เลขที่': no, 'ชื่อ': fname, 'นามสกุล': lname,
                    'ชื่อกลุ่ม': get_group_info(row.get('ส่วน', '')),
                    'กิจกรรม': all_act.group(1) if all_act else None,
                    'สถานะ': '✓', 'is_unknown': is_unk
                })
            
            # เก็บข้อมูลลง Session
            st.session_state['processed_data'] = pd.DataFrame(temp_results)
            st.session_state['history'].append({
                "file": uploaded_file.name, 
                "time": datetime.now().strftime("%d/%m/%Y %H:%M")
            })
            st.rerun() # รีโหลดเพื่อแสดงผลจาก Session
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {e}")
else:
    # --- แสดงผลจากข้อมูลที่มีอยู่ในหน่วยความจำ ---
    res_df = st.session_state['processed_data']
    st.success(f"ใช้ข้อมูลจากไฟล์ล่าสุด: {st.session_state['history'][-1]['file']}")

    # 1. ตารางสรุปกิจกรรม
    st.subheader("✅ 1. ตารางสรุปการส่งงาน ม.3")
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        df_act = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม'])
        pivot = df_act.pivot(index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
                            columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
        
        pivot['sort_key'] = pivot.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
        st.dataframe(pivot, use_container_width=True)

        # ปุ่ม Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pivot.to_excel(writer, index=False, sheet_name='Summary_M3')
        st.download_button(label="📥 ดาวน์โหลดไฟล์สรุป (Excel)", data=output.getvalue(), file_name="สรุปส่งงาน_ม3.xlsx")

    # 2. ตารางคนไม่ระบุกิจกรรม
    st.markdown("---")
    st.subheader("⚠️ 2. ตารางตรวจสอบ (นับจำนวนงานที่ไม่ระบุเลขกิจกรรม)")
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงาน')
        summ_no['sort_key'] = summ_no.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        st.table(summ_no.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key']))
