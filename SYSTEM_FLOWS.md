# System Flows & User Journeys
## Visual Guide to Dashboard Operations

---

## Flow 1: Reply Approval (Happy Path)

```
┌──────────────────────────────────────────────────────────────────┐
│ TIME: 10:00 AM - Bot runs automatically (every 30 min)          │
└──────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  TWITTER BOT    │
│  (Background)   │
└────────┬────────┘
         │
         │ 1. Scrapes tweets
         │    - #BuildInPublic
         │    - Recent (2-12 hours)
         │
         ▼
    [Finds tweet]
    "Struggling with imposter
     syndrome as a founder..."
         │
         │ 2. Scores tweet
         │    - Engagement: 68
         │    - Authority: 75
         │    - Timing: 85
         │    → Total: 78/100 ✓
         │
         │ 3. Commercial filter
         │    - Detected: "imposter syndrome"
         │    → Priority: CRITICAL
         │
         │ 4. Generate reply (LLM)
         │    - Call OpenRouter (Claude)
         │    - Validate voice
         │    → "I've been embracing this too..."
         │
         ▼
┌──────────────────┐
│  BACKEND API     │
│  POST /queue     │
└────────┬─────────┘
         │
         │ 5. Save to database
         │    INSERT INTO pending_replies
         │
         ├─────────────────┬─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   TELEGRAM   │  │ WEB DASHBOARD│  │    REDIS     │
│              │  │              │  │    QUEUE     │
└──────┬───────┘  └──────┬───────┘  └──────────────┘
       │                 │
       │ 6a. Push        │ 6b. WebSocket
       │  notification   │     event sent
       │                 │
       ▼                 ▼
┌──────────────────────────────────┐
│  Lloyd's Phone (Telegram)        │
│                                   │
│  🤖 New Reply Pending             │
│                                   │
│  Priority: 🔴 CRITICAL            │
│  Score: 78/100                    │
│                                   │
│  Tweet: "Struggling with          │
│          imposter syndrome..."    │
│  Author: @jane_founder            │
│                                   │
│  Suggested Reply:                 │
│  "I've been embracing this        │
│   too—quite liberating..."        │
│                                   │
│  [✅ Approve] [✏️ Edit] [❌ Reject]│
└──────────┬───────────────────────┘
           │
           │ 7. Lloyd taps "Approve"
           │    (within 30 seconds)
           │
           ▼
    POST /replies/{id}/approve
           │
           ▼
┌──────────────────┐
│  BACKEND API     │
│  - Update status │
│  - Trigger post  │
└────────┬─────────┘
         │
         │ 8. Call Twitter API
         │    (via existing bot)
         │
         ▼
┌──────────────────┐
│   TWITTER API    │
│   POST reply     │
└────────┬─────────┘
         │
         │ 9. Reply posted!
         │
         ▼
┌──────────────────────────────────┐
│  Lloyd's Phone (Telegram)        │
│                                   │
│  ✅ Reply approved and posted!    │
│                                   │
│  View on Twitter: [Link]          │
│                                   │
│  📊 3 replies sent today          │
└──────────────────────────────────┘

END RESULT:
- Reply posted within 30 seconds of generation
- Lloyd maintains quality control
- Full audit trail in database
- Analytics tracked automatically
```

---

## Flow 2: Edit Before Approving

```
┌──────────────────────────────────┐
│  Telegram Notification           │
│                                   │
│  Suggested Reply:                 │
│  "I've been feeling this too!"    │
│                                   │
│  [✅ Approve] [✏️ Edit] [❌]      │
└──────────┬───────────────────────┘
           │
           │ Lloyd notices:
           │ - Missing British spelling
           │ - Needs softer language
           │
           ▼
     Lloyd taps [✏️ Edit]
           │
           ▼
┌──────────────────────────────────┐
│  Telegram                         │
│                                   │
│  Send edited reply text:          │
│  (Type your correction)           │
└──────────┬───────────────────────┘
           │
           │ Lloyd types:
           │ "I've been embracing this
           │  too—quite natural when
           │  you're pioneering"
           │
           ▼
    POST /replies/{id}/edit
    Body: { edited_text: "..." }
           │
           ▼
┌──────────────────┐
│  BACKEND API     │
│  - Validate edit │
│    (voice check) │
└────────┬─────────┘
         │
         ├─── Validation Pass ✓ ──┐
         │                         │
         │                         ▼
         │                  Post to Twitter
         │                         │
         │                         ▼
         │                   ✅ Success
         │                         │
         │                         ▼
         │            Save to sent_replies
         │            (marked as edited)
         │                         │
         │                         ▼
         └───────> Lloyd notified: "✅ Edited
                                    reply posted!"

ALTERNATIVE: Validation Fail ✗
         │
         ▼
┌──────────────────────────────────┐
│  Telegram                         │
│                                   │
│  ⚠️ Voice validation failed       │
│                                   │
│  Issues detected:                 │
│  - American spelling "realize"    │
│  - Exclamation mark               │
│                                   │
│  Try again? [Edit] [Post Anyway]  │
└──────────────────────────────────┘
```

---

## Flow 3: Batch Review via Web Dashboard

```
┌──────────────────────────────────────────────────────────┐
│ SCENARIO: Lloyd prefers to review replies in bulk        │
│ TIME: 2:00 PM - Lloyd sits down at desk                  │
└──────────────────────────────────────────────────────────┘

Lloyd opens: https://dashboard.beliefforge.com

┌────────────────────────────────────────────────────────┐
│ 🤖 Belief Forge Bot Dashboard            Lloyd [👤]    │
├────────────────────────────────────────────────────────┤
│                                                         │
│  🏠 Dashboard                                           │
│  ⏳ Reply Queue [7]  ← Badge shows pending count       │
│  📊 Analytics                                           │
│  ⚙️  Settings                                           │
│                                                         │
└────────────────────────────────────────────────────────┘
           │
           │ Lloyd clicks "Reply Queue"
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ Pending Replies (7)              [Pause Bot] [▼]       │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Filters: [🔴 Critical: 2] [🟠 High: 3] [🟡 Medium: 2] │
│ Sort: [Priority ▼]                                     │
│                                                         │
│ [✓] Select All    [✅ Approve Selected (7)]            │
│                                                         │
├────────────────────────────────────────────────────────┤
│                                                         │
│ REPLY 1:  🔴 CRITICAL • 15m ago • Score: 78            │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Tweet: "Struggling with imposter syndrome..."      │ │
│ │ @jane_founder • 5.2K followers                     │ │
│ │                                                     │ │
│ │ Suggested: "I've been embracing this too—quite     │ │
│ │             liberating..."                         │ │
│ │                                                     │ │
│ │ [✅ Approve] [✏️ Edit] [❌ Reject] [🔗 View]       │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ REPLY 2:  🔴 CRITICAL • 28m ago • Score: 82            │
│ ┌────────────────────────────────────────────────────┐ │
│ │ ... (similar structure)                            │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ... (5 more replies)                                    │
│                                                         │
└────────────────────────────────────────────────────────┘
           │
           │ Lloyd reviews all 7 replies:
           │ - Quickly scans each
           │ - Edits 1 reply (typo fix)
           │ - Rejects 1 reply (too generic)
           │ - Approves remaining 5
           │
           │ Total time: 3 minutes
           │
           ▼
  Lloyd clicks "Approve Selected (5)"
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ ⏳ Posting replies...                                   │
│                                                         │
│ ✅ Reply 1 posted                                       │
│ ✅ Reply 2 posted                                       │
│ ✅ Reply 3 posted                                       │
│ ⏸️  Waiting 30 seconds... (human-like delay)           │
│ ✅ Reply 4 posted                                       │
│ ✅ Reply 5 posted                                       │
│                                                         │
│ 🎉 All replies posted successfully!                     │
└────────────────────────────────────────────────────────┘

OUTCOME:
- 5 replies posted in 3 minutes of review time
- Staggered posting (30-60 sec delays between each)
- Quality maintained (1 rejected, 1 edited)
- Efficient batch workflow
```

---

## Flow 4: Auto-Approve with Recall Window

```
┌──────────────────────────────────────────────────────────┐
│ SCENARIO: After 2 weeks of successful manual approval    │
│ Lloyd switches to "Smart Auto" mode:                     │
│ - Critical/High priority → Manual approval               │
│ - Medium/Low priority → Auto-approve after 5 min delay   │
└──────────────────────────────────────────────────────────┘

TIME: 3:30 PM - Bot generates medium-priority reply

┌─────────────────┐
│  TWITTER BOT    │
└────────┬────────┘
         │
         │ Generates reply
         │ Priority: MEDIUM (not critical)
         │
         ▼
┌──────────────────┐
│  BACKEND API     │
│  POST /queue     │
└────────┬─────────┘
         │
         │ Check priority
         │ → MEDIUM
         │ → Auto-approve enabled
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌──────────────┐  ┌──────────────┐
│   TELEGRAM   │  │    REDIS     │
│              │  │  (Schedule)  │
└──────┬───────┘  └──────┬───────┘
       │                 │
       │                 │ Set timer:
       │                 │ Post after 5 min
       │                 │
       ▼                 ▼
┌──────────────────────────────────┐
│  Lloyd's Phone (Telegram)        │
│                                   │
│  ℹ️ Auto-Approving (Medium)       │
│                                   │
│  Reply will post in 5 minutes     │
│  unless you cancel.               │
│                                   │
│  Tweet: "How do I improve my      │
│          brand messaging?"        │
│                                   │
│  Suggested Reply:                 │
│  "I've found clarity comes from   │
│   understanding your audience..." │
│                                   │
│  [🛑 Cancel Auto-Approve]         │
│  [✏️ Edit Before Posting]         │
│  [▶️ Post Now]                    │
└──────────┬───────────────────────┘
           │
           │ Lloyd glances at notification
           │ Looks good, does nothing
           │
           │ 5 minutes pass...
           │
           ▼
    Timer expires → Auto-post
           │
           ▼
┌──────────────────┐
│   TWITTER API    │
│   POST reply     │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────┐
│  Lloyd's Phone (Telegram)        │
│                                   │
│  ✅ Auto-approved reply posted    │
│                                   │
│  4 auto-approved today            │
│  2 manual approvals pending       │
└──────────────────────────────────┘

ALTERNATIVE: Lloyd wants to cancel
           │
           │ Within 5-min window
           │
           ▼
  Lloyd taps [🛑 Cancel Auto-Approve]
           │
           ▼
    Delete from scheduled queue
           │
           ▼
┌──────────────────────────────────┐
│  Telegram                         │
│                                   │
│  🛑 Auto-approve cancelled        │
│                                   │
│  Reply moved to manual queue.     │
│  View in dashboard to review.     │
└──────────────────────────────────┘

BENEFITS:
- Critical replies still need manual review
- Medium/low priority replies auto-post
- 5-minute recall window for safety
- Lloyd can override anytime
- Reduces approval burden by 60-70%
```

---

## Flow 5: Settings Management

```
Lloyd wants to adjust commercial filters (too many replies)

┌────────────────────────────────────────────────────────┐
│ Dashboard → Settings → Filtering & Scoring             │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ Filtering & Scoring                                     │
├────────────────────────────────────────────────────────┤
│                                                         │
│ Base Filters:                                           │
│ Min Followers:    [500  ▼]  →  [1000 ▼]  (changed)    │
│ Min Likes:        [10   ▼]  →  [20   ▼]  (changed)    │
│ Min Replies:      [3    ▼]                             │
│                                                         │
│ Scoring Threshold: [65 / 100 ▼] → [70 / 100 ▼]        │
│                                                         │
│ Commercial Priority:                                    │
│ Minimum Priority: [Medium ▼] → [High ▼]                │
│                                                         │
│ [Save Changes] [Reset to Defaults] [Test Impact]       │
└────────┬───────────────────────────────────────────────┘
         │
         │ Lloyd clicks "Test Impact"
         │ (Shows how many recent tweets would pass new filters)
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ 📊 Filter Impact Preview                                │
│                                                         │
│ Based on last 7 days:                                   │
│                                                         │
│ Current settings:     42 tweets matched                │
│ New settings:         18 tweets matched  (-57%)        │
│                                                         │
│ Breakdown:                                              │
│ - Min followers 1000: -12 tweets                       │
│ - Min likes 20:       -8 tweets                        │
│ - Score ≥70:          -4 tweets                        │
│                                                         │
│ Expected replies:     ~2-3 per day  (was 5-6/day)      │
│                                                         │
│ [Apply Settings] [Cancel]                              │
└────────┬───────────────────────────────────────────────┘
         │
         │ Lloyd: "Perfect, that's the right balance"
         │
         ▼
  Lloyd clicks "Apply Settings"
         │
         ▼
    POST /api/v1/settings/filtering
    Body: { min_followers: 1000, ... }
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ Backend:                                                │
│ - Update settings in database                           │
│ - Signal bot to reload config                           │
│ - Log settings change in audit log                      │
└────────┬───────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────┐
│ ✅ Settings saved successfully!                         │
│                                                         │
│ Changes will apply to next bot run (in 12 minutes).    │
│                                                         │
│ [Run Bot Now] [View Audit Log]                         │
└────────────────────────────────────────────────────────┘

RESULT:
- Bot now generates fewer, higher-quality replies
- No code changes needed
- Takes effect immediately
- Full audit trail
- Can revert anytime
```

---

## Flow 6: Analytics Review

```
Lloyd wants to see how the bot is performing this week

┌────────────────────────────────────────────────────────┐
│ Dashboard → Analytics                                   │
└────────────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ Analytics Dashboard           [Last 7 Days ▼]          │
├────────────────────────────────────────────────────────┤
│                                                         │
│ PERFORMANCE OVERVIEW                                    │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│ │ 42 Replies   │ │ 2.8% Avg     │ │ $8.45 API    │   │
│ │ Sent         │ │ Engagement   │ │ Cost         │   │
│ └──────────────┘ └──────────────┘ └──────────────┘   │
│                                                         │
│ ENGAGEMENT TREND                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │     📈 Line Chart                                   │ │
│ │                                                     │ │
│ │     Mon  Tue  Wed  Thu  Fri  Sat  Sun              │ │
│ │      4    6    8    7    6    5    6   (replies)   │ │
│ │                                                     │ │
│ │     Engagement Rate:                                │ │
│ │     2.1% 2.5% 3.2% 2.9% 2.4% 3.1% 2.8%             │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ COMMERCIAL PERFORMANCE                                  │
│ ┌────────────────────────────────────────────────────┐ │
│ │  🔴 Critical: 12 replies → 4.2% engagement  🔥     │ │
│ │  🟠 High:     18 replies → 2.6% engagement         │ │
│ │  🟡 Medium:   12 replies → 1.8% engagement         │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ TOP PERFORMING REPLIES                                  │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 1. "I've been embracing this too..."               │ │
│ │    💗 12 likes • 💬 4 replies • 5.2% engagement    │ │
│ │    [View Thread] [Mark as Example]                 │ │
│ │                                                     │ │
│ │ 2. "As someone who naturally..."                   │ │
│ │    💗 9 likes • 💬 3 replies • 4.1% engagement     │ │
│ │    [View Thread] [Mark as Example]                 │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ VOICE QUALITY                                           │
│ ✅ Validation Pass Rate: 94% (target: 90%)             │
│ ✅ Avg Character Count: 82 (target: <100)              │
│ ✅ Violation Rate: 2% (target: <5%)                    │
│                                                         │
│ [Export CSV] [Share Report] [View Detailed Metrics]    │
└────────────────────────────────────────────────────────┘

Lloyd's Insights:
- Critical priority replies performing best (4.2% engagement)
- Wednesday peak performance (adjust schedule?)
- Voice quality excellent (94% pass rate)
- Under budget ($8.45 / $50 monthly budget)
- Top replies marked as learning examples

Action Items:
→ Mark top 2 replies as "good examples" for LLM learning
→ Consider increasing critical priority filter weight
→ Schedule more bot runs on Wednesdays
```

---

## Flow 7: Emergency Stop

```
┌──────────────────────────────────────────────────────────┐
│ SCENARIO: Lloyd notices bot is replying to wrong tweets  │
│ TIME: 11:45 PM - Late night discovery                    │
└──────────────────────────────────────────────────────────┘

Lloyd opens Telegram

┌──────────────────────────────────┐
│  Chat with @BeliefForgeBot       │
│                                   │
│  Lloyd types: /stop               │
└──────────┬───────────────────────┘
           │
           ▼
    POST /api/v1/bot/stop
           │
           ▼
┌──────────────────┐
│  BACKEND API     │
│  - Pause bot     │
│  - Clear queue   │
│  - Log event     │
└────────┬─────────┘
         │
         ├─────────────────┬─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   TELEGRAM   │  │ WEB DASHBOARD│  │   DATABASE   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       ▼                 ▼                 ▼
┌──────────────────────────────────┐
│  Telegram                         │
│                                   │
│  🛑 EMERGENCY STOP ACTIVATED      │
│                                   │
│  Bot Status: STOPPED              │
│  Queue: CLEARED (7 pending)       │
│  Scheduled runs: CANCELLED        │
│                                   │
│  Bot will not run until you       │
│  manually resume.                 │
│                                   │
│  Reason for stop? (optional)      │
│  Type reason or /skip             │
└──────────┬───────────────────────┘
           │
           │ Lloyd types: "Wrong filter
           │ targeting - replying to
           │ crypto tweets by mistake"
           │
           ▼
    Log to bot_events table
    Notify via email (critical alert)
           │
           ▼
┌──────────────────────────────────┐
│  Telegram                         │
│                                   │
│  ✅ Stop reason logged            │
│                                   │
│  Next steps:                      │
│  1. Review settings in dashboard  │
│  2. Check recent replies          │
│  3. Resume when ready: /resume    │
│                                   │
│  [Open Dashboard] [View Logs]     │
└──────────────────────────────────┘

Lloyd opens dashboard (next morning)

┌────────────────────────────────────────────────────────┐
│ 🔴 BOT STOPPED - Emergency Stop Active                 │
│                                                         │
│ Stopped: Yesterday 11:47 PM                            │
│ Reason: Wrong filter targeting                         │
│                                                         │
│ Pending actions cleared: 7 replies discarded           │
│                                                         │
│ [Review Settings] [View Logs] [Resume Bot]             │
└────────────────────────────────────────────────────────┘
           │
           │ Lloyd reviews settings,
           │ fixes filter issue
           │
           ▼
  Lloyd clicks "Resume Bot"
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ ✅ Bot Resumed                                          │
│                                                         │
│ Status: Active                                          │
│ Next run: in 30 minutes                                │
│                                                         │
│ Emergency stop lifted. Bot will resume normal          │
│ operation with updated settings.                        │
└────────────────────────────────────────────────────────┘

SAFETY FEATURES:
- One-command stop from anywhere (Telegram/web)
- Immediate halt (no pending actions execute)
- Queue cleared (no orphaned replies)
- Audit trail (why stopped, when, by whom)
- Manual resume only (no auto-restart)
```

---

## User Journey Map: Lloyd's Typical Day

```
┌──────────────────────────────────────────────────────────┐
│ MONDAY - Lloyd's Day with the Bot                        │
└──────────────────────────────────────────────────────────┘

07:00 AM - Bot starts active hours
         ↓
         [Bot runs automatically every 30 min]
         ↓
09:30 AM - Lloyd wakes up, checks phone
         ↓
         📱 Telegram: "3 pending replies (2 critical)"
         ↓
         Lloyd reviews on phone:
         • Approve 2 critical (30 sec each)
         • Skip 1 medium (will review later)
         ↓
         Time spent: 1 minute
         ↓
12:00 PM - Lunch break
         ↓
         📱 Telegram: "2 new pending"
         ↓
         Lloyd approves both while eating
         ↓
         Time spent: 45 seconds
         ↓
02:00 PM - Desk work
         ↓
         💻 Opens web dashboard
         ↓
         Reviews analytics:
         • 8 replies sent today
         • 3.2% avg engagement (good!)
         • $0.24 API cost today
         ↓
         Adjusts settings:
         • Lower score threshold (65 → 70)
         ↓
         Time spent: 3 minutes
         ↓
04:30 PM - Meeting break
         ↓
         📱 Telegram: "1 critical pending"
         ↓
         Lloyd edits reply (typo fix), approves
         ↓
         Time spent: 1 minute
         ↓
08:00 PM - Evening
         ↓
         📱 Telegram: "2 pending"
         ↓
         Lloyd does batch review on phone
         ↓
         Time spent: 1 minute
         ↓
11:00 PM - Before bed
         ↓
         📱 Quick check: "1 pending"
         ↓
         Lloyd approves
         ↓
         Time spent: 20 seconds
         ↓
MIDNIGHT - Bot stops (end of active hours)

TOTAL TIME SPENT: ~7 minutes throughout the day
REPLIES APPROVED: 12
TWEETS ENGAGED WITH: High-quality, targeted
FEELING: In control, efficient, hands-off enough
```

---

## Summary: Key System Benefits

1. **Mobile-First Approval**: Approve in 30 seconds via Telegram
2. **Batch Efficiency**: Review 5-10 replies in 3 minutes on desktop
3. **Quality Control**: Every reply gets human review (optional auto-approve later)
4. **Analytics Visibility**: Always know performance at a glance
5. **Settings Flexibility**: Adjust filters without touching code
6. **Emergency Safety**: One-command stop from anywhere
7. **Audit Trail**: Complete history of all decisions
8. **Time Savings**: 80% reduction vs manual Twitter engagement
9. **Professional Appearance**: Dashboard for investors/clients
10. **Scalable Architecture**: Easy to add features as business grows

---

**Next Step**: Review QUICK_START_GUIDE.md to start building!
