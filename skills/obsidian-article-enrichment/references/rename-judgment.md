# Rename judgment

Bryan does not rename every clipping. Whether he renames depends on the author, the site, and the format of the piece. `analyze_note.py` turns his past choices into a `rename.lean` value. This file explains how to act on it.

## How the history is measured

For each enriched clipping (one that has a `note` summary), the script compares the filename (timestamp suffix removed) with the frontmatter `title`, keeping only letters and digits. If the two match, Bryan **kept** the original title. If they differ, he **renamed** it. Punctuation changes forced by filename rules (a colon becoming ` -`, curly quotes becoming `'`) do not count as renames.

History is counted at three levels, from most to least specific:

1. This author, on this site, in this format
2. This author, on this site
3. This author, anywhere

If the author has fewer than 3 enriched notes, the script falls back to the same site with any author. The first level with 3 or more notes decides. A rename rate of 70% or more gives `rename`, 30% or less gives `keep`, and anything in between gives `unclear`.

## Formats

| format | how it's detected | rule |
|---|---|---|
| `weekly-roundup` | title starts `YYYY.NN` (e.g. `2026.42: Home At Last`) | always keep |
| `interview` | title starts `An Interview with` | always keep |
| `non-headline` | title like `Joe (@joedaroo) on X`, `Untitled` | always rename |
| `podcast` | sharptech.fm, sharpchina.fm, `podcast` or `/episode` in URL | use history |
| `update` | comma or semicolon list of topics (Stratechery daily Updates) | use history |
| `article` | anything else | use history |

## Acting on `rename.lean`

| lean | what to do |
|---|---|
| `skip` | The file was already renamed. Do nothing. |
| `keep` | Do not rename. Don't run the headline prompt. |
| `rename` | Run the headline prompt. If it returns a different headline, rename. If it returns the title unchanged, keep. |
| `unclear` | Run the headline prompt, then apply the **scan test** below. |

### The scan test (for `unclear`)

Read the original title on its own, as one line in a list of fifty, and ask whether a reader could tell what the story is about without opening it.

- **Clearly fails → rename without asking.** Examples: a question headline (`So What Was Trump Saying to South Korea on Sunday?`), a pun or allusion (`Some of All Fears`, `Home At Last`, `Begun, the Aggregator Wars Have`) on a standalone essay, no named subject, or a vague phrase hiding the news (`Important Security Update`).
- **Clearly passes → keep without asking.** The title already names who did what, with specifics (`SpaceX agrees to buy $8 billion in spectrum…`, `GM and CarPlay`, `Apple HomeView, The New Apple TV, The App Story`).
- **Neither → ask Bryan.** Show the original title, the proposed headline, and the history counts in one line, and wait for yes or no. In a batch or non-interactive run, don't rename. List the proposal in the final report instead.

## Worked examples from the vault

| title | author / site / format | history | what Bryan did |
|---|---|---|---|
| `2026.42: Home At Last` | Ben Thompson / stratechery / weekly-roundup | — | kept (format rule) |
| `An Interview with Colossus EIC Jeremy Stern…` | Ben Thompson / stratechery / interview | 8 kept, 0 renamed | kept |
| `Apple HomeView, The New Apple TV, The App Story` | Ben Thompson / stratechery / update | 58 kept, 11 renamed → `keep` | kept |
| `SpaceX Buys More Spectrum, Musk and Market Structure, Distributed Cellular` | same | `keep` | **renamed** to `SpaceX agrees to buy $8 billion in cellular spectrum from Grain Management…`. One of the minority cases; history doesn't catch every rename. |
| `Joe (@joedaroo) on X` | joedaroo / x.com / non-headline | x.com 3 kept, 11 renamed | renamed (format rule) |
| `Some of All Fears` | Andrew Sharp / sharptext / article | 3 kept, 3 renamed → `unclear` | renamed. The pun fails the scan test. |
| `Apple Enters the Uncanny Valley, The SpaceX Play for Cellular, Q&A…` | Sharp + Thompson / sharptech.fm / podcast | 4 kept, 2 renamed → `unclear` | kept. The topic list passes the scan test. |

## Backtest (October 2026, 1,098 enriched clippings, leave-one-out)

History alone decides 31% of notes and matches Bryan's choice in 76% of those. The rest come out `unclear`, which is why the scan test carries real weight. Bryan decides most renames article by article, so judge the title itself and use the history only as a tiebreaker.
