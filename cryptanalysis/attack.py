#!/usr/bin/env python3
"""
Ciphertext-only attack on the Bigraph Cryptography System

Measures how much encoded text an attacker needs to recover the plaintext
without the key. The attacker is assumed to know how the system works (the
code is public) and to have turned each drawn symbol into a label, which is
straightforward because the drawings are distinct shapes on a fixed grid.

The attacker sees, in order, a label for each symbol and the partial marker
("|"). It does not see the key or the symbol indices.

Attack steps:
1. Find the 7 space markers. Each cycle of the rotation uses every marker
   once, so occurrences of any two markers strictly alternate.
2. Split the text into words at the markers. Each word is a list of symbols,
   and a word whose last symbol follows the partial marker has an odd number
   of letters.
3. Start by matching the most frequent cipher words to the most frequent
   English words of the same shape (symbol count and odd/even length).
4. Search for the symbol-to-bigram assignment that makes the words most
   English-like, using simulated annealing scored by a word frequency model
   with a letter trigram fallback for unknown words. Moves either change one
   symbol or set a whole cipher word to a dictionary word of the same shape.
   The search is restarted several times and the best result is kept.

The attack does not use the single-letter rotation order (|EA, |EB, ...) or
sentence-end markers, so a stronger attacker could do better than this.

Usage:
    python3 cryptanalysis/attack.py [--words 25 50 ...] [--keys 3] [--out results.json]
"""

import argparse
import json
import multiprocessing
import math
import os
import random
import re
import sys
import time
import urllib.request
import zipfile
from collections import Counter, defaultdict
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from bigraph.constants import BIGRAMS, LETTERS  # noqa: E402
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


# ---------------------------------------------------------------------------
# Language model
# ---------------------------------------------------------------------------

class LanguageModel:
    """Word unigram model with a letter trigram model for unknown words"""

    def __init__(self, words):
        counts = Counter(words)
        total = sum(counts.values())
        self.word_logp = {w: math.log(c / total) for w, c in counts.items()}

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
        self.cache[word] = value
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

def encode_for_attacker(text, rng):
    """
    Encode text with a new secure key and return the attacker's view

    Returns (tokens, truth) where tokens is a list of labels and PARTIAL, and
    truth maps each label to its real meaning (used only for scoring).
    """
    key = KeyManager(keys_directory=os.path.join(DATA_DIR, 'keys')).generate_key('attack')
    encoded = BigramEncoder(key).encode(text)

    # Give each drawing a random label, as an attacker transcribing them would
    indices = list(key['symbol_to_meaning'])
    labels = rng.sample(range(100000), len(indices))
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
    """Find 7 symbols whose occurrences all strictly alternate with each other"""
    positions = defaultdict(list)
    for i, t in enumerate(tokens):
        if t != PARTIAL and (i == 0 or tokens[i - 1] != PARTIAL):
            positions[t].append(i)

    candidates = [s for s, _ in Counter({s: len(p) for s, p in positions.items()}).most_common(40)]

    def alternates(a, b):
        pa, pb = positions[a], positions[b]
        if abs(len(pa) - len(pb)) > 1:
            return False
        merged = sorted([(p, 0) for p in pa] + [(p, 1) for p in pb])
        return all(merged[i][1] != merged[i + 1][1] for i in range(len(merged) - 1))

    neighbours = {a: {b for b in candidates if b != a and alternates(a, b)} for a in candidates}

    best = None
    for a in candidates:
        group = [b for b in neighbours[a] if b in candidates]
        for combo in combinations(group, 6):
            if all(y in neighbours[x] for x, y in combinations(combo, 2)):
                clique = (a,) + combo
                size = sum(len(positions[s]) for s in clique)
                if best is None or size > best[0]:
                    best = (size, clique)
        if best:
            break
    return set(best[1]) if best else set()


def split_words(tokens, markers):
    """Split tokens into words; each word is a list of (symbol, is_partial)"""
    words, current, partial = [], [], False
    for t in tokens:
        if t == PARTIAL:
            partial = True
            continue
        if t in markers and not partial:
            if current:
                words.append(tuple(current))
                current = []
        else:
            current.append((t, partial))
        partial = False
    if current:
        words.append(tuple(current))
    return words


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def decode_word(word, assignment):
    return ''.join(assignment[s][0] if partial else assignment[s] for s, partial in word)


def word_shape(word):
    """(number of symbols, ends with a single letter) for a cipher word"""
    return len(word), word[-1][1]


def plain_shape(word):
    return (len(word) + 1) // 2, len(word) % 2 == 1


def word_targets(cipher_word, plain_word, assignment):
    """
    Bigram for each symbol so that cipher_word decodes as plain_word

    Returns None if the word cannot be mapped consistently.
    """
    targets = {}
    for i, (s, partial) in enumerate(cipher_word):
        if partial:
            letter = plain_word[-1]
            current = assignment.get(s)
            b = current if current and current[0] == letter else None
            if s in targets:
                if targets[s][0] != letter:
                    return None
                continue
            targets[s] = b or (letter, )  # resolved later to a free bigram
        else:
            b = plain_word[2 * i:2 * i + 2]
            if targets.get(s, b) != b:
                return None
            targets[s] = b
    wanted = [b for b in targets.values() if isinstance(b, str)]
    if len(wanted) != len(set(wanted)):
        return None
    return targets


class Solver:
    """Simulated annealing over the symbol-to-bigram assignment"""

    def __init__(self, cipher_words, model, train_counts, rng):
        self.model = model
        self.rng = rng
        self.t_start, self.t_end = 30.0, 0.5
        self.word_counts = Counter(cipher_words)
        self.distinct = list(self.word_counts)
        self.words_with = defaultdict(set)
        self.symbol_counts = Counter()
        for w in self.distinct:
            for s, _ in w:
                self.words_with[s].add(w)
                self.symbol_counts[s] += self.word_counts[w]
        self.symbols = [s for s, _ in self.symbol_counts.most_common()]
        self.symbol_weights = [math.sqrt(self.symbol_counts[s]) for s in self.symbols]
        self.word_weights = [math.sqrt(self.word_counts[w]) for w in self.distinct]

        # Dictionary words grouped by shape, most frequent first
        self.candidates = defaultdict(list)
        for word, count in train_counts.most_common(30000):
            self.candidates[plain_shape(word)].append((word, count))
        self.candidate_weights = {
            shape: [math.sqrt(c) for _, c in words[:3000]]
            for shape, words in self.candidates.items()
        }

        bigram_freq = aligned_bigram_counts(train_counts.elements())
        self.bigram_weights = [bigram_freq.get(b, 0) + 1 for b in BIGRAMS]
        self.ranked_bigrams = [b for b, _ in bigram_freq.most_common()]
        self.ranked_bigrams += [b for b in BIGRAMS if b not in bigram_freq]

    # -- state ------------------------------------------------------------

    def initial_assignment(self):
        """Match frequent cipher words to frequent dictionary words of the same shape"""
        assignment, owner = {}, {}
        used = defaultdict(int)
        for w, _ in self.word_counts.most_common(300):
            shape = word_shape(w)
            options = self.candidates.get(shape, [])
            for word, _ in options[used[shape]:used[shape] + 20]:
                targets = word_targets(w, word, assignment)
                if targets is None:
                    continue
                ok = True
                for s, b in targets.items():
                    if isinstance(b, tuple):
                        continue
                    if (s in assignment and assignment[s] != b) or (b in owner and owner[b] != s):
                        ok = False
                        break
                if ok:
                    for s, b in targets.items():
                        if isinstance(b, tuple):
                            b = self.free_bigram(b[0], owner)
                        if s not in assignment:
                            assignment[s] = b
                            owner[b] = s
                    used[shape] += 1
                    break

        free = [b for b in self.ranked_bigrams if b not in owner]
        for s in self.symbols:
            if s not in assignment:
                b = free.pop(0)
                assignment[s] = b
                owner[b] = s
        return assignment, owner

    def free_bigram(self, letter, owner):
        options = [letter + x for x in LETTERS if letter + x not in owner]
        return self.rng.choice(options) if options else letter + self.rng.choice(LETTERS)

    def score_words(self, words):
        return {w: self.model.logp(decode_word(w, self.assignment)) for w in words}

    def set_bigram(self, s, b, changed):
        """Give symbol s bigram b, swapping with the symbol that has b"""
        old = self.assignment[s]
        if old == b:
            return
        t = self.owner.get(b)
        changed.setdefault(s, old)
        self.assignment[s] = b
        self.owner[b] = s
        if t is not None:
            changed.setdefault(t, self.assignment[t])
            self.assignment[t] = old
            self.owner[old] = t
        else:
            del self.owner[old]

    def undo(self, changed):
        for s, b in changed.items():
            current = self.assignment[s]
            if self.owner.get(current) == s:
                del self.owner[current]
        for s, b in changed.items():
            self.assignment[s] = b
            self.owner[b] = s

    # -- moves ------------------------------------------------------------

    def symbol_move(self, changed):
        s = self.rng.choices(self.symbols, self.symbol_weights)[0]
        if self.rng.random() < 0.7:
            b = self.rng.choices(BIGRAMS, self.bigram_weights)[0]
        else:
            b = self.rng.choice(BIGRAMS)
        self.set_bigram(s, b, changed)

    def word_move(self, changed):
        w = self.rng.choices(self.distinct, self.word_weights)[0]
        shape = word_shape(w)
        options = self.candidates.get(shape)
        if not options:
            return
        word = self.rng.choices(options[:3000], self.candidate_weights[shape])[0][0]
        targets = word_targets(w, word, self.assignment)
        if targets is None:
            return
        for s, b in targets.items():
            if isinstance(b, tuple):
                b = self.free_bigram(b[0], self.owner)
            self.set_bigram(s, b, changed)

    # -- search -----------------------------------------------------------

    def run(self, iterations):
        self.assignment, self.owner = self.initial_assignment()
        word_score = self.score_words(self.distinct)
        score = sum(word_score[w] * self.word_counts[w] for w in self.distinct)
        best_score, best = score, dict(self.assignment)
        t_start, t_end = self.t_start, self.t_end

        for step in range(iterations):
            temperature = t_start * (t_end / t_start) ** (step / iterations)
            changed = {}
            if self.rng.random() < 0.5:
                self.word_move(changed)
            else:
                self.symbol_move(changed)
            if not changed:
                continue

            affected = set()
            for s in changed:
                affected |= self.words_with[s]
            new_scores = self.score_words(affected)
            delta = sum((new_scores[w] - word_score[w]) * self.word_counts[w] for w in affected)

            if delta >= 0 or self.rng.random() < math.exp(delta / temperature):
                score += delta
                word_score.update(new_scores)
                if score > best_score:
                    best_score, best = score, dict(self.assignment)
            else:
                self.undo(changed)

        return best_score, best


def attack(cipher_words, model, train_counts, rng, iterations, restarts):
    """Run the search several times and keep the most English-like result"""
    best_score, best = None, None
    for _ in range(restarts):
        solver = Solver(cipher_words, model, train_counts, random.Random(rng.random()))
        score, assignment = solver.run(iterations)
        if best_score is None or score > best_score:
            best_score, best = score, assignment
    return best


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

def run_trial(text, model, train_counts, rng, iterations, restarts):
    tokens, truth = encode_for_attacker(text, rng)
    real_markers = {s for s, m in truth.items() if m.startswith('SPACE_')}

    markers = find_space_markers(tokens)
    markers_found = markers == real_markers

    cipher_words = split_words(tokens, markers)
    plain_words = words_of(text)

    start = time.time()
    assignment = attack(cipher_words, model, train_counts, rng, iterations, restarts)
    elapsed = time.time() - start

    decoded = [decode_word(w, assignment) for w in cipher_words]
    letters = sum(len(w) for w in plain_words)
    if markers_found and len(decoded) == len(plain_words):
        correct_letters = sum(a == b for d, p in zip(decoded, plain_words) for a, b in zip(d, p))
        correct_words = sum(d == p for d, p in zip(decoded, plain_words))
    else:
        correct_letters = correct_words = 0

    return {
        'words': len(plain_words),
        'letters': letters,
        'symbols': len(tokens),
        'markers_found': markers_found,
        'letter_accuracy': correct_letters / letters,
        'word_accuracy': correct_words / len(plain_words),
        'seconds': round(elapsed, 1),
        'sample_plain': ' '.join(plain_words[:12]),
        'sample_decoded': ' '.join(decoded[:12]),
    }


def take_passage(words_and_ends, start, count):
    """Return `count` words from `start`, keeping sentence ends"""
    picked = words_and_ends[start:start + count]
    return ' '.join(picked)


WORKER = {}


def init_worker():
    """Build the language model once per worker process"""
    books = load_books()
    train_words = []
    for name in TRAIN_BOOKS:
        train_words += words_of(clean_text(books[name]))
    WORKER['model'] = LanguageModel(train_words)
    WORKER['train_counts'] = Counter(train_words)


def worker_trial(task):
    count, trial, text, seed, iterations, restarts = task
    result = run_trial(text, WORKER['model'], WORKER['train_counts'],
                       random.Random(seed), iterations, restarts)
    result['trial'] = trial
    result['iterations'] = iterations
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--words', type=int, nargs='+',
                        default=[25, 50, 100, 200, 400, 800, 1600, 3200])
    parser.add_argument('--keys', type=int, default=3, help='trials (keys) per length')
    parser.add_argument('--seed', type=int, default=1, help='seed for choosing passages')
    parser.add_argument('--restarts', type=int, default=1, help='searches per trial')
    parser.add_argument('--min-iterations', type=int, default=400000)
    parser.add_argument('--max-iterations', type=int, default=3000000)
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--out', default=os.path.join(os.path.dirname(__file__), 'results.json'))
    args = parser.parse_args()

    books = load_books()
    test_tokens = clean_text(books[TEST_BOOK]).split(' ')
    rng = random.Random(args.seed)

    tasks = []
    for count in args.words:
        iterations = min(args.max_iterations, max(args.min_iterations, 2000 * count))
        for trial in range(args.keys):
            start = rng.randrange(len(test_tokens) // 10, len(test_tokens) - count - 1)
            text = take_passage(test_tokens, start, count)
            tasks.append((count, trial, text, rng.random(), iterations, args.restarts))

    # Longest tasks first so the pool finishes sooner
    tasks.sort(key=lambda t: -t[0])

    results = []
    with multiprocessing.Pool(args.jobs, initializer=init_worker) as pool:
        for result in pool.imap_unordered(worker_trial, tasks):
            results.append(result)
            print(f"{result['words']:5d} words  trial {result['trial']}  "
                  f"markers={'yes' if result['markers_found'] else 'no '}  "
                  f"letters {result['letter_accuracy']:.0%}  words {result['word_accuracy']:.0%}  "
                  f"{result['seconds']}s", flush=True)
            results.sort(key=lambda r: (r['words'], r['trial']))
            with open(args.out, 'w') as f:
                json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
