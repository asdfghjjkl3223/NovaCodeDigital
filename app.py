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
    # Local testing ke liye dummy values
    GENAI_KEY = "TEST"
    SUPABASE_URL = "TEST"
    SUPABASE_KEY = "TEST"

# Setup Clients
if GENAI_KEY != "TEST":
    genai.configure(api_key=GENAI_KEY)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- ADMIN DETAILS (Updated) ---
ADMIN_EMAIL = "neeraj14soni78@gmail.com"

# --- HELPER FUNCTIONS ---

def get_or_create_user(email):
    """User ko database mein check karta hai"""
    try:
        response = supabase.table('users').select("*").eq('email', email).execute()
        if response.data:
            return response.data[0]
        else:
            # New User = 2 Credits
            new_user = {"email": email, "credits": 2, "is_premium": False}
            supabase.table('users').insert(new_user).execute()
            return new_user
    except Exception as e:
        # Agar table na bani ho to crash nahi hoga, bas error dikhayega
        st.error(f"Database Error: {e}. Please check Supabase Table settings.")
        return {"email": email, "credits": 0, "is_premium": False}

def update_credits(email, current_credits):
    """Credit deduct karta hai"""
    try:
        supabase.table('users').update({"credits": current_credits - 1}).eq('email', email).execute()
    except:
        pass

def download_youtube_video(url):
    """YouTube video download fixed logic"""
    # Filename fix kiya hai taaki error na aaye
    output_filename = "downloaded_yt_video.mp4"
    
    # Purani file hatao agar hai to
    if os.path.exists(output_filename):
        os.remove(output_filename)
        
    ydl_opts = {
        'format': 'best[ext=mp4]',
        'outtmpl': output_filename, # Fixed name
        'quiet': True,
        'no_warnings': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        
    return output_filename

# --- UI START ---
st.set_page_config(page_title="AI Viral Studio", page_icon="🎥")

# --- LOGIN SYSTEM ---
if "user_email" not in st.session_state:
    st.title("👋 AI Viral Studio")
    st.markdown("### 🚀 Create Viral Shorts in Seconds")
    st.write("Login karke **2 Free Videos** banayein!")
    
    email_input = st.text_input("Apna Email ID dalein:")
    
    if st.button("Start Now"):
        if "@" in email_input:
            st.session_state.user_email = email_input.lower().strip()
            st.rerun()
        else:
            st.error("Please enter a valid email.")
    st.stop() 

# --- LOAD USER ---
if GENAI_KEY != "TEST":
    user = get_or_create_user(st.session_state.user_email)
else:
    user = {"email": "test@local", "credits": 2, "is_premium": False}

is_admin = (st.session_state.user_email == ADMIN_EMAIL)

# --- ADMIN PANEL ---
if is_admin:
    st.sidebar.markdown("### 👮‍♂️ Admin Panel")
    st.sidebar.info("Kisi bhi email ko Premium access dein")
    target_email = st.sidebar.text_input("User Email:")
    if st.sidebar.button("Activate Premium Access"):
        try:
            supabase.table('users').update({"is_premium": True, "credits": 9999}).eq('email', target_email).execute()
            st.sidebar.success(f"Done! {target_email} is now Premium.")
        except:
            st.sidebar.error("Failed. Check email spelling.")
    st.sidebar.divider()

# --- CHECK QUOTA ---
has_access = False
status_msg = ""

if user['is_premium']:
    has_access = True
    status_msg = "🌟 Premium Member (Unlimited)"
    st.sidebar.success(status_msg)
elif user['credits'] > 0:
    has_access = True
    status_msg = f"🎁 Free Account: {user['credits']} videos left"
    st.sidebar.info(status_msg)
else:
    has_access = False

st.sidebar.write(f"User: {user['email']}")

# --- MAIN TOOL ---
if has_access:
    st.title("✂️ AI Viral Studio")
    
    tab1, tab2 = st.tabs(["📤 Upload Video", "🔗 YouTube Link"])
    
    video_path = None
    
    # 1. Upload
    with tab1:
        uploaded_file = st.file_uploader("Video select karein (MP4)", type=["mp4"])
        if uploaded_file:
            tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tfile.write(uploaded_file.read())
            video_path = tfile.name
    
    # 2. YouTube
    with tab2:
        yt_url = st.text_input("YouTube Video Link paste karein:")
        if yt_url:
            if st.button("📥 Load Video"):
                with st.spinner("Downloading from YouTube..."):
                    try:
                        video_path = download_youtube_video(yt_url)
                        st.session_state['current_video'] = video_path # Save path
                        st.success("Video Loaded!")
                    except Exception as e:
                        st.error(f"Download Error: {e}")

    # Restore video path from session if available
    if 'current_video' in st.session_state and os.path.exists(st.session_state['current_video']):
        video_path = st.session_state['current_video']

    # --- PROCESSING ---
    if video_path:
        st.video(video_path)
        
        if st.button("✨ Make Viral Short (Cost: 1 Credit)"):
            with st.spinner('AI Cutting & Resizing...'):
                try:
                    clip = VideoFileClip(video_path)
                    
                    # Logic: Max 60 sec video
                    duration = clip.duration
                    start_t = 0
                    if duration > 60:
                        start_t = duration / 3 
                        
                    subclip = clip.subclip(start_t, min(start_t + 30, duration))
                    
                    # 9:16 Resize (Mobile)
                    w, h = subclip.size
                    target_ratio = 9/16
                    new_w = h * target_ratio
                    
                    if new_w < w:
                        subclip = subclip.crop(x1=(w/2 - new_w/2), y1=0, width=new_w, height=h)
                    
                    output_path = "viral_final.mp4"
                    subclip.write_videofile(output_path, codec='libx264', audio_codec='aac', logger=None)
                    
                    # Deduct Credit
                    if not user['is_premium']:
                        update_credits(user['email'], user['credits'])
                    
                    st.success("✅ Video Created Successfully!")
                    
                    with open(output_path, "rb") as file:
                        st.download_button(
                            label="📥 Download Viral Short",
                            data=file,
                            file_name="viral_short.mp4",
                            mime="video/mp4"
                        )
                        
                except Exception as e:
                    st.error(f"Error: {e}")

# --- PAYMENT SCREEN ---
else:
    st.title("🔒 Quota Khatam!")
    st.error("Aapke 2 Free Videos pure ho gaye.")
    st.markdown("---")
    st.markdown("### 🔓 Get Unlimited Access")
    st.write("Sirf **₹499/Month** mein unlimited videos banayein.")
    
    # WhatsApp Logic
    MY_NUMBER = "919575887748" 
    msg = f"Hello! Meri ID {user['email']} hai. Mujhe Premium Plan lena hai."
    wa_link = f"https://wa.me/{MY_NUMBER}?text={msg.replace(' ', '%20')}"
    
    st.link_button("👉 WhatsApp: Buy Premium", wa_link)
