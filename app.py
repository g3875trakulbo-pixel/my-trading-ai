import streamlit as st
import pandas as pd
import re
import io
from PIL import Image

# 1. ตั้งค่าหน้าแอป
st.set_page_config(page_title="ระบบส่งงาน", layout="wide")

# ระบบหน่วยความจำ
if 'current_files' not in st.session_state:
    st.session_state['current_files'] = {}
if 'active_file' not in st.session_state:
    st.session_state['active_file'] = ""
if 'processed_df' not in st.session_state:
    st.session_state['processed_df'] = None
if 'teacher_image' not in st.session_state:
    st.session_state['teacher_image'] = None

# --- ส่วนหัว: ชื่อแอป รูปภาพ และชื่อโรงเรียน ---
head_col1, head_col2, head_col3 = st.columns([1, 3, 2])

with head_col1:
    if st.session_state['teacher_image']:
        st.image(st.session_state['teacher_image'], width=140)
    else:
        st.image("https
