# --- 1. ตัดระบบหน่วยความจำรูปภาพออก ---
# ลบ if 'teacher_image' not in st.session_state: ... ออกไปได้เลย

# --- 2. ส่วนหัว: แสดงรูปภาพแบบ Simple ---
head_col1, head_col2 = st.columns([1, 5])

with head_col1:
    # กำหนดรูปเริ่มต้นเป็น Icon หรือ URL รูปประจำตัวของคุณครูโดยตรง
    default_avatar = "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    
    # แสดงรูปภาพ (จะไม่มีการดึงจาก session_state แล้ว)
    st.image(default_avatar, width=140)
    
    # หากต้องการให้มีการอัปโหลดเพื่อดูเล่นๆ แต่ไม่บันทึกลงประวัติ 
    # ก็สามารถคง file_uploader ไว้ได้แต่ไม่ต้องสั่ง save ลง session_state
    # หรือถ้าไม่ใช้เลย ให้ลบส่วน uploaded_photo ออกครับ

with head_col2:
    st.title("ระบบส่งงาน")
    st.subheader("โรงเรียนตระกาศประชาสามัคคี")
    st.write("คุณครูตระกูล บุญชิต")

st.markdown("---")
