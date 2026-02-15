import streamlit as st
import pandas as pd
import re, io

st.set_page_config(page_title="ระบบส่งงานครูตระกูล", layout="wide")

# ระบบหน่วยความจำชั่วคราว (จำไฟล์งานในเซสชัน ไม่จำรูปโปรไฟล์)
if 'fs' not in st.session_state: st.session_state.fs = {}
if 'sl' not in st.session_state: st.session_state.sl = ""

# --- Header ---
c1, c2 = st.columns([1, 5])
c1.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120)
c2.markdown("## 📋 ระบบสรุปการส่งงานและรวมคะแนน")
c2.caption("👨‍🏫 **คุณครูตระกูล บุญชิต** | โรงเรียนตระกาศประชาสามัคคี")

st.markdown("---")

# --- การจัดการไฟล์ (จำไว้ใช้ต่อได้) ---
up = st.file_uploader("อัปโหลดไฟล์", type=["csv", "xlsx"], accept_multiple_files=True, label_visibility="collapsed")
if up:
    for f in up: st.session_state.fs[f.name] = f.getvalue()
    if not st.session_state.sl: st.session_state.sl = up[0].name

if st.session_state.fs:
    btns = st.columns(len(st.session_state.fs))
    for i, name in enumerate(st.session_state.fs.keys()):
        if btns[i].button(f"📄 {name[:10]}", key=name, use_container_width=True):
            st.session_state.sl = name
            st.rerun()

# --- ประมวลผลและคำนวณคะแนน ---
if st.session_state.sl:
    fn = st.session_state.sl
    raw = st.session_state.fs[fn]
    try:
        df = pd.read_csv(io.BytesIO(raw)) if fn.endswith('.csv') else pd.read_excel(io.BytesIO(raw))
        df.columns = df.columns.astype(str).str.strip()
        
        res = []
        for _, r in df.iterrows():
            t = f"{r.get('เรื่อง','')} {r.get('เนื้อหา','')} {r.get('ผู้เขียน','')}"
            no = re.search(r'เลขที่\s*(\d+)', t)
            ac = re.search(r'กิจกรรมที่\s*(\d+\.?\d*)', t)
            nm = re.search(r'(นาย|นางสาว|ด\.ช\.|ด\.ญ\.)\s*([^\s\d]+)\s+([^\s\d]+)', t)
            
            res.append({
                'เลขที่': int(no.group(1)) if no else 999,
                'ชื่อ': nm.group(2) if nm else "-", 'นามสกุล': nm.group(3) if nm else "-",
                'กลุ่ม': str(r.get('ส่วน','')).replace('กลุ่มที่','').strip(),
                'กิจกรรม': ac.group(1) if ac else None, 'สถานะ': '✓'
            })
        
        df_r = pd.DataFrame(res).dropna(subset=['กิจกรรม'])
        
        # 1. สร้าง Pivot Table
        pv = df_r.drop_duplicates(['เลขที่','ชื่อ','กิจกรรม']).pivot(
            index=['เลขที่','ชื่อ','นามสกุล','กลุ่ม'], columns='กิจกรรม', values='สถานะ'
        ).fillna('-').reset_index()

        # 2. จัดเรียงคอลัมน์กิจกรรม 1.1, 1.2 ...
        fixed = ['เลขที่','ชื่อ','นามสกุล','กลุ่ม']
        acts = [c for c in pv.columns if c not in fixed]
        acts.sort(key=lambda x: float(x) if re.match(r'^\d+\.?\d*$', x) else 999)
        
        # 3. คำนวณคะแนนรวม (นับจำนวน ✓)
        pv['คะแนนรวม'] = (pv[acts] == '✓').sum(axis=1)
        
        # จัดลำดับคอลัมน์ใหม่ (ข้อมูลพื้นฐาน + กิจกรรมที่เรียงแล้ว + คะแนนรวม)
        pv = pv[fixed + acts + ['คะแนนรวม']].sort_values('เลขที่')
        
        st.success(f"📍 แสดงผล: {fn}")
        st.dataframe(pv, use_container_width=True)
        
        # ดาวน์โหลด
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as w: pv.to_excel(w, index=False)
        st.download_button("📥 โหลด Excel (พร้อมคะแนน)", out.getvalue(), f"สรุปคะแนน_{fn}.xlsx")
        
    except Exception as e: st.error(f"Error: {e}")
