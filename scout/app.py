import streamlit as st
import pandas as pd
from datetime import datetime
import time

from scout.core.db import ScoutDB
from scout.main import ScoutEngine
from scout.config import config

# Page Config
st.set_page_config(
    page_title="Belief Forge Scout",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize
if 'db' not in st.session_state:
    st.session_state.db = ScoutDB()
if 'engine' not in st.session_state:
    st.session_state.engine = ScoutEngine()

# Custom CSS
st.markdown("""
<style>
    .briefing-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 20px;
    }
    .intent-badge {
        color: #ffffff;
        padding: 4px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.85em;
        letter-spacing: 0.5px;
    }
    /* WCAG AAA Compliant Backgrounds (Contrast > 7:1 with white text) */
    .intent-distress { background-color: #b71c1c; } /* Dark Red */
    .intent-strategy { background-color: #0d47a1; } /* Dark Blue */
    .intent-venting { background-color: #004d40; }  /* Dark Teal */
    .intent-ignore { background-color: #424242; }   /* Dark Gray */
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🛡️ The Scout")
    
    # Navigation
    page = st.radio("Go to", ["Briefings", "Settings"])
    
    st.markdown("---")
    
    # Status Widget
    if page == "Briefings":
        st.subheader("System Status")
        col1, col2 = st.columns(2)
        col1.metric("Run Cost", "$0.00") # Placeholder
        col2.metric("Handshakes", "0") # Placeholder
        
        st.markdown("---")
        
        # Actions
        if st.button("🚀 Run Mission Now", type="primary"):
            # Check for keys in config (persistent) OR session state (just typed)
            api_key = config.ai.api_key or st.session_state.get('openrouter_key')
            
            if not api_key:
                 st.error("Please configure API Keys in Settings first!")
            else:
                # Mission Control UI
                st.markdown("### 📡 Mission Control")
                progress_bar = st.progress(0, text="Initializing query...")
                status_area = st.empty()
                log_area = st.expander("Mission Logs", expanded=True)
                logs = []
                
                def ui_callback(msg, pct):
                    # Update Progress
                    progress_bar.progress(pct, text=msg)
                    # Update Log
                    logs.append(f"{datetime.now().strftime('%H:%M:%S')} - {msg}")
                    log_area.code("\n".join(logs[-10:]), language="bash") # Show last 10 lines
                
                try:
                    # Run mission with callback
                    st.session_state.engine.run_mission(callback=ui_callback)
                    st.success("Mission Complete!")
                    time.sleep(1) # Let user see success
                    st.rerun()
                except Exception as e:
                    st.error(f"Mission failed: {e}")

# Main Content
if page == "Settings":
    st.title("⚙️ Settings")
    st.markdown("Configure your scout safely. Keys are saved to `scout/.env` and persist.")
    
    # Import config to get current values (loaded from .env on startup)
    from scout.config import config
    
    with st.form("settings_form"):
        st.subheader("🤖 AI Brain (OpenRouter)")
        st.caption("Required for screening and drafting. (Get key from openrouter.ai)")
        
        # Default to session state (if just edited) OR config (if loaded from disk)
        current_op_key = st.session_state.get('openrouter_key', config.ai.api_key or '')
        op_key = st.text_input("OpenRouter API Key", type="password", value=current_op_key)
        
        st.subheader("📡 Reddit Access (Read-Only OK)")
        st.caption("You only need Client ID & Secret to scrape. Username/Pass required ONLY for posting.")
        
        current_r_id = st.session_state.get('reddit_client_id', config.reddit.client_id or '')
        current_r_secret = st.session_state.get('reddit_client_secret', config.reddit.client_secret or '')
        
        r_id = st.text_input("Client ID", value=current_r_id)
        r_secret = st.text_input("Client Secret", type="password", value=current_r_secret)
        
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            # Update Session State
            st.session_state['openrouter_key'] = op_key
            st.session_state['reddit_client_id'] = r_id
            st.session_state['reddit_client_secret'] = r_secret
            
            # Update Config in Memory
            config.ai.api_key = op_key
            config.reddit.client_id = r_id
            config.reddit.client_secret = r_secret
            
            # Persist to .env file
            env_content = f"""# Generated by Scout Settings
OPENROUTER_API_KEY={op_key}
REDDIT_CLIENT_ID={r_id}
REDDIT_CLIENT_SECRET={r_secret}
SCOUT_SCHEDULE_HOURS=6,18
"""
            try:
                # Write to .env in the scout directory
                with open("scout/.env", "w") as f:
                    f.write(env_content)
                st.success("Settings saved to disk! Keys will persist.")
            except Exception as e:
                st.error(f"Failed to save to .env file: {e}")

elif page == "Briefings":
    st.title("Daily Briefing")
    st.markdown("Here are the high-value opportunities found today.")

    # Fetch Pending Briefings
    briefings = st.session_state.db.get_pending_briefings()

    if not briefings:
        st.info("No pending briefings. Go to Settings > Configure Keys > Run Mission.")
    else:
        for item in briefings:
            with st.container():
                # Card Layout
                col_content, col_action = st.columns([2, 1])
                
                with col_content:
                    st.markdown(f"### {item['title']}")
                    # Use lower() for class name matching
                    intent_cls = f"intent-{item['intent'].lower()}"
                    st.markdown(f"**r/{item['subreddit']}** • <span class='intent-badge {intent_cls}'>{item['intent'].upper()}</span>", unsafe_allow_html=True)
                    st.caption(f"Posted: {item['created_at']}")
                    
                    with st.expander("View Original Post Content"):
                        st.write(item['post_content'])
                        st.markdown(f"[View on Reddit]({item['post_url']})")
                    
                    st.text_area("Draft Reply", value=item['draft_content'], height=150, key=f"draft_{item['post_id']}")
                    
                with col_action:
                    st.markdown("### Action")
                    
                    if st.button("✅ Approve & Post", key=f"approve_{item['post_id']}", type="primary"):
                        st.session_state.db.update_briefing_status(item['post_id'], 'approved', st.session_state[f"draft_{item['post_id']}"])
                        st.success("Reply stored (Scheduling not valid in safe mode)")
                        st.rerun()
                        
                    if st.button("🗑️ Discard", key=f"discard_{item['post_id']}"):
                        st.session_state.db.update_briefing_status(item['post_id'], 'discarded')
                        st.rerun()

                st.divider()
