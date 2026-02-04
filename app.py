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

# --- CONFIGURATION & SECRETS ---
try:
    GENAI_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    
    # AUTH SECRETS
    ADMIN_EMAIL = st.secrets["ADMIN_EMAIL"]
    ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]
    
    # EMAIL SECRETS
    SENDER_EMAIL = st.secrets["EMAIL_SENDER"]
    SENDER_PASSWORD = st.secrets["EMAIL_PASSWORD"]
    
except:
    st.error("⚠️ Secrets Missing! Please check Streamlit settings.")
    st.stop()

if GENAI_KEY != "TEST":
    genai.configure(api_key=GENAI_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- TEMP MAIL BLOCKER ---
TEMP_DOMAINS = ["tempmail", "10minutemail", "guerrillamail", "yopmail", "mailinator"]

def is_temp_mail(email):
    if "@" in email:
        domain = email.split('@')[-1]
        for temp in TEMP_DOMAINS:
            if temp in domain: return True
    return False

# --- EMAIL OTP FUNCTION ---
def send_otp_email(to_email):
    otp_code = str(random.randint(1000, 9999)) # 4 Digit Code
    
    subject = "Verify your AI Viral Studio Account"
    body = f"Hello,\n\nYour Verification Code is: {otp_code}\n\nUse this to activate your account.\n\nRegards,\nAI Viral Team"
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SENDER_EMAIL
    msg['To'] = to_email
    
    try:
        # Gmail Server Connection
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        server.quit()
        return otp_code
    except Exception as e:
        return None

# --- DB FUNCTIONS ---
def login_user(email, password):
    try:
        response = supabase.table('users').select("*").eq('email', email).eq('password', password).execute()
        return response.data[0] if response.data else None
    except: return None

def register_user_final(email, password):
    """OTP Verify hone ke baad ye chalega"""
    try:
        new_user = {"email": email, "password": password, "credits": 2, "is_premium": False}
        supabase.table('users').insert(new_user).execute()
        return True
    except:
        return False

def update_credits(email, current_credits):
    try:
        supabase.table('users').update({"credits": current_credits - 1}).eq('email', email).execute()
    except: pass

# --- UI CONFIG ---
st.set_page_config(page_title="AI Viral Studio", page_icon="🎥")

# --- AUTH SYSTEM (WITH OTP) ---
if "user_email" not in st.session_state:
    st.title("👋 AI Viral Studio")
    st.markdown("### Upload & Create Viral Shorts 🚀")
    
    tab_login, tab_signup = st.tabs(["Login", "Create Account"])

    # LOGIN TAB
    with tab_login:
        l_email = st.text_input("Email", key="l_email")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            if l_email == ADMIN_EMAIL and l_pass == ADMIN_PASSWORD:
                st.session_state.user_email = l_email
                st.success("Welcome Admin!")
                st.rerun()
            user = login_user(l_email, l_pass)
            if user:
                st.session_state.user_email = user['email']
                st.rerun()
            else:
                st.error("Galat Email ya Password!")

    # SIGNUP TAB (OTP LOGIC)
    with tab_signup:
        if "signup_step" not in st.session_state:
            st.session_state.signup_step = 1
        
        # STEP 1: ENTER DETAILS
        if st.session_state.signup_step == 1:
            s_email = st.text_input("New Email", key="s_email")
            s_pass = st.text_input("New Password", type="password", key="s_pass")
            
            if st.button("Send Verification Code"):
                if is_temp_mail(s_email):
                    st.error("Temp Mail not allowed!")
                elif len(s_pass) < 4:
                    st.warning("Password weak hai.")
                else:
                    check = supabase.table('users').select("*").eq('email', s_email).execute()
                    if check.data:
                        st.error("Account pehle se hai. Login karein.")
                    else:
                        with st.spinner("Sending OTP..."):
                            otp = send_otp_email(s_email)
                            if otp:
                                st.session_state.generated_otp = otp
                                st.session_state.temp_email = s_email
                                st.session_state.temp_pass = s_pass
                                st.session_state.signup_step = 2
                                st.success("OTP sent to your email!")
                                st.rerun()
                            else:
                                st.error("Email Error. Check Secrets.")

        # STEP 2: VERIFY OTP
        elif st.session_state.signup_step == 2:
            st.info(f"OTP sent to: {st.session_state.temp_email}")
            user_otp = st.text_input("Enter 4-Digit OTP")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Verify & Create Account"):
                    if user_otp == st.session_state.generated_otp:
                        success = register_user_final(st.session_state.temp_email, st.session_state.temp_pass)
                        if success:
                            st.session_state.user_email = st.session_state.temp_email
                            del st.session_state.generated_otp
                            del st.session_state.signup_step
                            st.success("Account Verified!")
                            st.rerun()
                        else:
                            st.error("Database Error.")
                    else:
                        st.error("Wrong OTP! Try again.")
            
            with col2:
                if st.button("Cancel / Back"):
                    st.session_state.signup_step = 1
                    st.rerun()
    
    st.stop()

# --- MAIN LOGIC (LOGGED IN) ---

# 1. Fetch User
is_admin = False
user = None
if st.session_state.user_email == ADMIN_EMAIL:
    user = {"email": ADMIN_EMAIL, "credits": 9999, "is_premium": True}
    is_admin = True
else:
    try:
        response = supabase.table('users').select("*").eq('email', st.session_state.user_email).execute()
        user = response.data[0] if response.data else None
    except: user = None

# 2. Admin Panel
if is_admin:
    st.sidebar.markdown("### 👮‍♂️ Admin Panel")
    target_email = st.sidebar.text_input("User Email ID:")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("Make Premium ✅"):
            if target_email:
                supabase.table('users').update({"is_premium": True, "credits": 9999}).eq('email', target_email).execute()
                st.sidebar.success("Premium Active!")
    with col2:
        if st.button("Remove Premium ❌"):
            if target_email:
                supabase.table('users').update({"is_premium": False, "credits": 2}).eq('email', target_email).execute()
                st.sidebar.error("Premium Removed!")
    st.sidebar.divider()
    if st.sidebar.button("Logout Admin"):
        del st.session_state.user_email
        st.rerun()

else:
    if user: st.sidebar.write(f"ID: {user['email']}")
    if st.sidebar.button("Logout"):
        del st.session_state.user_email
        st.rerun()

# 3. Access Check
has_access = False
if user and (user['is_premium'] or is_admin):
    has_access = True
    st.sidebar.success("🌟 Premium Plan")
elif user and user['credits'] > 0:
    has_access = True
    st.sidebar.info(f"Free Credits: {user['credits']}")

# 4. Upload & Process
if has_access:
    st.title("✂️ AI Viral Studio")
    st.write("Upload Large Video (Max 1GB)")
    
    video_path = None
    uf = st.file_uploader("Upload MP4", type=["mp4"])
    
    if uf:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uf.read())
        video_path = tfile.name
        
    if video_path:
        st.video(video_path)
        if st.button("✨ Make Viral Short (1 Credit)"):
            with st.spinner('Processing...'):
                try:
                    clip = VideoFileClip(video_path)
                    dur = clip.duration
                    start = dur/3 if dur > 60 else 0
                    sub = clip.subclip(start, min(start+30, dur))
                    
                    w, h = sub.size
                    target_ratio = 9/16
                    new_w = h * target_ratio
                    if new_w < w: sub = sub.crop(x1=(w/2 - new_w/2), y1=0, width=new_w, height=h)
                    
                    out = "viral.mp4"
                    sub.write_videofile(out, codec='libx264', audio_codec='aac', logger=None)
                    
                    if not is_admin and not user['is_premium']:
                        update_credits(user['email'], user['credits'])
                        
                    with open(out, "rb") as f:
                        st.download_button("Download", f, file_name="viral.mp4")
                except Exception as e: st.error(f"Error: {e}")

else:
    st.error("Free Limit Khatam!")
    
    # --- PRICING & WHATSAPP SECTION ---
    st.markdown("### 🔓 Unlock Unlimited Access")
    st.write("**Plan:** ₹99 for 1 Month")
    
    MY_NUMBER = "919575887748"
    # Is message mein change kiya gaya hai 👇
    msg = f"Hello! My ID is {user['email'] if user else 'User'}. I want to buy Premium Plan for ₹99 for 1 Month."
    url = f"https://wa.me/{MY_NUMBER}?text={msg.replace(' ', '%20')}"
    
    st.link_button("👉 Buy Premium (₹99/Month)", url)
