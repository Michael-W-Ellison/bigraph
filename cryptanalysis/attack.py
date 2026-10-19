#!/usr/bin/env python3
"""
Ciphertext-only attack on the Bigraph Cryptography System

Measures how much encoded text an attacker needs to recover the plaintext
without the key. The attacker is assumed to know how the system works (the
code is public, including the list of common words and how many symbols each
has) and to have turned each drawn symbol into a label, which is
straightforward because the drawings are distinct shapes on a fixed grid.

The attacker sees, in order, a label for each symbol and the partial marker
("|"). It does not see the key or the symbol indices.

Attack steps:
1. Find the 7 space markers. A symbol after the partial marker is always the
   last letter of a word, so the symbol after it is always a space marker.
2. Split the text into words at the markers, and into sentences at two
   markers in a row. Each word is a list of symbols, and a word whose last
   symbol follows the partial marker has an odd number of letters.
3. Symbols that only ever appear as a whole one-symbol word may be common
   word symbols; all other symbols are bigrams. Common words are never
   spelled out, so spelled words are matched only against other words.
4. Start by matching the most frequent spelled cipher words to the most
   frequent English words of the same shape (symbol count and odd/even
   length), and spread the possible word symbols over the common words.
5. Search for the assignment of symbols to bigrams and common words that
   makes the text most English-like, using simulated annealing scored by a
   word-pair model (which word tends to follow which), with a letter trigram
   fallback for unknown words. Moves either change one symbol or set a whole
   cipher word to a dictionary word of the same shape.

The attack does not use the single-letter rotation order (|EA, |EB, ...) or
combine messages, so a stronger attacker could do better than this.

Usage:
    python3 cryptanalysis/attack.py [--words 25 50 ...] [--budgets 0 510] [--keys 3]
"""

import argparse
import difflib
import json
import math
import multiprocessing
import os
import random
import re
import sys
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bigraph.constants import BIGRAMS, LETTERS, COMMON_WORDS, word_symbol_counts  # noqa: E402
from bigraph.encoder import BigramEncoder  # noqa: E402
from bigraph.key_manager import KeyManager  # noqa: E402

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CORPUS_URL = ('https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/'
              'packages/corpora/gutenberg.zip')

# Public domain books from Project Gutenberg (via NLTK). The test book is by
# an author who is not in the training books.
TRAIN_BOOKS = ['austen-emma', 'austen-persuasion', 'austen-sense', 'bryant-stories',
               'burgess-busterbrown', 'carroll-alice', 'edgeworth-parents',
               'melville-moby_dick']
TEST_BOOK = 'chesterton-thursday'

PARTIAL = '|'
WORD_PREFIX = '#'


# ---------------------------------------------------------------------------
# Corpus
# ---------------------------------------------------------------------------

def load_books():
    """Download the corpus once and return {book name: text}"""
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, 'gutenberg.zip')
    if not os.path.exists(path):
        print(f"Downloading corpus to {path}")
        urllib.request.urlretrieve(CORPUS_URL, path)

    books = {}
    with zipfile.ZipFile(path) as z:
        for name in TRAIN_BOOKS + [TEST_BOOK]:
            books[name] = z.read(f'gutenberg/{name}.txt').decode('latin-1')
    return books


def clean_text(text):
    """Keep letters, spaces, and sentence ends, in upper case"""
    text = text.upper().replace('\n', ' ')
    text = re.sub(r'[!?]', '.', text)
    text = re.sub(r"[^A-Z. ]", ' ', text)
    text = re.sub(r'\.(\s*\.)+', '.', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def words_of(text):
    return re.findall(r'[A-Z]+', text)


def sentences_of(text):
    return [words for words in (words_of(s) for s in text.split('.')) if words]


# ---------------------------------------------------------------------------
# Language model
# ---------------------------------------------------------------------------

class LanguageModel:
    """Word-pair model, backed off to word frequency and letter trigrams"""

    PAIR_WEIGHT = 0.6

    def __init__(self, sentences):
        counts = Counter()
        pairs = Counter()
        starts = Counter()
        for sentence in sentences:
            counts.update(sentence)
            starts[sentence[0]] += 1
            pairs.update(zip(sentence, sentence[1:]))
        total = sum(counts.values())
        self.counts = counts
        self.word_logp = {w: math.log(c / total) for w, c in counts.items()}
        self.pairs = pairs
        self.starts = starts
        self.sentences = len(sentences)

        trigrams = Counter()
        bigrams = Counter()
        for w, c in counts.items():
            padded = f'^^{w}$'
            for i in range(len(padded) - 2):
                trigrams[padded[i:i + 3]] += c
                bigrams[padded[i:i + 2]] += c
        self.trigrams = trigrams
        self.bigrams = bigrams
        # Unknown words cost more than their letters alone suggest, so that
        # real words are preferred
        self.unknown_penalty = math.log(1 / total) - 2.0
        self.cache = {}
        self.pair_cache = {}

    def letter_logp(self, word):
        padded = f'^^{word}$'
        logp = 0.0
        for i in range(len(padded) - 2):
            tri = self.trigrams.get(padded[i:i + 3], 0)
            bi = self.bigrams.get(padded[i:i + 2], 0)
            logp += math.log((tri + 0.1) / (bi + 2.7))
        return logp

    def logp(self, word):
        cached = self.cache.get(word)
        if cached is not None:
            return cached
        if word in self.word_logp:
            value = self.word_logp[word]
        else:
            value = self.unknown_penalty + self.letter_logp(word)
        if len(self.cache) > 2_000_000:
            self.cache.clear()
        self.cache[word] = value
        return value

    def pair_logp(self, prev, word):
        """log P(word | previous word), with prev None at a sentence start"""
        key = (prev, word)
        cached = self.pair_cache.get(key)
        if cached is not None:
            return cached
        unigram = self.logp(word)
        if prev is None:
            seen, total = self.starts.get(word, 0), self.sentences
        else:
            seen, total = self.pairs.get(key, 0), self.counts.get(prev, 0)
        if seen:
            value = math.log(self.PAIR_WEIGHT * seen / total +
                             (1 - self.PAIR_WEIGHT) * math.exp(unigram))
        else:
            value = math.log(1 - self.PAIR_WEIGHT) + unigram
        if len(self.pair_cache) > 3_000_000:
            self.pair_cache.clear()
        self.pair_cache[key] = value
        return value


def aligned_bigram_counts(words):
    """Count bigrams as the encoder aligns them, with single letters as x+A"""
    counts = Counter()
    for w in words:
        for i in range(0, len(w) - 1, 2):
            counts[w[i:i + 2]] += 1
        if len(w) % 2:
            counts[w[-1] + 'A'] += 1
    return counts


# ---------------------------------------------------------------------------
# What the attacker sees
# ---------------------------------------------------------------------------

def encode_for_attacker(text, rng, budget):
    """
    Encode text with a new secure key and return the attacker's view

    Returns (tokens, truth) where tokens is a list of labels and PARTIAL, and
    truth maps each label to its real meaning (used only for scoring).
    """
    km = KeyManager(keys_directory=os.path.join(DATA_DIR, 'keys'))
    key = km.generate_key('attack', word_symbol_budget=budget)
    encoded = BigramEncoder(key).encode(text)

    # Give each drawing a random label, as an attacker transcribing them would
    indices = list(key['symbol_to_meaning'])
    labels = rng.sample(range(1_000_000), len(indices))
    label_of = dict(zip(indices, labels))

    tokens, truth = [], {}
    for value in encoded:
        if value < 0:
            index = -value - 1
            tokens.append(PARTIAL)
        else:
            index = value
        label = label_of[index]
        tokens.append(label)
        truth[label] = key['symbol_to_meaning'][index]
    return tokens, truth


def find_space_markers(tokens):
    """
    Find the 7 space markers

    The symbol after the partial marker is the last letter of a word, so the
    symbol after that is a space marker. If fewer than 7 are seen this way,
    the most frequent other symbols are added.
    """
    after_partial = Counter()
    for i, t in enumerate(tokens):
        if t == PARTIAL and i + 2 < len(tokens):
            after_partial[tokens[i + 2]] += 1
    markers = {s for s, _ in after_partial.most_common(7)}

    if len(markers) < 7:
        carriers = {tokens[i + 1] for i, t in enumerate(tokens) if t == PARTIAL}
        others = Counter(t for t in tokens if t != PARTIAL and t not in carriers and t not in markers)
        for s, _ in others.most_common(7 - len(markers)):
            markers.add(s)
    return markers


def split_words(tokens, markers):
    """
    Split tokens into words and sentences

    Returns a list of cipher words, with None between sentences. Each word is
    a tuple of (symbol, is_partial).
    """
    items, current = [], []
    partial = False
    previous_marker = False
    for t in tokens:
        if t == PARTIAL:
            partial = True
            continue
        if t in markers and not partial:
            if current:
                items.append(tuple(current))
                current = []
            elif previous_marker and items and items[-1] is not None:
                items.append(None)
            previous_marker = True
        else:
            current.append((t, partial))
            previous_marker = False
        partial = False
    if current:
        items.append(tuple(current))
    return items


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def word_shape(word):
    """(number of symbols, ends with a single letter) for a cipher word"""
    return len(word), word[-1][1]


def plain_shape(word):
    return (len(word) + 1) // 2, len(word) % 2 == 1


class Solver:
    """Simulated annealing over the assignment of symbols to bigrams and words"""

    def __init__(self, items, model, train_counts, budget, rng):
        self.model = model
        self.rng = rng
        self.t_start, self.t_end = 30.0, 0.5

        # Common words and how many symbols each has (public knowledge)
        self.capacity = {WORD_PREFIX + w: c for w, c in word_symbol_counts(budget).items()}
        self.common = {w[1:] for w in self.capacity}
        common_freq = dict(COMMON_WORDS)
        self.word_values = list(self.capacity)
        self.word_value_weights = [common_freq[w[1:]] / self.capacity[w] for w in self.word_values]

        # Sequence of words, as pairs of (previous word or None, word)
        self.pair_counts = Counter()
        self.word_counts = Counter()
        prev = None
        for item in items:
            if item is None:
                prev = None
                continue
            self.pair_counts[(prev, item)] += 1
            self.word_counts[item] += 1
            prev = item
        self.distinct = list(self.word_counts)
        self.pairs_with = defaultdict(set)
        for pair in self.pair_counts:
            for w in pair:
                if w is not None:
                    self.pairs_with[w].add(pair)

        self.words_with = defaultdict(set)
        self.symbol_counts = Counter()
        inside_words = set()
        for w in self.distinct:
            for s, partial in w:
                self.words_with[s].add(w)
                self.symbol_counts[s] += self.word_counts[w]
                if partial or len(w) > 1:
                    inside_words.add(s)
        self.symbols = [s for s, _ in self.symbol_counts.most_common()]
        self.symbol_weights = [math.sqrt(self.symbol_counts[s]) for s in self.symbols]
        self.standalone = {s for s in self.symbols if s not in inside_words} if budget else set()
        self.word_weights = [math.sqrt(self.word_counts[w]) for w in self.distinct]

        # Dictionary words for spelled cipher words, grouped by shape
        self.candidates = defaultdict(list)
        for word, count in train_counts.most_common(30000):
            if word not in self.common:
                self.candidates[plain_shape(word)].append((word, count))
        self.candidate_weights = {
            shape: [math.sqrt(c) for _, c in words[:3000]]
            for shape, words in self.candidates.items()
        }

        spelled = [w for w in train_counts.elements() if w not in self.common]
        bigram_freq = aligned_bigram_counts(spelled)
        self.bigram_weights = [bigram_freq.get(b, 0) + 1 for b in BIGRAMS]
        self.ranked_bigrams = [b for b, _ in bigram_freq.most_common()]
        self.ranked_bigrams += [b for b in BIGRAMS if b not in bigram_freq]

    # -- state ------------------------------------------------------------

    def add(self, s, v):
        self.value[s] = v
        if v[0] == WORD_PREFIX:
            self.holders[v].add(s)
        else:
            self.owner[v] = s

    def remove(self, s):
        v = self.value.pop(s)
        if v[0] == WORD_PREFIX:
            self.holders[v].discard(s)
        elif self.owner.get(v) == s:
            del self.owner[v]

    def apply(self, move):
        old = {s: self.value[s] for s in move}
        for s in move:
            self.remove(s)
        for s, v in move.items():
            self.add(s, v)
        return old

    def valid(self, move):
        used = set()
        for s, v in move.items():
            if v[0] == WORD_PREFIX:
                if s not in self.standalone:
                    return False
            else:
                if v in used:
                    return False
                used.add(v)
                o = self.owner.get(v)
                if o is not None and o not in move:
                    return False
        change = Counter()
        for s, v in move.items():
            if self.value[s][0] == WORD_PREFIX:
                change[self.value[s]] -= 1
            if v[0] == WORD_PREFIX:
                change[v] += 1
        return all(len(self.holders[w]) + d <= self.capacity[w] for w, d in change.items() if d > 0)

    def decode(self, word):
        if len(word) == 1 and self.value[word[0][0]][0] == WORD_PREFIX:
            return self.value[word[0][0]][1:]
        return ''.join(self.value[s][0] if partial else self.value[s] for s, partial in word)

    def initial_assignment(self):
        self.value, self.owner, self.holders = {}, {}, defaultdict(set)

        # Spread possible word symbols over the common words
        slots = [w for w, c in self.capacity.items() for _ in range(c)]
        self.rng.shuffle(slots)
        for s in sorted(self.standalone, key=lambda s: -self.symbol_counts[s]):
            if not slots:
                break
            self.add(s, slots.pop())

        # Match frequent spelled cipher words to frequent dictionary words
        used = defaultdict(int)
        for w, _ in self.word_counts.most_common(300):
            if len(w) == 1 and w[0][0] in self.value:
                continue
            shape = word_shape(w)
            options = self.candidates.get(shape, [])
            for word, _ in options[used[shape]:used[shape] + 20]:
                targets = self.word_targets(w, word)
                if targets is None:
                    continue
                if all(self.value.get(s, b) == b and self.owner.get(b, s) == s
                       for s, b in targets.items()):
                    for s, b in targets.items():
                        if s not in self.value:
                            self.add(s, b)
                    used[shape] += 1
                    break

        free = [b for b in self.ranked_bigrams if b not in self.owner]
        for s in self.symbols:
            if s not in self.value:
                self.add(s, free.pop(0))

    def word_targets(self, cipher_word, plain_word):
        """Bigram for each symbol so that cipher_word spells plain_word, or None"""
        targets = {}
        for i, (s, partial) in enumerate(cipher_word):
            if partial:
                letter = plain_word[-1]
                current = self.value.get(s)
                if current and current[0] == letter:
                    b = current
                else:
                    options = [letter + x for x in LETTERS if letter + x not in self.owner]
                    b = self.rng.choice(options) if options else letter + self.rng.choice(LETTERS)
            else:
                b = plain_word[2 * i:2 * i + 2]
            if targets.get(s, b) != b:
                return None
            targets[s] = b
        if len(set(targets.values())) != len(targets):
            return None
        return targets

    def complete_move(self, targets):
        """Add swaps so that symbols losing their bigram take the old values"""
        move = dict(targets)
        for s, b in targets.items():
            t = self.owner.get(b)
            if t is not None and t != s and t not in move:
                move[t] = self.value[s]
        return move if self.valid(move) else None

    # -- moves ------------------------------------------------------------

    def symbol_move(self):
        s = self.rng.choices(self.symbols, self.symbol_weights)[0]
        if s in self.standalone and self.rng.random() < 0.5:
            v = self.rng.choices(self.word_values, self.word_value_weights)[0]
            if v == self.value[s]:
                return None
            if len(self.holders[v]) >= self.capacity[v]:
                t = self.rng.choice(sorted(self.holders[v]))
                move = {s: v, t: self.value[s]}
                return move if self.valid(move) else None
            move = {s: v}
            return move if self.valid(move) else None
        if self.rng.random() < 0.7:
            b = self.rng.choices(BIGRAMS, self.bigram_weights)[0]
        else:
            b = self.rng.choice(BIGRAMS)
        if b == self.value[s]:
            return None
        return self.complete_move({s: b})

    def word_move(self):
        w = self.rng.choices(self.distinct, self.word_weights)[0]
        if len(w) == 1 and w[0][0] in self.standalone:
            return self.symbol_move()
        shape = word_shape(w)
        options = self.candidates.get(shape)
        if not options:
            return None
        word = self.rng.choices(options[:3000], self.candidate_weights[shape])[0][0]
        targets = self.word_targets(w, word)
        if targets is None:
            return None
        return self.complete_move(targets)

    # -- search -----------------------------------------------------------

    def pair_score(self, pair, decoded):
        prev, cur = pair
        return self.model.pair_logp(decoded[prev] if prev is not None else None, decoded[cur])

    def run(self, iterations):
        self.initial_assignment()
        decoded = {w: self.decode(w) for w in self.distinct}
        pair_scores = {p: self.pair_score(p, decoded) for p in self.pair_counts}
        score = sum(pair_scores[p] * c for p, c in self.pair_counts.items())
        best_score, best = score, dict(self.value)

        for step in range(iterations):
            temperature = self.t_start * (self.t_end / self.t_start) ** (step / iterations)
            move = self.word_move() if self.rng.random() < 0.5 else self.symbol_move()
            if not move:
                continue

            old = self.apply(move)
            affected_words = set()
            for s in move:
                affected_words |= self.words_with[s]
            old_decoded = {w: decoded[w] for w in affected_words}
            for w in affected_words:
                decoded[w] = self.decode(w)
            affected_pairs = set()
            for w in affected_words:
                affected_pairs |= self.pairs_with[w]
            new_scores = {p: self.pair_score(p, decoded) for p in affected_pairs}
            delta = sum((new_scores[p] - pair_scores[p]) * self.pair_counts[p] for p in affected_pairs)

            if delta >= 0 or self.rng.random() < math.exp(delta / temperature):
                score += delta
                pair_scores.update(new_scores)
                if score > best_score:
                    best_score, best = score, dict(self.value)
            else:
                self.apply(old)
                decoded.update(old_decoded)

        self.value = best
        return best_score, best


def attack(items, model, train_counts, budget, rng, iterations, restarts):
    """
    Run the search several times

    Returns the score and decoded words of the best result.
    """
    best_score, best = None, None
    for _ in range(restarts):
        solver = Solver(items, model, train_counts, budget, random.Random(rng.random()))
        score, _ = solver.run(iterations)
        if best_score is None or score > best_score:
            best_score, best = score, [solver.decode(w) for w in items if w is not None]
    return best_score, best


def true_score(items, truth, model, train_counts, budget):
    """Score of the real key under the attacker's model (for diagnosis only)"""
    solver = Solver(items, model, train_counts, budget, random.Random(0))
    solver.value = {s: (WORD_PREFIX + m.split('_')[1] if m.startswith('WORD_') else m)
                    for s, m in truth.items()}
    decoded = {w: solver.decode(w) for w in solver.distinct}
    return sum(solver.pair_score(p, decoded) * c for p, c in solver.pair_counts.items())


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def run_trial(text, model, train_counts, budget, rng, iterations, restarts):
    tokens, truth = encode_for_attacker(text, rng, budget)
    real_markers = {s for s, m in truth.items() if m.startswith('SPACE_')}

    markers = find_space_markers(tokens)
    markers_found = markers == real_markers

    items = split_words(tokens, markers)
    plain_words = words_of(text)

    start = time.time()
    found_score, decoded = attack(items, model, train_counts, budget, rng, iterations, restarts)
    elapsed = time.time() - start

    letters = sum(len(w) for w in plain_words)
    if len(decoded) == len(plain_words) and all(len(d) == len(p) for d, p in zip(decoded, plain_words)):
        correct_letters = sum(a == b for d, p in zip(decoded, plain_words) for a, b in zip(d, p))
        correct_words = sum(d == p for d, p in zip(decoded, plain_words))
    else:
        # Word boundaries were wrong, so compare the letter sequences instead
        matcher = difflib.SequenceMatcher(None, ''.join(plain_words), ''.join(decoded), autojunk=False)
        correct_letters = sum(block.size for block in matcher.get_matching_blocks())
        correct_words = len(set(decoded) & set(plain_words))

    return {
        'budget': budget,
        'words': len(plain_words),
        'letters': letters,
        'symbols': len(tokens),
        'markers_found': markers_found,
        'letter_accuracy': correct_letters / letters,
        'word_accuracy': correct_words / len(plain_words),
        'seconds': round(elapsed, 1),
        # If the real key scores higher than the result, the search stopped
        # short; if not, the model cannot tell the real text apart
        'found_score': round(found_score),
        'true_score': round(true_score(items, truth, model, train_counts, budget)) if markers_found else None,
        'sample_plain': ' '.join(plain_words[:12]),
        'sample_decoded': ' '.join(decoded[:12]),
    }


WORKER = {}


def init_worker():
    """Build the language model once per worker process"""
    books = load_books()
    sentences = []
    for name in TRAIN_BOOKS:
        sentences += sentences_of(clean_text(books[name]))
    WORKER['model'] = LanguageModel(sentences)
    WORKER['train_counts'] = Counter(w for s in sentences for w in s)


def worker_trial(task):
    budget, count, trial, text, seed, iterations, restarts = task
    result = run_trial(text, WORKER['model'], WORKER['train_counts'], budget,
                       random.Random(seed), iterations, restarts)
    result['nominal_words'] = count
    result['trial'] = trial
    result['iterations'] = iterations
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--words', type=int, nargs='+',
                        default=[200, 400, 800, 1600, 3200, 6400])
    parser.add_argument('--budgets', type=int, nargs='+', default=[0, 510],
                        help='word symbol budgets to compare (0 for no word symbols)')
    parser.add_argument('--keys', type=int, default=3, help='trials (keys) per length')
    parser.add_argument('--seed', type=int, default=1, help='seed for choosing passages')
    parser.add_argument('--restarts', type=int, default=1, help='searches per trial')
    parser.add_argument('--min-iterations', type=int, default=400000)
    parser.add_argument('--max-iterations', type=int, default=4000000)
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--out', default=os.path.join(os.path.dirname(__file__), 'results.json'))
    args = parser.parse_args()

    books = load_books()
    test_tokens = clean_text(books[TEST_BOOK]).split(' ')

    tasks = []
    for budget in args.budgets:
        # The same passages for every budget, so the budgets are comparable
        rng = random.Random(args.seed)
        for count in args.words:
            iterations = min(args.max_iterations, max(args.min_iterations, 2000 * count))
            for trial in range(args.keys):
                start = rng.randrange(len(test_tokens) // 10, len(test_tokens) - count - 1)
                text = ' '.join(test_tokens[start:start + count])
                tasks.append((budget, count, trial, text, rng.random(), iterations, args.restarts))

    # Longest tasks first so the pool finishes sooner
    tasks.sort(key=lambda t: -t[1])

    results = []
    with multiprocessing.Pool(args.jobs, initializer=init_worker) as pool:
        for result in pool.imap_unordered(worker_trial, tasks):
            results.append(result)
            print(f"budget {result['budget']:5d}  {result['nominal_words']:5d} words  "
                  f"trial {result['trial']}  markers={'yes' if result['markers_found'] else 'no '}  "
                  f"letters {result['letter_accuracy']:.0%}  words {result['word_accuracy']:.0%}  "
                  f"{result['seconds']}s", flush=True)
            results.sort(key=lambda r: (r['budget'], r['nominal_words'], r['trial']))
            with open(args.out, 'w') as f:
                json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
