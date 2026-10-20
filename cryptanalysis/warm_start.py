#!/usr/bin/env python3
"""
Warm-start test for the grouping attack

Starts the Gibbs sampler of attack_grouping.py from the real key with a share
of the symbols replaced by the attack's own starting guesses, and reports how
much of the text it recovers. This separates the two limits of the attack:
getting started (a cold start) and the model's own ceiling (starting from the
real key).

Usage:
    python3 cryptanalysis/warm_start.py WORDS SCRAMBLED_SHARE SWEEPS
    python3 cryptanalysis/warm_start.py 6400 0.5 6
"""

import difflib
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))

import attack as A  # noqa: E402
import attack_grouping as G  # noqa: E402


def accuracy(solver, items, plain):
    decoded = [solver.decode(w) for w in items if w is not None]
    words = difflib.SequenceMatcher(None, plain, decoded, autojunk=False)
    letters = difflib.SequenceMatcher(None, ''.join(plain), ''.join(decoded), autojunk=False)
    return (sum(b.size for b in letters.get_matching_blocks()) / sum(map(len, plain)),
            sum(b.size for b in words.get_matching_blocks()) / len(plain))


def main():
    count, share, sweeps = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
    books = A.load_books()
    sentences = []
    for name in A.TRAIN_BOOKS:
        sentences += A.sentences_of(A.clean_text(books[name]))
    model = G.MixedModel(sentences)
    train_counts = Counter(w for s in sentences for w in s)

    tokens_all = A.clean_text(books[A.TEST_BOOK]).split(' ')
    rng = random.Random(7)
    text = ' '.join(tokens_all[8000:8000 + count])
    tokens, truth = A.encode_for_attacker(text, rng, 2000, 1500)
    items = A.split_words(tokens, A.find_space_markers(tokens))
    plain = A.words_of(text)

    solver = G.GroupingSolver(items, model, train_counts, 2000, 1500, random.Random(1),
                              G.find_links(items))
    solver.initial_assignment()
    start = {s: A.true_value(m) for s, m in truth.items() if s in solver.value}
    for s in random.Random(2).sample(sorted(start), int(share * len(start))):
        start[s] = solver.value[s]
    solver.set_values(start)

    letters, words = accuracy(solver, items, plain)
    print(f"{count} words, {share:.0%} scrambled: start letters {letters:.0%} words {words:.0%} "
          f"score {solver.full_score():.0f}")
    solver.gibbs(sweeps, t_start=1.0, t_end=0.3)
    letters, words = accuracy(solver, items, plain)
    print(f"after {sweeps} sweeps: letters {letters:.0%} words {words:.0%} score {solver.full_score():.0f}")


if __name__ == '__main__':
    main()
