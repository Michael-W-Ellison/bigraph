# Ciphertext-Only Attack Results

Produced by `attack.py` with its default settings (`python3 cryptanalysis/attack.py --jobs 4`).
Raw results are in `results.json`.

## Setup

- **Attacker knowledge:** how the system works, and a label for each distinct
  drawn symbol. No key.
- **Keys:** a new key from the secure random source for every trial.
- **Training text:** word and letter statistics from 8 public-domain books
  (Austen, Bryant, Burgess, Carroll, Edgeworth, Melville).
- **Test text:** passages from *The Man Who Was Thursday* (Chesterton), an
  author not in the training books. Passages were reduced to letters, spaces
  and sentence ends.
- **Search:** one simulated-annealing run per trial, with the number of
  steps shown below. Trials ran 4 at a time on one machine.
- **Trials:** 3 per length. With this few trials the averages are rough.

## Results

| Words | Letters correct (each trial) | Letters (average) | Whole words (average) | Search steps | Minutes per trial |
|---:|---|---:|---:|---:|---:|
| 25 | 34%, 37%, 19% | 30% | 25% | 400,000 | 0.5 |
| 50 | 14%, 10%, 10% | 11% | 7% | 400,000 | 0.5 |
| 100 | 6%, 16%, 15% | 12% | 7% | 400,000 | 0.7 |
| 200 | 27%, 36%, 26% | 30% | 22% | 400,000 | 0.8 |
| 400 | 42%, 15%, 40% | 32% | 22% | 800,000 | 2.1 |
| 800 | 95%, 46%, 97% | 79% | 68% | 1,600,000 | 6.1 |
| 1,600 | 98%, 29%, 99% | 75% | 69% | 3,000,000 | 16.4 |
| 3,200 | 99%, 99%, 99% | 99% | 96% | 3,000,000 | 23.2 |

The space markers were identified correctly in every trial.

## Findings

- Up to 400 words, the attack recovered 11–32% of letters on average. That is
  mostly frequent short words (THE, OF, AND, TO), not readable text.
- From 800 words, most trials recovered almost the whole text: 5 of the 6
  trials at 800 and 1,600 words reached 95–99% of letters.
- At 3,200 words all 3 trials reached 99% of letters.
- The two failed trials at 800 and 1,600 words (46% and 29%) stopped at a
  wrong solution. Running the search again with a different start
  (`--restarts`) is the usual fix, so an attacker with more time would likely
  succeed on those too.
- The 25-word average is higher than the 50- and 100-word averages because a
  25-word passage is mostly very common words. This is an artifact of short
  passages and small trial counts.

## Limits of this measurement

These numbers are an upper bound on how much text is needed, because the
attack leaves information unused:

- It does not use the order of the single-letter rotation (the first single
  E in a message is always |EA, the second |EB, and so on).
- It does not use sentence-end markers or combine several messages written
  with the same key.
- It uses one search run per trial, at most 3,000,000 steps.

A stronger attacker, or more computing time, could need less text. Text is
counted per key: several messages written with the same key add up.
