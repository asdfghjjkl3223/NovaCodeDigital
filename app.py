import streamlit as st
import google.generativeai as genai
from moviepy.editor import VideoFileClip
from supabase import create_client, Client
import yt_dlp
import tempfile
import os
import time

# --- CONFIGURATION & SECRETS ---
try:
    GENAI_KEY = st.secrets["GEMINI_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    GENAI_KEY = "TEST"
    SUPABASE_URL = "TEST"
    SUPABASE_KEY = "TEST"

if GENAI_KEY != "TEST":
    genai.configure(api_key=GENAI_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ADMIN DETAILS ---
ADMIN_EMAIL = "neeraj14soni78@gmail.com"
ADMIN_PASSWORD = "Neerajansh123"  # <-- Password yahan set karein

# --- TEMP MAIL BLOCKER ---
TEMP_DOMAINS = ["tempmail", "10minutemail", "guerrillamail", "yopmail", "mailinator"]

# --- HELPER FUNCTIONS ---

def is_temp_mail(email):
    if "@" in email:
        domain = email.split('@')[-1]
        for temp in TEMP_DOMAINS:
            if temp in domain: return True
    return False

def login_user(email, password):
    try:
        response = supabase.table('users').select("*").eq('email', email).eq('password', password).execute()
        return response.data[0] if response.data else None
    except: return None

def register_user(email, password):
    if is_temp_mail(email): return "TEMP_MAIL_ERROR"
    try:
        check = supabase.table('users').select("*").eq('email', email).execute()
        if check.data: return "USER_EXISTS"
        
        # Default: Free Account (2 Credits)
        new_user = {"email": email, "password": password, "credits": 2, "is_premium": False}
        supabase.table('users').insert(new_user).execute()
        return "SUCCESS"
    except Exception as e:
        return f"Error: {e}"

def update_credits(email, current_credits):
    try:
        supabase.table('users').update({"credits": current_credits - 1}).eq('email', email).execute()
    except: pass

def download_youtube_video(url):
    """YouTube Fix: Try Android then iOS client"""
    output_filename = "downloaded_yt_video.mp4"
    if os.path.exists(output_filename): os.remove(output_filename)
    
    # Try Android Client
    opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_filename,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['android']}},
    }
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        return output_filename
    except:
        # Try iOS Client if Android fails
        try:
            opts['extractor_args'] = {'youtube': {'player_client': ['ios']}}
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return output_filename
        except:
            return None

# --- UI START ---
st.set_page_config(page_title="AI Viral Studio", page_icon="🎥")

# --- AUTH SYSTEM ---
if "user_email" not in st.session_state:
    st.title("👋 AI Viral Studio")
    
    tab_login, tab_signup = st.tabs(["Login", "Create Account"])

    # Login Tab
    with tab_login:
        l_email = st.text_input("Email", key="l_email")
        l_pass = st.text_input("Password", type="password", key="l_pass")
        if st.button("Login"):
            # Admin Check
            if l_email == ADMIN_EMAIL and l_pass == ADMIN_PASSWORD:
                st.session_state.user_email = l_email
                st.success("Welcome Admin!")
                st.rerun()
            
            # User Check
            user = login_user(l_email, l_pass)
            if user:
                st.session_state.user_email = user['email']
                st.rerun()
            else:
                st.error("Email ya Password galat hai.")

    # Signup Tab
    with tab_signup:
        s_email = st.text_input("New Email", key="s_email")
        s_pass = st.text_input("New Password", type="password", key="s_pass")
        if st.button("Sign Up"):
            if len(s_pass) < 4:
                st.warning("Password thoda strong rakhein.")
            else:
                res = register_user(s_email, s_pass)
                if res == "SUCCESS":
                    st.session_state.user_email = s_email
                    st.success("Account Ban Gaya!")
                    st.rerun()
                elif res == "USER_EXISTS": st.error("Account pehle se bana hai. Login karein.")
                elif res == "TEMP_MAIL_ERROR": st.error("Temp mail allowed nahi hai.")
                else: st.error(res)
    st.stop()

# --- MAIN APP LOGIC ---

# 1. Fetch User Data
is_admin = False
user = None
if GENAI_KEY != "TEST":
    if st.session_state.user_email == ADMIN_EMAIL:
        user = {"email": ADMIN_EMAIL, "credits": 9999, "is_premium": True}
        is_admin = True
    else:
        response = supabase.table('users').select("*").eq('email', st.session_state.user_email).execute()
        user = response.data[0] if response.data else None

# 2. Sidebar & Admin Panel (UPDATED FOR YOU)
if is_admin:
    st.sidebar.markdown("### 👮‍♂️ Admin Panel")
    st.sidebar.success("Mode: Upgrade Users")
    
    st.sidebar.info("User ki Email dalein jise Premium banana hai:")
    target_email = st.sidebar.text_input("User Email ID:")
    
    if st.sidebar.button("Upgrade to Premium ✅"):
        if target_email:
            try:
                # Sirf update query chalegi
                response = supabase.table('users').update({"is_premium": True, "credits": 9999}).eq('email', target_email).execute()
                # Check agar user exist karta tha
                if response.data:
                    st.sidebar.success(f"Success! {target_email} ab Premium hai.")
                else:
                    st.sidebar.error("Yeh Email Database mein nahi mili.")
            except Exception as e:
                st.sidebar.error(f"Error: {e}")
        else:
            st.sidebar.warning("Pehle Email likhein.")
            
    st.sidebar.divider()
    if st.sidebar.button("Logout Admin"):
        del st.session_state.user_email
        st.rerun()

else:
    # Normal User Sidebar
    st.sidebar.write(f"ID: {user['email']}")
    if st.sidebar.button("Logout"):
        del st.session_state.user_email
        st.rerun()

# 3. Access Check
has_access = False
if user and (user['is_premium'] or is_admin):
    has_access = True
    st.sidebar.success("🌟 Premium Plan Active")
elif user and user['credits'] > 0:
    has_access = True
    st.sidebar.info(f"Free Credits: {user['credits']}")

# 4. Tool Interface
if has_access:
    st.title("✂️ AI Viral Studio")
    tab1, tab2 = st.tabs(["📤 Upload Video", "🔗 YouTube Link"])
    video_path = None
    
    with tab1:
        uf = st.file_uploader("Upload MP4", type=["mp4"])
        if uf:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uf.read())
            video_path = tfile.name
            
    with tab2:
        yt_url = st.text_input("Paste Link:")
        if yt_url:
            if st.button("Download Video"):
                with st.spinner("Downloading..."):
                    path = download_youtube_video(yt_url)
                    if path:
                        st.session_state['vpath'] = path
                        st.success("Video Loaded!")
                    else:
                        st.error("YouTube Error: Please use Upload option.")
    
    if 'vpath' in st.session_state and os.path.exists(st.session_state['vpath']):
        video_path = st.session_state['vpath']
        
    if video_path:
        st.video(video_path)
        if st.button("✨ Make Viral Short"):
            with st.spinner('AI Cutting & Resizing...'):
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
                        st.download_button("Download Viral Video", f, file_name="viral.mp4")
                except Exception as e: st.error(f"Processing Error: {e}")

else:
    st.error("Free Limit Khatam!")
    
    MY_NUMBER = "919575887748" 
    msg = f"Hello! My ID is {user['email']}. I want to upgrade to Premium."
    url = f"https://wa.me/{MY_NUMBER}?text={msg.replace(' ', '%20')}"
    st.link_button("👉 Upgrade on WhatsApp", url)
