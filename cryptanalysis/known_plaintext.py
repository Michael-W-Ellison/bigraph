#!/usr/bin/env python3
"""
Known-plaintext attack: how much a few known words help

Gives the attacker the first K words of a message, as a greeting, a name or a
standard opening would, and measures how much of the rest of the message the
grouping attack (attack_grouping.py) then recovers. The known words are at
known positions; since word boundaries are visible, a known phrase can
usually be found by its pattern of word lengths.

Every symbol in the known words is fixed to its meaning. For a symbol seen
only as a single letter (after the partial marker), this also fixes the
bigram's second letter, which the plaintext alone does not reveal, so the
attacker gets slightly more than the known words give.

Only the unknown part of the message (after the first K words) is scored.

Usage:
    python3 cryptanalysis/known_plaintext.py [--words 1600 6400] [--known 0 25 100 400]
"""

import argparse
import difflib
import json
import multiprocessing
import os
import random
import time

import attack as base
import attack_grouping as grouping


def known_symbols(items, truth, known_words):
    """Meaning of every symbol used in the first known_words words"""
    known = {}
    seen = 0
    for item in items:
        if item is None:
            continue
        if seen >= known_words:
            break
        for symbol, _ in item:
            known[symbol] = base.true_value(truth[symbol])
        seen += 1
    return known


def run_trial(text, model, train_counts, budget, bigram_budget, known_words, rng,
              iterations, sweeps):
    tokens, truth = base.encode_for_attacker(text, rng, budget, bigram_budget)
    markers = base.find_space_markers(tokens)
    items = base.split_words(tokens, markers)
    plain_words = base.words_of(text)

    known = known_symbols(items, truth, known_words)
    solver = grouping.GroupingSolver(items, model, train_counts, budget, bigram_budget,
                                     random.Random(rng.random()), grouping.find_links(items), known)
    start = time.time()
    found_score, _ = solver.run(iterations, sweeps)
    elapsed = time.time() - start

    decoded = [solver.decode(w) for w in items if w is not None]
    rest_plain, rest_decoded = plain_words[known_words:], decoded[known_words:]
    letters = difflib.SequenceMatcher(None, ''.join(rest_plain), ''.join(rest_decoded), autojunk=False)
    words = difflib.SequenceMatcher(None, rest_plain, rest_decoded, autojunk=False)

    # Share of the unknown part's symbol occurrences whose meaning is known
    rest_items = [w for w in items if w is not None][known_words:]
    occurrences = [s for w in rest_items for s, _ in w]
    covered = sum(1 for s in occurrences if s in known) / max(1, len(occurrences))

    return {
        'budget': budget,
        'bigram_budget': bigram_budget,
        'words': len(plain_words),
        'known_words': known_words,
        'known_symbols': len(known),
        'unknown_part_symbols_known': round(covered, 3),
        'markers_found': markers == {s for s, m in truth.items() if m.startswith('SPACE_')},
        'letter_accuracy': sum(b.size for b in letters.get_matching_blocks()) / sum(map(len, rest_plain)),
        'word_accuracy': sum(b.size for b in words.get_matching_blocks()) / len(rest_plain),
        'found_score': round(found_score),
        'seconds': round(elapsed, 1),
        'sample_plain': ' '.join(rest_plain[:30]),
        'sample_decoded': ' '.join(rest_decoded[:30]),
    }


def worker_trial(task):
    budget, bigram_budget, count, known_words, trial, text, seed, iterations, sweeps = task
    result = run_trial(text, grouping.WORKER['model'], grouping.WORKER['train_counts'], budget,
                       bigram_budget, known_words, random.Random(seed), iterations, sweeps)
    result.update({'nominal_words': count, 'trial': trial, 'iterations': iterations,
                   'sweeps': sweeps})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--words', type=int, nargs='+', default=[1600, 6400])
    parser.add_argument('--known', type=int, nargs='+', default=[0, 25, 100, 400],
                        help='numbers of known words at the start of each message')
    parser.add_argument('--budget', type=int, default=2000)
    parser.add_argument('--bigram-budget', type=int, default=1500)
    parser.add_argument('--keys', type=int, default=2, help='trials (keys) per setting')
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--sweeps', type=int, default=20)
    parser.add_argument('--iterations', type=int, default=1000000)
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--out', default=os.path.join(os.path.dirname(__file__),
                                                      'results_known_plaintext.json'))
    args = parser.parse_args()

    books = base.load_books()
    test_tokens = base.clean_text(books[base.TEST_BOOK]).split(' ')

    tasks = []
    for count in args.words:
        # The same passages and keys' seeds for every number of known words
        rng = random.Random(args.seed + count)
        passages = []
        for trial in range(args.keys):
            start = rng.randrange(0, len(test_tokens) - count - 1)
            passages.append((' '.join(test_tokens[start:start + count]), rng.random()))
        for known_words in args.known:
            if known_words >= count:
                continue
            for trial, (text, seed) in enumerate(passages):
                tasks.append((args.budget, args.bigram_budget, count, known_words, trial, text,
                              seed, args.iterations, args.sweeps))
    tasks.sort(key=lambda t: -t[2])

    results = []
    with multiprocessing.Pool(args.jobs, initializer=grouping.init_worker) as pool:
        for result in pool.imap_unordered(worker_trial, tasks):
            results.append(result)
            print(f"{result['nominal_words']:5d} words  {result['known_words']:4d} known  "
                  f"trial {result['trial']}  symbols known in rest "
                  f"{result['unknown_part_symbols_known']:.0%}  "
                  f"letters {result['letter_accuracy']:.0%}  words {result['word_accuracy']:.0%}  "
                  f"{result['seconds']}s", flush=True)
            results.sort(key=lambda r: (r['nominal_words'], r['known_words'], r['trial']))
            with open(args.out, 'w') as f:
                json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
