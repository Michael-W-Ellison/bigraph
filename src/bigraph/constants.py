"""
Constants for the Bigraph Cryptography System
"""

# Generate all bigrams AA-ZZ
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
BIGRAMS = [f"{a}{b}" for a in LETTERS for b in LETTERS]  # 676 bigrams

# Rare bigrams used as space markers (one is chosen at random for each space)
SPACE_MARKERS = ['JQ', 'QG', 'QK', 'QY', 'QZ', 'WQ', 'WZ']

# Special characters that need symbols
SPECIAL_CHARS = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '=', '<', '>', '?']

# Mathematical operators that need symbols ('*' is already a special character)
MATH_OPERATORS = ['+', '-', '/']

# The 100 most common English words, with how often each is used (per million
# words, counted in public-domain books). Each word gets its own symbols.
COMMON_WORDS = [
    ('THE', 47911), ('AND', 30824), ('TO', 28777), ('OF', 26540), ('A', 19687),
    ('I', 15785), ('IN', 15504), ('IT', 13704), ('WAS', 12738), ('THAT', 12322),
    ('HE', 12095), ('HER', 10210), ('YOU', 10189), ('HIS', 9515), ('SHE', 8979),
    ('AS', 8703), ('FOR', 8682), ('NOT', 8676), ('BE', 8025), ('BUT', 7904),
    ('HAD', 7612), ('WITH', 7611), ('IS', 6666), ('AT', 6400), ('ALL', 5933),
    ('HAVE', 5626), ('HIM', 5180), ('SO', 5137), ('THIS', 4607), ('BY', 4549),
    ('ON', 4536), ('SAID', 4432), ('THEY', 4238), ('MY', 3958), ('VERY', 3799),
    ('FROM', 3771), ('NO', 3748), ('ME', 3574), ('WERE', 3573), ('WHICH', 3557),
    ('WOULD', 3397), ('ONE', 3360), ('WHAT', 3333), ('COULD', 3309), ('THERE', 3231),
    ('BEEN', 3036), ('THEM', 2966), ('WHEN', 2937), ('OR', 2859), ('THEIR', 2748),
    ('LITTLE', 2709), ('IF', 2706), ('DO', 2701), ('WILL', 2658), ('MORE', 2576),
    ('NOW', 2570), ('ARE', 2546), ('AN', 2481), ('WHO', 2447), ('YOUR', 2349),
    ('ANY', 2260), ('OUT', 2194), ('WE', 2050), ('MUST', 2043), ('SUCH', 2033),
    ('SOME', 1999), ('THEN', 1997), ('UP', 1992), ('THAN', 1987), ('MUCH', 1894),
    ('TIME', 1816), ('WELL', 1812), ('ONLY', 1805), ('DID', 1801), ('GOOD', 1801),
    ('KNOW', 1739), ('HOW', 1734), ('LIKE', 1688), ('AM', 1665), ('MAN', 1648),
    ('INTO', 1634), ('CAN', 1619), ('SEE', 1597), ('NEVER', 1589), ('ABOUT', 1588),
    ('SHOULD', 1571), ('EVERY', 1544), ('GREAT', 1526), ('OWN', 1449), ('OTHER', 1446),
    ('THINK', 1413), ('BEFORE', 1397), ('HAS', 1365), ('SAY', 1362), ('BEING', 1336),
    ('MIGHT', 1282), ('DOWN', 1280), ('THOUGH', 1265), ('THING', 1259),
    ('AFTER', 1258)
]

# Number of symbols shared among the common words, in proportion to their use
WORD_SYMBOL_BUDGET = 2000


def word_symbol_counts(budget: int = WORD_SYMBOL_BUDGET) -> dict:
    """
    Number of symbols for each common word

    Each word gets at least one symbol (when the budget allows), and the rest
    are shared in proportion to how often the word is used, so that each
    symbol is used about equally often.

    Args:
        budget: Total number of word symbols

    Returns:
        Dictionary mapping each word to its number of symbols
    """
    if budget <= 0:
        return {}
    words = COMMON_WORDS[:budget]
    total = sum(freq for _, freq in words)
    extra = budget - len(words)
    shares = {word: freq * extra / total for word, freq in words}
    counts = {word: 1 + int(share) for word, share in shares.items()}
    remaining = budget - sum(counts.values())
    by_remainder = sorted(words, key=lambda wf: shares[wf[0]] - int(shares[wf[0]]), reverse=True)
    for word, _ in by_remainder[:remaining]:
        counts[word] += 1
    return counts


# Number characters
DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

# Special marker for partial bigram usage
PARTIAL_MARKER = '|'

# Multiply/divide indicator
MULTIPLY_DIVIDE_MARKER = 'MULDIV'

# Total number of symbols needed
# 676 bigrams + 10 digits (positive) + 10 digits (negative) + 1 mul/div + 14 special chars
# + 3 math operators + 7 space markers, plus the common word symbols
BASE_SYMBOLS = (len(BIGRAMS) + len(DIGITS) * 2 + 1 + len(SPECIAL_CHARS) +
                len(MATH_OPERATORS) + len(SPACE_MARKERS))
TOTAL_SYMBOLS = BASE_SYMBOLS + WORD_SYMBOL_BUDGET
