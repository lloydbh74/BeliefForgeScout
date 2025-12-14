-- Initialize database schema for Social Reply Bot
-- This runs automatically when PostgreSQL container starts for the first time

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Reply approval queue
CREATE TABLE IF NOT EXISTS reply_queue (
    id SERIAL PRIMARY KEY,
    tweet_id TEXT NOT NULL,
    tweet_author TEXT,
    tweet_text TEXT,
    tweet_metrics JSONB,
    created_at TIMESTAMP DEFAULT NOW(),

    -- Generated reply
    reply_text TEXT NOT NULL,
    reply_score FLOAT,
    commercial_priority TEXT,
    commercial_signals JSONB,
    voice_validation_score FLOAT,
    voice_violations JSONB,

    -- Approval status
    status TEXT DEFAULT 'pending',
    approved_by TEXT,
    approved_at TIMESTAMP,
    rejection_reason TEXT,

    -- Metadata
    session_id TEXT,
    attempt_number INT DEFAULT 1,

    CONSTRAINT unique_tweet_per_session UNIQUE (tweet_id, session_id)
);

-- Reply performance tracking
CREATE TABLE IF NOT EXISTS reply_performance (
    id SERIAL PRIMARY KEY,
    tweet_id TEXT NOT NULL,
    reply_id TEXT,
    reply_text TEXT NOT NULL,
    posted_at TIMESTAMP NOT NULL,

    -- Performance metrics
    like_count INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0,

    -- Quality indicators
    validation_score FLOAT,
    had_violations BOOLEAN DEFAULT false,

    -- Learning flags
    marked_as_good_example BOOLEAN DEFAULT false,
    marked_as_bad_example BOOLEAN DEFAULT false,

    -- Context
    original_tweet_text TEXT,
    commercial_priority TEXT
);

-- Index for learning queries
CREATE INDEX IF NOT EXISTS idx_good_examples ON reply_performance(marked_as_good_example, posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_recent_replies ON reply_performance(posted_at DESC);

-- User-editable settings
CREATE TABLE IF NOT EXISTS bot_settings (
    id SERIAL PRIMARY KEY,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by TEXT,

    CONSTRAINT unique_category_key UNIQUE (category, key)
);

-- Analytics metrics (aggregated daily)
CREATE TABLE IF NOT EXISTS analytics_daily (
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

    -- Engagement metrics
    avg_likes_received FLOAT,
    avg_replies_received FLOAT,
    avg_engagement_rate FLOAT,

    -- Cost metrics
    api_cost_usd FLOAT DEFAULT 0,
    token_usage INT DEFAULT 0,

    CONSTRAINT unique_date UNIQUE (date)
);

-- Error log
CREATE TABLE IF NOT EXISTS error_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    severity TEXT,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    tweet_id TEXT,
    session_id TEXT,
    resolved BOOLEAN DEFAULT false,
    resolved_at TIMESTAMP
);

-- User sessions (authentication)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT DEFAULT 'admin',
    telegram_chat_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Notification preferences
CREATE TABLE IF NOT EXISTS notification_settings (
    user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    telegram_enabled BOOLEAN DEFAULT true,
    email_enabled BOOLEAN DEFAULT false,
    telegram_events JSONB DEFAULT '["reply_ready", "error_critical"]',
    email_events JSONB DEFAULT '["daily_summary"]'
);

-- Deduplication tracking (legacy from SQLite)
CREATE TABLE IF NOT EXISTS replied_tweets (
    tweet_id TEXT PRIMARY KEY,
    author_username TEXT NOT NULL,
    tweet_text TEXT,
    replied_at TIMESTAMP NOT NULL,
    reply_text TEXT,
    commercial_priority TEXT,
    score FLOAT,
    engagement_velocity FLOAT,
    user_authority FLOAT,
    timing_score FLOAT,
    discussion_score FLOAT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_reply_queue_status ON reply_queue(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reply_queue_session ON reply_queue(session_id);
CREATE INDEX IF NOT EXISTS idx_error_log_timestamp ON error_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_error_log_severity ON error_log(severity);
CREATE INDEX IF NOT EXISTS idx_analytics_date ON analytics_daily(date DESC);
CREATE INDEX IF NOT EXISTS idx_replied_tweets_timestamp ON replied_tweets(replied_at DESC);

-- Insert default admin user (password: changeme123 - CHANGE THIS!)
-- Password hash for 'changeme123' using bcrypt
INSERT INTO users (email, hashed_password, role)
VALUES ('admin@beliefforge.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5eTRZq5u7yYEG', 'admin')
ON CONFLICT (email) DO NOTHING;

-- Insert default bot settings
INSERT INTO bot_settings (category, key, value) VALUES
('search', 'keywords', '["imposter syndrome", "self-doubt", "brand identity", "positioning"]'),
('search', 'hashtags', '["#BuildInPublic", "#Bootstrapped", "#StartupLife", "#SoloFounder"]'),
('filtering', 'min_followers', '500'),
('filtering', 'min_likes', '10'),
('filtering', 'min_replies', '3'),
('engagement', 'max_replies_per_hour', '5'),
('scheduling', 'active_hours_start', '7'),
('scheduling', 'active_hours_end', '24')
ON CONFLICT (category, key) DO NOTHING;

-- Create function to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for bot_settings
CREATE TRIGGER update_bot_settings_updated_at BEFORE UPDATE ON bot_settings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
