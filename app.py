import streamlit as st
import pandas as pd
import re, io

st.set_page_config(page_title="ระบบส่งงานครูตระกูล", layout="wide")

# ระบบหน่วยความจำชั่วคราว (ไม่บันทึกประวัติ)
if 'fs' not in st.session_state: st.session_state.fs = {}
if 'sl' not in st.session_state: st.session_state.sl = ""

# --- Header ---
c1, c2 = st.columns([1, 5])
c1.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120)
c2.markdown("## 📋 ระบบสรุปการส่งงาน (แยกตารางข้อมูลไม่สมบูรณ์)")
c2.caption("👨‍🏫 **คุณครูตระกูล บุญชิต** | โรงเรียนตระกาศประชาสามัคคี")

st.markdown("---")

# --- การจัดการไฟล์ ---
up = st.file_uploader("อัปโหลดไฟล์", type=["csv", "xlsx"], accept_multiple_files=True, label_visibility="collapsed")
if up:
    for f in up: st.session_state.fs[f.name] = f.getvalue()
    if not st.session_state.sl: st.session_state.sl = up[0].name

if st.session_state.fs:
    st.write("📂 **เลือกไฟล์:**")
    btns = st.columns(len(st.session_state.fs) if len(st.session_state.fs) < 5 else 5)
    for i, name in enumerate(st.session_state.fs.keys()):
        if btns[i % 5].button(f"📄 {name[:12]}", key=name, use_container_width=True):
            st.session_state.sl = name
            st.rerun()

# --- ประมวลผลข้อมูล ---
if st.session_state.sl:
    fn = st.session_state.sl
    raw = st.session_state.fs[fn]
    try:
        df = pd.read_csv(io.BytesIO(raw)) if fn.endswith('.csv') else pd.read_excel(io.BytesIO(raw))
        df.columns = df.columns.astype(str).str.strip()
        
        all_data = []
        for _, r in df.iterrows():
            t = f"{r.get('เรื่อง','')} {r.get('เนื้อหา','')} {r.get('ผู้เขียน','')}"
            no = re.search(r'เลขที่\s*(\d+)', t)
            ac = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', t)
            nm = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.|ดช\.|ดญ\.|เด็กชาย|เด็กหญิง)\s*([^\s\d]+)\s+([^\s\d]+)', t)
            
            all_data.append({
                'เลขที่': int(no.group(1)) if no else 999,
                'ชื่อ': nm.group(2) if nm else "-", 
                'นามสกุล': nm.group(3) if nm else "-",
                'กลุ่ม': str(r.get('ส่วน','')).replace('กลุ่มที่','').strip(),
                'กิจกรรม': ac.group(1) if ac else None, 
                'สถานะ': '✓',
                'raw_text': t[:50] + "..." # เก็บไว้ตรวจสอบกรณีไม่มีชื่อ
            })
        
        df_r = pd.DataFrame(all_data).dropna(subset=['กิจกรรม'])
        
        # ฟังก์ชันจัดเรียงกิจกรรม 1.1, 1.2...
        def sort_activities(cols):
            fixed = ['เลขที่','ชื่อ','นามสกุล','กลุ่ม']
            acts = [c for c in cols if c not in fixed and c != 'คะแนนรวม']
            acts.sort(key=lambda x: float(x) if re.match(r'^\d+\.?\d*$', x) else 999)
            return fixed, acts

        # --- แยกตาราง ---
        # 1. ตารางสมบูรณ์ (มีทั้งชื่อและนามสกุล)
        df_valid = df_r[(df_r['ชื่อ'] != "-") & (df_r['นามสกุล'] != "-")]
        # 2. ตารางไม่สมบูรณ์ (ขาดชื่อหรือนามสกุล)
        df_invalid = df_r[(df_r['ชื่อ'] == "-") | (df_r['นามสกุล'] == "-")]

        st.success(f"📍 กำลังแสดงผล: {fn}")

        # แสดงตารางสมบูรณ์
        if not df_valid.empty:
            st.subheader("✅ ตารางสรุปคะแนน (ข้อมูลสมบูรณ์)")
            pv_v = df_valid.drop_duplicates(['เลขที่','ชื่อ','กิจกรรม']).pivot(
                index=['เลขที่','ชื่อ','นามสกุล','กลุ่ม'], columns='กิจกรรม', values='สถานะ'
            ).fillna('-').reset_index()
            
            fix, acts = sort_activities(pv_v.columns)
            pv_v['คะแนนรวม'] = (pv_v[acts] == '✓').sum(axis=1)
            pv_v = pv_v[fix + acts + ['คะแนนรวม']].sort_values('เลขที่')
            st.dataframe(pv_v, use_container_width=True)

        # แสดงตารางไม่สมบูรณ์
        if not df_invalid.empty:
            st.markdown("---")
            st.subheader("⚠️ ตารางตรวจสอบ (ข้อมูลไม่สมบูรณ์/ไม่มีชื่อ)")
            pv_inv = df_invalid.drop_duplicates(['เลขที่','กลุ่ม','กิจกรรม','raw_text']).pivot(
                index=['เลขที่','กลุ่ม','raw_text'], columns='กิจกรรม', values='สถานะ'
            ).fillna('-').reset_index()
            
            # จัดเรียงกิจกรรมและนับคะแนนให้ด้วย
            inv_fix = ['เลขที่','กลุ่ม','raw_text']
            inv_acts = [c for c in pv_inv.columns if c not in inv_fix]
            inv_acts.sort(key=lambda x: float(x) if re.match(r'^\d+\.?\d*$', x) else 999)
            pv_inv['คะแนนรวม'] = (pv_inv[inv_acts] == '✓').sum(axis=1)
            
            st.dataframe(pv_inv[inv_fix + inv_acts + ['คะแนนรวม']].sort_values('เลขที่'), use_container_width=True)
            st.info("💡 หมายเหตุ: 'raw_text' คือข้อความบางส่วนจาก Padlet เพื่อช่วยให้คุณระบุตัวตนนักเรียนได้ง่ายขึ้น")

    except Exception as e: st.error(f"เกิดข้อผิดพลาด: {e}")

# Sidebar สำหรับล้างข้อมูล
if st.sidebar.button("🗑️ ล้างข้อมูลทั้งหมด"):
    st.session_state.fs = {}
    st.session_state.sl = ""
    st.rerun()
