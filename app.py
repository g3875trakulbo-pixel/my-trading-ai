import streamlit as st
import cv2
import numpy as np
from PIL import Image

# ตั้งค่าหน้าเว็บให้เหมาะสมกับการใช้งานบนมือถือ
st.set_page_config(page_title="กฎ 6 ข้อ - ระบบวิเคราะห์กราฟ", layout="centered")

st.markdown("""
    <style>
    .result-text { font-size: 28px; font-weight: bold; text-align: center; padding: 15px; border-radius: 10px; }
    .rule-label { font-size: 18px; color: #555; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 วิเคราะห์ตามกฎ 6 ข้อ")
st.write("ระบบวิเคราะห์: ทิศทางตามสี MACD และความยาวตามตัวเลขแกนขวา")

def analyze_logic(image):
    # 1. แปลงไฟล์ภาพ
    img_array = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    h, w, _ = img_bgr.shape
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # 2. แบ่งโซนวิเคราะห์ (เน้นแกนขวาสำหรับวัดความยาว)
    macd_zone = hsv[int(h*0.65):int(h*0.8), int(w*0.5):w]
    vol_zone = hsv[int(h*0.8):int(h*0.95), int(w*0.7):w] # โซน Volume ติดแกนขวา
    price_zone = hsv[int(h*0.3):int(h*0.6), int(w*0.5):w]

    # --- กฎข้อ 1-4: ทิศทางจาก MACD (เน้นกฎข้อ 1 ที่หายไป) ---
    mask_g = cv2.inRange(macd_zone, np.array([40, 40, 40]), np.array([80, 255, 255]))
    mask_r = cv2.inRange(macd_zone, np.array([0, 40, 40]), np.array([10, 255, 255]))
    
    is_green = np.sum(mask_g) > np.sum(mask_r)
    density = np.mean(mask_g if is_green else mask_r)
    is_clear = density < 140 # ค่าความเข้มต่ำ = ใส

    # --- กฎข้อ 5: วัดความยาวแท่งอ้างอิงจากระดับพิกเซลแกนขวา ---
    vol_mask = cv2.inRange(vol_zone, np.array([0, 0, 50]), np.array([180, 255, 255]))
    coords = np.column_stack(np.where(vol_mask > 0))
    if len(coords) > 0:
        highest_point = np.min(coords[:, 0]) # จุดสูงสุดของแท่งเมื่อเทียบกับแกน
        score = 100 - int((highest_point / vol_zone.shape[0]) * 100)
    else:
        score = 0

    # --- กฎข้อ 6: ตรวจสอบเส้นแนวโน้ม ---
    mask_line = cv2.inRange(price_zone, np.array([20, 100, 100]), np.array([30, 255, 255]))
    is_strong = np.sum(mask_line) > 10

    # --- ประมวลผลลัพธ์ตามกฎของคุณ ---
    if is_green:
        # กฎข้อ 1: เขียวใส = ขึ้น | กฎข้อ 2: เขียวทึบ = ลง
        res_color, res_dir = ("สีเขียว", "ขึ้น") if is_clear else ("สีแดง", "ลง")
    else:
        # กฎข้อ 3: แดงใส = ลง | กฎข้อ 4: แดงทึบ = ขึ้น
        res_color, res_dir = ("สีแดง", "ลง") if is_clear else ("สีเขียว", "ขึ้น")
    
    return res_color, res_dir, score, "แข็งแกร่ง" if is_strong else "อ่อนแรง"

# ส่วนการอัปโหลดและแสดงผล
uploaded_file = st.file_uploader("อัปโหลดรูปกราฟของคุณ...", type=["jpg", "png", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, use_container_width=True)
    
    color, direction, score, trend = analyze_logic(img)
    
    st.markdown("---")
    # ปรับสีตามทิศทาง
    bg_color = "#D4EDDA" if direction == "ขึ้น" else "#F8D7DA"
    text_color = "#155724" if direction == "ขึ้น" else "#721C24"
    
    st.markdown(f"<div class='result-text' style='background-color: {bg_color}; color: {text_color};'>"
                f"ผลลัพธ์: {color}, {direction}</div>", unsafe_allow_html=True)
    
    st.write(f"### 📏 ระดับความยาว (อ้างอิงแกนขวา): {score}%")
    st.progress(score / 100)
    st.info(f"สถานะแนวโน้ม (กฎข้อ 6): **{trend}**")
