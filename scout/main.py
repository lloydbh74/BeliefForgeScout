import logging
import os
import time
from typing import List
from scout.config import config

# Ensure log directory exists
log_dir = os.path.dirname(config.app.log_path)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.app.log_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ScoutEngine")

from scout.core.models import ScoutPost
from scout.core.reddit_client import RedditScout
from scout.core.screener import Screener
from scout.core.copywriter import Copywriter
from scout.core.db import ScoutDB

class ScoutEngine:
    def __init__(self):
        self.reddit = RedditScout()
        self.screener = Screener()
        self.copywriter = Copywriter()
        self.db = ScoutDB()
        
    def run_mission(self, callback=None):
        """
        Execute the full Scout mission (Discovery -> Screening -> Drafting).
        callback: Optional function(message, percent) to report progress.
        """
        def report(msg, pct):
            logger.info(msg)
            if callback:
                callback(msg, pct)

        report("🚀 Starting Scout Mission...", 0.0)
        
        # 1. DISCOVERY
        # Define targets (Load from dynamic config)
        known_subs = config.settings.get("target_subreddits", ["entrepreneur", "python"])
        keywords = config.settings.get("pathfinder_keywords", [])
        
        report(f"🔭 Scanning Watchtower targets: {known_subs}...", 0.1)
        
        raw_posts = []
        try:
            # Track A: Watchtower
            raw_posts.extend(self.reddit.scan_watchtower(known_subs, limit=10))
            
            # Track B: Pathfinder (if configured)
            if keywords:
                report(f"🧭 Pathfinder searching wilds for: {keywords}...", 0.2)
                wild_posts = self.reddit.scan_pathfinder(keywords, limit=10)
                raw_posts.extend(wild_posts)
                report(f"   > Found {len(wild_posts)} wild targets.", 0.25)
                
        except Exception as e:
            report(f"❌ Discovery Error: {e}", 0.15)
        
        # Filter out already processed
        new_posts = [p for p in raw_posts if not self.db.is_processed(p.id)]
        report(f"✅ Discovery complete. Found {len(raw_posts)} raw, {len(new_posts)} new candidates.", 0.3)
        
        if not new_posts:
            report("💤 No new posts to process. Mission Aborted.", 1.0)
            return

        # 2. SCREENING (Tier 1)
        report(f"🧠 Screening {len(new_posts)} posts with Tier 1 AI...", 0.4)
        try:
            analysis_results = self.screener.analyze_batch(new_posts)
        except Exception as e:
             report(f"❌ Screener Error: {e}", 0.45)
             analysis_results = []
        
        relevant_posts = []
        for result in analysis_results:
            # Mark as processed in DB
            self.db.mark_processed(result.post_id, result.intent, result.is_relevant)
            
            if result.is_relevant and result.intent != 'ignore':
                # Find the original post object
                original_post = next((p for p in new_posts if p.id == result.post_id), None)
                if original_post:
                    relevant_posts.append((original_post, result))

        report(f"🎯 Screening complete. {len(relevant_posts)} relevant opportunities identified.", 0.6)

        # 3. DRAFTING (Tier 2)
        if not relevant_posts:
             report("🏁 No relevant posts found. Mission Complete.", 1.0)
             return

        target_posts = relevant_posts[:5]
        report(f"✍️ Drafting responses for top {len(target_posts)} candidates...", 0.7)
        
        for i, (post, analysis) in enumerate(target_posts):
            report(f"   > Drafting for: {post.title[:30]}... ({analysis.intent})", 0.7 + (0.2 * (i/len(target_posts))))
            
            # Generate Draft
            draft = self.copywriter.generate_draft(post, analysis.intent)
            
            if draft.status != 'error':
                self.db.save_briefing(post, draft, analysis.intent)
                logger.error(f"Failed to draft for {post.id}")
                
        # Notification
        if relevant_posts:
            from scout.core.notifier import Notifier
            notifier = Notifier()
            notifier.notify_mission_report(len(relevant_posts))
            report("🔔 Notification sent.", 0.95)

        report("🏁 Mission Complete. Briefings active.", 1.0)
        
    def run_profile_watcher(self):
        """
        Execute the Profile Watcher mission (Engagement Tracking).
        """
        logger.info("🔭 Starting Profile Watcher...")
        
        # 1. Scan History
        engagements = self.reddit.scan_my_history(limit=25)
        logger.info(f"   > Found {len(engagements)} recent comments.")
        
        # 2. Update DB
        new_handshakes = 0
        for eng in engagements:
            self.db.upsert_engagement(eng)
            if eng['handshake']:
                new_handshakes += 1
        
        # 3. Reconcile Briefings (Mark as 'posted')
        self.db.reconcile_posted_briefings()
                
        logger.info(f"🏁 Profile Watcher Complete. {new_handshakes} handshakes active.")
        return len(engagements), new_handshakes

if __name__ == "__main__":
    engine = ScoutEngine()
    engine.run_mission()
