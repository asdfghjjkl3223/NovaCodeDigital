import streamlit as st
import google.generativeai as genai
from moviepy.editor import VideoFileClip
from supabase import create_client, Client
import tempfile
import os
import smtplib
from email.mime.text import MIMEText
import random
import time
import cv2
import json
import re

# --- 1. CONFIGURATION & SECRETS ---
try:
    GENAI_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    
    ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    
    SENDER_EMAIL = st.secrets["EMAIL_SENDER"]
    SENDER_PASSWORD = st.secrets["EMAIL_PASSWORD"]
except:
    st.error("⚠️ Secrets Missing!")
    st.stop()

if GENAI_KEY != "TEST":
    genai.configure(api_key=GENAI_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. HELPER FUNCTIONS ---
TEMP_DOMAINS = ["tempmail", "10minutemail", "guerrillamail", "yopmail", "mailinator"]
def is_temp_mail(email):
    if "@" in email:
        domain = email.split('@')[-1]
        for temp in TEMP_DOMAINS:
            if temp in domain: return True
    return False

def send_otp_email(to_email):
    otp_code = str(random.randint(1000, 9999))
    msg = MIMEText(f"Your Verification Code: {otp_code}")
    msg['Subject'] = "AI Viral Studio OTP"
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return otp_code
    except: return None

def login_user(email, password):
    try:
        response = supabase.table('users').select("*").eq('email', email).eq('password', password).execute()
        return response.data[0] if response.data else None
    except: return None

def register_user_final(email, password):
    try:
        new_user = {"email": email, "password": password, "credits": 2, "is_premium": False}
        supabase.table('users').insert(new_user).execute()
        return True
    except: return False

def update_credits(email, current_credits):
    try:
        supabase.table('users').update({"credits": current_credits - 1}).eq('email', email).execute()
    except: pass

# --- 3. INTELLIGENT AI FUNCTIONS (ROBUST FIX) ---

def get_smart_crop_focus(video_path, start_time, end_time):
    """Face Detection (Eyes)"""
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: return 50
        
        mid_frame = int((start_time + (end_time - start_time)/2) * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid_frame)
        ret, frame = cap.read()
        cap.release()
        
        if not ret: return 50
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        width = frame.shape[1]
        
        if len(faces) > 0:
            x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
            center_x = x + (w // 2)
            percent = (center_x / width) * 100
            return percent
        else:
            return 50
    except: return 50

def analyze_viral_moments_gemini(video_path):
    """Gemini Analysis (Fixed Brain)"""
    try:
        # 1. Upload
        video_file = genai.upload_file(video_path)
        
        # Wait for processing (Max 60 seconds wait)
        wait_time = 0
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            wait_time += 2
            video_file = genai.get_file(video_file.name)
            if wait_time > 60: return [] # Timeout fix
            
        if video_file.state.name == "FAILED": return []

        # 2. Strict Prompt
        prompt = """
        You are a video editor. Find exactly 2 most viral/interesting short segments from this video.
        OUTPUT REQUIREMENT: Return ONLY a raw JSON list. Do not use Markdown. Do not write "Here is the json".
        Format: [{"start": 10, "end": 25, "title": "Clip1"}, {"start": 40, "end": 55, "title": "Clip2"}]
        """
        
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        response = model.generate_content([video_file, prompt])
        
        # 3. Robust Parsing (Fix for "AI couldn't analyze")
        text = response.text
        
        # Extract JSON from text using regex (brackets ke beech ka maal uthao)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            # Fallback parsing
            clean_text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_text)
            
    except Exception as e:
        print(f"Gemini Error: {e}")
        return []

# --- 4. UI SETUP ---
st.set_page_config(page_title="AI Viral Studio", page_icon="🎥", layout="wide")

# --- 5. AUTH ---
if "user_email" not in st.session_state:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.title("👋 AI Viral Studio")
        st.write("Fully Automated Viral Shorts Generator")
    with col2:
        tab_login, tab_signup = st.tabs(["Login", "Create Account"])
        with tab_login:
            l_email = st.text_input("Email", key="l_email")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Login"):
                if l_email == ADMIN_EMAIL and l_pass == ADMIN_PASSWORD:
                    st.session_state.user_email = l_email
                    st.rerun()
                user = login_user(l_email, l_pass)
                if user:
                    st.session_state.user_email = user['email']
                    st.rerun()
                else: st.error("Invalid Credentials")
        with tab_signup:
            if "signup_step" not in st.session_state: st.session_state.signup_step = 1
            if st.session_state.signup_step == 1:
                s_email = st.text_input("New Email", key="s_email")
                s_pass = st.text_input("New Password", type="password", key="s_pass")
                if st.button("Get OTP"):
                    otp = send_otp_email(s_email)
                    if otp:
                        st.session_state.otp = otp
                        st.session_state.temp_email = s_email
                        st.session_state.temp_pass = s_pass
                        st.session_state.signup_step = 2
                        st.rerun()
            elif st.session_state.signup_step == 2:
                otp_in = st.text_input("Enter OTP")
                if st.button("Verify"):
                    if otp_in == st.session_state.otp:
                        register_user_final(st.session_state.temp_email, st.session_state.temp_pass)
                        st.session_state.user_email = st.session_state.temp_email
                        st.rerun()
    st.stop()

# --- 6. LOGGED IN ---
is_admin = (st.session_state.user_email == ADMIN_EMAIL)
user = {"email": ADMIN_EMAIL, "credits": 9999, "is_premium": True} if is_admin else None
if not is_admin:
    try:
        response = supabase.table('users').select("*").eq('email', st.session_state.user_email).execute()
        user = response.data[0] if response.data else None
    except: pass
if not user:
    st.session_state.clear()
    st.rerun()

# --- 7. SIDEBAR ---
st.sidebar.title("🛠️ Menu")
if is_admin:
    st.sidebar.header("👮‍♂️ Admin Panel")
    with st.sidebar.expander("Add Premium"):
        e = st.text_input("Email:")
        if st.button("Add"): 
            supabase.table('users').update({"is_premium": True, "credits": 9999}).eq('email', e).execute()
else:
    st.sidebar.write(f"Credits: {user['credits']}")
if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# --- 8. MAIN AUTOMATED TOOL ---
has_access = user['is_premium'] or user['credits'] > 0

if has_access:
    st.title("🤖 Auto-Pilot Viral Studio")
    st.info("Upload Video -> AI Finds Clips -> AI Tracks Face -> Enhanced Output")
    
    if 'generated_clips' not in st.session_state:
        st.session_state['generated_clips'] = []

    uf = st.file_uploader("Upload Video", type=["mp4"])
    
    if uf:
        if "cached_video_path" not in st.session_state:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uf.read())
            st.session_state["cached_video_path"] = tfile.name
        
        video_path = st.session_state["cached_video_path"]
        st.video(video_path)
        
        # Enhance Checkbox
        enhance_mode = st.checkbox("✨ Enhance Quality (Bright & Sharp)", value=True)
        
        if st.button("✨ Auto-Generate Viral Shorts (1 Credit)"):
            with st.status("🤖 AI is working magic...", expanded=True) as status:
                
                # 1. BRAIN
                status.write("🧠 Finding viral segments...")
                clips_data = analyze_viral_moments_gemini(video_path)
                
                if not clips_data:
                    status.error("AI couldn't analyze. Please try a different video.")
                    st.stop()
                
                status.write(f"✅ Found {len(clips_data)} clips!")
                
                # 2. EYES & HANDS
                original_clip = VideoFileClip(video_path)
                
                for i, c_data in enumerate(clips_data):
                    start = c_data['start']
                    end = c_data['end']
                    label = c_data.get('title', f"Viral Clip {i+1}")
                    
                    status.write(f"👀 Tracking Face: {label}...")
                    
                    face_pos = get_smart_crop_focus(video_path, start, end)
                    
                    # Ensure valid time range
                    if end > original_clip.duration: end = original_clip.duration
                    if start >= end: continue

                    sub = original_clip.subclip(start, end)
                    w, h = sub.size
                    new_w = int(h * (9/16))
                    if new_w % 2 != 0: new_w -= 1
                    
                    max_x = w - new_w
                    x1 = int((face_pos / 100) * max_x)
                    
                    final_clip = sub.crop(x1=x1, width=new_w, height=h)
                    
                    out_name = f"auto_viral_{i}_{int(time.time())}.mp4"
                    
                    ffmpeg_opts = ['-pix_fmt', 'yuv420p']
                    if enhance_mode:
                        ffmpeg_opts.extend(['-vf', 'eq=contrast=1.1:saturation=1.3,unsharp=5:5:1.0:5:5:0.0'])
                    
                    final_clip.write_videofile(
                        out_name, 
                        codec='libx264', 
                        audio_codec='aac', 
                        ffmpeg_params=ffmpeg_opts,
                        logger=None
                    )
                    
                    with open(out_name, "rb") as f:
                        st.session_state['generated_clips'].append({
                            "title": label,
                            "data": f.read(),
                            "name": out_name
                        })
                
                if not user['is_premium'] and not is_admin:
                    update_credits(user['email'], user['credits'])
                
                status.update(label="✅ Success!", state="complete")

    if st.session_state['generated_clips']:
        st.markdown("### 🔥 Ready Viral Shorts")
        for clip in st.session_state['generated_clips']:
            with st.expander(f"🎬 {clip['title']}", expanded=True):
                st.video(clip['data'])
                st.download_button("📥 Download", clip['data'], clip['name'])

else:
    st.error("Quota Expired.")
    st.link_button("👉 Buy Premium (₹99)", "https://wa.me/919575887748")
