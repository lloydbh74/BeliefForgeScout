"""
Unit tests for Voice Validator.

CRITICAL: These tests ensure brand safety by validating British English
voice guidelines. Any failures here represent potential brand damage.
"""

import pytest
from src.voice.validator import VoiceValidator, validate_reply, is_valid_reply


class TestVoiceValidatorCharacterLimits:
    """Test character limit validation"""

    def test_reply_under_preferred_max(self):
        """Test valid reply under 100 characters"""
        validator = VoiceValidator()
        text = "I understand that feeling. What aspect troubles you most?"

        result = validator.validate(text)

        assert result['is_valid'] is True
        assert result['character_count'] < 100
        assert len(result['violations']) == 0

    def test_reply_between_preferred_and_absolute(self):
        """Test reply between 100-280 characters (warning, but valid)"""
        validator = VoiceValidator()
        text = "I completely understand what you're going through, and I think it's quite normal to feel this way when building something new."

        result = validator.validate(text)

        assert result['is_valid'] is True
        assert 100 < result['character_count'] <= 280
        assert any('preferred max' in w for w in result['warnings'])

    def test_reply_exceeds_absolute_max(self):
        """Test reply exceeding 280 characters (violation)"""
        validator = VoiceValidator()
        text = "I completely understand what you're going through because I've been there myself many times before, and I want to share with you that it's completely normal to feel this way when you're building something new and putting yourself out there for everyone to see and judge, which can be quite overwhelming and scary."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert result['character_count'] > 280
        assert any('absolute max' in v for v in result['violations'])


class TestVoiceValidatorExclamationMarks:
    """Test exclamation mark detection (CRITICAL)"""

    def test_no_exclamation_marks(self):
        """Test valid reply without exclamation marks"""
        validator = VoiceValidator()
        text = "I understand that feeling. Perhaps focus on what matters most?"

        result = validator.validate(text)

        assert result['is_valid'] is True
        assert '!' not in text
        assert len(result['violations']) == 0

    def test_single_exclamation_mark(self):
        """Test invalid reply with single exclamation mark"""
        validator = VoiceValidator()
        text = "You can do this!"

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('exclamation' in v.lower() for v in result['violations'])

    def test_multiple_exclamation_marks(self):
        """Test invalid reply with multiple exclamation marks"""
        validator = VoiceValidator()
        text = "You're amazing! Keep going! Don't give up!"

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('exclamation' in v.lower() for v in result['violations'])

    def test_exclamation_in_middle(self):
        """Test exclamation mark in middle of text"""
        validator = VoiceValidator()
        text = "I understand! Perhaps we can explore this together."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('exclamation' in v.lower() for v in result['violations'])


class TestVoiceValidatorBritishSpellings:
    """Test British English spelling detection (CRITICAL)"""

    def test_british_spellings_valid(self):
        """Test valid British spellings"""
        validator = VoiceValidator()
        text = "I realise this is quite colourful, whilst we organise amongst ourselves."

        result = validator.validate(text)

        assert result['is_valid'] is True
        assert len(result['violations']) == 0

    def test_american_spelling_ize(self):
        """Test American -ize ending (violation)"""
        validator = VoiceValidator()
        text = "I realize this is important."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('realize' in v.lower() for v in result['violations'])

    def test_american_spelling_or(self):
        """Test American -or endings (violation)"""
        validator = VoiceValidator()
        text = "I favor this approach to give it more color."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('color' in v.lower() or 'favor' in v.lower() for v in result['violations'])

    def test_american_spelling_while(self):
        """Test 'while' instead of 'whilst' (violation)"""
        validator = VoiceValidator()
        text = "I understand this challenge while working on it."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('while' in v.lower() for v in result['violations'])

    def test_american_spelling_among(self):
        """Test 'among' instead of 'amongst' (violation)"""
        validator = VoiceValidator()
        text = "This is common among founders."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('among' in v.lower() for v in result['violations'])

    def test_mixed_spellings(self):
        """Test mix of British and American (violation)"""
        validator = VoiceValidator()
        text = "I realise the color is wrong while organizing."

        result = validator.validate(text)

        assert result['is_valid'] is False
        # Should detect American spellings
        assert len(result['violations']) > 0


class TestVoiceValidatorCorporateJargon:
    """Test corporate jargon detection"""

    def test_no_jargon(self):
        """Test valid reply without jargon"""
        validator = VoiceValidator()
        text = "I understand your challenge. Perhaps focus on what truly matters?"

        result = validator.validate(text)

        assert result['is_valid'] is True
        assert len(result['violations']) == 0

    def test_synergy_jargon(self):
        """Test 'synergy' jargon (violation)"""
        validator = VoiceValidator()
        text = "You need to create synergy between teams."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('synergy' in v.lower() for v in result['violations'])

    def test_leverage_jargon(self):
        """Test 'leverage' jargon (violation)"""
        validator = VoiceValidator()
        text = "Try leveraging your strengths."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('leverag' in v.lower() for v in result['violations'])

    def test_disrupt_jargon(self):
        """Test 'disrupt' jargon (violation)"""
        validator = VoiceValidator()
        text = "You can disrupt the market with this."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('disrupt' in v.lower() for v in result['violations'])

    def test_game_changer_jargon(self):
        """Test 'game-changer' jargon (violation)"""
        validator = VoiceValidator()
        text = "This could be a real game-changer for you."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('game' in v.lower() for v in result['violations'])

    def test_crushing_it_jargon(self):
        """Test 'crushing it' jargon (violation)"""
        validator = VoiceValidator()
        text = "You're crushing it out there."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('crushing' in v.lower() for v in result['violations'])

    def test_multiple_jargon_terms(self):
        """Test multiple jargon terms (multiple violations)"""
        validator = VoiceValidator()
        text = "Leverage synergy to disrupt the market."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert len(result['violations']) >= 3  # Should catch all three


class TestVoiceValidatorSalesyLanguage:
    """Test salesy language detection"""

    def test_no_salesy_language(self):
        """Test valid reply without salesy language"""
        validator = VoiceValidator()
        text = "I understand your challenge. Perhaps we can explore this together?"

        result = validator.validate(text)

        assert result['is_valid'] is True
        assert len(result['violations']) == 0

    def test_buy_now(self):
        """Test 'buy now' pattern (violation)"""
        validator = VoiceValidator()
        text = "You should buy now before it's too late."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('salesy' in v.lower() or 'buy now' in v.lower() for v in result['violations'])

    def test_limited_time(self):
        """Test 'limited time' pattern (violation)"""
        validator = VoiceValidator()
        text = "This is a limited time opportunity."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('salesy' in v.lower() or 'limited time' in v.lower() for v in result['violations'])

    def test_dm_me(self):
        """Test 'DM me' pattern (violation)"""
        validator = VoiceValidator()
        text = "DM me for more details."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('salesy' in v.lower() or 'dm' in v.lower() for v in result['violations'])

    def test_link_in_bio(self):
        """Test 'link in bio' pattern (violation)"""
        validator = VoiceValidator()
        text = "Check the link in bio for more information."

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('salesy' in v.lower() or 'link in bio' in v.lower() for v in result['violations'])


class TestVoiceValidatorEmojiAndHashtags:
    """Test emoji and hashtag detection"""

    def test_no_emoji_or_hashtags(self):
        """Test valid reply without emoji or hashtags"""
        validator = VoiceValidator()
        text = "I understand your challenge quite well."

        result = validator.validate(text)

        assert result['is_valid'] is True
        assert len(result['violations']) == 0
        assert len(result['warnings']) == 0

    def test_single_hashtag(self):
        """Test single hashtag (warning, but acceptable)"""
        validator = VoiceValidator()
        text = "I understand your challenge. #BuildInPublic"

        result = validator.validate(text)

        # Single hashtag is a warning, not a violation
        assert any('hashtag' in w.lower() for w in result['warnings'])

    def test_multiple_hashtags(self):
        """Test multiple hashtags (violation)"""
        validator = VoiceValidator()
        text = "Great insight! #BuildInPublic #Founders #StartupLife"

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert any('hashtag' in v.lower() for v in result['violations'])


class TestVoiceValidatorScoring:
    """Test scoring algorithm"""

    def test_perfect_score(self):
        """Test perfect reply gets 100 score"""
        validator = VoiceValidator()
        text = "I understand that feeling. What aspect troubles you most?"

        result = validator.validate(text)

        assert result['score'] == 100
        assert result['is_valid'] is True

    def test_score_with_warnings(self):
        """Test score deduction for warnings"""
        validator = VoiceValidator()
        text = "I understand your challenge quite well, and I think it's normal. #BuildInPublic"

        result = validator.validate(text)

        # Score should be reduced but still valid
        assert result['score'] < 100
        assert result['score'] >= 90  # Minor deduction for warnings
        assert len(result['warnings']) > 0

    def test_score_with_violations(self):
        """Test major score deduction for violations"""
        validator = VoiceValidator()
        text = "I realize this is amazing!"  # American spelling + exclamation

        result = validator.validate(text)

        assert result['is_valid'] is False
        assert result['score'] < 80  # Major deductions
        assert len(result['violations']) >= 2


class TestVoiceValidatorImprovementSuggestions:
    """Test improvement suggestion generation"""

    def test_suggestions_for_char_limit(self):
        """Test suggestions for character limit violations"""
        validator = VoiceValidator()
        text = "I completely understand what you're going through because I've been there myself many times before, and I want to share with you that it's completely normal to feel this way when you're building something new and putting yourself out there for everyone to see and judge, which can be quite overwhelming and scary at times."

        validation = validator.validate(text)
        suggestions = validator.suggest_improvements(text, validation)

        assert len(suggestions) > 0
        assert any('reduce' in s.lower() for s in suggestions)

    def test_suggestions_for_exclamation(self):
        """Test suggestions for exclamation marks"""
        validator = VoiceValidator()
        text = "You can do this!"

        validation = validator.validate(text)
        suggestions = validator.suggest_improvements(text, validation)

        assert any('exclamation' in s.lower() for s in suggestions)

    def test_suggestions_for_jargon(self):
        """Test suggestions for corporate jargon"""
        validator = VoiceValidator()
        text = "You need to leverage synergy."

        validation = validator.validate(text)
        suggestions = validator.suggest_improvements(text, validation)

        assert any('jargon' in s.lower() for s in suggestions)


class TestVoiceValidatorConvenienceFunctions:
    """Test convenience functions"""

    def test_validate_reply_function(self):
        """Test validate_reply convenience function"""
        text = "I understand that feeling. Perhaps focus on what matters?"

        result = validate_reply(text)

        assert result['is_valid'] is True
        assert 'score' in result
        assert 'violations' in result

    def test_is_valid_reply_function(self):
        """Test is_valid_reply convenience function"""
        valid_text = "I understand that feeling. Perhaps focus on what matters?"
        invalid_text = "This is amazing!"

        assert is_valid_reply(valid_text) is True
        assert is_valid_reply(invalid_text) is False


# Parametrized tests for comprehensive coverage
@pytest.mark.parametrize("text,expected_valid,description", [
    (
        "I realise this is quite challenging.",
        True,
        "Valid British English with qualifier"
    ),
    (
        "This is amazing!",
        False,
        "Exclamation mark violation"
    ),
    (
        "I realize this works.",
        False,
        "American spelling violation"
    ),
    (
        "We need to leverage synergy.",
        False,
        "Corporate jargon violation"
    ),
    (
        "Buy now for limited time offer!",
        False,
        "Salesy language + exclamation"
    ),
    (
        "I understand your challenge. Perhaps consider what truly matters to you?",
        True,
        "Valid with gentle qualifier and question"
    ),
    (
        "Check out my link in bio for discount code!",
        False,
        "Multiple violations: salesy + exclamation"
    ),
])
def test_voice_validation_parametrized(text, expected_valid, description):
    """Parametrized test covering multiple voice validation scenarios"""
    validator = VoiceValidator()
    result = validator.validate(text)

    assert result['is_valid'] == expected_valid, f"Failed: {description}"


# Mark critical tests
pytestmark = pytest.mark.critical
