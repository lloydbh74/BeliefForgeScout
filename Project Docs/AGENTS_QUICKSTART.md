# Agent Suite - Quick Reference

## 📦 Complete Agent Suite (20 Agents)

### 🎯 Core Orchestration (2)
- **[orchestrator](file://./.claude/agents/core/orchestrator.md)** - Main workflow coordinator, runs complete engagement sessions
- **[session-manager](file://./.claude/agents/core/session-manager.md)** - Tracks session limits and lifecycle

### 🔍 Scraping & Discovery (2)
- **[tweet-scraper](file://./.claude/agents/scraping/tweet-scraper.md)** - Extracts tweets via Playwright from hashtags/lists/users
- **[target-resolver](file://./.claude/agents/scraping/target-resolver.md)** - Converts targets to Twitter URLs

### ✅ Filtering & Quality (2)
- **[content-filter](file://./.claude/agents/filtering/content-filter.md)** - Applies engagement/keyword/recency filters
- **[quality-checker](file://./.claude/agents/filtering/quality-checker.md)** - Assesses content quality and detects spam

### 💬 Engagement & Replies (3)
- **[reply-generator](file://./.claude/agents/engagement/reply-generator.md)** - Generates replies using templates or LLM
- **[reply-poster](file://./.claude/agents/engagement/reply-poster.md)** - Posts replies via browser automation
- **[template-manager](file://./.claude/agents/engagement/template-manager.md)** - Manages reply templates and variables

### 🎭 Humanization (3)
- **[behavior-randomizer](file://./.claude/agents/humanization/behavior-randomizer.md)** - Adds randomness to actions (delays, probability)
- **[timing-controller](file://./.claude/agents/humanization/timing-controller.md)** - Enforces UK timezone active hours (07:00-24:00)
- **[cooldown-manager](file://./.claude/agents/humanization/cooldown-manager.md)** - Calculates rest periods between sessions

### 💾 Data Management (2)
- **[deduplication-manager](file://./.claude/agents/data/deduplication-manager.md)** - Prevents duplicate replies, tracks 7-day history
- **[storage-manager](file://./.claude/agents/data/storage-manager.md)** - Handles JSON/CSV file I/O

### 📊 Monitoring & Safety (3)
- **[logger](file://./.claude/agents/monitoring/logger.md)** - Structured logging for all actions
- **[metrics-tracker](file://./.claude/agents/monitoring/metrics-tracker.md)** - Tracks performance metrics
- **[error-handler](file://./.claude/agents/monitoring/error-handler.md)** - Detects errors and determines recovery strategies

### 🌐 Browser Automation (2)
- **[playwright-controller](file://./.claude/agents/browser/playwright-controller.md)** - Manages browser lifecycle and interactions
- **[auth-manager](file://./.claude/agents/browser/auth-manager.md)** - Handles Twitter authentication and cookies

### ⚙️ Configuration (1)
- **[config-loader](file://./.claude/agents/config/config-loader.md)** - Loads and validates YAML configuration

---

## 🚀 Common Usage Patterns

### Run a Full Engagement Session
```
Use orchestrator to run a complete Twitter engagement session
```

### Test Individual Components

**Scraping:**
```
Use tweet-scraper to scrape tweets from #BuildInPublic hashtag from last 30 minutes
```

**Filtering:**
```
Use content-filter to filter these tweets using default criteria
```

**Reply Generation:**
```
Use reply-generator to create an authentic reply for this tweet about startup growth
```

**Posting (Dry Run):**
```
Use reply-poster to simulate posting this reply (describe steps without actually posting)
```

### Debugging & Monitoring

**Check Active Hours:**
```
Use timing-controller to check if bot should be active right now
```

**View Session Metrics:**
```
Use metrics-tracker to show metrics for session-20251107-001
```

**Check Deduplication:**
```
Use deduplication-manager to check if we've replied to tweet ID 1234567890
```

---

## 📋 Agent Call Flow

```
User Request: "Run an engagement session"
    ↓
[orchestrator]
    ├─→ [config-loader] Load settings
    ├─→ [timing-controller] Check active hours
    ├─→ [session-manager] Create session
    ├─→ [playwright-controller] Initialize browser
    │       └─→ [auth-manager] Load cookies
    ├─→ [tweet-scraper] Scrape tweets
    │       ├─→ [target-resolver] Build URLs
    │       └─→ [playwright-controller] Navigate & extract
    ├─→ [content-filter] Filter tweets
    │       └─→ [quality-checker] Check quality
    ├─→ [deduplication-manager] Remove duplicates
    ├─→ [behavior-randomizer] Shuffle & select
    ├─→ FOR EACH TWEET:
    │   ├─→ [behavior-randomizer] Should reply?
    │   ├─→ [reply-generator] Generate text
    │   │       └─→ [template-manager] Get template
    │   ├─→ [behavior-randomizer] Random delay
    │   ├─→ [reply-poster] Post reply
    │   └─→ [deduplication-manager] Record reply
    ├─→ [metrics-tracker] Calculate metrics
    ├─→ [cooldown-manager] Set next run time
    └─→ [session-manager] Close session

[logger] ← Logs from all agents
[error-handler] ← Errors from all agents
```

---

## 🎯 Design Principles

1. **Single Responsibility** - Each agent has ONE clear job
2. **No Overlap** - Clear boundaries between agents
3. **Composable** - Agents work together via orchestration
4. **Testable** - Each agent can be tested independently
5. **Minimal Context** - Agents only know what they need
6. **Clear Interfaces** - Standardized inputs/outputs

---

## 📁 File Locations

**Agent Definitions:** [.claude/agents/](file://./.claude/agents/)
**Agent Registry:** [.claude/agents/README.md](file://./.claude/agents/README.md)
**Project Outline:** [PROJECT_OUTLINE.md](file://./PROJECT_OUTLINE.md)
**This Quickstart:** [AGENTS_QUICKSTART.md](file://./AGENTS_QUICKSTART.md)

---

**Created:** 2025-11-07
**Total Agents:** 20
**Status:** ✅ Complete - Ready for Implementation
