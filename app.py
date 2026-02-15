import streamlit as st
import pandas as pd
import re
import io

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบสรุปงานชีววิทยา ม.3", layout="wide")

st.title("📋 ระบบสรุปการส่งงานวิชาชีววิทยา ม.3")
st.write("คอลัมน์: เลขที่ | ชื่อ | นามสกุล | กลุ่มที่... [ชื่อกลุ่ม]")
st.info("รายชื่อที่ไม่ระบุนามสกุลหรือใช้ชื่อนามแฝงจะถูกจัดไว้ท้ายตารางอัตโนมัติ")

# ฟังก์ชันจัดการชื่อ (ตัดคำนำหน้า และแยกชื่อ-นามสกุล)
def clean_name_parts(raw_name):
    prefixes = [r'^นาย', r'^นางสาว', r'^ด\.ช\.', r'^ด\.ญ\.', r'^เด็กชาย', r'^เด็กหญิง', r'^ดช\.', r'^ดญ\.']
    s = str(raw_name).strip()
    
    # ตรวจสอบว่าเป็นชื่อไทยและมีนามสกุลหรือไม่
    is_valid_thai = bool(re.search(r'[\u0e00-\u0e7f]', s))
    
    for p in prefixes:
        s = re.sub(p, '', s).strip()
    
    parts = s.split(maxsplit=1)
    f_name = parts[0] if len(parts) > 0 else "-"
    l_name = parts[1] if len(parts) > 1 else "-"
    
    # รายชื่อไม่ชัดเจนคือ: ไม่ใช่ภาษาไทย หรือ ไม่มีนามสกุลจริง
    is_unknown = not is_valid_thai or l_name == "-"
    
    return f_name, l_name, is_unknown

# ฟังก์ชันดึงชื่อกลุ่ม (ดึง "กลุ่มที่ X" และ "ชื่อกลุ่ม" มาต่อกัน)
def get_group_full_name(section_text):
    text = str(section_text)
    # หาคำว่า "กลุ่มที่ X"
    num_match = re.search(r'(กลุ่มที่\s*\d+)', text)
    # หาชื่อกลุ่มที่มักจะอยู่หลังวงเล็บ ) หรือช่องว่าง
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
        # ตรวจสอบประเภทไฟล์
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        else:
            df = pd.read_excel(uploaded_file)
            
        df.columns = [str(c).strip() for c in df.columns]

        # กรองโพสต์คุณครูออก
        if 'ผู้เขียน' in df.columns:
            df = df[~df['ผู้เขียน'].str.contains("ตระกูล", na=False)]

        all_results = []
        for _, row in df.iterrows():
            sub = str(row.get('เรื่อง', ''))
            con = str(row.get('เนื้อหา', ''))
            full_txt = sub + " " + con
            
            # 1. เลขที่
            n_match = re.search(r'เลขที่\s*(\d+)', full_txt)
            st_no = n_match.group(1) if n_match else "-"
            
            # 2-3. ชื่อ-นามสกุล
            nm_match = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', full_txt)
            if nm_match:
                raw_name = nm_match.group(0)
            else:
                raw_name = str(row.get('ผู้เขียน', 'ไม่ระบุ')).split('(')[0].strip()
            
            fname, lname, is_unk = clean_name_parts(raw_name)
            
            # 4. ชื่อกลุ่ม
            group_display = get_group_full_name(row.get('ส่วน', ''))
            
            # ตรวจสอบเลขกิจกรรม
            a_match = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', full_txt)
            act_id = a_match.group(1) if a_match else None
            
            all_results.append({
                'เลขที่': st_no, 'ชื่อ': fname, 'นามสกุล': lname,
                'ชื่อกลุ่ม': group_display, 'กิจกรรม': act_id,
                'สถานะ': '✓', 'is_unknown': is_unk
            })
            
        res_df = pd.DataFrame(all_results)

        # --- ส่วนแสดงตารางสรุปกิจกรรม ---
        st.subheader("✅ ตารางสรุปการส่งงาน ม.3")
        df_act = res_df[res_df['กิจกรรม'].notna()].copy()
        
        if not df_act.empty:
            df_act = df_act.drop_duplicates(subset=['เลขที่', 'ชื่อ', 'นามสกุล', 'กิจกรรม'])
            pivot = df_act.pivot(
                index=['เลขที่', 'ชื่อ', 'นามสกุล', 'ชื่อกลุ่ม', 'is_unknown'], 
                columns='กิจกรรม', 
                values='สถานะ'
            ).fillna('-').reset_index()
            
            # ลอจิกการเรียงลำดับ: เรียงคนปกติ (is_unknown=False) ไว้ก่อน แล้วเรียงตาม เลขที่ > ชื่อ > นามสกุล
            def sort_logic(row):
                val = 999
                try:
                    if row['เลขที่'] != "-": val = int(row['เลขที่'])
                except: pass
                return (row['is_unknown'], val, row['ชื่อ'], row['นามสกุล'])

            pivot['sort_key'] = pivot.apply(sort_logic, axis=1)
            pivot = pivot.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
            
            st.dataframe(pivot, use_container_width=True)
            
            # ปุ่มดาวน์โหลด Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                pivot.to_excel(writer, index=False, sheet_name='Summary_M3')
            st.download_button(
                label="📥 ดาวน์โหลดไฟล์สรุป (Excel)",
                data=output.getvalue(),
                file_name="สรุปส่งงาน_ชีววิทยา_ม3.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("ไม่พบคนระบุเลขกิจกรรม")

        # --- ตารางส่งงานแต่ไม่ระบุกิจกรรม (ท้ายตาราง) ---
        st.markdown("---")
        st.subheader("❓ ตารางตรวจสอบ (ส่งงานแล้วแต่ไม่มีเลขกิจกรรม)")
        df_unk = res_df[res_df['กิจกรรม'].isna()].drop(columns=['กิจกรรม', 'สถานะ']).drop_duplicates(subset=['ชื่อ', 'นามสกุล'])
        
        if not df_unk.empty:
            df_unk['sort_key'] = df_unk.apply(lambda r: (r['is_unknown'], int(r['เลขที่']) if r['เลขที่'].isdigit() else 999, r['ชื่อ']), axis=1)
            df_unk = df_unk.sort_values('sort_key').drop(columns=['is_unknown', 'sort_key'])
            st.table(df_unk)
        else:
            st.write("ไม่มีงานค้างตรวจสอบ")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
