import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
from st_copy_to_clipboard import st_copy_to_clipboard
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import time
from typing import Optional

from scout.core.db import ScoutDB
from scout.main import ScoutEngine
from scout.config import config
from scout.core.system import SystemManager
from st_clipboard import copy_to_clipboard
import streamlit_authenticator as stauth
import os
import re

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

# --- GLOBAL INITIALIZATION (Background Persistence) ---
@st.cache_resource
def get_system_manager():
    from apscheduler.schedulers.background import BackgroundScheduler
    from scout.core.system import SystemManager
    
    scheduler = BackgroundScheduler()
    scheduler.start()
    return SystemManager(scheduler)

system_manager = get_system_manager()

# --- HELPERS ---
def format_time_ago(timestamp_float):
    if not timestamp_float:
        return ""
    
    dt = datetime.fromtimestamp(timestamp_float)
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days}d ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600}h ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60}m ago"
    else:
        return "Just now"

def clean_html(raw_html):
    """Remove HTML tags and unescape entities from a string."""
    if not raw_html:
        return ""
    
    # First unescape (e.g. &lt; -> <)
    import html
    text = html.unescape(raw_html)
    
    # Then strip tags
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', text)
    
    return cleantext

def scheduled_job():
    """Wrapper to run mission in background."""
    print("⏰ Scheduled Mission Triggered")
    eng = ScoutEngine()
    eng.run_mission()

# Start/Stop Job based on config (Global App Level)
from apscheduler.triggers.cron import CronTrigger
sched_enabled = config.settings.get("scheduler_enabled", False)
job_id = "scout_mission_cron"
trigger = CronTrigger(hour='7,14,21', minute='0')

system_manager.sync_scheduler(
    enabled=sched_enabled,
    job_id=job_id,
    job_func=scheduled_job,
    trigger=trigger
)

# --- AUTHENTICATION ---
# We use simple env vars for a single-user setup
admin_username = "admin"
admin_name = "Scout Admin"
admin_hashed_password = os.getenv("AUTH_PASSWORD_HASH", "")

# If no password hash is provided, we disable auth for now but warn
if not admin_hashed_password:
    st.warning("⚠️ AUTH_PASSWORD_HASH not found in .env. Authentication is disabled.")
    st.session_state["authentication_status"] = True
else:
    credentials = {
        "usernames": {
            admin_username: {
                "name": admin_name,
                "password": admin_hashed_password
            }
        }
    }
    
    authenticator = stauth.Authenticate(
        credentials,
        os.getenv("AUTH_COOKIE_NAME", "scout_auth"),
        os.getenv("AUTH_COOKIE_KEY", "scout_secret_key"),
        cookie_expiry_days=30
    )

    name, authentication_status, username = authenticator.login(location="main")

    if st.session_state["authentication_status"] == False:
        st.error("Username/password is incorrect")
    elif st.session_state["authentication_status"] == None:
        st.warning("Please enter your username and password")

if st.session_state.get("authentication_status"):
    
    # --- URL OPENER & CLIPBOARD LOGIC ---
    if 'open_url_next' in st.session_state:
        target_url = st.session_state['open_url_next']
        copy_text = st.session_state.get('copy_text_next', '')
        
        # 1. Trigger Programmatic Copy (No iframe restriction)
        if copy_text:
            copy_to_clipboard(copy_text)
            # Note: We don't delete copy_text_next yet because we might need it for a rerun context
            # but st-clipboard triggers its own JS safely.
        
        # 2. Open Reddit (JS Injection)
        # We use a very slight delay or just standard injection for the window.open
        js = f"""
        <script>
            // Opening tab immediately after copy trigger
            setTimeout(() => {{
                window.open("{target_url}", "_blank");
            }}, 100);
        </script>
        """
        components.html(js, height=0, width=0)
        
        # Cleanup flags
        del st.session_state['open_url_next']
        if 'copy_text_next' in st.session_state:
            del st.session_state['copy_text_next']
    # ------------------------
    
    
    # Custom CSS
    st.markdown("""
    <style>
        .briefing-card {
            background-color: #f0f2f6;
            color: #31333F; /* WCAG AA: High contrast text */
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
        .intent-manual { background-color: #e65100; }   /* Deep Orange */
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.title("🛡️ The Scout")
        
        # Navigation
        page = st.radio("Go to", ["Briefings", "Quick Draft", "Engagements", "Settings"])
        
        st.markdown("---")
        
        # Logout
        if os.getenv("AUTH_PASSWORD_HASH"):
            authenticator.logout("Logout", "sidebar")
            st.markdown("---")
    
        # Scheduler Status
        if sched_enabled:
            job = system_manager.scheduler.get_job(job_id)
            if job:
                next_run = job.next_run_time
                st.caption(f"✅ Auto-Scout: Active\nNext: {next_run.strftime('%H:%M')}")
            else:
                 st.caption("✅ Auto-Scout: Active (Queueing...)")
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
            try:
                 data = st.session_state.db.get_recent_engagements(limit=50)
                 df = pd.DataFrame(data)
                     
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
    
    elif page == "Quick Draft":
        st.title("🎯 Quick Draft")
        st.markdown("Generate a comment or reply from any Reddit URL")
        
        # Import required modules
        from scout.core.url_parser import RedditURLParser
        from scout.core.reddit_client import RedditScout
        from scout.core.copywriter import Copywriter
        
        # Initialize components
        if 'reddit_scout' not in st.session_state:
            st.session_state.reddit_scout = RedditScout()
        if 'copywriter' not in st.session_state:
            st.session_state.copywriter = Copywriter()
        
        # URL Input
        st.subheader("📎 Paste Reddit URL")
        url_input = st.text_input(
            "Post or Comment URL",
            placeholder="https://reddit.com/r/entrepreneur/comments/abc123/...",
            help="Paste a link to a Reddit post (to comment) or comment (to reply)"
        )
        
        col1, col2 = st.columns([1, 3])
        with col1:
            generate_btn = st.button("🚀 Generate Draft", type="primary", disabled=not url_input)
        
        # Processing
        if generate_btn and url_input:
            # Validate URL
            if not RedditURLParser.validate_url(url_input):
                st.error(RedditURLParser.get_error_message(url_input))
            else:
                # Parse URL
                parsed = RedditURLParser.parse_reddit_url(url_input)
                
                if not parsed:
                    st.error("Unable to parse Reddit URL. Please check the format.")
                else:
                    url_type = parsed['type']
                    post_id = parsed['post_id']
                    
                    # Check for duplicates
                    duplicate = st.session_state.db.check_duplicate_briefing(post_id)
                    if duplicate:
                        st.warning(f"⚠️ This URL is already in your briefings (Status: {duplicate['status']})")
                        if not st.button("Generate Anyway"):
                            st.stop()
                    
                    try:
                        with st.spinner("Fetching content from Reddit..."):
                            if url_type == 'post':
                                # Fetch post
                                post = st.session_state.reddit_scout.fetch_post_by_id(post_id)
                                
                                # Generate draft
                                with st.spinner("Generating comment draft..."):
                                    draft = st.session_state.copywriter.generate_draft(post, "Manual")
                                    
                                if draft.status != "error":
                                    # Store in session state
                                    st.session_state.current_draft_type = 'post'
                                    st.session_state.current_draft_obj = draft
                                    st.session_state.current_post_obj = post
                                    st.session_state.current_parsed_url = parsed
                                else:
                                    st.error("Failed to generate draft.")

                            else:  # comment
                                comment_id = parsed['comment_id']
                                
                                # Fetch comment
                                comment_data = st.session_state.reddit_scout.fetch_comment_by_id(comment_id, post_id)
                                context = st.session_state.reddit_scout.get_comment_context(comment_id, depth=3)
                                
                                # Generate reply
                                with st.spinner("Generating reply draft..."):
                                    draft = st.session_state.copywriter.generate_reply_draft(comment_data, context)
                                    
                                if draft.status != "error":
                                    # Store in session state
                                    st.session_state.current_draft_type = 'comment'
                                    st.session_state.current_draft_obj = draft
                                    st.session_state.current_comment_data = comment_data
                                    st.session_state.current_comment_context = context
                                    st.session_state.current_parsed_url = parsed
                                else:
                                    st.error("Failed to generate reply.")

                            st.rerun() # Rerun to show the draft UI below

                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                        st.caption("The post/comment may have been deleted or is unavailable.")

        # --- PERSISTENT PREVIEW & SAVE UI ---
        if 'current_draft_obj' in st.session_state:
            
            # --- POST UI ---
            if st.session_state.current_draft_type == 'post':
                post = st.session_state.current_post_obj
                draft = st.session_state.current_draft_obj
                
                # Display preview
                st.markdown("---")
                st.subheader("📌 Post Preview")
                badge_html = f'<span style="background-color:#0d47a1; color:white; padding:4px 12px; border-radius:15px; font-size:0.85em; font-weight:bold;">💬 COMMENT</span>'
                st.markdown(badge_html, unsafe_allow_html=True)
                
                st.markdown(f"**{post.title}**")
                st.caption(f"👤 u/{post.author} • r/{post.subreddit}")
                
                with st.expander("View Post Content", expanded=True):
                    st.write(post.content[:500] + ("..." if len(post.content) > 500 else ""))
                
                st.markdown("---")
                st.subheader("✍️ Generated Draft")
                
                draft_text = st.text_area(
                    "Edit your comment",
                    value=draft.content,
                    height=200,
                    key="manual_draft"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Save to Briefings", type="primary"):
                        st.session_state.db.save_manual_briefing(
                            post_id=post.id,
                            subreddit=post.subreddit,
                            title=post.title,
                            post_content=post.content,
                            post_url=post.url,
                            draft_content=draft_text,
                            intent='Manual',
                            score=getattr(post, 'score', 0),
                            comment_count=getattr(post, 'comment_count', 0),
                            post_created_at=getattr(post, 'created_utc', None)
                        )
                        st.success("✅ Saved to Briefings!")
                        
                        # Cleanup
                        del st.session_state.current_draft_obj
                        del st.session_state.current_draft_type
                        time.sleep(1)
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Discard"):
                        del st.session_state.current_draft_obj
                        del st.session_state.current_draft_type
                        st.rerun()

            # --- COMMENT UI ---
            elif st.session_state.current_draft_type == 'comment':
                comment_data = st.session_state.current_comment_data
                context = st.session_state.current_comment_context
                draft = st.session_state.current_draft_obj
                
                # Display preview
                st.markdown("---")
                st.subheader("💬 Comment Preview")
                
                badge_html = f'<span style="background-color:#b71c1c; color:white; padding:4px 12px; border-radius:15px; font-size:0.85em; font-weight:bold;">↩️ REPLY to @{comment_data["author"]}</span>'
                st.markdown(badge_html, unsafe_allow_html=True)
                
                st.markdown(f"**Original Post:** {comment_data['post_title']}")
                st.caption(f"r/{comment_data['subreddit']}")
                
                with st.expander("View Comment You're Replying To", expanded=True):
                    st.markdown(f"**@{comment_data['author']} said:**")
                    st.write(comment_data['body'])
                
                if context:
                    with st.expander("Thread Context (Earlier Comments)"):
                        for i, ctx in enumerate(context, 1):
                            st.caption(f"{i}. @{ctx['author']}: {ctx['body']}")
                
                st.markdown("---")
                st.subheader("✍️ Generated Reply")
                
                draft_text = st.text_area(
                    f"Your reply to @{comment_data['author']}",
                    value=draft.content,
                    height=200,
                    key="manual_reply"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    comment_id = st.session_state.current_parsed_url['comment_id']
                    if st.button("💾 Save to Briefings", type="primary"):
                        st.session_state.db.save_manual_briefing(
                            post_id=comment_id,
                            subreddit=comment_data['subreddit'],
                            title=f"Reply to @{comment_data['author']} in: {comment_data['post_title']}",
                            post_content=comment_data['body'],
                            post_url=f"https://reddit.com{comment_data['permalink']}",
                            draft_content=draft_text,
                            intent="Reply",
                            parent_comment_id=comment_id,
                            parent_author=comment_data['author'],
                            score=comment_data.get('score', 0),
                            comment_count=comment_data.get('replies', 0),
                            post_created_at=comment_data.get('created_utc')
                        )
                        st.success("✅ Saved to Briefings!")
                        
                        # Cleanup
                        del st.session_state.current_draft_obj
                        del st.session_state.current_draft_type
                        time.sleep(1)
                        st.rerun()
                
                with col2:
                    if st.button("🗑️ Discard"):
                        del st.session_state.current_draft_obj
                        del st.session_state.current_draft_type
                        st.rerun()
    
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
                
                # Prepare Data
                subs_list = [s.strip() for s in subs_input.split(",") if s.strip()]
                keywords_list = [k.strip() for k in keywords_input.split(",") if k.strip()]
                
                settings_to_save = {
                    "target_subreddits": subs_list,
                    "pathfinder_keywords": keywords_list,
                    "scheduler_enabled": sched_enabled_ui,
                    "system_prompt": prompt_input,
                    "telegram_token": tg_token,
                    "telegram_chat_id": tg_chat,
                    "reddit_username": r_user
                }
                
                api_keys = {
                    "openrouter_api_key": op_key,
                    "reddit_client_id": r_id,
                    "reddit_client_secret": r_secret
                }
                
                # Persist via SystemManager
                success = system_manager.save_settings(settings_to_save, api_keys)
                
                if success:
                    st.success("Settings saved to disk! Keys & Config will persist.")
                    # Update Session State for immediate UI feedback
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
                else:
                    st.error("Failed to save settings.")

        # --- DIAGNOSTICS SECTION ---
        st.markdown("---")
        with st.expander("🛠️ Diagnostics & Connectivity", expanded=False):
            st.info("Test your connections to Reddit and AI from this environment.")
            
            if st.button("🔍 Run Connectivity Tests"):
                # 1. Reddit Test
                with st.status("Testing Reddit API...", expanded=True) as status:
                    try:
                        import praw
                        test_reddit = praw.Reddit(
                            client_id=config.reddit.client_id,
                            client_secret=config.reddit.client_secret,
                            user_agent=config.reddit.user_agent
                        )
                        # Try to fetch one post from a safe sub
                        list(test_reddit.subreddit("test").new(limit=1))
                        st.write("✅ Reddit: Connection Successful")
                    except Exception as e:
                        st.error(f"❌ Reddit: Connection Failed - {e}")
                    
                    # 2. AI Test
                    try:
                        from openai import OpenAI
                        test_ai = OpenAI(
                            base_url=config.ai.base_url,
                            api_key=config.ai.api_key
                        )
                        # Simple ping
                        test_ai.chat.completions.create(
                            model=config.ai.tier1_model,
                            messages=[{"role": "user", "content": "ping"}],
                            max_tokens=5
                        )
                        st.write("✅ AI Brain: Connection Successful")
                    except Exception as e:
                        st.error(f"❌ AI Brain: Connection Failed - {e}")
                    
                    status.update(label="Tests Complete!", state="complete", expanded=True)

        # --- DANGER ZONE ---
        st.markdown("---")
        with st.expander("☢️ Danger Zone", expanded=False):
            st.warning("These actions are destructive and cannot be undone.")
            
            # Use a popover for confirmation (Modern Streamlit)
            with st.popover("💥 Clear Campaign Data"):
                st.write("This will remove all Mission Briefings and clear your discovery history. Your settings will be preserved.")
                if st.button("Confirm Reset", type="primary"):
                    st.session_state.db.clear_campaign_data()
                    st.success("Campaign data cleared! Return to the dashboard for a fresh start.")
                    st.balloons()
                    time.sleep(1)
                    st.rerun()

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
                    badge_class = f"intent-{item['intent'].lower()}" if item.get('intent') else "intent-ignore"
                    
                    # Source badge
                    source = item.get('source', 'auto')
                    source_badge = "🤖 Auto" if source == 'auto' else "👤 Manual"
                    source_color = "#4CAF50" if source == 'auto' else "#FF9800"
                    
                    # Reply context
                    reply_context = ""
                    if item.get('parent_comment_id') and item.get('parent_author'):
                        reply_context = f"""
                        <div style="background-color:#fff3cd; padding:8px; border-radius:5px; margin-bottom:10px; border-left:3px solid #ff9800;">
                            <strong>↩️ Reply to @{item['parent_author']}</strong>
                        </div>
                        """
                    
                    st.markdown(f"""
                    <div class="briefing-card">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                            <div>
                                <span class="intent-badge {badge_class}">{item['intent'].upper()}</span>
                                <span style="background-color:{source_color}; color:white; padding:4px 12px; border-radius:15px; font-size:0.85em; font-weight:bold; margin-left:8px;">{source_badge}</span>
                            </div>
                            <span style="color:#666; font-size:0.9em;">
                                r/{item['subreddit']} • ⬆️ {item.get('score', 0)} • 💬 {item.get('comment_count', 0)} • 🕒 {format_time_ago(item.get('post_created_at'))}
                            </span>
                        </div>
                        {reply_context}
                        <h4>{item['title']}</h4>
                        <div style="max-height: 200px; overflow-y: auto; background-color: #f9f9f9; padding: 10px; border-radius: 5px; margin: 10px 0; font-family: sans-serif; font-size: 0.9em; white-space: pre-wrap; color: #333; border: 1px solid #eee;">
                            {clean_html(item['post_content'])}
                        </div>
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
                        
                        if is_cooldown:
                            # Show disabled visual
                            st_autorefresh(interval=1000, limit=100, key=f"refresh_{item['post_id']}")
                            st.button(f"⏳ Wait {int(remaining)}s", disabled=True, key=f"wait_{item['post_id']}")
                            
                            if st.button("❌ Discard", key=f"discard_{item['post_id']}"):
                                 st.session_state.db.update_briefing_status(item['post_id'], 'discarded')
                                 st.rerun()
                        else:
                            # --- SIMPLE APPROVE & OPEN ---
                            # 1. Update DB (Backend)
                            # 2. Rerun
                            # 3. New Run sees "Just Approved" -> Injects JS to Open URL (Client)
                            
                            if st.button("✅ Approve & Open", key=f"approve_{item['post_id']}", type="primary"):
                                 # 1. Database
                                 st.session_state.db.update_briefing_status(item['post_id'], 'approved', draft_text) 
                                 
                                 # 2. Rate Limit
                                 st.session_state['last_post_time'] = time.time()
                                 
                                 # 3. Trigger URL Open & Clipboard Copy
                                 st.session_state['open_url_next'] = item['post_url']
                                 st.session_state['copy_text_next'] = draft_text
                                 
                                 st.toast("✅ Approved! Opening Reddit...", icon="🚀")
                                 st.rerun()
    
                            if st.button("❌ Discard", key=f"discard_{item['post_id']}"):
                                 st.session_state.db.update_briefing_status(item['post_id'], 'discarded')
                                 st.rerun()
