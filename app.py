import streamlit as st
import cv2
import numpy as np
from PIL import Image

# ตั้งค่าหน้าเว็บ
st.set_page_config(page_title="Trading AI - 6 Rules", layout="centered")

st.markdown("""
    <style>
    .main-result { font-size: 30px; font-weight: bold; text-align: center; padding: 20px; border-radius: 15px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 วิเคราะห์ตามกฎ 6 ข้อ (ฉบับแก้ไข)")

def analyze_all_rules(image):
    # 1. เตรียมภาพ
    img_array = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    h, w, _ = img_bgr.shape
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # 2. กำหนดโซน (สัดส่วนโดยประมาณจากรูป 1000022318.jpg)
    price_zone = hsv[int(h*0.3):int(h*0.6), int(w*0.5):w]
    macd_zone = hsv[int(h*0.65):int(h*0.8), int(w*0.5):w]
    vol_zone = hsv[int(h*0.8):int(h*0.95), int(w*0.5):w]

    # 3. กฎ 1-4: MACD สีและสถานะ (ใส/ทึบ)
    mask_g = cv2.inRange(macd_zone, np.array([40, 40, 40]), np.array([80, 255, 255]))
    mask_r = cv2.inRange(macd_zone, np.array([0, 40, 40]), np.array([10, 255, 255]))
    
    is_green = np.sum(mask_g) > np.sum(mask_r)
    density = np.mean(mask_g if is_green else mask_r)
    is_clear = density < 130 

    # 4. กฎข้อ 5: Volume Score (ตัวเลข 0-100)
    vol_mask = cv2.inRange(vol_zone, np.array([0, 0, 50]), np.array([180, 255, 255]))
    vol_pixels = np.sum(vol_mask > 0)
    vol_score = min(int(vol_pixels / 100), 100) 
    is_long = vol_score > 50

    # 5. กฎข้อ 6: เส้นค่าเฉลี่ย
    mask_yellow = cv2.inRange(price_zone, np.array([20, 100, 100]), np.array([30, 255, 255]))
    above_line = np.sum(mask_yellow) > 10

    # 6. สรุปผล
    if is_green:
        res_color, res_dir = ("สีเขียว", "ขึ้น") if is_clear else ("สีแดง", "ลง")
    else:
        res_color, res_dir = ("สีแดง", "ลง") if is_clear else ("สีเขียว", "ขึ้น")
    
    res_size = "ยาว" if is_long else "สั้น"
    res_trend = "แข็งแกร่ง" if above_line else "อ่อนแรง"

    return {
        "text": f"{res_color}, {res_dir}, {res_size}",
        "score": vol_score,
        "trend": res_trend,
        "is_up": res_dir == "ขึ้น"
    }

# หน้าเว็บ
uploaded_file = st.file_uploader("อัปโหลดภาพกราฟ...", type=["jpg", "png", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, use_container_width=True)
    
    try:
        res = analyze_all_rules(img)
        st.markdown("---")
        
        # แสดงผลลัพธ์หลัก
        bg_color = "#e8f5e9" if res['is_up'] else "#ffebee"
        text_color = "#2e7d32" if res['is_up'] else "#c62828"
        
        st.markdown(f"""
            <div class='main-result' style='background-color: {bg_color}; color: {text_color};'>
                ผลลัพธ์: {res['text']}
            </div>
            """, unsafe_allow_html=True)
        
        # กฎข้อ 5 และ 6
        col1, col2 = st.columns(2)
        with col1:
            st.metric("ระดับความยาว (Volume)", f"{res['score']}%")
        with col2:
            st.metric("สถานะแนวโน้ม", res['trend'])
            
        st.progress(res['score'] / 100)

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการคำนวณ: {e}")
