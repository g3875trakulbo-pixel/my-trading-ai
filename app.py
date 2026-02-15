import streamlit as st
import cv2
import numpy as np
from PIL import Image

# ตั้งค่าหน้าเว็บให้ดูทันสมัย
st.set_page_config(page_title="Trading AI - 6 Rules Complete", layout="centered")

# ปรับแต่ง CSS ให้ตัวเลขและข้อความเด่นชัด
st.markdown("""
    <style>
    .main-result { font-size: 30px; font-weight: bold; color: #1E88E5; text-align: center; }
    .rule-box { padding: 10px; border-radius: 10px; background-color: #f0f2f6; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 วิเคราะห์กราฟตามกฎ 6 ข้อ")
st.write("ระบบจะวิเคราะห์: สี, ทิศทาง, ความยาว (ตัวเลข), และความแข็งแกร่งของแนวโน้ม")

def analyze_all_rules(image):
    # แปลงภาพ
    img_array = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    h, w, _ = img_bgr.shape
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # --- โซนวิเคราะห์ (ปรับตามสัดส่วนหน้าจอมือถือทั่วไป) ---
    # แท่งราคา (บน), MACD (กลาง), Volume (ล่าง)
    price_zone = hsv[int(h*0.3):int(h*0.6), int(w*0.5):w]
    macd_zone = hsv[int(h*0.65):int(h*0.8), int(w*0.5):w]
    vol_zone = hsv[int(h*0.8):int(h*0.95), int(w*0.5):w]

    # --- กฎ 1-4: ตรวจสอบสีและสถานะ MACD (ใส/ทึบ) ---
    mask_g = cv2.inRange(macd_zone, np.array([40, 40, 40]), np.array([80, 255, 2
