# Quick Setup Guide

## ✅ Credentials Configured

Your `.env` file has been created with the following:

### 1. ✅ OpenRouter API Key
- **Status**: Configured
- **Key**: `sk-or-v1-4571...f886`

### 2. ✅ PostgreSQL (Local Docker)
- **Status**: Configured
- **Database**: `social_reply`
- **User**: `social_reply`
- **Password**: Auto-generated (stored in `.env`)
- **Port**: 5432

### 3. ✅ Redis (Local Docker)
- **Status**: Configured
- **Password**: Auto-generated (stored in `.env`)
- **Port**: 6379

### 4. ✅ JWT Secret
- **Status**: Generated
- **Secret**: 64-character hex string (stored in `.env`)

### 5. ⏳ Telegram Bot (TODO)
**You need to set this up now.**

## 🤖 Create Telegram Bot (5 minutes)

### Step 1: Create Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Send: `/newbot`
3. Bot name: `Belief Forge Reply Bot`
4. Bot username: `beliefforge_reply_bot` (must end in 'bot')
5. Copy the **bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

1. Start a chat with your new bot (search for `@beliefforge_reply_bot`)
2. Send any message (e.g., "Hello")
3. Visit this URL in your browser (replace `YOUR_BOT_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
   ```
4. Look for `"chat":{"id":123456789}` in the JSON response
5. Copy that number - it's your chat ID

### Step 3: Update .env File

Edit `.env` and replace:
```bash
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE  # Replace with token from Step 1
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE      # Replace with ID from Step 2
```

Example:
```bash
TELEGRAM_BOT_TOKEN=6847239812:AAGxKL3mP9qN8rStUvWxYz0123456789AB
TELEGRAM_CHAT_ID=987654321
```

## 🍪 Twitter Authentication (TODO)

You need Twitter cookies for authentication.

### Option A: Export from Browser (Recommended)

1. Install browser extension:
   - Chrome: [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg)
   - Firefox: [Cookie Editor](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/)

2. Login to Twitter/X in your browser

3. Click the extension icon → Export cookies

4. Save the JSON file as: `data/cookies.json`

5. Restart bot: `docker-compose restart bot`

### Option B: Manual Login (Alternative)

After starting the bot:
```bash
docker-compose run --rm bot python src/auth/manual_login.py
```
Follow prompts to login. Cookies saved automatically.

## 🚀 Start the Bot

### Step 1: Build Docker Images

```bash
cd "C:\Users\lloyd\Documents\Social Reply"
docker-compose build
```

### Step 2: Start Services

```bash
docker-compose up -d
```

### Step 3: Check Status

```bash
# View all services
docker-compose ps

# View bot logs
docker-compose logs -f bot

# View all logs
docker-compose logs -f
```

### Step 4: Test Telegram Bot

Send `/start` to your Telegram bot. You should receive a welcome message.

## 🧪 Test Configuration

Test individual components:

```bash
# Test configuration loading
docker-compose run --rm bot python src/config/loader.py

# Test database connection
docker-compose run --rm bot python src/db/connection.py

# Test voice validator
docker-compose run --rm bot python src/voice/validator.py
```

## 📊 Monitor the Bot

### Telegram Commands

- `/start` - Start bot and show welcome
- `/status` - Current bot status
- `/queue` - View pending replies
- `/stats` - Reply statistics
- `/help` - Command help

### View Logs

```bash
# Follow bot logs
docker-compose logs -f bot

# Last 100 lines
docker-compose logs --tail=100 bot

# All services
docker-compose logs -f
```

### Access Database

```bash
# PostgreSQL
docker exec -it social_reply_db psql -U social_reply -d social_reply

# Redis
docker exec -it social_reply_redis redis-cli -a bb+q0YYTTM0NdijPUqPkhomj4dYw7tkE
```

## 🛠️ Common Commands

### Start/Stop

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart bot only
docker-compose restart bot

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v
```

### Rebuild After Code Changes

```bash
docker-compose build bot
docker-compose up -d bot
```

### View Service Status

```bash
docker-compose ps
```

## 🚨 Troubleshooting

### Bot won't start

```bash
# Check logs
docker-compose logs bot

# Check environment variables
docker-compose exec bot env | grep OPENROUTER
```

### Database connection failed

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

### Telegram bot not responding

1. Verify `TELEGRAM_BOT_TOKEN` is correct
2. Verify `TELEGRAM_CHAT_ID` is correct
3. Check bot logs: `docker-compose logs bot | grep -i telegram`

### Twitter authentication expired

1. Re-export cookies from browser
2. Save to `data/cookies.json`
3. Restart: `docker-compose restart bot`

## ✅ Next Steps

Once everything is running:

1. **Monitor first session**: Watch logs as bot scrapes and filters tweets
2. **Approve replies**: Respond to Telegram notifications with ✅/❌
3. **Adjust config**: Edit `config/bot_config.yaml` as needed
4. **Check stats**: Use `/stats` command in Telegram

## 📝 Current Status

- [x] OpenRouter API configured
- [x] PostgreSQL configured
- [x] Redis configured
- [x] JWT Secret generated
- [ ] Telegram bot configured (TODO: See Step 5)
- [ ] Twitter cookies exported (TODO: See Step 6)

---

**Need help?** Check the full documentation:
- [README.md](README.md) - Overview
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
- [CLAUDE.md](CLAUDE.md) - Development guide
