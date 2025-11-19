"""
Constants for the Bigraph Cryptography System
"""

# Generate all bigrams AA-ZZ
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
BIGRAMS = [f"{a}{b}" for a in LETTERS for b in LETTERS]  # 676 bigrams

# Rare bigrams used as space markers (rotate through these)
SPACE_MARKERS = ['JQ', 'QG', 'QK', 'QY', 'QZ', 'WQ', 'WZ']

# Special characters that need symbols
SPECIAL_CHARS = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '=', '<', '>', '?']

# Number characters
DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

# Special marker for partial bigram usage
PARTIAL_MARKER = '|'

# Multiply/divide indicator
MULTIPLY_DIVIDE_MARKER = 'MULDIV'

# Default bigram for final letters not found in word
DEFAULT_FINAL_BIGRAM = 'SA'

# Total number of symbols needed
# 676 bigrams + 10 digits (positive) + 10 digits (negative) + 1 mul/div + 14 special chars + 7 space markers
TOTAL_SYMBOLS = len(BIGRAMS) + len(DIGITS) * 2 + 1 + len(SPECIAL_CHARS) + len(SPACE_MARKERS)
