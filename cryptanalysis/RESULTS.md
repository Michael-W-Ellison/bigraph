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

---

# Common Word Symbols

The 100 most common words were given their own symbols, several per word in
proportion to how often the word is used, chosen at random each time. Space
markers were changed from a fixed rotation to random choice. The attack was
updated for this design (see the docstring of `attack.py`):

- It finds space markers from the symbol after each single-letter word ending,
  which does not depend on their order. Markers were found in every trial.
- It knows the 100 common words and how many symbols each has, and that
  common words are never spelled out.
- It scores text with a word-pair model (which word tends to follow which),
  so it can use context to tell apart the symbols of different common words.

The budgets compared are 0 (no word symbols, as before), 510 (every shape with
at most 3 extensions) and 2,000 (uses shapes with 4 extensions). Each trial
used a new secure key. Raw results: `results_ws_800_1600.json`,
`results_ws_3200.json` and `results_ws_2000.json`.

## Results

Letters correct, then whole words correct, averaged over the trials (trials in
parentheses).

| Words | No word symbols | 510 word symbols | 2,000 word symbols |
|---:|---|---|---|
| 800 | 80% / 71% (3) | 18% / 7% (3) | not run |
| 1,600 | 99% / 96% (3) | 79% / 61% (3) | 77% / 54% (2) |
| 3,200 | 99% / 97% (2) | 84% / 69% (2) | 78% / 57% (2) |

At 800 words without word symbols, two trials reached 97–98% and one stopped
at 45%.

A single earlier trial at 6,400 words with 510 word symbols recovered about
88% of letters (measured by aligning the letter sequences, because some words
decoded to a different length). It ran before a fix to the word count, so its
word figure is not reported.

The 2,000-symbol trials used different passages from the 510-symbol trials,
because the passages are chosen per run.

## Findings

- Word symbols roughly double the text needed for a useful result. Without
  them, 800 words was usually enough to recover almost everything. With 510
  word symbols, 800 words gave 18% of letters, and 1,600–3,200 words gave about
  80% of letters and 60–70% of words.
- What remains wrong is mostly the common words. Long words are spelled with
  bigram symbols and are still recovered, so the topic and much of the meaning
  can be read. For example, a 1,600-word trial decoded "THAT IT SHOULD CONTINUE
  UNTIL ONE OF THE COMBATANTS WAS DISABLED" as "THE YOU WILL CONTINUE UNTIL THEY
  OF THE COMBATANTS OF DISABLED".
- 2,000 word symbols lowered recovery a little further than 510: by 2–6 points
  of letters and 7–12 points of whole words.

## What stopped the attack

Each trial also records the score of the real key under the attacker's model.

- At 800 words with word symbols, the real key scored far higher than the
  attack's result in every trial. The search did not find the answer, so more
  computing time or a better search could recover more.
- At 1,600 words and above with word symbols, the attack's result scored
  higher than the real key in every trial. More search would not help; the
  remaining errors are common words that a word-pair model cannot place. An
  attacker with a stronger model of English (for example, three-word
  sequences) could recover more of them.

So these results show how this attack fares, not a limit on all attacks.
Text is counted per key: several messages written with the same key add up.

---

# Extra Bigram Symbols

The default common word budget was raised to 2,000. Then the 200 most frequent
bigrams in spelled words were given 1,500 extra symbols in proportion to their
use (IN has 44 symbols, ER 33, TH 24), chosen at random each time a bigram is
written. The attack was updated to know how many symbols each bigram has.
Raw results: `results_bigram_symbols.json` and
`results_bigram_symbols_long_search.json`.

## Results

Letters correct / whole words correct, average of 2 trials. The left column
is from `results_ws_2000.json`, which used the same passages.

| Words | 2,000 word symbols | Plus 1,500 extra bigram symbols |
|---:|---|---|
| 1,600 | 77% / 54% | 14% / 5% |
| 3,200 | 78% / 57% | 8% / 3% |
| 6,400 | not run | 9% / 3% |

With 4 times the search (16,000,000 steps, about 65 minutes per trial), the
3,200-word trials recovered 8% and 8% of letters, the same as with
4,000,000 steps. Space markers were found in every trial.

## What stopped the attack

In every trial from 1,600 words up, the real key scored far higher under the
attacker's model than the attack's result (for example -23,921 against
-36,992 at 3,200 words). The model could recognise the right answer, but the
search could not find it, and four times more search did not help.

This means this attack fails, not that every attack would. With many symbols
per bigram, the search has to work out which symbols mean the same thing
before word statistics become useful, and simulated annealing did not manage
that. A different method, for example one that first groups symbols by the
contexts they appear in, might do better. So these numbers show the extra
bigram symbols defeat this attack up to at least 6,400 words, not that the
cipher is secure.

---

# Stronger Attack: Symbol Grouping and Gibbs Sampling

`attack_grouping.py` targets the extra word and bigram symbols:

- **Grouping.** Spelled cipher words of the same shape that differ in one
  position are linked, since the differing symbols often mean the same bigram.
  At 6,400 words, 52% of links between full bigram symbols were correct, and
  86% of links between single-letter symbols (by letter); at 25,600 words, 33%
  and 81%. So links are used only to propose moves.
- **Gibbs sampling.** Each symbol in turn is given a value chosen in proportion
  to how well each candidate fits with the other symbols fixed, with priors
  from the public symbol counts. Then annealing with link moves.
- **Smoother scoring.** Word frequency mixed with a letter 5-gram model, so
  partly correct words score better.

Raw results: `results_grouping.json` (20 Gibbs sweeps, 1,000,000 annealing
steps, 2 keys per length).

## Cold start (the attack as an attacker would run it)

Default settings: 2,000 word symbols and 1,500 extra bigram symbols.

| Words | Letters correct (each trial) | Real key score vs. found |
|---:|---|---|
| 1,600 | 12%, 17% (test runs) | -11,784 vs. -13,259 |
| 6,400 | 11% (test run) | -46,678 vs. -73,491 |
| 12,800 | 8%, 7% | -92,492 vs. -153,003 |
| 25,600 | 8%, 11% | -179,285 vs. -282,150 |

More text did not help: at 25,600 words the attack still recovered about 10%
of letters, and the real key scored far higher than its result.

## Warm start (how close an attacker needs to get)

`warm_start.py` starts the Gibbs sampler from the real key with part of it
replaced by the attack's own starting guesses, on a 6,400-word passage, for 6
sweeps:

| Start | Letters | Words | Score |
|---|---:|---:|---:|
| Real key | 80% | 59% | -43,943 (real key: -47,499) |
| Real key, 50% of symbols scrambled | 75% | 47% | -49,148 |
| Attack's own start (cold) | 11% | 3% | -73,491 |

## Findings

- **This attack does not break the current defaults at any length tested, up
  to 25,600 words** (roughly 50 pages) with one key.
- **The barrier is getting started.** From a cold start the search stays near
  10%. An attacker who already knew about half of the symbols' meanings
  reached 75% of letters at 6,400 words.
- **The attack's model has a ceiling of about 80% of letters at 6,400 words.**
  Even starting from the real key, it moved to readings it scored higher than
  the truth, mostly common words swapped for others. So a perfect search with
  this model would read about 80% of the text.
- **What would change this.** A better start, such as knowing some of the
  plaintext (a greeting, a name, a known phrase) or the meaning of some
  symbols from an earlier break or a captured key, would put an attacker in
  the warm-start case. A stronger model of English, for example one using
  longer word sequences, would raise the 80% ceiling. Neither was tested here.

These results show where the attacks built so far fail, not that the cipher
is secure. It is still a substitution cipher, and it has not been tested
against known-plaintext attacks or against methods beyond those described.
