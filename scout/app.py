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

# Initialize Scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

if 'scheduler' not in st.session_state:
    st.session_state.scheduler = BackgroundScheduler()
    st.session_state.scheduler.start()

def scheduled_job():
    """Wrapper to run mission in background."""
    print("⏰ Scheduled Mission Triggered")
    eng = ScoutEngine()
    eng.run_mission()

# Start/Stop Job based on config
sched_enabled = config.settings.get("scheduler_enabled", False)
job_id = "scout_mission_cron"

if sched_enabled:
    if not st.session_state.scheduler.get_job(job_id):
        # Run 3 times a day: 07:00, 14:00, 21:00
        trigger = CronTrigger(hour='7,14,21', minute='0')
        st.session_state.scheduler.add_job(
            scheduled_job, 
            trigger, 
            id=job_id
        )
else:
    if st.session_state.scheduler.get_job(job_id):
        st.session_state.scheduler.remove_job(job_id)


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
    page = st.radio("Go to", ["Briefings", "Settings", "Engagements"])
    
    st.markdown("---")
    
    # Scheduler Status
    if sched_enabled:
        next_run = st.session_state.scheduler.get_job(job_id).next_run_time
        st.caption(f"✅ Auto-Scout: Active\nNext: {next_run.strftime('%H:%M')}")
    else:
        st.caption("⏸️ Auto-Scout: Paused")

    st.markdown("---")
    
    # Status Widget
    if page == "Briefings":
        st.subheader("System Status")
        col1, col2 = st.columns(2)
        col1.metric("Run Cost", "$0.00") # Placeholder
        
        # Get Engagement Stats
        try:
           eng_stats = st.session_state.db.get_engagement_stats()
           handshakes = eng_stats.get('handshakes', 0)
        except:
           handshakes = 0
           
        col2.metric("Handshakes", handshakes)
        
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

if page == "Engagements":
    st.title("🤝 Engagement Tracker")
    st.markdown("Monitoring your recent comments for replies (Handshakes).")
    
    if st.button("🔭 Scan My Profile Now"):
        with st.spinner("Scanning your Reddit history..."):
            total, new_handshakes = st.session_state.engine.run_profile_watcher()
            if new_handshakes > 0:
                st.balloons()
            st.success(f"Scanned {total} comments. Found {new_handshakes} new handshakes!")
            
    # Stats
    stats = st.session_state.db.get_engagement_stats()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Threads", stats['active_conversations'])
    col2.metric("Net Karma", stats['net_karma'])
    col3.metric("Handshakes (Replies)", stats['handshakes'])
    
    st.markdown("---")
    
    # Table View
    with st.expander("Detailed Engagement Log", expanded=True):
        # Fetch data manually
        import sqlite3
        try:
             with sqlite3.connect(st.session_state.db.db_path) as conn:
                 df = pd.read_sql_query("SELECT * FROM engagements ORDER BY posted_at DESC LIMIT 50", conn)
                 
             if not df.empty:
                 # Clean up display
                 df['posted_at'] = pd.to_datetime(df['posted_at'], unit='s')
                 st.dataframe(
                     df[['subreddit', 'body_snippet', 'score', 'reply_count', 'has_handshake', 'posted_at']],
                     use_container_width=True
                 )
             else:
                 st.info("No engagement data found yet. Run a scan!")
        except Exception as e:
            st.error(f"Error loading log: {e}")

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
        st.caption("You only need Client ID & Secret to scrape. Username required for Profile Watcher.")
        
        current_r_id = st.session_state.get('reddit_client_id', config.reddit.client_id or '')
        current_r_secret = st.session_state.get('reddit_client_secret', config.reddit.client_secret or '')
        current_r_user = st.session_state.get('reddit_username', config.settings.get("reddit_username", ""))
        
        r_id = st.text_input("Client ID", value=current_r_id)
        r_secret = st.text_input("Client Secret", type="password", value=current_r_secret)
        r_user = st.text_input("Reddit Username (for Engagement Tracking)", value=current_r_user, placeholder="e.g. belief_forge_guy")

        st.subheader("🔔 Notifications (Telegram)")
        st.caption("Get alerted when new opportunities are found.")
        current_tg_token = st.session_state.get('telegram_token', config.settings.get("telegram_token", ""))
        current_tg_chat = st.session_state.get('telegram_chat_id', config.settings.get("telegram_chat_id", ""))
        
        tg_token = st.text_input("Bot Token", type="password", value=current_tg_token)
        tg_chat = st.text_input("Chat ID", value=current_tg_chat)

        st.markdown("---")
        st.subheader("🎯 Scout Targets")
        st.caption("Subreddits to monitor (comma separated).")
        current_subs = st.session_state.get('target_subreddits', ", ".join(config.settings.get("target_subreddits", [])))
        subs_input = st.text_area("Subreddits", value=current_subs, height=100)
        
        st.subheader("🧭 Pathfinder Keywords")
        st.caption("Keywords to hunt for in the wild (comma separated).")
        current_keywords = st.session_state.get('pathfinder_keywords', ", ".join(config.settings.get("pathfinder_keywords", [])))
        keywords_input = st.text_area("Keywords", value=current_keywords, height=60)

        st.markdown("---")
        st.subheader("⏰ Automation")
        current_sched = st.session_state.get('scheduler_enabled', config.settings.get("scheduler_enabled", False))
        sched_enabled_ui = st.checkbox("Enable Auto-Scout (07:00, 14:00, 21:00)", value=current_sched)

        st.markdown("---")
        st.subheader("🧠 Brain Voice (System Prompt)")
        st.caption("The instruction given to the AI copywriter.")
        current_prompt = st.session_state.get('system_prompt', config.settings.get("system_prompt", ""))
        prompt_input = st.text_area("System Prompt", value=current_prompt, height=300)
        
        submitted = st.form_submit_button("Save Settings")
        if submitted:
            # Update Session State
            st.session_state['openrouter_key'] = op_key
            st.session_state['reddit_client_id'] = r_id
            st.session_state['reddit_client_secret'] = r_secret
            st.session_state['reddit_username'] = r_user
            st.session_state['target_subreddits'] = subs_input
            st.session_state['pathfinder_keywords'] = keywords_input
            st.session_state['scheduler_enabled'] = sched_enabled_ui
            st.session_state['system_prompt'] = prompt_input
            st.session_state['telegram_token'] = tg_token
            st.session_state['telegram_chat_id'] = tg_chat
            
            # Update Config in Memory
            config.ai.api_key = op_key
            config.reddit.client_id = r_id
            config.reddit.client_secret = r_secret
            
            # Parse lists
            subs_list = [s.strip() for s in subs_input.split(",") if s.strip()]
            keywords_list = [k.strip() for k in keywords_input.split(",") if k.strip()]
            
            # Save Dynamic Settings to JSON
            config.save_settings({
                "target_subreddits": subs_list,
                "pathfinder_keywords": keywords_list,
                "scheduler_enabled": sched_enabled_ui,
                "system_prompt": prompt_input,
                "telegram_token": tg_token,
                "telegram_chat_id": tg_chat,
                "reddit_username": r_user
            })
            
            # Persist Secrets to .env file
            env_content = f"""# Generated by Scout Settings
OPENROUTER_API_KEY={op_key}
REDDIT_CLIENT_ID={r_id}
REDDIT_CLIENT_SECRET={r_secret}
REDDIT_USERNAME={r_user}
SCOUT_SCHEDULE_HOURS=6,18
TELEGRAM_BOT_TOKEN={tg_token}
TELEGRAM_CHAT_ID={tg_chat}
"""
            try:
                # Write to .env in the scout directory
                with open("scout/.env", "w") as f:
                    f.write(env_content)
                st.success("Settings saved to disk! Keys & Config will persist.")
            except Exception as e:
                st.error(f"Failed to save to .env file: {e}")

elif page == "Briefings":
    st.title("🦅 Mission Briefings")
    
    # --- METRICS DASHBOARD ---
    # Fetch real stats from DB
    try:
        stats = st.session_state.db.get_stats()
    except Exception as e:
        stats = {"pending": 0, "approved": 0, "discarded": 0, "total_scanned": 0}

    # Display Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Scanned", stats['total_scanned'])
    m2.metric("Pending", stats['pending'])
    m3.metric("Approved", stats['approved'])
    m4.metric("Discarded", stats['discarded'])
    st.markdown("---")

    # --- PENDING BRIEFINGS ---
    briefings = st.session_state.db.get_pending_briefings()

    if not briefings:
        st.info("Everything is quiet. No pending briefings.")
    else:
        for item in briefings:
            with st.container():
                # Card Styling
                badge_class = f"intent-{item['intent']}"
                
                st.markdown(f"""
                <div class="briefing-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                        <span class="intent-badge {badge_class}">{item['intent'].upper()}</span>
                        <span style="color:#666; font-size:0.9em;">r/{item['subreddit']} • Score: Unknown</span>
                    </div>
                    <h4>{item['title']}</h4>
                    <p style="font-size:0.95em; color:#444;">{item['post_content'][:300]}...</p>
                    <a href="{item['post_url']}" target="_blank" style="text-decoration:none; color:#0d47a1; font-weight:bold; font-size:0.9em;">🔗 Open Reddit Source</a>
                </div>
                """, unsafe_allow_html=True)

                # Editing & Actions
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    draft_text = st.text_area("Draft Response", value=item['draft_content'], height=150, key=f"draft_{item['post_id']}")
                
                with col2:
                    st.write("### Actions")
                    
                    # Rate Limit Logic
                    last_post = st.session_state.get('last_post_time', 0)
                    now = time.time()
                    time_diff = now - last_post
                    cooldown = 46 
                    remaining = cooldown - time_diff
                    is_cooldown = remaining > 0
                    
                    # Approve & Copy (Manual Flow)
                    btn_label = f"⏳ Wait {int(remaining)}s" if is_cooldown else "✅ Approve & Copy"
                    
                    if st.button(btn_label, key=f"approve_{item['post_id']}", type="primary", disabled=is_cooldown):
                        # 1. Update DB -> 'approved'
                        st.session_state.db.update_briefing_status(item['post_id'], 'approved', draft_text) 
                        
                        # 2. Update Rate Limit
                        st.session_state['last_post_time'] = time.time()
                        
                        # 3. Show Copy UI
                        st.success("Approved! Copy code below:")
                        st.code(draft_text, language="text")
                        st.link_button("➡️ Open Reddit Reply Box", item['post_url'])
                        
                        # We stop execution here so the buttons stay visible for copying/clicking

                    if st.button("❌ Discard", key=f"discard_{item['post_id']}"):
                         st.session_state.db.update_briefing_status(item['post_id'], 'discarded')
                         st.rerun()
