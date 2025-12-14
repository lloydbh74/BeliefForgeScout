# Twitter/X Engagement Bot - Project Outline

## 1. Project Overview

An intelligent, human-like Twitter/X engagement bot for **Belief Forge** that automatically discovers and creates authentic, brand-aligned replies to relevant tweets. The bot uses sophisticated LLM-based reply generation via OpenRouter, implements multi-layered commercial filtering to target entrepreneurs facing belief-based challenges, and maintains a consistent voice embodying warmth, vulnerability, and British authenticity.

**Target Audience**: Entrepreneurs experiencing imposter syndrome, self-doubt, brand clarity struggles, and seeking purpose-driven business guidance.

## 2. Core Objectives

- **Targeted Discovery**: Scrape tweets from specific hashtags, public lists, and user profiles
- **Commercial Filtering**: Prioritise tweets with high commercial value for Belief Forge (mental blocks, brand clarity struggles)
- **LLM-Powered Replies**: Generate contextual, voice-consistent replies via OpenRouter (Claude Sonnet 3.5)
- **Intelligent Scoring**: Score tweets based on engagement velocity, user authority, timing, and discussion opportunity
- **Voice Consistency**: Enforce British English, gentle tone, and brand guidelines programmatically
- **Human-Like Behavior**: Randomise all actions, timings, and reply patterns
- **Compliance**: Operate only during specified hours with intelligent cooldowns
- **Auditability**: Comprehensive logging and deduplication tracking
- **Learning System**: Learn from past successful replies to maintain voice consistency

## 3. Key Features

### 3.1 Scraping & Discovery
- Monitor target hashtags: `#BuildInPublic`, `#Bootstrapped`, `#StartupLife`, `#SoloFounder`
- Track specified Twitter lists and user profiles
- Fetch only latest tweets (configurable time window)
- Minimize API calls through smart pre-filtering

### 3.2 Multi-Layered Filtering

#### 3.2.1 Base Filters
- **Recency**: Configurable time window (default: last 2-12 hours for optimal engagement)
- **Engagement**: Minimum likes (10+), replies (3+), views (100+)
- **Language**: English only
- **Banned Keywords**: Skip giveaways, promos, contests, sponsored content, crypto, NFTs
- **User Quality**: Minimum follower count (500+), account age (90+ days)

#### 3.2.2 Commercial Filters (Belief Forge-Specific)
- **Mental Block Keywords** (highest value 3x): "imposter syndrome", "self-doubt", "not ready yet", "perfectionism", "fear of visibility"
- **Brand Clarity Keywords** (high value 2x): "positioning", "finding my why", "brand identity", "target audience", "differentiator"
- **Growth Frustration Keywords** (medium-high 1.5x): "plateau", "stuck", "inauthentic", "forced", "standing out"
- **Values Alignment Keywords** (medium 1x): "purpose-driven", "authentic", "integrity", "mission", "belief-led"
- **Target Hashtags** (baseline 0.5x): Priority hashtags matching target audience

#### 3.2.3 Tweet Scoring System (from N8N workflow)
Score tweets using weighted formula:
- **Engagement Velocity (40%)**: Like/view ratio, reply rate, tweet age (fresher = higher)
- **User Authority (30%)**: Follower count (log scale), verification status, account maturity
- **Timing (20%)**: Golden window (2-12 hours), UK active hours alignment
- **Discussion Opportunity (10%)**: Contains questions, target hashtags, substantive length, reply count sweet spot (3-20)

**Minimum Score Threshold**: 65/100 to engage

### 3.3 LLM-Powered Reply Generation

#### 3.3.1 OpenRouter Integration
- **Primary Model**: Claude Sonnet 3.5 (`anthropic/claude-3.5-sonnet`)
- **Fallback Model**: Claude Haiku (`anthropic/claude-3-haiku`)
- **Temperature**: 0.7 (balance creativity and consistency)
- **Max Tokens**: 150 (keep replies concise)
- **Retry Logic**: 3 attempts with exponential backoff
- **Rate Limiting**: 20 requests/minute
- **Cost Tracking**: Monthly budget monitoring ($50 default)

#### 3.3.2 Voice Guidelines (Programmatically Enforced)

**Core Voice Identity**:
- Warm, authentic friend sharing insights
- Vulnerable yet gently confident
- British English (realise, colour, whilst, amongst)
- Short replies (<100 characters preferred, 280 hard limit)
- 95% standalone (not threaded)

**Language Patterns**:
- Soften statements: "I'd rather..." not "I will"
- Gentle qualifiers: quite, rather, perhaps, might, could
- Present tense for current experiences
- Concrete, relatable metaphors (everyday life, nature, craftsmanship)

**Preferred Opening Phrases**:
- "I've been embracing..."
- "As someone who naturally..."
- "I'm curious—which of these resonates with you?"
- "For my fellow [entrepreneurs/founders]..."
- "In my experience..."

**Strict Avoidance**:
- Exclamation marks (!)
- Hyphenation instead of commas
- Corporate jargon (synergy, leverage, disrupt, game-changer, crushing it)
- American spellings (-ize, -or endings, while, among)
- Excessive hashtags (max 1, prefer 0)
- Multiple emojis (max 1 if it enhances)
- Salesy language (Buy now, Limited time, DM me)
- Buzzwords (ninja, guru, rockstar, hustle, grind)

**Voice Validation**:
- Character count enforcement
- Regex pattern detection (American spellings, exclamation marks)
- Corporate jargon detection
- Emoji counting
- Validation score tracking (target: 90%+ pass rate on first attempt)

#### 3.3.3 Learning from Past Replies
- Query 3-5 recent successful replies as context
- Prefer manually marked "good examples"
- Minimum validation score 0.9 for learning corpus
- Exclude replies with voice violations
- Sort by engagement rate (likes + 2x replies)
- Rotate examples to prevent repetition
- Periodic refresh of learning corpus

#### 3.3.4 Prompt Engineering
**System Prompt**: Comprehensive voice guidelines, Belief Forge mission context, engagement rules
**User Prompt**: Tweet content, scoring analysis, learning examples, strict requirements
**Dynamic Variables**: User follower count, tweet age, commercial priority, detected signals

### 3.4 Randomization & Human Behavior
- Random tweet selection (subset of eligible tweets)
- Randomised delays between actions (15-60 seconds)
- Random "rest periods" and cooldowns (30-90 min)
- Varied reply probability based on priority score
- A/B testing support for prompt variations

### 3.5 Scheduling & Timing
- **Active Hours**: 07:00 - 24:00 UK time (GMT/BST aware)
- **Cooldown Periods**: Random breaks during active hours
- **Session Management**: Max 5 replies/hour, 15 likes/hour
- **Run Interval**: 30 minutes (configurable)

### 3.6 Deduplication & Safety
- Track all replied tweets (prevent double-replies)
- Maintain reply history (7 days minimum)
- Skip tweets from already-engaged users within timeframe
- Error handling for captchas, rate limits, blocks
- Reply performance tracking (likes, replies, engagement rate)
- Manual review flags for quality control

### 3.7 Logging & Monitoring
- JSON/CSV logs for all actions
- Track: scraped tweets, replies sent, skips, errors, scores, priorities
- Timestamp all activities
- Performance metrics (success rate, engagement, voice validation)
- Token usage and cost tracking
- Reply performance dashboard

## 4. Technical Architecture

### 4.1 Technology Stack
- **Language**: Python 3.9+
- **Browser Automation**: Playwright (preferred) or Selenium
- **LLM Provider**: OpenRouter API (Claude Sonnet 3.5 / Haiku)
- **HTTP Client**: httpx (async support)
- **Scheduling**: APScheduler or custom scheduler
- **Timezone**: pytz for GMT/BST handling
- **Logging**: JSON/CSV with rotation
- **Database**: SQLite for deduplication and performance tracking

### 4.2 Project Structure

```
social-reply-bot/
├── README.md
├── PROJECT_OUTLINE.md
├── requirements.txt
├── setup.py
│
├── config/
│   ├── bot_config.yaml              # Main bot configuration
│   ├── llm_config.yaml              # OpenRouter & LLM settings
│   ├── voice_profile.yaml           # Voice guidelines (enforced)
│   ├── scoring_weights.yaml         # Tweet scoring configuration
│   ├── commercial_filters.yaml      # Belief Forge filtering logic
│   ├── credentials.yaml             # API keys (gitignored)
│   └── banned_words.txt             # Filtered keywords
│
├── src/
│   ├── __init__.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── bot.py                   # Main bot orchestration
│   │   └── config_loader.py         # Configuration management
│   │
│   ├── twitter/
│   │   ├── __init__.py
│   │   ├── auth.py                  # Twitter OAuth
│   │   ├── search.py                # Tweet search
│   │   ├── actions.py               # Like, reply actions
│   │   └── rate_limiter.py          # Rate limiting
│   │
│   ├── llm/                          # LLM integration module
│   │   ├── __init__.py
│   │   ├── openrouter_client.py     # OpenRouter API client
│   │   ├── prompt_builder.py        # Dynamic prompt construction
│   │   ├── reply_generator.py       # Reply orchestration
│   │   └── scoring.py               # Tweet scoring logic
│   │
│   ├── voice/                        # Voice enforcement module
│   │   ├── __init__.py
│   │   ├── guidelines.py            # Voice validation
│   │   ├── templates.py             # Prompt templates
│   │   └── constraints.py           # Character limits, patterns
│   │
│   ├── filtering/                    # Enhanced filtering
│   │   ├── __init__.py
│   │   ├── base_filter.py           # Base filtering logic
│   │   ├── commercial_filter.py     # Belief Forge commercial logic
│   │   └── deduplication_filter.py  # Deduplication logic
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── deduplication_db.py      # Enhanced with learning
│   │   └── analytics_db.py          # Performance tracking
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging_config.py
│       ├── scheduling.py            # UK timezone scheduling
│       └── randomization.py         # Human-like delays
│
├── prompts/                          # Prompt templates
│   ├── system_prompt_v1.md          # System prompt templates
│   ├── user_prompt_template.md      # User prompt templates
│   └── examples/                    # Example prompt variations
│       ├── high_authority_user.md
│       ├── mental_block_tweet.md
│       └── brand_clarity_tweet.md
│
├── data/
│   ├── deduplication.db             # SQLite database
│   ├── analytics.db                 # Performance tracking
│   └── logs/                        # Action logs
│       ├── bot.log
│       ├── replies.csv
│       └── performance.csv
│
├── tests/
│   ├── test_llm/
│   │   ├── test_openrouter_client.py
│   │   ├── test_prompt_builder.py
│   │   └── test_scoring.py
│   ├── test_voice/
│   │   └── test_guidelines.py
│   ├── test_filtering/
│   │   └── test_commercial_filter.py
│   └── test_integration/
│       └── test_end_to_end.py
│
└── .env                             # Secrets (cookies, API keys)
```

### 4.3 Data Models

#### Tweet Object (Enhanced)
```json
{
  "id": "1234567890",
  "author": {
    "username": "example_user",
    "display_name": "Example User",
    "followers_count": 5000,
    "verified": true,
    "created_at": "2020-01-01T00:00:00Z"
  },
  "text": "Tweet content...",
  "created_at": "2025-11-07T10:30:00Z",
  "public_metrics": {
    "like_count": 45,
    "reply_count": 12,
    "retweet_count": 8,
    "impression_count": 9062
  },
  "language": "en",
  "entities": {
    "hashtags": ["BuildInPublic", "StartupLife"],
    "urls": [],
    "mentions": []
  },
  "source_hashtag": "#BuildInPublic",
  "url": "https://twitter.com/example_user/status/1234567890"
}
```

#### Tweet Score Object
```json
{
  "total_score": 72.5,
  "engagement_velocity_score": 68.0,
  "user_authority_score": 75.0,
  "timing_score": 85.0,
  "discussion_score": 60.0,
  "meets_threshold": true,
  "reasoning": "Score: 72.5 (threshold: 65). Factors: high engagement velocity, authoritative user, optimal timing window."
}
```

#### Commercial Signals Object
```json
{
  "mental_block_keywords": ["imposter syndrome", "self-doubt"],
  "brand_clarity_keywords": ["positioning"],
  "growth_frustration_keywords": [],
  "values_alignment_keywords": ["authentic"],
  "target_hashtags": ["#BuildInPublic"],
  "startup_stage_signals": ["early_stage"],
  "commercial_priority": "critical",
  "priority_score": 7.5
}
```

#### Reply Log Entry (Enhanced)
```json
{
  "tweet_id": "1234567890",
  "reply_id": "9876543210",
  "replied_at": "2025-11-07T10:35:42Z",
  "reply_text": "I've been embracing this too—quite liberating when you let go of perfectionism",
  "success": true,
  "error": null,
  "session_id": "session-20251107-001",
  "commercial_priority": "critical",
  "tweet_score": 72.5,
  "validation_score": 0.95,
  "had_violations": false,
  "character_count": 82,
  "attempt_number": 1,
  "token_usage": 145,
  "cost_usd": 0.002
}
```

#### Reply Performance Entry
```json
{
  "id": 1,
  "tweet_id": "1234567890",
  "reply_id": "9876543210",
  "reply_text": "I've been embracing this too...",
  "posted_at": "2025-11-07T10:35:42Z",
  "like_count": 5,
  "reply_count": 2,
  "engagement_rate": 9.0,
  "validation_score": 0.95,
  "had_violations": false,
  "marked_as_good_example": true,
  "original_tweet_text": "Struggling with imposter syndrome as a founder...",
  "commercial_priority": "critical"
}
```

## 5. Configuration Schema

### 5.1 Main Bot Config (bot_config.yaml)

```yaml
# Enhanced Bot Configuration for Belief Forge

general:
  name: "Belief Forge Twitter Engagement Bot"
  version: "2.0.0"
  timezone: "Europe/London"

search:
  keywords:
    - "imposter syndrome"
    - "self-doubt"
    - "brand identity"
    - "positioning"
    - "founder struggles"
    - "belief-led"

  hashtags:
    - "#BuildInPublic"
    - "#Bootstrapped"
    - "#StartupLife"
    - "#SoloFounder"
    - "#Entrepreneurship"

  result_type: "mixed"
  max_results: 50

filtering:
  # Base filters
  min_followers: 500
  min_text_length: 60
  min_likes: 10
  min_replies: 3
  min_views: 100
  language: "en"
  account_age_days: 90

  # Commercial filtering
  use_commercial_filter: true
  commercial_priority_threshold: "medium"

  # Tweet age window (optimal for engagement)
  min_tweet_age_hours: 2
  max_tweet_age_hours: 12

engagement:
  # LLM-based reply generation (mandatory)
  use_llm_replies: true
  llm_config: "config/llm_config.yaml"
  voice_profile: "config/voice_profile.yaml"
  scoring_config: "config/scoring_weights.yaml"
  commercial_config: "config/commercial_filters.yaml"

  # Deduplication
  deduplication_window_days: 7

  # Rate limiting (human-like)
  max_replies_per_hour: 5
  max_likes_per_hour: 15

  # Randomization
  random_delay_min_seconds: 15
  random_delay_max_seconds: 60

scheduling:
  active_hours:
    start: 7   # 7am UK
    end: 24    # Midnight UK

  run_interval_minutes: 30
  tweets_per_batch: 10

  # Cooldowns
  cooldown_min_minutes: 30
  cooldown_max_minutes: 90

logging:
  level: "INFO"
  file: "data/logs/bot.log"
  rotation: "daily"
  retention_days: 30
  csv_log_replies: true
  csv_log_performance: true

analytics:
  track_reply_performance: true
  performance_check_interval_hours: 24

database:
  deduplication: "data/deduplication.db"
  analytics: "data/analytics.db"
```

### 5.2 LLM Config (llm_config.yaml)

```yaml
# OpenRouter LLM Configuration

openrouter:
  api_key: "${OPENROUTER_API_KEY}"
  base_url: "https://openrouter.ai/api/v1"

  # Model selection
  model: "anthropic/claude-3.5-sonnet"
  fallback_model: "anthropic/claude-3-haiku"

  # Generation parameters
  max_tokens: 150
  temperature: 0.7
  top_p: 0.9

  # Reliability
  timeout: 30
  max_retries: 3
  retry_delay: 2.0

  # Rate limiting
  requests_per_minute: 20

  # Cost tracking
  log_token_usage: true
  monthly_budget_usd: 50.00

generation:
  max_attempts_per_tweet: 3
  min_validation_score: 0.8

  # Learning from history
  learn_from_past_replies: true
  learning_context_size: 5
  min_example_validation_score: 0.9

  # A/B testing
  enable_ab_testing: false
  test_models:
    - "anthropic/claude-3.5-sonnet"
    - "anthropic/claude-3-haiku"
  test_split: 0.5
```

### 5.3 Voice Profile (voice_profile.yaml)

```yaml
# Voice Profile for Belief Forge Twitter Engagement

version: "1.0.0"
last_updated: "2025-01-07"

tone_descriptors:
  - "Warm, authentic friend sharing insights"
  - "Vulnerable yet gently confident"
  - "Thoughtful entrepreneur, not corporate brand"
  - "Curious and open-minded"

british_spellings:
  - "realise/recognise/organise (not -ize)"
  - "colour/favour/honour (not -or)"
  - "whilst/amongst (not while/among)"
  - "centre/theatre (not -er)"

preferred_phrases:
  - "I've been embracing..."
  - "As someone who naturally..."
  - "I'm curious—which of these resonates with you?"
  - "For my fellow [entrepreneurs/founders]..."
  - "I've noticed that..."
  - "In my experience..."

qualifier_words:
  - "quite"
  - "rather"
  - "perhaps"
  - "might"
  - "could"
  - "seems"
  - "tends to"

avoid_patterns:
  - "Exclamation marks (!)"
  - "Corporate jargon (synergy, leverage, disrupt, game-changer)"
  - "American spellings (-ize, -or endings)"
  - "Hashtags (max 1)"
  - "Excessive emojis (max 1)"
  - "Salesy language (Buy now, Limited time)"
  - "Buzzwords (crushing it, killing it, epic, ninja, guru)"

character_limit: 100
hard_limit: 280
standalone_preference: 0.95

emoji_policy:
  max_per_reply: 1
  allowed_contexts:
    - "Enhancing emotional tone (💭 for reflection)"
    - "Visual metaphor (🌱 for growth)"

belief_forge_mention_policy:
  frequency: "rare"
  contexts:
    - "Direct question about belief-led branding"
    - "Relevant case study or framework"
```

### 5.4 Scoring Weights (scoring_weights.yaml)

```yaml
# Tweet Scoring Weights

weights:
  engagement_velocity: 0.40
  user_authority: 0.30
  timing: 0.20
  discussion_opportunity: 0.10

thresholds:
  minimum_score: 65.0
  critical_score: 85.0

engagement_velocity:
  like_weight: 1
  reply_weight: 2
  retweet_weight: 3
  age_decay:
    golden_hours: [2, 12]
    decay_start_hours: 12
    full_decay_hours: 48

user_authority:
  follower_brackets:
    - {min: 0, max: 1000, score: 30}
    - {min: 1000, max: 10000, score: 60}
    - {min: 10000, max: 100000, score: 85}
    - {min: 100000, max: null, score: 100}
  verified_bonus: 15
  account_age_bonus: 20

timing:
  golden_window_hours: [2, 12]
  uk_active_hours: [7, 24]

discussion:
  question_score: 40
  target_hashtag_score: 30
  substantive_length_score: 20
  reply_count_sweet_spot: [3, 20]
```

### 5.5 Commercial Filters (commercial_filters.yaml)

```yaml
# Commercial Filtering for Belief Forge

target_audience:
  mental_block_keywords:
    - "imposter syndrome"
    - "self-doubt"
    - "not ready yet"
    - "perfectionism"
    - "fear of visibility"
    - "confidence"
    - "limiting belief"

  brand_clarity_keywords:
    - "positioning"
    - "finding my why"
    - "brand identity"
    - "target audience"
    - "differentiator"
    - "unique value"

  growth_frustration_keywords:
    - "plateau"
    - "stuck"
    - "inauthentic"
    - "forced"
    - "standing out"

  values_alignment_keywords:
    - "purpose-driven"
    - "authentic"
    - "integrity"
    - "mission"
    - "belief-led"

hashtags:
  priority:
    - "#BuildInPublic"
    - "#Bootstrapped"
    - "#StartupLife"
    - "#SoloFounder"
  secondary:
    - "#Entrepreneurship"
    - "#BrandStrategy"
    - "#Positioning"

user_criteria:
  followers:
    min: 500
    max: 100000
    ideal_min: 1000
    ideal_max: 50000
  account_age_days: 90
  tweet_frequency_per_week: 3

skip_patterns:
  - "giveaway"
  - "contest"
  - "dm me"
  - "link in bio"
  - "crypto"
  - "nft"
  - "forex"

priority_scoring:
  mental_block_multiplier: 3.0
  brand_clarity_multiplier: 2.0
  growth_frustration_multiplier: 1.5
  values_alignment_multiplier: 1.0
  hashtag_multiplier: 0.5

  thresholds:
    critical: 6.0
    high: 4.0
    medium: 2.0
    low: 1.0
```

## 6. Core Workflow Algorithm

### 6.1 Enhanced Main Loop

```
1. Check if within active hours (07:00-24:00 UK)
   └─ If not, sleep until next active period

2. Initialize browser session with saved profile/cookies

3. FOR EACH target (hashtag/list/user):
   a. Navigate to target search/page
   b. Scrape latest tweets (time window: 2-12 hours)
   c. Apply base filters:
      - Engagement thresholds (likes, replies, views)
      - Language detection (English only)
      - Banned keywords check
      - User quality check (followers, account age)
   d. Add to candidate pool

4. FOR EACH candidate tweet:
   a. Apply commercial filter:
      - Detect mental block, brand clarity, growth signals
      - Calculate commercial priority (critical/high/medium/low)
      - Skip if priority below threshold
   b. Score tweet using scoring system:
      - Engagement velocity (40%)
      - User authority (30%)
      - Timing (20%)
      - Discussion opportunity (10%)
      - Skip if score < 65
   c. Add to prioritized pool with score & priority

5. Deduplicate candidates:
   - Remove already-replied tweets
   - Remove tweets from recently-engaged users

6. Sort by priority and score:
   - Critical priority first
   - Then by total score descending

7. FOR EACH selected tweet (top N based on session limits):
   a. Generate reply using LLM:
      - Build system prompt with voice guidelines
      - Build user prompt with tweet + score + learning examples
      - Call OpenRouter API (Claude Sonnet 3.5)
      - Validate reply against voice guidelines
      - Retry up to 3 times if validation fails

   b. If reply generation successful:
      - Random delay (15-60 sec)
      - Post reply to Twitter
      - Log to deduplication DB with performance tracking
      - Update session counters

   c. If reply generation failed:
      - Log error with details
      - Continue to next tweet

8. End session:
   - Log metrics (tweets processed, replies sent, scores, priorities)
   - Random cooldown (30-90 min)
   - Close browser

9. Sleep until next scheduled run
```

### 6.2 Error Handling Strategy

```
- Captcha detected → Pause 2+ hours, notify, screenshot
- Rate limit → Exponential backoff, extend cooldown
- Network error → Retry 3x with jitter
- Element not found → Screenshot + log, skip tweet
- Login expired → Reload profile/cookies, re-auth
- LLM API error → Retry with exponential backoff, use fallback model
- Voice validation failure → Regenerate reply (max 3 attempts)
- Budget exceeded → Pause, notify, wait until next budget period
- Database error → Log, notify, continue with caution
```

## 7. Implementation Phases

### Phase 1: LLM Foundation (Week 1)
- [ ] Set up new directory structure (src/llm/, src/voice/, src/filtering/)
- [ ] Create configuration files (llm_config.yaml, voice_profile.yaml, scoring_weights.yaml, commercial_filters.yaml)
- [ ] Implement OpenRouterClient with error handling and retry logic
- [ ] Implement VoiceValidator with regex patterns
- [ ] Write unit tests for core modules

### Phase 2: Scoring & Filtering (Week 2)
- [ ] Port N8N scoring logic to Python (TweetScorer class)
- [ ] Implement CommercialFilter for Belief Forge
- [ ] Integrate scoring with existing search flow
- [ ] Add commercial priority to deduplication database
- [ ] Test filtering on real tweet samples

### Phase 3: Prompt Engineering (Week 3)
- [ ] Build PromptBuilder with dynamic templates
- [ ] Create system prompt incorporating voice guidelines
- [ ] Create user prompt template with variables
- [ ] Test prompts with OpenRouter API
- [ ] Refine based on output quality and voice consistency

### Phase 4: Reply Generation (Week 4)
- [ ] Implement ReplyGenerator orchestration
- [ ] Add learning from past replies feature
- [ ] Integrate validation pipeline
- [ ] Add retry logic for failed validations
- [ ] Performance tracking in database

### Phase 5: Integration & Testing (Week 5)
- [ ] Integrate LLM module with existing bot flow
- [ ] Enhanced deduplication DB with reply performance
- [ ] End-to-end testing with test Twitter account
- [ ] Monitor reply quality and engagement
- [ ] Tune scoring weights and commercial thresholds

### Phase 6: Production Deployment (Week 6)
- [ ] Deploy to production environment
- [ ] Set up monitoring and alerting
- [ ] Manual review process for top replies
- [ ] Performance dashboard
- [ ] Operational runbook

## 8. Environment Requirements

### Python Packages

```
# Core dependencies
playwright==1.40.0
pytz==2023.3
pyyaml==6.0.1
python-dotenv==1.0.0
apscheduler==3.10.4

# LLM integration
httpx==0.25.0
openai==1.3.0  # for OpenRouter compatibility

# Database
sqlite3  # built-in

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
```

### System Requirements
- Python 3.9+
- Chrome/Chromium browser
- 2GB RAM minimum
- Stable internet connection
- Linux/Windows/macOS compatible

### Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Environment variables (.env)
OPENROUTER_API_KEY=sk-or-v1-...
TWITTER_COOKIES_FILE=./cookies.json

# Optional monitoring
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

## 9. Success Metrics

### Quality Metrics
- **Voice Validation Pass Rate**: Target 90%+ on first attempt
- **Character Count Compliance**: 95%+ replies under 100 chars
- **Violation Rate**: <5% replies with voice guideline violations
- **Reply Relevance**: Manual review sample (n=50) monthly

### Engagement Metrics (Tracked via Performance DB)
- **Reply Like Rate**: % of replies that get at least 1 like
- **Reply Reply Rate**: % of replies that spark follow-up discussion
- **Conversation Threads**: # of back-and-forth exchanges
- **Profile Visits**: Track clicks to Belief Forge profile

### Commercial Metrics
- **High-Priority Engagement Rate**: % of critical/high priority tweets engaged with
- **Signal Hit Rate**: % of replies targeting mental block/brand clarity signals
- **Follow Rate**: # of target users who follow after engagement
- **Website Referrals**: beliefforge.com visits from Twitter

### Efficiency Metrics
- **Scoring Accuracy**: How well scores predict engagement
- **Generation Speed**: Avg time to generate reply
- **API Cost**: Monthly OpenRouter spend
- **False Positive Rate**: % of low-quality engagements
- **Token Usage**: Avg tokens per reply

## 10. Safety & Ethics Considerations

- **Rate Limiting**: Never exceed reasonable engagement rates (5 replies/hour max)
- **Authenticity**: Only engage with genuinely relevant content
- **Transparency**: Replies are authentic and add value (not spam)
- **Privacy**: Don't scrape or store personal data beyond what's needed
- **Platform Terms**: Regular review of Twitter/X ToS compliance
- **Kill Switch**: Easy way to immediately stop all activity
- **Voice Consistency**: Maintain human-like, non-robotic replies
- **Commercial Intent**: Balance helping vs. promoting (help first, promote sparingly)
- **Belief Forge Mentions**: Rare and only when genuinely adds value

## 11. Risk Mitigation

### Voice Drift Risk
- Monthly manual review of random reply sample (n=50)
- Quarterly voice profile audit and refresh
- Flag outlier replies for review (validation score <0.6)
- Maintain "hall of fame" examples for learning

### Repetitive Responses Risk
- Rotate learning examples (limit to recent 2 weeks)
- Phrase diversity checker (warn if same phrase >3 times/day)
- Periodically inject "fresh" prompts without learning context
- Manual review flags repetitive patterns

### Commercial Over-Optimization Risk
- Monthly filter effectiveness review
- A/B test different priority thresholds
- Allow 10% "exploration" mode (engage medium-priority randomly)
- Monitor follower quality vs. quantity

### LLM Hallucination/Inappropriate Content Risk
- Multi-layer validation (voice validator + manual spot checks)
- Content policy enforcement
- Implement content safety API as secondary check
- Kill switch for pausing bot if issues detected

### Cost Runaway Risk
- Hard monthly budget cap ($50)
- Track token usage per request
- Request rate limiting (max 20/min)
- Use cheaper fallback model when appropriate
- Alert when 80% of budget consumed

## 12. Frontend Dashboard & User Interface

### 12.1 Overview

The bot requires a frontend interface for human-in-the-loop approval, settings management, and monitoring. The recommended solution is a **Hybrid Web Dashboard + Telegram Bot** approach providing mobile convenience and desktop power.

**Core Problem**: Lloyd needs to approve replies before posting, adjust settings without editing YAML files, and monitor bot performance/errors in real-time.

### 12.2 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                          │
├──────────────────────────┬──────────────────────────────────┤
│   Mobile (Telegram)      │   Desktop (Web Dashboard)        │
│   - Quick approvals      │   - Detailed analytics           │
│   - Push notifications   │   - Settings management          │
│   - Emergency controls   │   - Batch review                 │
└──────────────────────────┴──────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   API LAYER (FastAPI)                        │
│   - REST API (CRUD operations)                              │
│   - WebSocket (real-time updates)                           │
│   - Authentication (JWT tokens)                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   BACKEND SERVICES                           │
│   - Bot Orchestrator (existing Python bot)                  │
│   - Reply Queue Manager                                      │
│   - Settings Manager                                         │
│   - Analytics Engine                                         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              DATA LAYER (PostgreSQL + Redis)                 │
│   - Reply queue (pending approvals)                         │
│   - Settings/config (editable via UI)                       │
│   - Analytics/metrics (performance tracking)                │
│   - User sessions (authentication)                          │
└─────────────────────────────────────────────────────────────┘
```

### 12.3 Technology Stack

#### Frontend
- **Framework**: React 18 + Vite
- **UI Library**: shadcn/ui + Tailwind CSS
- **State Management**: TanStack Query (React Query)
- **Real-time**: WebSocket client
- **Charts**: Recharts or Chart.js
- **Forms**: React Hook Form + Zod validation

#### Backend API
- **Framework**: FastAPI (Python) - integrates with existing bot
- **Authentication**: JWT tokens (email/password)
- **Real-time**: WebSocket support
- **Database ORM**: SQLAlchemy
- **Task Queue**: Celery (optional, for background jobs)

#### Mobile Notifications
- **Platform**: Telegram Bot API
- **Library**: python-telegram-bot
- **Features**: Inline keyboards, message editing, push notifications

#### Database
- **Primary**: PostgreSQL (replaces SQLite for production)
- **Cache**: Redis (for real-time features, session management)
- **Migration**: Alembic (database versioning)

#### Hosting
- **Recommended**: Railway ($5-20/month, all-in-one)
- **Alternative**: Render (cheaper, $0-10/month)
- **Domain**: Custom domain (beliefforge-bot.com)

### 12.4 Core Features

#### 12.4.1 Reply Approval System (Human-in-the-Loop)

**Primary Feature**: Review and approve LLM-generated replies before posting.

**Telegram Bot Interface**:
```
🤖 New Reply Ready for Approval

Tweet from @username (5.2K followers)
"Struggling with imposter syndrome as a founder. How do you deal with it?"

📊 Score: 72.5 | Priority: Critical
🎯 Signals: Mental Block (imposter syndrome, self-doubt)

💬 Suggested Reply:
"I've been embracing this too—quite liberating when you let go of perfectionism"

✅ Voice Check: Passed | Length: 82 chars | British ✓

[✅ Approve] [✏️ Edit] [❌ Reject] [⏸️ Skip]
```

**Web Dashboard Interface**:
- **Reply Queue View**: Table showing all pending replies
  - Tweet preview (author, text, metrics)
  - Generated reply with validation status
  - Score breakdown (velocity, authority, timing, discussion)
  - Commercial signals detected
  - Quick actions (approve, edit, reject)

- **Edit Modal**:
  - Live character counter
  - Voice validation (real-time feedback on British English, exclamation marks)
  - Tweet context sidebar
  - Preview before posting

**Approval Modes**:
1. **Full Manual** (default): Every reply needs approval
2. **Smart Auto**: Critical/high need approval, medium/low auto-post (with 5-min recall window)
3. **Batch Review**: Review all replies once per day (morning queue)

#### 12.4.2 Settings Management

**Editable via UI** (no YAML editing required):

**Search & Targeting**:
- Keywords to monitor (text input, multi-line)
- Hashtags to track (tag input)
- Twitter lists/users (searchable dropdown)
- Time window (slider: 2-24 hours)

**Commercial Filters**:
- Mental block keywords (list editor with weights)
- Brand clarity keywords (list editor)
- Growth frustration keywords (list editor)
- Priority thresholds (sliders: critical, high, medium, low)
- Skip patterns (blocked words/phrases)

**Tweet Scoring**:
- Scoring weights (sliders: velocity 40%, authority 30%, timing 20%, discussion 10%)
- Minimum score threshold (slider: 0-100, default 65)
- Follower range (min/max inputs, ideal range)

**Voice Guidelines**:
- Character limit (input: preferred, hard limit)
- Preferred phrases (text area, one per line)
- Avoid patterns (text area, one per line)
- Emoji policy (toggle + max count)

**Bot Schedule**:
- Active hours (time range picker: 07:00-24:00 UK)
- Run interval (slider: 15-60 minutes)
- Max replies per hour (input: default 5)
- Cooldown periods (range: 30-90 min)

**LLM Configuration**:
- Model selection (dropdown: Sonnet 3.5, Haiku)
- Temperature (slider: 0.0-1.0)
- Max tokens (input: 50-280)
- Monthly budget (input with alert threshold)
- Learn from history (toggle + learning size)

#### 12.4.3 Bot Control Panel

**Status Dashboard**:
- Current status (running, paused, error)
- Last run time and next scheduled run
- Session stats (tweets scraped, replies sent, errors)
- Rate limit status (API calls remaining)

**Manual Controls**:
- **Start/Pause**: Toggle bot on/off
- **Run Now**: Trigger immediate run (bypass schedule)
- **Emergency Stop**: Halt all activity immediately
- **Restart**: Reload configuration

**Queue Management**:
- Pending approvals count
- Auto-approve queue (with recall window)
- Failed/error queue

#### 12.4.4 Analytics Dashboard

**Overview Cards** (last 7 days):
- Total replies sent
- Engagement rate (likes + replies received)
- Voice validation pass rate
- API cost (OpenRouter spend)

**Charts & Visualizations**:

1. **Reply Performance Over Time** (line chart)
   - X-axis: Date/time
   - Y-axis: Reply count, engagement rate
   - Toggle: Daily, weekly, monthly

2. **Commercial Priority Distribution** (pie chart)
   - Critical: X%
   - High: Y%
   - Medium: Z%
   - Shows targeting effectiveness

3. **Voice Quality Trends** (stacked bar chart)
   - Validation pass rate per day
   - Character count compliance
   - Violation types breakdown

4. **Tweet Score Distribution** (histogram)
   - X-axis: Score buckets (0-20, 20-40, 40-60, 60-80, 80-100)
   - Y-axis: Count
   - Shows scoring effectiveness

5. **Cost Tracking** (line chart + budget indicator)
   - Daily API spend
   - Monthly budget line
   - Alert threshold indicator

6. **Engagement by Priority** (grouped bar chart)
   - X-axis: Commercial priority (critical, high, medium, low)
   - Y-axis: Avg likes, avg replies
   - Shows ROI by priority

**Filters**:
- Date range picker (last 7 days, 30 days, 90 days, custom)
- Priority filter (all, critical, high, medium, low)
- Status filter (approved, rejected, auto-posted)

#### 12.4.5 Reply History Browser

**Table View**:
- Columns: Date, Tweet (preview), Reply (preview), Priority, Score, Engagement, Status
- Sort by: Date, engagement, score, priority
- Filters: Date range, priority, status, voice validation
- Search: Full-text search in tweets/replies
- Pagination: 25/50/100 per page

**Detail View** (click row):
- Original tweet (full text, author, metrics, URL)
- Generated reply (full text, validation details)
- Score breakdown (all components)
- Commercial signals detected
- Performance metrics (likes, replies, engagement rate)
- Actions: Mark as good example, view on Twitter

#### 12.4.6 Error & Alert Center

**Error Log**:
- Timestamp, severity (warning, error, critical)
- Error type (captcha, rate limit, network, LLM API, validation)
- Error message and stack trace
- Resolution status (open, investigating, resolved)

**Alerts**:
- Budget threshold reached (80%, 90%, 100%)
- Rate limit approaching
- Captcha detected (requires manual intervention)
- Voice validation failure rate spike (>10%)
- Bot paused/stopped unexpectedly

**Notification Channels**:
- In-app notifications (bell icon)
- Telegram alerts (critical errors only)
- Email digest (daily summary)

### 12.5 User Workflows

#### Workflow 1: Approve Reply (Mobile - Telegram)

```
1. User receives Telegram notification
   "🤖 New Reply Ready"

2. User reviews tweet context and suggested reply

3. User makes decision:
   A. Tap [✅ Approve] → Reply posts immediately → Success confirmation
   B. Tap [✏️ Edit] → Edit modal → Save → Review → Approve/Reject
   C. Tap [❌ Reject] → Reply discarded → Optional feedback
   D. Tap [⏸️ Skip] → Reply moved to batch queue

4. Bot continues to next tweet
```

**Time**: 30 seconds per reply

#### Workflow 2: Batch Review (Desktop - Web Dashboard)

```
1. User opens web dashboard → Reply Queue tab

2. User sees table of 10 pending replies

3. User quickly scans each row:
   - Tweet preview
   - Reply preview
   - Score/priority indicators

4. User bulk selects:
   - Check boxes for approve (7 replies)
   - Click [Bulk Approve] button

5. Remaining 3 replies:
   - Click [Edit] on reply #5 → Adjust wording → Approve
   - Click [Reject] on reply #8 → Add reason
   - Click [Skip] on reply #10 → Review later

6. Confirmation modal: "Post 8 approved replies now?"

7. User clicks [Confirm] → All approved replies post sequentially
```

**Time**: 3-5 minutes for 10 replies

#### Workflow 3: Adjust Commercial Filters (Desktop)

```
1. User opens dashboard → Settings tab → Commercial Filters section

2. User notices too many "growth frustration" tweets being prioritized

3. User adjusts:
   - Reduce "growth_frustration_multiplier" from 1.5x to 1.0x
   - Add "pivot" to growth frustration keywords
   - Raise "high priority" threshold from 4.0 to 5.0

4. User clicks [Save Changes]

5. System validates settings → Shows preview:
   "This will affect approximately 15% fewer tweets (based on last 7 days)"

6. User confirms → Settings saved and applied to next bot run

7. Bot reloads configuration automatically
```

**Time**: 2 minutes

#### Workflow 4: Review Weekly Performance (Desktop)

```
1. User opens dashboard → Analytics tab

2. User sets date range: "Last 7 days"

3. User reviews Overview Cards:
   - 42 replies sent (avg 6/day)
   - 23% engagement rate (9.6 likes/replies per reply)
   - 94% voice validation pass rate
   - $8.40 API cost (17% of monthly budget)

4. User scrolls to "Engagement by Priority" chart:
   - Critical priority: 35% engagement rate (good!)
   - High priority: 20% engagement rate
   - Medium priority: 10% engagement rate (meh)

5. User insight: "Medium priority not worth it"

6. User navigates to Settings → Commercial Filters
   - Changes threshold from "medium" to "high"
   - Expects to reduce reply volume by 30% but increase avg engagement

7. User returns to Analytics next week to validate hypothesis
```

**Time**: 5 minutes

### 12.6 Database Schema Updates

#### New Tables for Dashboard

```sql
-- Reply approval queue
CREATE TABLE reply_queue (
  id SERIAL PRIMARY KEY,
  tweet_id TEXT NOT NULL,
  tweet_author TEXT,
  tweet_text TEXT,
  tweet_metrics JSONB, -- likes, replies, views
  created_at TIMESTAMP DEFAULT NOW(),

  -- Generated reply
  reply_text TEXT NOT NULL,
  reply_score FLOAT,
  commercial_priority TEXT, -- critical/high/medium/low
  commercial_signals JSONB,
  voice_validation_score FLOAT,
  voice_violations JSONB,

  -- Approval status
  status TEXT DEFAULT 'pending', -- pending/approved/rejected/auto_posted/edited
  approved_by TEXT,
  approved_at TIMESTAMP,
  rejection_reason TEXT,

  -- Metadata
  session_id TEXT,
  attempt_number INT DEFAULT 1,

  CONSTRAINT unique_tweet_per_session UNIQUE (tweet_id, session_id)
);

-- User-editable settings (mirrors YAML configs)
CREATE TABLE bot_settings (
  id SERIAL PRIMARY KEY,
  category TEXT NOT NULL, -- search/filtering/engagement/scheduling/llm
  key TEXT NOT NULL,
  value JSONB NOT NULL,
  updated_at TIMESTAMP DEFAULT NOW(),
  updated_by TEXT,

  CONSTRAINT unique_category_key UNIQUE (category, key)
);

-- Analytics metrics (aggregated)
CREATE TABLE analytics_daily (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL,

  -- Volume metrics
  tweets_scraped INT DEFAULT 0,
  tweets_filtered INT DEFAULT 0,
  replies_generated INT DEFAULT 0,
  replies_approved INT DEFAULT 0,
  replies_rejected INT DEFAULT 0,
  replies_auto_posted INT DEFAULT 0,
  replies_posted INT DEFAULT 0,

  -- Quality metrics
  avg_voice_validation_score FLOAT,
  voice_violation_rate FLOAT,
  avg_character_count FLOAT,

  -- Commercial metrics
  critical_priority_count INT DEFAULT 0,
  high_priority_count INT DEFAULT 0,
  medium_priority_count INT DEFAULT 0,
  low_priority_count INT DEFAULT 0,

  -- Engagement metrics (updated periodically)
  avg_likes_received FLOAT,
  avg_replies_received FLOAT,
  avg_engagement_rate FLOAT,

  -- Cost metrics
  api_cost_usd FLOAT DEFAULT 0,
  token_usage INT DEFAULT 0,

  CONSTRAINT unique_date UNIQUE (date)
);

-- Error log
CREATE TABLE error_log (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMP DEFAULT NOW(),
  severity TEXT, -- warning/error/critical
  error_type TEXT, -- captcha/rate_limit/network/llm_api/validation
  error_message TEXT,
  stack_trace TEXT,
  tweet_id TEXT,
  session_id TEXT,
  resolved BOOLEAN DEFAULT FALSE,
  resolved_at TIMESTAMP
);

-- User sessions (authentication)
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  hashed_password TEXT NOT NULL,
  role TEXT DEFAULT 'admin', -- admin/viewer
  telegram_chat_id TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP
);

CREATE TABLE sessions (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(id),
  token TEXT UNIQUE NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Notification preferences
CREATE TABLE notification_settings (
  user_id INT PRIMARY KEY REFERENCES users(id),
  telegram_enabled BOOLEAN DEFAULT TRUE,
  email_enabled BOOLEAN DEFAULT FALSE,
  telegram_events JSONB DEFAULT '["reply_ready", "error_critical"]',
  email_events JSONB DEFAULT '["daily_summary"]'
);
```

### 12.7 API Design

#### REST Endpoints

```python
# Authentication
POST   /api/auth/login              # Login (email/password)
POST   /api/auth/logout             # Logout
GET    /api/auth/me                 # Current user info

# Reply Queue
GET    /api/replies/queue           # Get pending replies
GET    /api/replies/queue/:id       # Get single reply
POST   /api/replies/:id/approve     # Approve reply
POST   /api/replies/:id/reject      # Reject reply
PATCH  /api/replies/:id/edit        # Edit reply text
POST   /api/replies/bulk-approve    # Approve multiple replies

# Reply History
GET    /api/replies/history         # Get reply history (paginated)
GET    /api/replies/history/:id     # Get single historical reply
POST   /api/replies/:id/mark-good   # Mark as good example

# Bot Control
GET    /api/bot/status              # Get current bot status
POST   /api/bot/start               # Start bot
POST   /api/bot/pause               # Pause bot
POST   /api/bot/stop                # Emergency stop
POST   /api/bot/run-now             # Manual trigger

# Settings Management
GET    /api/settings                # Get all settings
GET    /api/settings/:category      # Get category settings
PATCH  /api/settings/:category/:key # Update setting
POST   /api/settings/validate       # Validate settings before save

# Analytics
GET    /api/analytics/overview      # Overview cards
GET    /api/analytics/charts/:type  # Chart data (reply_performance, priority_dist, etc.)
GET    /api/analytics/export        # Export data (CSV)

# Error Log
GET    /api/errors                  # Get error log (paginated)
PATCH  /api/errors/:id/resolve      # Mark error as resolved

# Notifications
GET    /api/notifications           # Get notifications
PATCH  /api/notifications/:id/read  # Mark as read
GET    /api/notifications/settings  # Get notification preferences
PATCH  /api/notifications/settings  # Update preferences
```

#### WebSocket Events

```javascript
// Client subscribes to real-time updates
ws://api.example.com/ws

// Server → Client events
{
  type: "reply_ready",
  data: { reply_id, tweet_preview, reply_text, score, priority }
}

{
  type: "reply_approved",
  data: { reply_id, status: "posted" }
}

{
  type: "bot_status_changed",
  data: { status: "paused", reason: "rate_limit" }
}

{
  type: "error",
  data: { severity: "critical", error_type: "captcha", message: "..." }
}

{
  type: "analytics_update",
  data: { replies_today: 8, engagement_rate: 0.25 }
}
```

### 12.8 Implementation Phases

#### Phase 1: Backend Foundation (Week 1)
- [ ] Set up FastAPI project structure
- [ ] PostgreSQL database setup (Docker Compose)
- [ ] Database schema migration (Alembic)
- [ ] User authentication (JWT)
- [ ] Basic CRUD endpoints (reply queue, settings)
- [ ] Redis setup for caching

#### Phase 2: Reply Queue System (Week 2)
- [ ] Reply queue manager (Python service)
- [ ] Bot integration (generate → queue → await approval → post)
- [ ] API endpoints for approval workflow
- [ ] WebSocket server for real-time updates
- [ ] Basic React frontend (reply queue table)

#### Phase 3: Telegram Bot Integration (Week 3)
- [ ] Telegram bot setup (python-telegram-bot)
- [ ] Reply notification handler
- [ ] Inline keyboard actions (approve/reject/edit)
- [ ] Edit modal workflow
- [ ] Status commands (/status, /queue, /stop)

#### Phase 4: Web Dashboard UI (Week 4)
- [ ] React frontend complete setup
- [ ] Reply queue view (table + detail modal)
- [ ] Bot control panel
- [ ] Basic analytics dashboard
- [ ] Settings forms (search, filters, scoring)

#### Phase 5: Analytics & Monitoring (Week 5)
- [ ] Analytics aggregation service (daily cron)
- [ ] Chart components (Recharts)
- [ ] Reply history browser
- [ ] Error log viewer
- [ ] Export functionality (CSV)

#### Phase 6: Settings Management (Week 6)
- [ ] Settings UI (all categories)
- [ ] Validation logic (server-side + client-side)
- [ ] Preview impact of changes
- [ ] Hot reload configuration (bot picks up changes)
- [ ] Settings versioning (rollback capability)

#### Phase 7: Polish & Deployment (Week 7)
- [ ] Mobile responsive design
- [ ] Loading states and error handling
- [ ] User onboarding flow
- [ ] Deployment to Railway/Render
- [ ] Domain setup and SSL
- [ ] Monitoring and alerting (Sentry, Uptime Robot)
- [ ] Documentation and user guide

### 12.9 Alternative Approaches Considered

#### Option A: Web Dashboard Only
**Pros**: Professional, comprehensive features
**Cons**: Not mobile-friendly, slower approval workflow
**Verdict**: ❌ Not recommended (Lloyd needs mobile access)

#### Option B: Telegram Bot Only
**Pros**: Instant mobile access, simple
**Cons**: Limited analytics, no visual charts
**Verdict**: ⚠️ Good for MVP, insufficient long-term

#### Option C: Hybrid (Web + Telegram)
**Pros**: Best of both worlds, flexible workflow
**Cons**: More complex to build
**Verdict**: ✅ **RECOMMENDED**

#### Option D: Desktop App (Electron)
**Pros**: Native feel, offline capability
**Cons**: Over-engineered, no mobile access
**Verdict**: ❌ Not suitable

#### Option E: No-Code (Airtable + Make.com)
**Pros**: Fast to build (2-3 days), cheap
**Cons**: Limited customization, vendor lock-in
**Verdict**: ⚠️ Good for quick validation

#### Option F: Minimal (Streamlit)
**Pros**: Very fast to build (Python only)
**Cons**: Ugly UI, poor mobile support
**Verdict**: ⚠️ Internal testing only

### 12.10 Deployment Strategy

#### Recommended: Railway

**Why Railway**:
- Simple deployment (git push)
- Auto-scaling
- Managed PostgreSQL + Redis included
- Reasonable pricing ($5-20/month)
- Good for Python + React

**Setup**:
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Add PostgreSQL + Redis
railway add postgresql
railway add redis

# Deploy backend
railway up

# Add frontend (separate service)
railway up --service frontend
```

**Environment Variables**:
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
OPENROUTER_API_KEY=sk-or-v1-...
TELEGRAM_BOT_TOKEN=...
JWT_SECRET=...
```

#### Alternative: Render

**Why Render**:
- Cheaper free tier ($0-10/month)
- Similar simplicity
- Good documentation

**Cost Comparison** (monthly):
- **Railway**: $5 (starter) + $5 (PostgreSQL) + $5 (Redis) = $15-20
- **Render**: Free (web service) + $7 (PostgreSQL) = $7-10
- **Total with LLM**: $30-50/month (including OpenRouter API)

### 12.11 Security Considerations

**Authentication**:
- JWT tokens (httpOnly cookies)
- Password hashing (bcrypt)
- Rate limiting (login attempts)
- Session expiry (7 days)

**API Security**:
- CORS configuration (whitelist frontend domain)
- Input validation (Pydantic models)
- SQL injection prevention (SQLAlchemy ORM)
- XSS prevention (React escaping)

**Secrets Management**:
- Environment variables (never in code)
- .env files gitignored
- Railway/Render secret management
- API key rotation schedule

**Telegram Bot Security**:
- Webhook signature validation
- Chat ID whitelist (only Lloyd's chat)
- Command rate limiting

### 12.12 Testing Strategy

**Backend Tests** (pytest):
- Unit tests (business logic)
- Integration tests (API endpoints)
- Database tests (schema migrations)
- Mocking (OpenRouter API, Telegram API)

**Frontend Tests** (Vitest):
- Component tests (React Testing Library)
- Integration tests (user workflows)
- E2E tests (Playwright)

**Manual Testing Checklist**:
- [ ] Telegram notification received on mobile
- [ ] Approve reply → Reply posts to Twitter
- [ ] Edit reply → Voice validation works
- [ ] Batch approve 5 replies → All post successfully
- [ ] Adjust settings → Bot reloads config
- [ ] View analytics → Charts render correctly
- [ ] Emergency stop → Bot halts immediately
- [ ] WebSocket → Real-time updates work

### 12.13 Monitoring & Observability

**Application Monitoring**:
- **Sentry** (error tracking, $0-26/month)
- **Uptime Robot** (uptime monitoring, free tier)
- **Railway Metrics** (CPU, memory, requests)

**Logging**:
- Structured JSON logs (FastAPI)
- Log aggregation (Railway built-in)
- Log retention (30 days)

**Alerts**:
- Bot stopped unexpectedly (Telegram + email)
- Error rate spike (>10 errors/hour)
- Budget threshold (80%, 90%, 100%)
- Disk space low (<10%)

## 13. Docker Deployment & Containerization

### 13.1 Docker Architecture

**Multi-Container Stack** (5 Services):
```yaml
├── PostgreSQL (Database)
├── Redis (Cache & Sessions)
├── Bot Service (Main Application)
├── Dashboard Service (FastAPI + React)
└── Nginx (Reverse Proxy + SSL)
```

### 13.2 Dockerfile Design

**Multi-Stage Build**:
- Stage 1: Builder (Python dependencies, C extensions)
- Stage 2: Runtime (Slim image, Playwright browsers)

**Key Features**:
- Base: Python 3.11-slim
- Non-root user (security)
- Playwright Chromium for browser automation
- Health checks built-in
- Optimized layer caching

**Image Size**: ~800MB (including Chromium)

### 13.3 docker-compose.yml Services

**PostgreSQL**:
- Image: postgres:15-alpine
- Volume: postgres_data (persistent)
- Health check: pg_isready
- Init script: init-db.sql (auto-creates schema)

**Redis**:
- Image: redis:7-alpine
- Password authentication
- Volume: redis_data (persistent)

**Bot Service**:
- Custom build (Dockerfile)
- Depends on: PostgreSQL + Redis
- Auto-restart policy
- Resource limits: 2GB RAM
- Volumes: data/ (logs, cookies, session data)

**Dashboard Service**:
- Custom build (Dockerfile)
- Exposes: Port 8000 (FastAPI + WebSocket)
- Depends on: PostgreSQL + Redis

**Nginx**:
- Reverse proxy for dashboard
- SSL/TLS termination (Let's Encrypt)
- Static file serving
- HTTP → HTTPS redirect

### 13.4 Environment Variables

**Required Variables** (.env file):
```bash
# Database
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=social_reply
POSTGRES_USER=social_reply

# Redis
REDIS_PASSWORD=your_redis_password_here

# OpenRouter API
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Security
JWT_SECRET=your-super-secret-jwt-key-min-32-chars

# Optional
LOG_LEVEL=INFO
TIMEZONE=Europe/London
```

### 13.5 Deployment Options

**Option A: Automated Script** (Recommended):
```bash
# Set VPS connection
export VPS_HOST=your-vps-ip
export VPS_USER=root
export VPS_PORT=22

# Run deployment
chmod +x deploy-hetzner.sh
./deploy-hetzner.sh
```

**Features**:
- Interactive menu (10 options)
- Automated VPS setup (Docker, UFW firewall)
- Code deployment with backup
- Service management (start/stop/restart)
- SSL certificate setup
- Log viewing
- SSH access

**Option B: Manual Deployment**:
1. Set up Hetzner VPS (Ubuntu 22.04)
2. Install Docker + Docker Compose
3. Transfer files (tarball + .env)
4. Run `docker-compose up -d`

### 13.6 Hetzner VPS Requirements

**Minimum Specs**:
- Model: CX21
- vCPU: 2 cores
- RAM: 4GB
- Disk: 40GB SSD
- OS: Ubuntu 22.04 LTS
- Network: Public IPv4

**Recommended Specs**:
- Model: CX31
- vCPU: 2 cores
- RAM: 8GB
- Disk: 80GB SSD

**Firewall Rules**:
- Port 22: SSH
- Port 80: HTTP
- Port 443: HTTPS

### 13.7 Deployment Flow

1. **Initial Setup** (5-10 minutes):
   - Create Hetzner VPS
   - Install Docker + Docker Compose
   - Configure UFW firewall
   - Create deployment directory

2. **Code Deployment** (2-3 minutes):
   - Create tarball (excludes data/, .git/)
   - SCP transfer to VPS
   - Extract to /opt/social-reply-bot
   - Copy .env separately

3. **Service Startup** (3-5 minutes):
   - docker-compose pull (base images)
   - docker-compose build (custom images)
   - docker-compose up -d
   - Verify health checks

4. **Twitter Authentication**:
   - Option A: Upload cookies.json from browser
   - Option B: Run manual_login.py interactively

5. **SSL Setup** (Optional):
   - Point domain to VPS IP
   - Run certbot for Let's Encrypt
   - Configure nginx SSL
   - Set up auto-renewal cron

### 13.8 Service Management

**Start/Stop**:
```bash
docker-compose up -d          # Start all services
docker-compose down           # Stop all services
docker-compose restart bot    # Restart specific service
```

**Logs**:
```bash
docker-compose logs -f        # Follow all logs
docker-compose logs -f bot    # Follow bot logs
docker-compose logs --tail=100
```

**Updates**:
```bash
# On local machine
tar czf update.tar.gz --exclude='data' .
scp update.tar.gz root@vps:/tmp/

# On VPS
cd /opt/social-reply-bot
docker-compose down
tar xzf /tmp/update.tar.gz
docker-compose build
docker-compose up -d
```

**Database Backup**:
```bash
# Manual backup
docker exec social_reply_db pg_dump -U social_reply social_reply > backup.sql

# Restore
docker exec -i social_reply_db psql -U social_reply social_reply < backup.sql

# Automated daily backup (cron)
0 2 * * * docker exec social_reply_db pg_dump -U social_reply social_reply > /opt/backups/db-$(date +\%Y\%m\%d).sql
```

### 13.9 Monitoring & Health

**Health Checks**:
- PostgreSQL: `pg_isready` (30s interval)
- Redis: `redis-cli ping` (30s interval)
- Bot: HTTP endpoint `/health` (60s interval)
- Dashboard: HTTP endpoint `/health` (60s interval)

**Resource Monitoring**:
```bash
docker stats                  # Real-time resource usage
df -h                        # Disk space
free -h                      # Memory usage
```

**Troubleshooting**:
- Bot not starting: Check logs, verify .env variables
- Database connection: Test with `psql` inside container
- Twitter auth expired: Re-upload cookies.json
- Out of memory: Reduce resource limits or upgrade VPS
- Disk full: Clean old logs, prune Docker images

### 13.10 Cost Breakdown (Monthly)

| Service | Cost (EUR) | Cost (USD) |
|---------|-----------|-----------|
| Hetzner CX21 VPS | €5.83 | ~$6 |
| Hetzner CX31 VPS (recommended) | €9.87 | ~$11 |
| OpenRouter API (Claude) | €10-30 | $10-30 |
| Domain (optional) | €1 | ~$1 |
| **Total (CX21)** | **€16-36** | **$17-37** |
| **Total (CX31)** | **€20-40** | **$22-44** |

**Notes**:
- OpenRouter cost varies with usage (5-20 replies/day)
- No Railway costs (self-hosted)
- Domain optional (can use IP address)
- SSL certificates free (Let's Encrypt)

### 13.11 Security Hardening

**VPS Level**:
- Disable root SSH login
- Use SSH keys only (no password auth)
- Enable UFW firewall
- Install fail2ban (brute force protection)
- Regular system updates: `apt-get update && apt-get upgrade`

**Application Level**:
- Non-root Docker user (UID 1000)
- JWT authentication for dashboard
- Environment variables for secrets (no hardcoding)
- PostgreSQL password authentication
- Redis password authentication

**Container Level**:
- Resource limits (memory, CPU)
- Read-only root filesystem (where possible)
- Drop unnecessary capabilities
- No privileged containers

### 13.12 Deployment Files

**Created Files**:
- [Dockerfile](Dockerfile) - Multi-stage Python build
- [docker-compose.yml](docker-compose.yml) - 5-service orchestration
- [.dockerignore](.dockerignore) - Build optimization
- [.env.example](.env.example) - Configuration template
- [init-db.sql](init-db.sql) - Database initialization
- [deploy-hetzner.sh](deploy-hetzner.sh) - Automated deployment script
- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide

**Quick Start**:
```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Add your credentials

# 2. Set VPS connection
export VPS_HOST=your-vps-ip
export VPS_USER=root

# 3. Run deployment
chmod +x deploy-hetzner.sh
./deploy-hetzner.sh  # Select option 1 (Full deployment)
```

## 14. Future Enhancements

- Multi-account rotation
- Sentiment analysis for better targeting
- A/B testing reply variations
- Machine learning for optimal timing
- Conversation thread management
- Direct message capabilities
- Performance-based prompt optimization
- Real-time engagement tracking
- Automated good example curation
- Voice drift detection and correction
- Multi-user support (team collaboration)
- Webhook integrations (Slack, Discord)
- Custom report generation
- Reply templates library
- Advanced analytics (cohort analysis, LTV prediction)

---

**Project Status**: Architecture Phase Complete - Ready for Implementation
**Last Updated**: 2025-01-07
**Author**: Lloyd
**License**: Private Use
**Target Brand**: Belief Forge (beliefforge.com)
