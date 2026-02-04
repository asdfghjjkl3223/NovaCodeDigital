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

# --- 3. UI SETUP ---
st.set_page_config(page_title="AI Viral Studio", page_icon="🎥", layout="wide")

# --- 4. LOGIN / SIGNUP ---
if "user_email" not in st.session_state:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.title("👋 AI Viral Studio")
        st.write("Login to create Viral Shorts.")
    with col2:
        tab_login, tab_signup = st.tabs(["Login", "Create Account"])
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
                else: st.error("Invalid Credentials")
        with tab_signup:
            if "signup_step" not in st.session_state: st.session_state.signup_step = 1
            if st.session_state.signup_step == 1:
                s_email = st.text_input("New Email", key="s_email")
                s_pass = st.text_input("New Password", type="password", key="s_pass")
                if st.button("Get OTP"):
                    if is_temp_mail(s_email): st.error("No Temp Mail!")
                    elif len(s_pass) < 4: st.warning("Weak Password")
                    else:
                        check = supabase.table('users').select("*").eq('email', s_email).execute()
                        if check.data: st.error("Exists!")
                        else:
                            otp = send_otp_email(s_email)
                            if otp:
                                st.session_state.otp = otp
                                st.session_state.temp_email = s_email
                                st.session_state.temp_pass = s_pass
                                st.session_state.signup_step = 2
                                st.rerun()
            elif st.session_state.signup_step == 2:
                st.info(f"OTP sent to {st.session_state.temp_email}")
                otp_in = st.text_input("Enter OTP")
                if st.button("Verify"):
                    if otp_in == st.session_state.otp:
                        register_user_final(st.session_state.temp_email, st.session_state.temp_pass)
                        st.session_state.user_email = st.session_state.temp_email
                        st.rerun()
                    else: st.error("Wrong OTP")
    st.stop()

# --- 5. LOGGED IN LOGIC ---
is_admin = False
user = None
if st.session_state.user_email == ADMIN_EMAIL:
    is_admin = True
    user = {"email": ADMIN_EMAIL, "credits": 9999, "is_premium": True}
else:
    try:
        response = supabase.table('users').select("*").eq('email', st.session_state.user_email).execute()
        user = response.data[0] if response.data else None
    except: pass

if not user:
    st.error("Session Error.")
    if st.sidebar.button("Logout"):
        del st.session_state.user_email
        st.rerun()
    st.stop()

# --- 6. SIDEBAR (ADMIN LIST FEATURE) ---
st.sidebar.title("🛠️ Menu")

if is_admin:
    st.sidebar.header("👮‍♂️ Admin Panel")
    
    # --- ADD PREMIUM ---
    with st.sidebar.expander("➕ Add Premium User", expanded=True):
        add_email = st.text_input("Email Address:", placeholder="user@gmail.com")
        if st.button("Grant Premium ✅"):
            if add_email:
                supabase.table('users').update({"is_premium": True, "credits": 9999}).eq('email', add_email).execute()
                st.success(f"Added: {add_email}")
                time.sleep(1)
                st.rerun()

    st.sidebar.markdown("---")
    
    # --- LIST & REMOVE PREMIUM ---
    st.sidebar.subheader("📋 Active Premium Users")
    
    try:
        # Fetch data
        p_users = supabase.table('users').select("email").eq('is_premium', True).execute()
        
        if p_users.data:
            for p_user in p_users.data:
                # Admin khud ko na dikhaye
                if p_user['email'] == ADMIN_EMAIL:
                    continue
                
                # Layout: Email | Remove Button
                c1, c2 = st.sidebar.columns([3, 1])
                
                c1.text(p_user['email'])
                
                # Make Free Button
                if c2.button("❌", key=f"rm_{p_user['email']}", help="Click to Make Free User"):
                    supabase.table('users').update({"is_premium": False, "credits": 2}).eq('email', p_user['email']).execute()
                    st.toast(f"Removed Premium: {p_user['email']}")
                    time.sleep(1)
                    st.rerun()
                
                st.sidebar.markdown("---") # Separator line
        else:
            st.sidebar.info("No Active Premium Users.")
            
    except Exception as e:
        st.sidebar.error("Loading Error...")

else:
    st.sidebar.write(f"User: **{user['email']}**")
    if user['is_premium']:
        st.sidebar.success("🌟 Premium Active")
    else:
        st.sidebar.info(f"Free Credits: {user['credits']}")

st.sidebar.markdown("---")
if st.sidebar.button("Logout"):
    del st.session_state.user_email
    st.rerun()

# --- 7. MAIN APP TOOL ---
has_access = user['is_premium'] or user['credits'] > 0

if has_access:
    st.title("✂️ AI Viral Studio")
    st.write("Upload Video (Max 1GB)")
    
    uf = st.file_uploader("Upload MP4", type=["mp4"])
    
    if uf:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uf.read())
        st.video(tfile.name)
        
        if st.button("✨ Make Viral Short (1 Credit)"):
            with st.spinner("Processing..."):
                try:
                    clip = VideoFileClip(tfile.name)
                    dur = clip.duration
                    start = dur/3 if dur > 60 else 0
                    sub = clip.subclip(start, min(start+30, dur))
                    
                    w, h = sub.size
                    new_w = h * (9/16)
                    if new_w < w: sub = sub.crop(x1=w/2-new_w/2, width=new_w, height=h)
                    
                    out = "viral.mp4"
                    sub.write_videofile(out, codec='libx264', audio_codec='aac', logger=None)
                    
                    if not user['is_premium'] and not is_admin:
                        update_credits(user['email'], user['credits'])
                    
                    st.success("Video Ready!")
                    with open(out, "rb") as f:
                        st.download_button("Download Viral Short", f, "viral_short.mp4")
                except Exception as e: st.error(f"Error: {e}")
else:
    st.title("🔒 Quota Expired")
    st.error("Free Credits khatam!")
    
    st.markdown("### 🔓 Unlimited Access")
    st.write("💰 **Price: ₹99 / Month**")
    
    MY_NUMBER = "919575887748"
    msg = f"Hello! My ID is {user['email']}. I want to buy Premium Plan for ₹99 for 1 Month."
    url = f"https://wa.me/{MY_NUMBER}?text={msg.replace(' ', '%20')}"
    
    st.link_button("👉 Buy Premium on WhatsApp", url)
