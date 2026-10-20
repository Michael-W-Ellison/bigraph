#!/usr/bin/env python3
"""
Stronger ciphertext-only attack: symbol grouping and letter 5-grams

Builds on attack.py (same attacker knowledge, corpus, and measurements) with
three changes aimed at the extra word and bigram symbols:

1. Grouping. Two spelled cipher words with the same shape that differ in
   exactly one position are often the same word written with different
   symbols, so the two differing symbols probably stand for the same bigram
   (or, after the partial marker, the same letter). These links are only
   suggestions: the search uses them to propose moves, and the score decides.
2. Smoother scoring. Each word is scored by a mix of its word frequency and a
   letter 5-gram model, so a partly correct word scores better than a wrong
   one, instead of all unknown words scoring about the same.
3. Restarts. The search is run several times and the best result is kept.

Usage:
    python3 cryptanalysis/attack_grouping.py [--words 6400 12800 ...] [--keys 2]
"""

import argparse
import functools
import json
import math
import multiprocessing
import os
import random
from collections import Counter, defaultdict

import attack as base
from bigraph.constants import BIGRAMS, COMMON_BIGRAMS, LETTERS

# Weight of the word frequency model when mixed with the letter 5-gram model
WORD_WEIGHT = 0.9
ORDER = 5


class LetterModel:
    """Letter 5-gram model over words, with Witten-Bell smoothing"""

    def __init__(self, word_counts):
        self.counts = [Counter() for _ in range(ORDER + 1)]
        self.followers = [defaultdict(set) for _ in range(ORDER + 1)]
        for w, c in word_counts.items():
            padded = '^' * (ORDER - 1) + w + '$'
            for i in range(ORDER - 1, len(padded)):
                for n in range(1, ORDER + 1):
                    gram = padded[i - n + 1:i + 1]
                    self.counts[n][gram] += c
                    self.followers[n][gram[:-1]].add(gram[-1])
        self.context_counts = [Counter() for _ in range(ORDER + 1)]
        for n in range(1, ORDER + 1):
            for gram, c in self.counts[n].items():
                self.context_counts[n][gram[:-1]] += c
        self.alphabet = 28
        self.cache = {}

    def prob(self, history, char):
        """P(char | history) with Witten-Bell interpolation"""
        p = 1 / self.alphabet
        for n in range(1, ORDER + 1):
            context = history[len(history) - (n - 1):] if n > 1 else ''
            total = self.context_counts[n].get(context, 0)
            if not total:
                continue
            types = len(self.followers[n][context])
            seen = self.counts[n].get(context + char, 0)
            p = (seen + types * p) / (total + types)
        return p

    def logp(self, word):
        cached = self.cache.get(word)
        if cached is not None:
            return cached
        padded = '^' * (ORDER - 1) + word + '$'
        value = sum(math.log(self.prob(padded[i - ORDER + 1:i], padded[i]))
                    for i in range(ORDER - 1, len(padded)))
        if len(self.cache) > 2_000_000:
            self.cache.clear()
        self.cache[word] = value
        return value


class MixedModel(base.LanguageModel):
    """Word-pair model whose word probabilities mix in a letter 5-gram model"""

    def __init__(self, sentences):
        super().__init__(sentences)
        self.letters = LetterModel(self.counts)

    def logp(self, word):
        cached = self.cache.get(word)
        if cached is not None:
            return cached
        word_p = math.exp(self.word_logp[word]) if word in self.word_logp else 0.0
        letter_p = math.exp(self.letters.logp(word))
        value = math.log(WORD_WEIGHT * word_p + (1 - WORD_WEIGHT) * letter_p)
        if len(self.cache) > 2_000_000:
            self.cache.clear()
        self.cache[word] = value
        return value


def find_links(items):
    """
    Link symbols that probably mean the same thing

    Returns {symbol: [linked symbols]}, from spelled cipher words of the same
    shape that differ in exactly one position.
    """
    words = {w for w in items if w is not None}
    by_shape = defaultdict(list)
    for w in words:
        by_shape[base.word_shape(w)].append(w)

    links = defaultdict(set)
    for shape, ws in by_shape.items():
        if shape[0] < 2:
            continue
        for pos in range(shape[0]):
            groups = defaultdict(list)
            for w in ws:
                groups[w[:pos] + w[pos + 1:]].append(w[pos][0])
            for symbols in groups.values():
                distinct = set(symbols)
                if len(distinct) < 2:
                    continue
                for s in distinct:
                    links[s] |= distinct - {s}
    return {s: sorted(linked) for s, linked in links.items()}


class GroupingSolver(base.Solver):
    """
    Gibbs sampling, then annealing with moves suggested by the symbol links

    Gibbs sampling takes one symbol at a time, scores every candidate value
    with the other symbols fixed, and picks a value with probability
    proportional to its score. The published number of symbols for each value
    gives the prior: a symbol is more likely to mean a value with many
    symbols.
    """

    # Share of one-symbol words that are spelled bigrams rather than common words
    SPELLED_SHARE = 0.02

    def __init__(self, items, model, train_counts, budget, bigram_budget, rng, links):
        super().__init__(items, model, train_counts, budget, bigram_budget, rng)
        self.links = {s: linked for s, linked in links.items() if s in self.symbol_counts}
        self.linked_symbols = sorted(self.links)

        # Candidate values and their prior log probability
        bigram_total = sum(self.capacity[b] for b in BIGRAMS)
        self.bigram_prior = {b: math.log(self.capacity[b] / bigram_total) for b in BIGRAMS}
        self.common_bigrams = [b for b, _ in COMMON_BIGRAMS]
        letter_capacity = Counter()
        for b in BIGRAMS:
            letter_capacity[b[0]] += self.capacity[b]
        self.letter_prior = {x: math.log(letter_capacity[x] / bigram_total) for x in LETTERS}
        word_total = sum(self.capacity[w] for w in self.word_values) or 1
        self.word_prior = {w: math.log((1 - self.SPELLED_SHARE) * self.capacity[w] / word_total)
                           for w in self.word_values}
        self.two_letter_words = [w for w, _ in train_counts.most_common(5000)
                                 if len(w) == 2 and w not in self.common][:40]

        self.partial_only = set()
        for sym in self.symbols:
            if all(partial for w in self.words_with[sym] for x, partial in w if x == sym):
                self.partial_only.add(sym)

    def link_move(self):
        """Give a symbol the value of a linked symbol, or move a group together"""
        s = self.rng.choice(self.linked_symbols)
        t = self.rng.choice(self.links[s])
        if self.rng.random() < 0.7:
            v = self.value[t]
            if v[0] == base.WORD_PREFIX:
                return None
            return self.complete_move({s: v})
        # Move s and its linked symbols to one bigram
        v = self.rng.choices(BIGRAMS, self.bigram_weights)[0]
        group = [s] + [x for x in self.links[s] if self.value[x][0] != base.WORD_PREFIX][:5]
        return self.complete_move({x: v for x in group})

    def render(self, word, sym, v):
        """Decode a word as if symbol sym had value v"""
        if len(word) == 1 and v[0] == base.WORD_PREFIX:
            return v[1:]
        parts = []
        for x, partial in word:
            value = v if x == sym else self.value[x]
            parts.append(value[0] if partial else value)
        return ''.join(parts)

    def value_candidates(self, sym):
        """Candidate values and their prior log probabilities"""
        if sym in self.standalone:
            options = [(w, self.word_prior[w]) for w in self.word_values]
            options += [(b, math.log(self.SPELLED_SHARE / len(self.two_letter_words)))
                        for b in self.two_letter_words]
            return options
        if sym in self.partial_only:
            return [(x + 'A', self.letter_prior[x]) for x in LETTERS]
        options = set(self.common_bigrams)
        if self.value[sym][0] != base.WORD_PREFIX:
            options.add(self.value[sym])
        return [(b, self.bigram_prior[b]) for b in options]

    def conditional_scores(self, sym, options):
        """Score of each candidate value with the other symbols fixed"""
        scores = []
        if sym in self.standalone:
            word = ((sym, False),)
            # Neighbouring words, decoded once; None marks this word
            pairs = []
            for w in self.words_with[sym]:
                for prev, cur in self.pairs_with[w]:
                    prev_text = None if prev == word else (self.decode(prev) if prev else '')
                    cur_text = None if cur == word else self.decode(cur)
                    pairs.append((prev_text, cur_text, self.pair_counts[(prev, cur)]))
            for v, prior in options:
                text = self.render(word, sym, v)
                total = prior
                for prev_text, cur_text, count in pairs:
                    prev_text = text if prev_text is None else (prev_text or None)
                    cur_text = text if cur_text is None else cur_text
                    total += count * self.model.pair_logp(prev_text, cur_text)
                scores.append(total)
            return scores
        words = [(w, self.word_counts[w]) for w in self.words_with[sym]]
        for v, prior in options:
            total = prior
            for w, count in words:
                total += count * self.model.logp(self.render(w, sym, v))
            scores.append(total)
        return scores

    def gibbs(self, sweeps, t_start=2.0, t_end=0.3):
        """Resample every symbol's value, sweep by sweep, cooling as it goes"""
        order = list(self.symbols)
        best_score, best = None, None
        for sweep in range(sweeps):
            temperature = t_start * (t_end / t_start) ** (sweep / max(1, sweeps - 1))
            self.rng.shuffle(order)
            for sym in order:
                options = self.value_candidates(sym)
                scores = self.conditional_scores(sym, options)
                top = max(scores)
                weights = [math.exp((sc - top) / temperature) for sc in scores]
                v = self.rng.choices(options, weights)[0][0]
                if v != self.value[sym]:
                    self.remove(sym)
                    self.add(sym, v)
            score = self.full_score()
            if best_score is None or score > best_score:
                best_score, best = score, dict(self.value)
        self.set_values(best)

    def full_score(self):
        decoded = {w: self.decode(w) for w in self.distinct}
        return sum(self.pair_score(p, decoded) * c for p, c in self.pair_counts.items())

    def set_values(self, values):
        self.value, self.holders = {}, defaultdict(set)
        for sym, v in values.items():
            self.add(sym, v)

    def run(self, iterations, sweeps=0):
        # Gibbs sweeps, then the same search as Solver.run with link moves mixed in
        self.initial_assignment()
        if sweeps:
            self.gibbs(sweeps)
            self.t_start = 3.0
        decoded = {w: self.decode(w) for w in self.distinct}
        pair_scores = {p: self.pair_score(p, decoded) for p in self.pair_counts}
        score = sum(pair_scores[p] * c for p, c in self.pair_counts.items())
        best_score, best = score, dict(self.value)

        for step in range(iterations):
            temperature = self.t_start * (self.t_end / self.t_start) ** (step / iterations)
            r = self.rng.random()
            if r < 0.3 and self.linked_symbols:
                move = self.link_move()
            elif r < 0.65:
                move = self.word_move()
            else:
                move = self.symbol_move()
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


def grouping_attack(items, model, train_counts, budget, bigram_budget, rng, iterations, restarts,
                    sweeps=20):
    links = find_links(items)
    best_score, best = None, None
    for _ in range(restarts):
        solver = GroupingSolver(items, model, train_counts, budget, bigram_budget,
                                random.Random(rng.random()), links)
        score, _ = solver.run(iterations, sweeps)
        if best_score is None or score > best_score:
            best_score, best = score, [solver.decode(w) for w in items if w is not None]
    return best_score, best


WORKER = {}


def init_worker():
    books = base.load_books()
    sentences = []
    for name in base.TRAIN_BOOKS:
        sentences += base.sentences_of(base.clean_text(books[name]))
    WORKER['model'] = MixedModel(sentences)
    WORKER['train_counts'] = Counter(w for s in sentences for w in s)


def worker_trial(task):
    budget, bigram_budget, count, trial, text, seed, iterations, restarts, sweeps = task
    # run_trial calls base.attack; point it at this attack
    base.attack = functools.partial(grouping_attack, sweeps=sweeps)
    result = base.run_trial(text, WORKER['model'], WORKER['train_counts'], budget, bigram_budget,
                            random.Random(seed), iterations, restarts)
    result['nominal_words'] = count
    result['trial'] = trial
    result['iterations'] = iterations
    result['restarts'] = restarts
    result['sweeps'] = sweeps
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--words', type=int, nargs='+', default=[6400, 12800, 25600])
    parser.add_argument('--budgets', type=int, nargs='+', default=[2000])
    parser.add_argument('--bigram-budgets', type=int, nargs='+', default=[1500])
    parser.add_argument('--keys', type=int, default=2, help='trials (keys) per length')
    parser.add_argument('--seed', type=int, default=1, help='seed for choosing passages')
    parser.add_argument('--restarts', type=int, default=2, help='searches per trial')
    parser.add_argument('--iterations', type=int, default=2000000,
                        help='annealing steps per search, after the Gibbs sweeps')
    parser.add_argument('--sweeps', type=int, default=20, help='Gibbs sweeps per search')
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--out', default=os.path.join(os.path.dirname(__file__),
                                                      'results_grouping.json'))
    args = parser.parse_args()

    books = base.load_books()
    test_tokens = base.clean_text(books[base.TEST_BOOK]).split(' ')

    tasks = []
    for budget in args.budgets:
        for bigram_budget in args.bigram_budgets:
            rng = random.Random(args.seed)
            for count in args.words:
                for trial in range(args.keys):
                    start = rng.randrange(0, max(1, len(test_tokens) - count - 1))
                    text = ' '.join(test_tokens[start:start + count])
                    tasks.append((budget, bigram_budget, count, trial, text, rng.random(),
                                  args.iterations, args.restarts, args.sweeps))
    tasks.sort(key=lambda t: -t[2])

    results = []
    with multiprocessing.Pool(args.jobs, initializer=init_worker) as pool:
        for result in pool.imap_unordered(worker_trial, tasks):
            results.append(result)
            print(f"words {result['budget']:5d}  bigrams {result['bigram_budget']:5d}  "
                  f"{result['nominal_words']:6d} words  trial {result['trial']}  "
                  f"markers={'yes' if result['markers_found'] else 'no '}  "
                  f"letters {result['letter_accuracy']:.0%}  words {result['word_accuracy']:.0%}  "
                  f"found {result['found_score']}  true {result['true_score']}  "
                  f"{result['seconds']}s", flush=True)
            results.sort(key=lambda r: (r['budget'], r['bigram_budget'], r['nominal_words'], r['trial']))
            with open(args.out, 'w') as f:
                json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
