# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Twitter/X Engagement Bot for Belief Forge

An intelligent Twitter/X engagement bot that automatically discovers and creates authentic, brand-aligned replies to tweets from entrepreneurs experiencing imposter syndrome, self-doubt, and brand clarity struggles. Uses OpenRouter (Claude Sonnet 3.5) for LLM-powered reply generation with strict British English voice guidelines.

**Target Brand**: Belief Forge (beliefforge.com)
**Target Audience**: Entrepreneurs with belief-based business challenges
**Stack**: Python 3.11, Playwright, FastAPI, PostgreSQL, Redis, Docker

# Agent Workflow Policy
All tasks must begin with the agent-orchestrator agent. The orchestrator is responsible for:
- Reviewing the list of all available agents.
- Selecting the most relevant agent(s) based on the task requirements.
- Coordinating the sequential or parallel execution of the chosen agents.
- Ensuring the overall task is completed efficiently and correctly before any commit or final action.


## Github Commit Operations
All commit operations to GitHub must use the following workflow:
- Invoke the code-reviewer agent to review proposed changes.
- If the review passes, invoke the security-auditor agent for a security check.
- Only if both agents return approval, invoke the [GitHub agent] to perform the commit/push/pull request.
Do not allow direct commits bypassing these intermediary agents.

## Development Commands

### Docker Development (Primary)

```bash
# Local testing
docker-compose up -d              # Start all services
docker-compose logs -f bot        # Follow bot logs
docker-compose logs -f dashboard  # Follow dashboard logs
docker-compose ps                 # Check service status
docker-compose down               # Stop all services

# Rebuild after code changes
docker-compose build bot
docker-compose up -d bot

# Database access
docker exec -it social_reply_db psql -U social_reply -d social_reply

# Redis access
docker exec -it social_reply_redis redis-cli -a $REDIS_PASSWORD
```

### Configuration Management

```bash
# Create environment file from template
cp .env.example .env

# Edit configuration (YAML-based, hot-reloadable)
nano config/bot_config.yaml

# Test configuration loading
python src/config/loader.py
```

### Deployment to Hetzner VPS

```bash
# Set VPS connection
export VPS_HOST=your-vps-ip
export VPS_USER=root
export VPS_PORT=22

# Deploy (interactive menu)
chmod +x deploy-hetzner.sh
./deploy-hetzner.sh

# Manual deployment steps
tar czf social-reply-bot.tar.gz --exclude='data' --exclude='.git' .
scp social-reply-bot.tar.gz root@$VPS_HOST:/opt/social-reply-bot/
ssh root@$VPS_HOST "cd /opt/social-reply-bot && tar xzf social-reply-bot.tar.gz"
```

## Architecture Overview

### Multi-Layered Pipeline Architecture

The bot operates as a sequential pipeline with human-in-the-loop approval:

```
Scraping → Base Filtering → Commercial Filtering → Scoring → Deduplication
    ↓
LLM Reply Generation → Voice Validation → Human Approval (Telegram)
    ↓
Posting → Performance Tracking → Learning Corpus
```

### Critical Design Patterns

1. **Configuration-as-Code**: All behavior defined in `config/bot_config.yaml` (YAML) with programmatic validation. Changes require restart unless using hot-reload mechanism.

2. **Learning System**: Recent successful replies (3-5 examples) are included as context for LLM to maintain voice consistency. Stored in `reply_performance` table with `marked_as_good_example` flag.

3. **Multi-Layered Filtering**:
   - **Base Filters**: Engagement thresholds, recency, banned keywords
   - **Commercial Filters**: Priority keyword detection (3x/2x/1.5x multipliers)
   - **Scoring**: Weighted formula (40% velocity, 30% authority, 20% timing, 10% discussion)
   - **Deduplication**: 7-day history, 48-hour same-author cooldown

4. **Voice Validation**: Strict British English enforcement (see Voice Guidelines section)

### Core Modules

**src/config/loader.py**: Configuration loader with dataclass-based validation. Loads YAML (`bot_config.yaml`) and environment variables into structured `BotConfig` and `EnvConfig` objects.

**src/db/models.py**: SQLAlchemy models matching `init-db.sql` schema:
- `ReplyQueue`: Pending approvals (status: pending/approved/rejected/posted)
- `ReplyPerformance`: Learning corpus (engagement metrics, good/bad flags)
- `RepliedTweets`: Deduplication tracking (7-day history)
- `AnalyticsDaily`: Aggregated metrics for monitoring

**src/scraping/**: Playwright-based Twitter scraper (headless Chrome with cookie authentication)

**src/filtering/**: Multi-stage filtering (base → commercial → deduplication)

**src/scoring/**: Weighted scoring system (engagement velocity, user authority, timing, discussion opportunity)

**src/llm/**: OpenRouter client with retry logic, rate limiting, cost tracking

**src/voice/**: Voice validation (British English patterns, character limits, jargon detection)

**src/telegram/**: Bot interface for mobile approval (interactive buttons, commands)

**src/timing/**: UK timezone-aware scheduling (GMT/BST auto-adjustment, 07:00-24:00 active hours)

### Database Schema Key Points

- **reply_queue.status**: Workflow progression (pending → approved/rejected → posted)
- **reply_performance.marked_as_good_example**: Learning corpus flag (updated by human or engagement metrics)
- **replied_tweets.replied_at**: Used for 7-day deduplication window
- **bot_settings**: Runtime-editable configuration (mirrors YAML structure)

### Environment Configuration

**Required Variables** (.env):
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD`: Database credentials
- `OPENROUTER_API_KEY`: LLM API key (format: `sk-or-v1-...`)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`: Notification bot
- `JWT_SECRET`: Dashboard authentication (32+ characters)

**Twitter Authentication**: Cookie-based (not OAuth). Store `cookies.json` in `data/` directory. Export from browser using extension (EditThisCookie) or manual login script.

## Voice Guidelines (Critical)

**British English Enforcement** (programmatic validation):
- Spellings: realise, colour, whilst, amongst (NOT -ize, -or, while, among)
- Character limit: <100 preferred, 280 absolute max
- NO exclamation marks (!)
- NO hyphenation instead of commas
- NO corporate jargon: synergy, leverage, disrupt, game-changer, crushing it

**Tone**: Warm, authentic friend; vulnerable yet gently confident

**Validation**: `src/voice/guidelines.py` implements regex-based pattern detection. Violations prevent reply posting if `strict_mode: true`.

## Commercial Filtering Logic

**Priority Multipliers** (applied to base score):
- **Critical (3x)**: "imposter syndrome", "self-doubt", "feeling like a fraud"
- **High (2x)**: "brand identity", "positioning", "finding my why"
- **Medium-High (1.5x)**: "plateau", "stuck", "no traction"
- **Medium (1.2x)**: "scaling challenges", "growth", "overwhelmed"

**Target User Profiles**: Entrepreneur keywords (founder, CEO, solopreneur) + early-stage indicators (pre-revenue, MVP, year 1/2)

**Minimum Score Threshold**: 65/100 (configurable in `config/bot_config.yaml`)

## LLM Reply Generation

**Model**: Claude Sonnet 3.5 via OpenRouter (`anthropic/claude-3.5-sonnet`)
**Temperature**: 0.7 (balance creativity/consistency)
**Max Tokens**: 150
**Learning**: Includes 3-5 recent `reply_performance` examples with `marked_as_good_example=true`

**Prompt Structure**:
1. System prompt: Voice guidelines, brand context, constraints
2. Learning examples: Recent successful replies
3. User prompt: Original tweet context + commercial signals

**Rate Limiting**: 20 req/min, $50/month budget cap

## Timing & Scheduling

**Active Hours**: 07:00-24:00 UK time (Europe/London timezone)
**Daylight Savings**: Auto-adjusts between GMT/BST
**Check Intervals**: Scrape every 30 min, approval check every 5 min
**Engagement Limits**: 5 replies/hour, 20 replies/day, 10 replies/session

**Human-Like Behavior**: Random delays (0.8-2s typing, 1-3s actions), breaks after 3 replies

## Deduplication Strategy

1. **Tweet-Level**: Never reply to same tweet_id twice (unique constraint)
2. **Author-Level**: 48-hour cooldown between replies to same author
3. **History Window**: 7-day lookback in `replied_tweets` table
4. **Session Isolation**: `session_id` tracks related operations for atomic rollback

## Monitoring & Alerts

**Telegram Notifications**:
- `reply_ready_for_approval`: New reply pending human review
- `reply_posted_success`: Reply successfully posted
- `error_critical`: System failure requiring intervention
- `daily_summary`: Aggregated metrics
- `budget_warning`: Approaching API cost limit

**Logs**: JSON-structured logs in `data/logs/` with 30-day retention

**Dashboard**: FastAPI + React (port 8000) for analytics, approval queue, settings management

## Testing Twitter Authentication

Twitter uses cookie-based authentication (not OAuth). Two methods:

**Option A - Browser Export** (recommended):
1. Login to Twitter/X in browser
2. Install EditThisCookie or Cookie Editor extension
3. Export cookies as JSON
4. Save to `data/cookies.json`
5. Restart bot: `docker-compose restart bot`

**Option B - Manual Login Script**:
```bash
docker-compose run --rm bot python src/auth/manual_login.py
```

Follow prompts to authenticate. Cookies saved automatically.

## Common Issues

**Bot Not Starting**: Check logs (`docker-compose logs bot`), verify `.env` variables, ensure Twitter cookies valid

**Database Connection Failed**: Verify PostgreSQL health (`docker-compose ps`), check `DATABASE_URL` format

**Twitter Auth Expired**: Re-export cookies from browser or run manual login script

**Rate Limit Exceeded**: OpenRouter rate limit (20 req/min). Check `llm.rate_limits` in config.

**Voice Violations**: Reply rejected due to British English patterns. Review `voice_violations` in `reply_queue` table.

## Project Structure Notes

- **config/**: YAML configuration (hot-reloadable in future)
- **data/**: Persistent storage (logs, cookies, session data) - mounted volume in Docker
- **src/agents/**: Specialized agent modules (future: multi-agent orchestration)
- **src/api/**: FastAPI dashboard backend (REST + WebSocket)
- **src/dashboard/**: React frontend (future implementation)
- **init-db.sql**: Auto-executed on first PostgreSQL container start

## Important Constraints

1. **No Exclamation Marks**: Absolute rule (British voice guideline)
2. **Character Limit**: 100 preferred, 280 hard limit
3. **Reply Window**: 2-12 hours after tweet (balance freshness vs. signal)
4. **Commercial Focus**: Prioritize mental blocks (3x) > brand clarity (2x) > growth (1.5x)
5. **Deduplication**: 7-day window, 48-hour same-author cooldown
6. **Learning Corpus**: Rotate 3-5 examples to prevent repetition

## Cost Management

**Monthly Budget**: $50 default (configurable in `bot_config.yaml`)
**Estimated Usage**: 5-20 replies/day = $10-30/month OpenRouter
**VPS Cost**: €5-10/month (Hetzner CX21-CX31)
**Total**: ~€20-40/month (~$22-44)

**Cost Tracking**: `analytics_daily.api_cost_usd` updated per request
