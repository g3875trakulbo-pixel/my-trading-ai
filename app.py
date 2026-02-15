import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอปให้กว้างเพื่อให้ดูตารางง่ายขึ้น
st.set_page_config(page_title="ระบบสรุปงานชีววิทยา ม.3", layout="wide")

# ระบบหน่วยความจำสำหรับเก็บไฟล์ที่อัปโหลดในรอบนั้น
if 'files_storage' not in st.session_state:
    st.session_state['files_storage'] = {}
if 'active_file' not in st.session_state:
    st.session_state['active_file'] = ""
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None

st.title("📋 ระบบสรุปงานวิชาชีววิทยา ม.3")
st.write("อัปโหลดไฟล์หลายไฟล์พร้อมกัน แล้วคลิกเลือกไฟล์ด้านล่างเพื่อดูสรุปงาน")
st.markdown("---")

# --- ฟังก์ชันจัดการข้อมูล (คงความแม่นยำสูงสุด) ---
def process_data(raw_bytes, file_name):
    try:
        if file_name.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(raw_bytes), encoding='utf-8-sig')
        else:
            df = pd.read_excel(io.BytesIO(raw_bytes))
            
        df.columns = [str(c).strip() for c in df.columns]
        # กรองชื่อครูออก
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]

        temp_results = []
        for _, row in df.iterrows():
            txt = f"{row.get('เรื่อง', '')} {row.get('เนื้อหา', '')}"
            # สกัดข้อมูล เลขที่ ชื่อ-นามสกุล
            st_no = re.search(r'เลขที่\s*(\d+)', txt)
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', txt)
            
            # จัดการเรื่องชื่อและคำนำหน้า
            raw_name = nm_match.group(0) if nm_match else str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
            prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
            s = raw_name
            is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
            for p in prefixes: s = re.sub(p, '', s).strip()
            parts = s.split(maxsplit=1)
            fname = parts[0] if len(parts) > 0 else "-"
            lname = parts[1] if len(parts) > 1 else "-"
            
            # สกัดกลุ่ม
            sec_txt = str(row.get('ส่วน', ''))
            g_num = re.search(r'(กลุ่มที่\s*\d+)', sec_txt)
            g_name = re.search(r'\)\s*(.*)', sec_txt)
            group_display = f"{g_num.group(1) if g_num else ''} {g_name.group(1).strip() if g_name else sec_txt}".strip()
            
            # สกัดกิจกรรม
            act = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', txt)
            
            temp_results.append({
                'เลขที่': st_no.group(1) if st_no else "-",
                'ชื่อ': fname, 'นามสกุล': lname,
                'ชื่อกลุ่ม': group_display,
                'กิจกรรม': act.group(1) if act else None,
                'สถานะ': '✓', 'is_unknown': (not is_valid_thai or lname == "-")
            })
        return pd.DataFrame(temp_results)
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์ {file_name}: {e}")
        return None

# --- ส่วนอัปโหลด (รองรับหลายไฟล์) ---
uploaded_files = st.file_uploader("📥 อัปโหลดไฟล์ (CSV หรือ Excel) เลือกได้หลายไฟล์พร้อมกัน", 
                                  type=["csv", "xlsx", "xls"], 
                                  accept_multiple_files=True)

if uploaded_files:
    # นำไฟล์เข้าสู่หน่วยความจำ
    for f in uploaded_files:
        st.session_state['files_storage'][f.name] = f.getvalue()
    
    # ถ้ายังไม่ได้เลือกไฟล์ ให้เริ่มที่ไฟล์แรก
    if not st.session_state['active_file']:
        first_file = uploaded_files[0].name
        st.session_state['active_file'] = first_file
        st.session_state['processed_df'] = process_data(st.session_state['files_storage'][first_file], first_file)

# --- ส่วนแสดงรายการไฟล์ใต้ปุ่มอัปโหลด ---
if st.session_state['files_storage']:
    st.write("📂 **ไฟล์ที่อัปโหลดแล้ว (คลิกปุ่มเพื่อเลือกดูข้อมูล):**")
    for f_name in st.session_state['files_storage'].keys():
        col_txt, col_btn = st.columns([5, 1])
        with col_txt:
            if f_name == st.session_state['active_file']:
                st.info(f"📍 กำลังแสดงผล: {f_name}")
            else:
                st.write(f"📄 {f_name}")
        with col_btn:
            if st.button("🔄 ดูข้อมูล", key=f"btn_{f_name}"):
                st.session_state['active_file'] = f_name
                st.session_state['processed_df'] = process_data(st.session_state['files_storage'][f_name], f_name)
                st.rerun()
    st.markdown("---")

# --- ส่วนแสดงผลตารางสรุป ---
if st.session_state['processed_df'] is not None:
    res_df = st.session_state['processed_df']
    st.subheader(f"📊 สรุปผลจากไฟล์: {st.session_state['active_file']}")
    
    # ตารางส่งงานปกติ
    df_act = res_df[res_df['กิจกรรม'].notna()].copy()
    if not df_act.empty:
        pivot = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม']).pivot(
            index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
            columns='กิจกรรม', values='สถานะ').fillna('-').reset_index()
        
        # เรียงลำดับเลขที่
        pivot['sort_key'] = pivot.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
        
        st.dataframe(pivot, use_container_width=True)

        # ปุ่มดาวน์โหลด Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            pivot.to_excel(writer, index=False)
        st.download_button(label="📥 ดาวน์โหลดสรุป Excel", 
                           data=output.getvalue(), 
                           file_name=f"สรุป_{st.session_state['active_file']}.xlsx")

    # ตารางลืมระบุกิจกรรม
    df_no_act = res_df[res_df['กิจกรรม'].isna()].copy()
    if not df_no_act.empty:
        st.markdown("---")
        st.subheader("⚠️ รายชื่อที่ลืมระบุเลขกิจกรรม")
        summ_no = df_no_act.groupby(['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown']).size().reset_index(name='จำนวนงาน')
        summ_no['sort_key'] = summ_no.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if str(r['เลขที่']).isdigit() else 999, r['ชื่อ']), axis=1)
        st.table(summ_no.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key']))
