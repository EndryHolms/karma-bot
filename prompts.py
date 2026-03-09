"""
This module generates system prompts for the Gemini model based on the user's selected language.
"""
from lexicon import get_text


def get_karma_system_prompt(lang: str) -> str:
    """Generates the system prompt for Karma tarot readings in the specified language."""
    return get_text(lang, "karma_system_prompt")


def get_universe_advice_system_prompt(lang: str) -> str:
    """Generates the system prompt for Universe Advice in the specified language."""
    return get_text(lang, "universe_advice_system_prompt")
