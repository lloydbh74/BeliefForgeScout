# Social Reply Bot for Belief Forge

An intelligent Twitter/X engagement bot that automatically discovers and creates authentic, brand-aligned replies to tweets from entrepreneurs experiencing imposter syndrome, self-doubt, and brand clarity struggles.

## 🎯 Overview

The bot uses sophisticated multi-layered filtering and LLM-powered reply generation to engage with high-value prospects while maintaining strict British English voice guidelines.

**Target Brand**: Belief Forge (beliefforge.com)
**Target Audience**: Entrepreneurs with belief-based business challenges
**Reply Style**: Warm, authentic British English (NO exclamation marks, NO corporate jargon)

## ✨ Key Features

- **Multi-Layered Filtering**: Base → Commercial → Scoring → Deduplication
- **LLM-Powered Replies**: OpenRouter (Claude Sonnet 3.5) with learning corpus
- **Voice Validation**: Strict British English enforcement
- **Human-in-the-Loop**: Telegram bot for approval
- **Smart Timing**: UK timezone-aware (07:00-24:00, auto GMT/BST)
- **Commercial Priority**: 3x critical (imposter syndrome) → 2x high (brand clarity) → 1.5x medium-high (growth)

## 🏗️ Architecture

```
Scraping → Base Filters → Commercial Filters → Scoring → Deduplication
    ↓
LLM Reply Generation → Voice Validation → Human Approval (Telegram)
    ↓
Posting → Performance Tracking → Learning Corpus
```

### Tech Stack

- **Language**: Python 3.11
- **Scraping**: Playwright (headless Chrome)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **LLM**: OpenRouter API (Claude Sonnet 3.5)
- **Notifications**: Telegram Bot
- **Deployment**: Docker + Docker Compose
- **Hosting**: Hetzner VPS (CX21/CX31)

## 🚀 Quick Start

### 1. Prerequisites

- Docker & Docker Compose installed
- Hetzner VPS (or any Ubuntu 22.04 server)
- OpenRouter API key
- Telegram bot token
- Twitter account (for cookie authentication)

### 2. Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your credentials
nano .env
```

Required environment variables:
```bash
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
OPENROUTER_API_KEY=sk-or-v1-your-key-here
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
JWT_SECRET=your-jwt-secret-min-32-chars
```

### 3. Twitter Authentication

Export cookies from your browser:

1. Install "EditThisCookie" or "Cookie Editor" extension
2. Login to Twitter/X
3. Export cookies as JSON
4. Save to `data/cookies.json`

### 4. Deploy

**Option A: Automated (Recommended)**

```bash
export VPS_HOST=your-vps-ip
export VPS_USER=root

chmod +x deploy-hetzner.sh
./deploy-hetzner.sh
```

**Option B: Manual**

```bash
# Local testing
docker-compose up -d

# Check logs
docker-compose logs -f bot
```

## 📂 Project Structure

```
social-reply-bot/
├── src/
│   ├── config/          # Configuration management
│   ├── db/              # Database models & connection
│   ├── scraping/        # Twitter scraper (Playwright)
│   ├── filtering/       # Base, commercial, deduplication filters
│   ├── scoring/         # Tweet scoring system
│   ├── llm/             # OpenRouter client & reply generator
│   ├── voice/           # Voice validation (British English)
│   ├── telegram/        # Telegram bot for approvals
│   ├── timing/          # UK timezone scheduling
│   ├── core/            # Main orchestrator
│   └── main.py          # Entry point
├── config/
│   └── bot_config.yaml  # Bot configuration (editable)
├── data/
│   ├── logs/            # Application logs
│   ├── cookies.json     # Twitter session cookies
│   └── db/              # SQLite (if not using PostgreSQL)
├── docker-compose.yml   # Docker orchestration
├── Dockerfile           # Bot container image
├── init-db.sql          # Database schema
├── deploy-hetzner.sh    # Deployment script
└── requirements.txt     # Python dependencies
```

## 🎛️ Configuration

Edit `config/bot_config.yaml` to customize:

- **Targets**: Hashtags, keywords, Twitter lists
- **Filters**: Engagement thresholds, banned keywords
- **Commercial**: Priority keywords and multipliers
- **Scoring**: Weights (velocity, authority, timing, discussion)
- **LLM**: Model, temperature, budget limits
- **Voice**: Character limits, British English patterns
- **Schedule**: Active hours, check intervals
- **Rate Limits**: Max replies per hour/day

## 📊 Monitoring

### Telegram Commands

- `/status` - Bot status and rate limits
- `/queue` - View pending approvals
- `/stats` - Reply statistics
- `/help` - Command help

### Dashboard (Future)

FastAPI dashboard on port 8000 (optional):
- Approval queue management
- Analytics and metrics
- Settings editor
- Error monitoring

### Logs

```bash
# View bot logs
docker-compose logs -f bot

# View all logs
docker-compose logs -f

# Last 100 lines
docker-compose logs --tail=100 bot
```

## 🧪 Testing

Each module includes test functionality:

```bash
# Test configuration
python src/config/loader.py

# Test database connection
python src/db/connection.py

# Test tweet scorer
python src/scoring/tweet_scorer.py

# Test voice validator
python src/voice/validator.py

# Test OpenRouter client (uses API credits)
python src/llm/openrouter_client.py
```

## 💰 Cost Estimates

**Monthly Costs**:
- Hetzner VPS (CX21): €5.83/month (~$6)
- OpenRouter API: $10-30/month (5-20 replies/day)
- **Total**: €16-36/month (~$17-37)

**Budget Controls**:
- Daily API budget: $50 (configurable)
- Rate limits: 5 replies/hour, 20/day
- Cost tracking per request

## 🔒 Security

- Non-root Docker user
- Environment variables for secrets
- JWT authentication for dashboard
- PostgreSQL + Redis password authentication
- UFW firewall on VPS
- SSL/TLS with Let's Encrypt (optional)

## 🚨 Important Voice Guidelines

The bot enforces strict British English voice:

✅ **Required**:
- British spellings (realise, colour, whilst, amongst)
- < 100 characters preferred
- Warm, authentic tone
- Gentle qualifiers (quite, rather, perhaps)

❌ **Forbidden**:
- Exclamation marks (!)
- Hyphenation instead of commas
- Corporate jargon (synergy, leverage, disrupt)
- American spellings (-ize, -or, while, among)
- Salesy language
- Excessive emoji/hashtags

## 📝 Development

See [CLAUDE.md](CLAUDE.md) for detailed development guidance.

### Key Modules

- **orchestrator.py**: Main workflow coordinator
- **twitter_scraper.py**: Playwright-based scraper
- **commercial_filter.py**: Priority keyword detection
- **tweet_scorer.py**: Weighted scoring (4 components)
- **reply_generator.py**: LLM + learning corpus
- **validator.py**: British English enforcement
- **approval_bot.py**: Telegram interface
- **scheduler.py**: UK timezone handling

## 🐛 Troubleshooting

**Bot not starting**:
```bash
docker-compose logs bot
docker-compose restart bot
```

**Database connection failed**:
```bash
docker-compose ps
docker exec -it social_reply_db psql -U social_reply
```

**Twitter auth expired**:
- Re-export cookies from browser
- Copy to `data/cookies.json`
- Restart bot

**Rate limit exceeded**:
- Check `/stats` in Telegram
- Adjust limits in `bot_config.yaml`

## 📚 Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Complete deployment guide
- [CLAUDE.md](CLAUDE.md) - Development guide for AI assistants
- [PROJECT_OUTLINE.md](PROJECT_OUTLINE.md) - Full architecture specification

## 📄 License

Private use - Belief Forge

## 👤 Author

Lloyd @ Belief Forge
