#!/usr/bin/env python3
"""
Run attack.py's attack on several (word symbols, extra bigram symbols) pairs

attack.py compares every combination of the budgets it is given; this runs
only the listed pairs, on the same passages for every pair, sharing one pool
of worker processes.

Usage:
    python3 cryptanalysis/compare_configs.py --configs 510:0 255:255 150:360 --words 1600
"""

import argparse
import json
import multiprocessing
import os
import random

import attack as base


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    parser.add_argument('--configs', nargs='+', required=True,
                        help='word:bigram budget pairs, for example 255:255')
    parser.add_argument('--words', type=int, nargs='+', default=[1600])
    parser.add_argument('--keys', type=int, default=2)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--min-iterations', type=int, default=400000)
    parser.add_argument('--max-iterations', type=int, default=4000000)
    parser.add_argument('--jobs', type=int, default=os.cpu_count() or 1)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()

    books = base.load_books()
    test_tokens = base.clean_text(books[base.TEST_BOOK]).split(' ')

    tasks = []
    for config in args.configs:
        budget, bigram_budget = (int(x) for x in config.split(':'))
        # Same passages for every pair, chosen as attack.py chooses them
        rng = random.Random(args.seed)
        for count in args.words:
            iterations = min(args.max_iterations, max(args.min_iterations, 2000 * count))
            for trial in range(args.keys):
                start = rng.randrange(len(test_tokens) // 10, len(test_tokens) - count - 1)
                text = ' '.join(test_tokens[start:start + count])
                tasks.append((budget, bigram_budget, count, trial, text, rng.random(), iterations, 1))
    tasks.sort(key=lambda t: -t[2])

    results = []
    with multiprocessing.Pool(args.jobs, initializer=base.init_worker) as pool:
        for result in pool.imap_unordered(base.worker_trial, tasks):
            results.append(result)
            print(f"words {result['budget']:5d}  bigrams {result['bigram_budget']:5d}  "
                  f"{result['nominal_words']:5d} words  trial {result['trial']}  "
                  f"letters {result['letter_accuracy']:.0%}  words {result['word_accuracy']:.0%}  "
                  f"found {result['found_score']}  true {result['true_score']}  "
                  f"{result['seconds']}s", flush=True)
            results.sort(key=lambda r: (r['budget'], r['bigram_budget'], r['nominal_words'], r['trial']))
            with open(args.out, 'w') as f:
                json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
