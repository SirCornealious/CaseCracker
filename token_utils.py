# token_utils.py 
# Created by SuperGrok and Sir_Cornealious on X

import logging

# Configure logger
logger = logging.getLogger(__name__)

# Maximum token limit with a 10% safety margin (131072 * 0.9)
MAX_TOKENS = 120000

def estimate_tokens(text: str) -> int:
    """
    Estimates the number of tokens in a text string using a word-based heuristic.
    Based on xAI's tokenizer: 445 chars = 100 tokens (~4.45 chars/token).
    Uses 1.33 tokens per word (assuming ~0.75 words/token) and adds 1% of chars for punctuation.
    """
    if not isinstance(text, str):
        logger.error(f"Invalid input for estimate_tokens: {type(text)}")
        raise ValueError("Text must be a string")
    
    # Count words (split on whitespace) and adjust for punctuation
    word_count = len(text.split())
    char_count = len(text)
    estimated_tokens = int(word_count * 1.33 + char_count / 100)
    logger.debug(f"Estimated tokens: {estimated_tokens} (words={word_count}, chars={char_count})")
    return max(1, estimated_tokens)  # Ensure at least 1 token

def truncate_text(text: str, max_tokens: int = MAX_TOKENS) -> str:
    """
    Truncates text to fit within the specified token limit.
    Returns the original text if within limit, otherwise truncates and logs the event.
    """
    if not isinstance(text, str):
        logger.error(f"Invalid input for truncate_text: {type(text)}")
        raise ValueError("Text must be a string")

    estimated_tokens = estimate_tokens(text)
    if estimated_tokens <= max_tokens:
        return text

    # Estimate truncation point: approximate chars per token (~4.45 from xAI data)
    max_chars = int(max_tokens * 4.45)
    truncated = text[:max_chars] + "... [Truncated due to token limit]"
    logger.warning(f"Text truncated: {estimated_tokens} tokens exceeded limit of {max_tokens}. Truncated to {max_chars} chars.")
    return truncated