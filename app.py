import streamlit as st
import cv2
import numpy as np
from PIL import Image

st.set_page_config(page_title="Trading AI - 6 Rules", layout="centered")
st.title("📊 วิเคราะห์ตามกฎ 6 ข้อของคุณ")

def analyze_all_rules(image):
    img_array = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    h, w, _ = img_bgr.shape
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # --- โซนวิเคราะห์ ---
    macd_zone = hsv[int(h*0.65):int(h*0.8), int(w*0.7):w]
    vol_zone = hsv[int(h*0.8):int(h*0.95), int(w*0.7):w]
    price_zone = hsv[int(h*0.3):int(h*0.6), int(w*0.7):w]

    # กฎ 1-4: สีและสถานะ MACD
    mask_g = cv2.inRange(macd_zone, np.array([40, 40, 40]), np.array([80, 255, 255]))
    mask_r = cv2.inRange(macd_zone, np.array([0, 40, 40]), np.array([10, 255, 255]))
    is_green = np.sum(mask_g) > np.sum(mask_r)
    is_clear = np.mean(mask_g if is_green else mask_r) < 150

    # กฎข้อ 5: ความยาวแท่ง (Volume)
    vol_mask = cv2.inRange(vol_zone, np.array([0, 0, 100]), np.array([180, 255, 255]))
    is_long = np.sum(vol_mask > 0) > 1500 

    # กฎข้อ 6: ตำแหน่งเหนือ/ใต้เส้น (Moving Average)
    mask_yellow = cv2.inRange(price_zone, np.array([20, 100, 100]), np.array([30, 255, 255]))
    above_line = np.sum(mask_yellow) > 0 # เช็กว่ามีราคาอยู่โซนเส้นไหม

    # ประมวลผลลัพธ์
    res_color = "สีเขียว" if (is_green and is_clear) or (not is_green and not is_clear) else "สีแดง"
    res_dir = "ขึ้น" if res_color == "สีเขียว" else "ลง"
    res_size = "ยาว" if is_long else "สั้น"
    res_trend = "แข็งแกร่ง" if above_line else "อ่อนแรง"

    return f"{res_color}, {res_dir}, {res_size} ({res_trend})"

uploaded_file = st.file_uploader("อัปโหลดรูปกราฟ...", type=["jpg", "png", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, use_container_width=True)
    with st.spinner('กำลังวิเคราะห์ตามกฎ 6 ข้อ...'):
        result = analyze_all_rules(img)
        st.header(f"👉 {result}")
