"""
Timing controller for UK timezone-aware scheduling.

Enforces active hours (07:00-24:00 UK time) with automatic GMT/BST handling
and provides scheduling utilities for human-like behavior.
"""

import logging
from typing import Tuple, Optional
from datetime import datetime, time, timedelta
import pytz
import random

from src.config.loader import get_config

logger = logging.getLogger(__name__)


class TimingController:
    """Manages timing, scheduling, and active hours enforcement"""

    def __init__(self):
        """Initialize timing controller with UK timezone"""
        self.bot_config, _ = get_config()
        self.schedule_config = self.bot_config.schedule

        # UK timezone (auto-handles GMT/BST)
        self.uk_tz = pytz.timezone(self.schedule_config.timezone)

        # Parse active hours
        self.active_start = self._parse_time(self.schedule_config.active_hours['start'])
        self.active_end = self._parse_time(self.schedule_config.active_hours['end'])

        logger.info(f"Timing controller initialized: {self.schedule_config.timezone}, "
                   f"active hours {self.active_start}-{self.active_end}")

    def _parse_time(self, time_str: str) -> time:
        """Parse time string (HH:MM) to time object"""
        hour, minute = map(int, time_str.split(':'))
        return time(hour, minute)

    def is_active_hours(self, check_time: Optional[datetime] = None) -> bool:
        """
        Check if current/given time is within active hours.

        Args:
            check_time: Time to check (default: now)

        Returns:
            True if within active hours, False otherwise
        """
        if check_time is None:
            check_time = datetime.now(pytz.utc)

        # Convert to UK time
        uk_time = check_time.astimezone(self.uk_tz)
        current_time = uk_time.time()

        # Check if within active window
        # Handle case where end time is midnight (24:00 = 00:00)
        if self.active_end == time(0, 0):
            # Active until midnight
            is_active = self.active_start <= current_time or current_time < self.active_end
        else:
            is_active = self.active_start <= current_time < self.active_end

        logger.debug(f"Time check: {uk_time.strftime('%H:%M')} UK time, active: {is_active}")

        return is_active

    def get_next_active_window(self, from_time: Optional[datetime] = None) -> Tuple[datetime, datetime]:
        """
        Get next active time window.

        Args:
            from_time: Starting time (default: now)

        Returns:
            Tuple of (window_start, window_end) in UTC
        """
        if from_time is None:
            from_time = datetime.now(pytz.utc)

        # Convert to UK time
        uk_time = from_time.astimezone(self.uk_tz)

        # If currently active, return current window
        if self.is_active_hours(from_time):
            # Window ends at active_end today
            window_end = uk_time.replace(
                hour=self.active_end.hour,
                minute=self.active_end.minute,
                second=0,
                microsecond=0
            )
            return from_time, window_end.astimezone(pytz.utc)

        # Not active - find next start time
        current_time = uk_time.time()

        if current_time < self.active_start:
            # Next window starts today
            window_start = uk_time.replace(
                hour=self.active_start.hour,
                minute=self.active_start.minute,
                second=0,
                microsecond=0
            )
        else:
            # Next window starts tomorrow
            tomorrow = uk_time + timedelta(days=1)
            window_start = tomorrow.replace(
                hour=self.active_start.hour,
                minute=self.active_start.minute,
                second=0,
                microsecond=0
            )

        # Window end
        window_end = window_start.replace(
            hour=self.active_end.hour,
            minute=self.active_end.minute
        )

        # Convert to UTC
        return window_start.astimezone(pytz.utc), window_end.astimezone(pytz.utc)

    def get_time_until_active(self, from_time: Optional[datetime] = None) -> Optional[timedelta]:
        """
        Get time until next active window.

        Args:
            from_time: Starting time (default: now)

        Returns:
            Timedelta until active, or None if currently active
        """
        if from_time is None:
            from_time = datetime.now(pytz.utc)

        if self.is_active_hours(from_time):
            return None  # Already active

        window_start, _ = self.get_next_active_window(from_time)
        return window_start - from_time

    def get_random_delay(self, min_ms: Optional[int] = None, max_ms: Optional[int] = None) -> float:
        """
        Get random delay for human-like behavior.

        Args:
            min_ms: Minimum delay in milliseconds (default: from config)
            max_ms: Maximum delay in milliseconds (default: from config)

        Returns:
            Delay in seconds
        """
        behavior_config = self.bot_config.behavior.randomization

        if min_ms is None or max_ms is None:
            # Use typing delay as default
            delay_range = behavior_config['typing_delay_ms']
            min_ms = delay_range[0]
            max_ms = delay_range[1]

        delay_ms = random.randint(min_ms, max_ms)
        return delay_ms / 1000.0

    def should_take_break(self, replies_count: int) -> bool:
        """
        Check if bot should take a break after N replies.

        Args:
            replies_count: Number of replies posted in current session

        Returns:
            True if should take break
        """
        break_after = self.bot_config.behavior.human_patterns.get('break_after_replies', 3)
        return replies_count >= break_after and replies_count % break_after == 0

    def get_break_duration(self) -> timedelta:
        """
        Get duration for a break between reply batches.

        Returns:
            Break duration (5-10 minutes)
        """
        minutes = random.randint(5, 10)
        return timedelta(minutes=minutes)

    def get_uk_time(self, utc_time: Optional[datetime] = None) -> datetime:
        """
        Convert UTC time to UK time.

        Args:
            utc_time: UTC datetime (default: now)

        Returns:
            UK datetime
        """
        if utc_time is None:
            utc_time = datetime.now(pytz.utc)

        if utc_time.tzinfo is None:
            utc_time = pytz.utc.localize(utc_time)

        return utc_time.astimezone(self.uk_tz)

    def get_utc_time(self, uk_time: datetime) -> datetime:
        """
        Convert UK time to UTC.

        Args:
            uk_time: UK datetime

        Returns:
            UTC datetime
        """
        if uk_time.tzinfo is None:
            uk_time = self.uk_tz.localize(uk_time)

        return uk_time.astimezone(pytz.utc)

    def format_uk_time(self, utc_time: Optional[datetime] = None) -> str:
        """
        Format time as UK time string.

        Args:
            utc_time: UTC datetime (default: now)

        Returns:
            Formatted string (e.g., "14:30 GMT" or "15:30 BST")
        """
        uk_time = self.get_uk_time(utc_time)
        tz_name = uk_time.strftime('%Z')  # GMT or BST
        return f"{uk_time.strftime('%H:%M')} {tz_name}"

    def get_scheduling_info(self) -> dict:
        """
        Get current scheduling information.

        Returns:
            Dict with scheduling details
        """
        now_utc = datetime.now(pytz.utc)
        now_uk = self.get_uk_time(now_utc)

        is_active = self.is_active_hours(now_utc)

        info = {
            'current_time_uk': self.format_uk_time(now_utc),
            'current_time_utc': now_utc.strftime('%H:%M UTC'),
            'is_active_hours': is_active,
            'active_window': f"{self.active_start.strftime('%H:%M')}-{self.active_end.strftime('%H:%M')} UK time",
            'timezone': self.schedule_config.timezone
        }

        if not is_active:
            time_until = self.get_time_until_active(now_utc)
            if time_until:
                hours = int(time_until.total_seconds() // 3600)
                minutes = int((time_until.total_seconds() % 3600) // 60)
                info['time_until_active'] = f"{hours}h {minutes}m"

        return info


# Global controller instance
_timing_controller: Optional[TimingController] = None


def get_timing_controller() -> TimingController:
    """Get global timing controller instance (singleton)"""
    global _timing_controller

    if _timing_controller is None:
        _timing_controller = TimingController()

    return _timing_controller


# Convenience functions
def is_active_hours() -> bool:
    """Check if currently within active hours"""
    controller = get_timing_controller()
    return controller.is_active_hours()


def get_random_delay(min_ms: int = 1000, max_ms: int = 3000) -> float:
    """Get random delay in seconds"""
    controller = get_timing_controller()
    return controller.get_random_delay(min_ms, max_ms)


if __name__ == "__main__":
    # Test timing controller
    import sys

    logging.basicConfig(level=logging.INFO)

    try:
        controller = get_timing_controller()

        logger.info("\n✓ Timing controller test:\n")

        # Get current scheduling info
        info = controller.get_scheduling_info()

        logger.info(f"Current time (UK): {info['current_time_uk']}")
        logger.info(f"Current time (UTC): {info['current_time_utc']}")
        logger.info(f"Active hours: {info['active_window']}")
        logger.info(f"Currently active: {info['is_active_hours']}")

        if 'time_until_active' in info:
            logger.info(f"Time until active: {info['time_until_active']}")

        # Test next active window
        next_start, next_end = controller.get_next_active_window()
        logger.info(f"\nNext active window:")
        logger.info(f"  Start: {controller.format_uk_time(next_start)}")
        logger.info(f"  End: {controller.format_uk_time(next_end)}")

        # Test random delays
        logger.info(f"\nRandom delays (human-like):")
        for i in range(3):
            delay = controller.get_random_delay()
            logger.info(f"  Delay {i+1}: {delay:.2f}s")

        # Test break logic
        logger.info(f"\nBreak logic:")
        for count in [1, 2, 3, 4, 5, 6]:
            should_break = controller.should_take_break(count)
            logger.info(f"  After {count} replies: {'Break' if should_break else 'Continue'}")

        logger.info("\n✓ All timing controller tests passed")

    except Exception as e:
        logger.error(f"✗ Timing controller test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
