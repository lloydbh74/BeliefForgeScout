"""
Voice validation system for enforcing Belief Forge brand guidelines.

Validates replies against strict British English voice rules:
- Character limits
- British spellings
- No exclamation marks
- No corporate jargon
- Gentle, authentic tone
"""

import re
import logging
from typing import Dict, Any, List, Tuple

from src.config.loader import get_config

logger = logging.getLogger(__name__)


class VoiceValidator:
    """Validates reply text against voice guidelines"""

    # American spellings to detect
    AMERICAN_SPELLINGS = [
        (r'\b(\w+)ize\b', 'ise'),  # realize -> realise
        (r'\b(\w+)ization\b', 'isation'),  # realization -> realisation
        (r'\bcolor\b', 'colour'),
        (r'\bfavor\b', 'favour'),
        (r'\bhonor\b', 'honour'),
        (r'\blabor\b', 'labour'),
        (r'\bcenter\b', 'centre'),
        (r'\bfiber\b', 'fibre'),
        (r'\bmeter\b', 'metre'),
        (r'\btheater\b', 'theatre'),
        (r'\bdefense\b', 'defence'),
        (r'\boffense\b', 'offence'),
        (r'\blicense\b', 'licence'),  # (noun form)
        (r'\bpractice\b', 'practise'),  # (verb form)
        (r'\b(while|among)\b', 'whilst/amongst')
    ]

    # Corporate jargon patterns
    CORPORATE_JARGON = [
        'synergy', 'synergies', 'leverage', 'leveraging',
        'disrupt', 'disruptive', 'disruption',
        'game-changer', 'game changer',
        'crushing it', 'crush it',
        'ninja', 'guru', 'rockstar',
        'hustle', 'hustling', 'grind', 'grinding',
        'move the needle', 'circle back',
        'low-hanging fruit', 'think outside the box',
        'paradigm shift', 'best in class',
        'cutting edge', 'bleeding edge',
        'growth hack', 'growth hacking'
    ]

    # Salesy language patterns
    SALESY_LANGUAGE = [
        r'\bbuy now\b',
        r'\blimited time\b',
        r'\bDM me\b',
        r'\bcheck out my\b',
        r'\blink in bio\b',
        r'\bdiscount code\b',
        r'\bspecial offer\b',
        r'\bfree trial\b',
        r'\bsign up now\b'
    ]

    def __init__(self):
        """Initialize voice validator with configuration"""
        self.bot_config, _ = get_config()
        self.voice = self.bot_config.voice
        self.char_limits = self.voice.character_limits
        self.strict_mode = self.voice.validation['strict_mode']

    def validate(self, text: str, platform: str = None) -> Dict[str, Any]:
        """
        Validate text against all voice guidelines.

        Args:
            text: Reply text to validate
            platform: Platform name (e.g. 'reddit') - optional

        Returns:
            Dict with validation results:
            {
                'is_valid': bool,
                'score': float (0-100),
                'violations': List[str],
                'warnings': List[str],
                'character_count': int
            }
        """
        violations = []
        warnings = []
        
        # Determine limits based on platform
        is_reddit = platform == 'reddit' or (hasattr(platform, 'value') and platform.value == 'reddit')
        
        pref_max = self.char_limits.get('reddit_preferred_max', 1000) if is_reddit else self.char_limits['preferred_max']
        abs_max = self.char_limits.get('reddit_max', 5000) if is_reddit else self.char_limits['absolute_max']

        # Character limit check
        char_count = len(text)
        if char_count > abs_max:
            violations.append(f"Exceeds absolute max ({char_count} > {abs_max} chars)")
        elif char_count > pref_max:
            warnings.append(f"Exceeds preferred max ({char_count} > {pref_max} chars)")

        # Exclamation marks (STRICT VIOLATION)
        if '!' in text:
            violations.append("Contains exclamation mark(s)")

        # Check for hyphens used instead of commas (anti-pattern)
        # This is tricky - we want to flag excessive hyphenation in running text
        hyphen_count = text.count(' - ')
        if hyphen_count > 1:
            warnings.append(f"Multiple hyphens used ({hyphen_count})")

        # American spellings
        american_found = self._check_american_spellings(text)
        if american_found:
            violations.extend([f"American spelling: '{word}'" for word in american_found])

        # Corporate jargon
        jargon_found = self._check_corporate_jargon(text)
        if jargon_found:
            violations.extend([f"Corporate jargon: '{word}'" for word in jargon_found])

        # Salesy language
        salesy_found = self._check_salesy_language(text)
        if salesy_found:
            violations.extend([f"Salesy language: '{pattern}'" for pattern in salesy_found])

        # Emoji check (max 1)
        emoji_count = self._count_emoji(text)
        if emoji_count > 1:
            warnings.append(f"Too many emoji ({emoji_count})")

        # Hashtag check (max 1, prefer 0)
        hashtag_count = text.count('#')
        if hashtag_count > 1:
            violations.append(f"Too many hashtags ({hashtag_count})")
        elif hashtag_count == 1:
            warnings.append("Contains 1 hashtag (prefer 0)")

        # Calculate score
        # Start at 100, deduct for violations and warnings
        score = 100
        score -= len(violations) * 15  # Major deduction for violations
        score -= len(warnings) * 5     # Minor deduction for warnings
        score = max(0, score)

        # Determine if valid
        is_valid = len(violations) == 0 if self.strict_mode else score >= 60

        return {
            'is_valid': is_valid,
            'score': round(score, 2),
            'violations': violations,
            'warnings': warnings,
            'character_count': char_count
        }

    def _check_american_spellings(self, text: str) -> List[str]:
        """Check for American spellings"""
        found = []
        text_lower = text.lower()

        for pattern, british_alternative in self.AMERICAN_SPELLINGS:
            # Use re.finditer to get full matches
            for match in re.finditer(pattern, text_lower, re.IGNORECASE):
                # Get the full matched text (not the capture group)
                found.append(match.group(0))

        return list(set(found))  # Remove duplicates

    def _check_corporate_jargon(self, text: str) -> List[str]:
        """Check for corporate jargon"""
        text_lower = text.lower()
        found = [jargon for jargon in self.CORPORATE_JARGON if jargon in text_lower]
        return list(set(found))

    def _check_salesy_language(self, text: str) -> List[str]:
        """Check for salesy language patterns"""
        found = []
        for pattern in self.SALESY_LANGUAGE:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(pattern)
        return found

    def _count_emoji(self, text: str) -> int:
        """Count emoji in text (simplified)"""
        # Simple heuristic: count common emoji patterns
        # More sophisticated emoji detection would use emoji library
        emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]'
        return len(re.findall(emoji_pattern, text))

    def suggest_improvements(self, text: str, validation: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements based on violations.

        Args:
            text: Original text
            validation: Validation results

        Returns:
            List of improvement suggestions
        """
        suggestions = []

        violations = validation['violations']
        char_count = validation['character_count']

        # Character count suggestions
        if char_count > self.char_limits['absolute_max']:
            suggestions.append(f"Reduce by {char_count - self.char_limits['absolute_max']} characters")
        elif char_count > self.char_limits['preferred_max']:
            suggestions.append(f"Consider reducing by {char_count - self.char_limits['preferred_max']} characters")

        # Exclamation mark
        if '!' in text:
            suggestions.append("Remove exclamation marks (British voice guideline)")

        # American spellings
        for violation in violations:
            if 'American spelling' in violation:
                word = violation.split("'")[1]
                # Suggest British alternative
                for pattern, british_form in self.AMERICAN_SPELLINGS:
                    if re.search(pattern, word, re.IGNORECASE):
                        suggestions.append(f"Replace '{word}' with British spelling: '{british_form}'")
                        break

        # Corporate jargon
        jargon_violations = [v for v in violations if 'Corporate jargon' in v]
        if jargon_violations:
            suggestions.append("Remove corporate jargon - use authentic, conversational language")

        # Salesy language
        salesy_violations = [v for v in violations if 'Salesy language' in v]
        if salesy_violations:
            suggestions.append("Remove promotional language - be helpful, not salesy")

        return suggestions


# Convenience functions
def validate_reply(text: str) -> Dict[str, Any]:
    """
    Validate reply text against voice guidelines.

    Args:
        text: Reply text

    Returns:
        Validation results dictionary
    """
    validator = VoiceValidator()
    return validator.validate(text)


def is_valid_reply(text: str) -> bool:
    """
    Check if reply is valid.

    Args:
        text: Reply text

    Returns:
        True if valid, False otherwise
    """
    validation = validate_reply(text)
    return validation['is_valid']


if __name__ == "__main__":
    # Test voice validator
    import sys

    logging.basicConfig(level=logging.INFO)

    # Test cases
    test_cases = [
        {
            'text': 'I realise this is quite challenging, whilst many struggle with it.',
            'expected': 'valid'
        },
        {
            'text': 'This is amazing! You should totally do this!',
            'expected': 'invalid (exclamation marks)'
        },
        {
            'text': 'I realize this is challenging while many struggle with it.',
            'expected': 'invalid (American spellings)'
        },
        {
            'text': 'We need to leverage synergy to disrupt the market and crush it!',
            'expected': 'invalid (jargon + exclamation)'
        },
        {
            'text': 'I understand the challenge. Perhaps consider focusing on what truly matters to you?',
            'expected': 'valid'
        },
        {
            'text': 'Buy now! Limited time offer! DM me for discount code!',
            'expected': 'invalid (salesy + exclamations)'
        }
    ]

    try:
        validator = VoiceValidator()

        logger.info("\n✓ Voice validator test results:\n")

        for i, test in enumerate(test_cases, 1):
            text = test['text']
            expected = test['expected']

            validation = validator.validate(text)

            logger.info(f"Test {i}: {expected}")
            logger.info(f"  Text: {text}")
            logger.info(f"  Valid: {validation['is_valid']}")
            logger.info(f"  Score: {validation['score']}")
            logger.info(f"  Character count: {validation['character_count']}")

            if validation['violations']:
                logger.info(f"  Violations:")
                for violation in validation['violations']:
                    logger.info(f"    - {violation}")

            if validation['warnings']:
                logger.info(f"  Warnings:")
                for warning in validation['warnings']:
                    logger.info(f"    - {warning}")

            # Show suggestions
            if not validation['is_valid']:
                suggestions = validator.suggest_improvements(text, validation)
                if suggestions:
                    logger.info(f"  Suggestions:")
                    for suggestion in suggestions:
                        logger.info(f"    - {suggestion}")

            logger.info("")

        logger.info("✓ All voice validator tests completed")

    except Exception as e:
        logger.error(f"✗ Voice validator test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
