"""
Configuration loader for Social Reply Bot.

Loads YAML configuration and environment variables, providing a unified
configuration object for the entire application.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class EngagementConfig:
    """Engagement filter thresholds"""
    min_followers: int
    max_followers: int
    min_likes: int
    min_replies: int
    max_replies: int


@dataclass
class RecencyConfig:
    """Tweet recency filters"""
    min_age_hours: int
    max_age_hours: int


@dataclass
class ContentQualityConfig:
    """Content quality filters"""
    min_length: int
    max_length: int
    reddit_max_length: int
    banned_keywords: List[str]
    banned_patterns: List[str]


@dataclass
class FiltersConfig:
    """Base filters configuration"""
    engagement: EngagementConfig
    recency: RecencyConfig
    language: Dict[str, str]
    content_quality: ContentQualityConfig


@dataclass
class PriorityKeywordsConfig:
    """Commercial priority keywords"""
    critical: List[str]
    high: List[str]
    medium_high: List[str]
    medium: List[str]


@dataclass
class ProfileIndicatorsConfig:
    """User profile indicators"""
    entrepreneur_keywords: List[str]
    target_stage: List[str]


@dataclass
class CommercialConfig:
    """Commercial filtering configuration"""
    priority_keywords: PriorityKeywordsConfig
    profile_indicators: ProfileIndicatorsConfig


@dataclass
class ScoringConfig:
    """Tweet scoring configuration"""
    weights: Dict[str, float]
    thresholds: Dict[str, int]


@dataclass
class LLMConfig:
    """LLM generation configuration"""
    provider: str
    model: str
    parameters: Dict[str, Any]
    rate_limits: Dict[str, int]
    learning: Dict[str, Any]


@dataclass
class VoiceConfig:
    """Voice guidelines configuration"""
    tone: str
    language: str
    character_limits: Dict[str, int]
    required_patterns: List[str]
    strict_avoidance: List[str]
    validation: Dict[str, Any]


@dataclass
class DeduplicationConfig:
    """Deduplication configuration"""
    history_days: int
    same_author_cooldown_hours: int
    engagement_limits: Dict[str, int]


@dataclass
class ScheduleConfig:
    """Scheduling configuration"""
    timezone: str
    active_hours: Dict[str, str]
    check_intervals: Dict[str, int]
    daylight_savings: Dict[str, bool]


@dataclass
class BehaviorConfig:
    """Behavior randomization configuration"""
    randomization: Dict[str, Any]
    human_patterns: Dict[str, Any]


@dataclass
class RetentionConfig:
    """Data retention configuration"""
    logs_days: int
    scraped_data_days: int
    scraped_data_keep_queued_days: int


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    telegram: Dict[str, Any]
    logging: Dict[str, Any]
    retention: RetentionConfig


@dataclass
class DashboardConfig:
    """Dashboard configuration"""
    default_view: str
    auto_refresh_seconds: int
    features: Dict[str, bool]


@dataclass
class SafetyConfig:
    """Safety and ethics configuration"""
    content_moderation: Dict[str, bool]
    transparency: Dict[str, Any]
    respect: Dict[str, bool]


@dataclass
class TargetsConfig:
    """Search targets configuration"""
    hashtags: List[str]
    keywords: List[str]
    subreddits: List[str] = field(default_factory=list)
    lists: List[str] = field(default_factory=list)


@dataclass
class PlatformStatus:
    """Platform specific status configuration"""
    enabled: bool


@dataclass
class PlatformsConfig:
    """Platforms configuration"""
    twitter: PlatformStatus
    reddit: PlatformStatus


@dataclass
class BotConfig:
    """Complete bot configuration"""
    targets: TargetsConfig
    platforms: PlatformsConfig
    filters: FiltersConfig
    commercial: CommercialConfig
    scoring: ScoringConfig
    llm: LLMConfig
    voice: VoiceConfig
    deduplication: DeduplicationConfig
    schedule: ScheduleConfig
    behavior: BehaviorConfig
    monitoring: MonitoringConfig
    dashboard: DashboardConfig
    safety: SafetyConfig


@dataclass
class EnvConfig:
    """Environment variables configuration"""
    # Database
    postgres_db: str
    postgres_user: str
    postgres_password: str
    database_url: str

    # Redis
    redis_password: str
    redis_url: str

    # OpenRouter
    openrouter_api_key: str

    # Telegram
    telegram_bot_token: str
    telegram_chat_id: str

    # Security
    jwt_secret: str

    # Optional
    log_level: str = "INFO"
    timezone: str = "Europe/London"


class ConfigLoader:
    """Loads and validates configuration from YAML and environment variables"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration loader.

        Args:
            config_path: Path to YAML config file (default: config/bot_config.yaml)
        """
        # Load environment variables from .env file
        load_dotenv()

        if config_path is None:
            # Default to config/bot_config.yaml relative to project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "bot_config.yaml"

        self.config_path = Path(config_path)
        self.yaml_config: Dict[str, Any] = {}
        self.bot_config: Optional[BotConfig] = None
        self.env_config: Optional[EnvConfig] = None

    def load(self) -> tuple[BotConfig, EnvConfig]:
        """
        Load configuration from YAML and environment variables.

        Returns:
            Tuple of (BotConfig, EnvConfig)

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If required config values are missing
        """
        self._load_yaml()
        self.bot_config = self._parse_bot_config()
        self.env_config = self._load_env_config()

        return self.bot_config, self.env_config

    def _load_yaml(self) -> None:
        """Load YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.yaml_config = yaml.safe_load(f)

    def _parse_bot_config(self) -> BotConfig:
        """Parse YAML into BotConfig dataclass"""
        cfg = self.yaml_config

        return BotConfig(
            targets=TargetsConfig(
                hashtags=cfg['targets']['hashtags'],
                keywords=cfg['targets']['keywords'],
                subreddits=cfg['targets'].get('subreddits', []),
                lists=cfg['targets'].get('lists', [])
            ),
            platforms=PlatformsConfig(
                twitter=PlatformStatus(**cfg.get('platforms', {}).get('twitter', {'enabled': True})),
                reddit=PlatformStatus(**cfg.get('platforms', {}).get('reddit', {'enabled': True}))
            ),
            filters=FiltersConfig(
                engagement=EngagementConfig(**cfg['filters']['engagement']),
                recency=RecencyConfig(**cfg['filters']['recency']),
                language=cfg['filters']['language'],
                content_quality=ContentQualityConfig(**cfg['filters']['content_quality'])
            ),
            commercial=CommercialConfig(
                priority_keywords=PriorityKeywordsConfig(**cfg['commercial']['priority_keywords']),
                profile_indicators=ProfileIndicatorsConfig(**cfg['commercial']['profile_indicators'])
            ),
            scoring=ScoringConfig(
                weights=cfg['scoring']['weights'],
                thresholds=cfg['scoring']['thresholds']
            ),
            llm=LLMConfig(
                provider=cfg['llm']['provider'],
                model=cfg['llm']['model'],
                parameters=cfg['llm']['parameters'],
                rate_limits=cfg['llm']['rate_limits'],
                learning=cfg['llm']['learning']
            ),
            voice=VoiceConfig(
                tone=cfg['voice']['tone'],
                language=cfg['voice']['language'],
                character_limits=cfg['voice']['character_limits'],
                required_patterns=cfg['voice']['required_patterns'],
                strict_avoidance=cfg['voice']['strict_avoidance'],
                validation=cfg['voice']['validation']
            ),
            deduplication=DeduplicationConfig(
                history_days=cfg['deduplication']['history_days'],
                same_author_cooldown_hours=cfg['deduplication']['same_author_cooldown_hours'],
                engagement_limits=cfg['deduplication']['engagement_limits']
            ),
            schedule=ScheduleConfig(
                timezone=cfg['schedule']['timezone'],
                active_hours=cfg['schedule']['active_hours'],
                check_intervals=cfg['schedule']['check_intervals'],
                daylight_savings=cfg['schedule']['daylight_savings']
            ),
            behavior=BehaviorConfig(
                randomization=cfg['behavior']['randomization'],
                human_patterns=cfg['behavior']['human_patterns']
            ),
            monitoring=MonitoringConfig(
                telegram=cfg['monitoring']['telegram'],
                logging=cfg['monitoring']['logging'],
                retention=RetentionConfig(**cfg['monitoring'].get('retention', {
                    'logs_days': 30,
                    'scraped_data_days': 14,
                    'scraped_data_keep_queued_days': 90
                }))
            ),
            dashboard=DashboardConfig(
                default_view=cfg['dashboard']['default_view'],
                auto_refresh_seconds=cfg['dashboard']['auto_refresh_seconds'],
                features=cfg['dashboard']['features']
            ),
            safety=SafetyConfig(
                content_moderation=cfg['safety']['content_moderation'],
                transparency=cfg['safety']['transparency'],
                respect=cfg['safety']['respect']
            )
        )

    def _load_env_config(self) -> EnvConfig:
        """Load environment variables into EnvConfig"""
        # Required environment variables
        postgres_password = os.getenv('POSTGRES_PASSWORD')
        redis_password = os.getenv('REDIS_PASSWORD')
        openrouter_api_key = os.getenv('OPENROUTER_API_KEY')
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        jwt_secret = os.getenv('JWT_SECRET')

        # Validate required variables
        required_vars = {
            'POSTGRES_PASSWORD': postgres_password,
            'REDIS_PASSWORD': redis_password,
            'OPENROUTER_API_KEY': openrouter_api_key,
            'TELEGRAM_BOT_TOKEN': telegram_bot_token,
            'TELEGRAM_CHAT_ID': telegram_chat_id,
            'JWT_SECRET': jwt_secret
        }

        missing_vars = [k for k, v in required_vars.items() if not v]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Database configuration
        postgres_db = os.getenv('POSTGRES_DB', 'social_reply')
        postgres_user = os.getenv('POSTGRES_USER', 'social_reply')
        postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')

        database_url = f"postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}"

        # Redis configuration
        redis_host = os.getenv('REDIS_HOST', 'redis')
        redis_port = os.getenv('REDIS_PORT', '6379')
        redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/0"

        return EnvConfig(
            postgres_db=postgres_db,
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            database_url=database_url,
            redis_password=redis_password,
            redis_url=redis_url,
            openrouter_api_key=openrouter_api_key,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            jwt_secret=jwt_secret,
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            timezone=os.getenv('TIMEZONE', 'Europe/London')
        )


# Global configuration instance
_config_loader: Optional[ConfigLoader] = None
_bot_config: Optional[BotConfig] = None
_env_config: Optional[EnvConfig] = None


def get_config() -> tuple[BotConfig, EnvConfig]:
    """
    Get global configuration instance (singleton pattern).

    Returns:
        Tuple of (BotConfig, EnvConfig)
    """
    global _config_loader, _bot_config, _env_config

    if _config_loader is None:
        _config_loader = ConfigLoader()
        _bot_config, _env_config = _config_loader.load()

    return _bot_config, _env_config


def reload_config() -> tuple[BotConfig, EnvConfig]:
    """
    Reload configuration from files (useful for config changes without restart).

    Returns:
        Tuple of (BotConfig, EnvConfig)
    """
    global _config_loader, _bot_config, _env_config

    _config_loader = ConfigLoader()
    _bot_config, _env_config = _config_loader.load()

    return _bot_config, _env_config


def update_config(updates: Dict[str, Any]) -> bool:
    """
    Update configuration values in YAML file.

    Args:
        updates: Dictionary of configuration updates

    Returns:
        True if update was successful, False otherwise
    """
    try:
        global _config_loader, _bot_config, _env_config

        if _config_loader is None:
            _config_loader = ConfigLoader()
            _config_loader.load()

        # Reload current YAML config from disk to get latest changes
        _config_loader._load_yaml()
        current_config = _config_loader.yaml_config

        # Apply updates recursively
        def update_nested_dict(d, updates):
            for key, value in updates.items():
                if isinstance(value, dict) and key in d and isinstance(d[key], dict):
                    update_nested_dict(d[key], value)
                else:
                    d[key] = value

        update_nested_dict(current_config, updates)

        # Write updated config back to file
        with open(_config_loader.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(current_config, f, default_flow_style=False, indent=2)

        # Reload configuration
        reload_config()

        return True

    except Exception as e:
        print(f"Error updating config: {e}")
        return False


if __name__ == "__main__":
    # Test configuration loading
    try:
        bot_config, env_config = get_config()
        print("Configuration loaded successfully")
        print(f"  - Targets: {len(bot_config.targets.hashtags)} hashtags, {len(bot_config.targets.keywords)} keywords")
        print(f"  - LLM Model: {bot_config.llm.model}")
        print(f"  - Database: {env_config.database_url}")
        print(f"  - Timezone: {bot_config.schedule.timezone}")
    except Exception as e:
        print(f"Configuration loading failed: {e}")
