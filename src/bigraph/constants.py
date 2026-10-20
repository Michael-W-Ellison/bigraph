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


def proportional_counts(items: list, budget: int) -> dict:
    """
    Share a number of symbols among items in proportion to their frequency

    Each item gets at least one symbol (when the budget allows), and the rest
    are shared in proportion to how often the item is used, so that each
    symbol is used about equally often.

    Args:
        items: List of (item, frequency), most frequent first
        budget: Total number of symbols

    Returns:
        Dictionary mapping each item to its number of symbols
    """
    if budget <= 0:
        return {}
    items = items[:budget]
    total = sum(freq for _, freq in items)
    extra = budget - len(items)
    shares = {item: freq * extra / total for item, freq in items}
    counts = {item: 1 + int(share) for item, share in shares.items()}
    remaining = budget - sum(counts.values())
    by_remainder = sorted(items, key=lambda i: shares[i[0]] - int(shares[i[0]]), reverse=True)
    for item, _ in by_remainder[:remaining]:
        counts[item] += 1
    return counts


def word_symbol_counts(budget: int = WORD_SYMBOL_BUDGET) -> dict:
    """
    Number of symbols for each common word

    Args:
        budget: Total number of word symbols

    Returns:
        Dictionary mapping each word to its number of symbols
    """
    return proportional_counts(COMMON_WORDS, budget)


# The 200 most frequent bigrams in spelled words (words that are not common
# words), as the encoder pairs their letters, per million bigrams. These
# bigrams get extra symbols.
COMMON_BIGRAMS = [
    ('IN', 26576), ('ER', 20080), ('ST', 19031), ('RE', 18190), ('ED', 17752),
    ('TH', 14190), ('EN', 13159), ('NG', 13099), ('CO', 12778), ('TE', 12498),
    ('LE', 12402), ('SE', 11957), ('ME', 11911), ('AR', 11887), ('MA', 11308),
    ('AN', 11213), ('DE', 11027), ('ES', 10899), ('ON', 10556), ('NE', 10350),
    ('HE', 10208), ('AL', 9770), ('NT', 9214), ('ND', 8889), ('LL', 8316),
    ('SI', 8194), ('TI', 7747), ('OU', 7687), ('CA', 7533), ('PE', 7409), ('BE', 7396),
    ('EL', 7281), ('UN', 7259), ('HA', 7257), ('SH', 7176), ('CE', 7094), ('LI', 7048),
    ('AT', 6983), ('VE', 6855), ('LO', 6737), ('WH', 6596), ('EA', 6542), ('IT', 6398),
    ('MO', 6322), ('CH', 6315), ('PR', 6211), ('LY', 6207), ('RI', 5929), ('SS', 5884),
    ('DI', 5849), ('WA', 5833), ('RS', 5831), ('LA', 5817), ('OR', 5799), ('RT', 5744),
    ('SU', 5628), ('MI', 5540), ('GH', 5500), ('HO', 5449), ('US', 5439), ('IL', 5384),
    ('TO', 5335), ('TA', 5274), ('SA', 5271), ('SO', 5164), ('RA', 5135), ('PA', 5133),
    ('IE', 5045), ('FA', 5034), ('FE', 4907), ('RO', 4879), ('AI', 4802), ('GE', 4650),
    ('FI', 4562), ('FO', 4411), ('KE', 4408), ('WO', 4351), ('IO', 4336), ('SP', 4322),
    ('AD', 4306), ('AC', 4247), ('UR', 4132), ('AS', 4017), ('BO', 4003), ('WI', 3995),
    ('PL', 3964), ('IC', 3946), ('MR', 3873), ('RD', 3842), ('EV', 3769), ('NS', 3769),
    ('EM', 3744), ('EE', 3738), ('OW', 3710), ('PO', 3699), ('TR', 3685), ('WE', 3537),
    ('DA', 3526), ('DO', 3516), ('QU', 3476), ('HI', 3441), ('RR', 3388), ('AG', 3376),
    ('VI', 3329), ('NC', 3300), ('OT', 3293), ('ET', 3171), ('GR', 3142), ('GO', 3127),
    ('TT', 3104), ('BL', 3100), ('NO', 3096), ('OK', 3066), ('EX', 3042), ('BR', 2961),
    ('TU', 2909), ('OS', 2782), ('CK', 2782), ('AB', 2776), ('RN', 2750), ('CR', 2740),
    ('IS', 2734), ('BA', 2701), ('OP', 2697), ('CI', 2588), ('YE', 2560), ('FR', 2499),
    ('OL', 2497), ('GA', 2487), ('AP', 2426), ('MP', 2425), ('EC', 2409), ('NA', 2353),
    ('ID', 2344), ('GI', 2333), ('CT', 2284), ('UL', 2214), ('IM', 2210), ('KI', 2201),
    ('CL', 2109), ('AY', 2109), ('OV', 2108), ('BU', 2087), ('IR', 2074), ('DR', 2070),
    ('SC', 2042), ('NI', 2039), ('OD', 2025), ('PP', 2022), ('NN', 1980), ('OM', 1910),
    ('UP', 1900), ('LD', 1881), ('KN', 1871), ('PI', 1859), ('TY', 1839), ('TW', 1814),
    ('OF', 1811), ('IG', 1774), ('RM', 1760), ('AM', 1751), ('TS', 1729), ('PU', 1681),
    ('HT', 1637), ('JU', 1592), ('FU', 1591), ('PT', 1566), ('UG', 1561), ('CU', 1561),
    ('LF', 1552), ('RL', 1545), ('YS', 1528), ('OO', 1500), ('DY', 1493), ('AW', 1468),
    ('UE', 1454), ('FL', 1451), ('GS', 1411), ('RU', 1376), ('AV', 1370), ('OB', 1360),
    ('RK', 1332), ('YO', 1329), ('HU', 1324), ('JO', 1323), ('SM', 1296), ('TL', 1295),
    ('VA', 1290), ('GL', 1276), ('RV', 1271), ('EW', 1270), ('RY', 1267), ('IV', 1265),
    ('EY', 1265), ('AF', 1264), ('BI', 1252), ('LU', 1220), ('VO', 1205), ('LK', 1199),
    ('EP', 1181)
]

# Number of extra symbols shared among the common bigrams, in proportion to
# their use
BIGRAM_SYMBOL_BUDGET = 1500


def bigram_symbol_counts(budget: int = BIGRAM_SYMBOL_BUDGET) -> dict:
    """
    Number of extra symbols for each common bigram

    Every bigram has one symbol; this gives the extra ones. The extra symbols
    are shared so that each of a common bigram's symbols, including its
    first, is used about equally often.

    Args:
        budget: Total number of extra bigram symbols

    Returns:
        Dictionary mapping each common bigram to its number of extra symbols
    """
    if budget <= 0:
        return {}
    counts = proportional_counts(COMMON_BIGRAMS, budget + len(COMMON_BIGRAMS))
    return {bigram: count - 1 for bigram, count in counts.items() if count > 1}


# Number characters
DIGITS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

# Security version of keys made by this release. Raise it when a security
# update requires new keys: keys made under a lower version can then only
# decode, and users are asked to replace them.
#   0: keys from before secure key generation, or stored without a password
#   1: secure random keys with message check secrets, in encrypted files
SECURITY_VERSION = 1

# A key is replaced automatically once it has written this many words, or is
# this many days old. The attacks in cryptanalysis/ read most of a message at
# about 6,400 words written with one key plus a few hundred known words, and
# none succeeded from a cold start up to 25,600 words.
KEY_WORD_LIMIT = 2000
KEY_MAX_AGE_DAYS = 30

# Days a message is kept before it is deleted, unless its sender sets another
DEFAULT_RETENTION_DAYS = 30

# Special marker for partial bigram usage
PARTIAL_MARKER = '|'

# Multiply/divide indicator
MULTIPLY_DIVIDE_MARKER = 'MULDIV'

# Total number of symbols needed
# 676 bigrams + 10 digits (positive) + 10 digits (negative) + 1 mul/div + 14 special chars
# + 3 math operators + 7 space markers, plus the common word and extra bigram symbols
BASE_SYMBOLS = (len(BIGRAMS) + len(DIGITS) * 2 + 1 + len(SPECIAL_CHARS) +
                len(MATH_OPERATORS) + len(SPACE_MARKERS))
TOTAL_SYMBOLS = BASE_SYMBOLS + WORD_SYMBOL_BUDGET + BIGRAM_SYMBOL_BUDGET
