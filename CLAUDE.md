# CLAUDE.md

Guidance for working in this repository.

## What this is

A single-page Shanghainese (Wu Chinese) phonology web app, served as a static
site at `noadiah.com` (see `CNAME`, GitHub Pages). Title: 上海閑話小家生.
No build system, bundler, or package manager — `index.html` loads three plain
`<script>` files directly. Open `index.html` in a browser to run it.

The UI (all in `index.html`, `lang="zh"`, labels in Shanghainese) has these panels:
- **Wugniu ⇄ IPA** — romanization to IPA, in `sinitic` and `broad` variants.
- **連讀變調 (tone sandhi)** — rich contenteditable editor with per-syllable
  boundary widgets (LPS `－` / RPS `＋` / break `✕`) and a drawn tone curve.
- **普通閑話翻上海閑話** — Mandarin → Shanghainese shallow-transfer translation.
- **尋字典發音 (dictionary lookup)** — hanzi → readings, or Wugniu → chars.

## The three loaded scripts (order matters)

`index.html` loads them in this exact order; later files depend on earlier ones:
1. `dict.js` — `const WUGNIU_PRON_DICT`, ~2.8 MB, **generated**. Keyed by
   pronunciation: `{ "<pron>": [{c: char, s: simplified, w: weight}, ...] }`.
   `index.html` builds a char-keyed index from it once at load.
2. `convert.js` — `toTraditional` / `toSimplified`, ~1.3 MB, **generated**.
   Dependency-free Simplified⇄Traditional converter, output-identical to OpenCC.
3. `translate.js` — Mandarin→Shanghainese transfer (hand-written, edit freely).

## Regenerating the data files (Python)

`dict.js` and `convert.js` are **auto-generated — never hand-edit them.**

**`dict.js` now comes from the Navi IME lexicon build** (GitHub `subaruphoe/Navi-IME`,
`Tools/lexicon/build_navi.py`, function `export_siaukasan_dict`). It shares Navi's source
normalisation, manual corrections, function-word orthography and 爲／裏 standardisation,
but keeps `-ae` finals (this site distinguishes 來／蘭; Navi only merges them for its input index)
and takes only curated sources (zaonhe, suwu, wuphin, rime, extra, manual — no corpus-predicted
words). 為／裡 spellings are emitted as aliases so lookups by either form work.
To regenerate, in the Navi repo run:

```sh
python3 Tools/lexicon/build_navi.py      # writes Data/build/siaukasan/dict.js
cp "Data/build/siaukasan/dict.js" ~/Developer/zaonheghaegho-siaukasan/dict.js
```

`build_dict.py` is the old generator, kept for reference only; don't use it for new builds.
`convert.js` is still built here:

```sh
python3.14 build_convert.py   # -> convert.js (needs `pip install opencc`)
```

`simp_trad_overrides.json` is the **shared** source of simp/trad exceptions,
read by BOTH build scripts so `dict.js`'s stored `s` field and the runtime
converter in `convert.js` can never drift. Edit exceptions there, then rerun
both scripts.

## Conventions worth knowing

- **Romanization is Wugniu.** Tone-1 (陰平) is encoded into the spelling itself,
  either as a vowel accent (`tsý`) or a yin-forcing initial (`nh`/`mh`/`lh`/`nk`,
  e.g. `nhi` = tone-1 `ni`). `apply_tone1_accent` / `applyTone1Accent` and
  `stripAccentTone1` implement this convention on both the Python and JS sides —
  keep them in sync if you touch one.
- Dictionary keys are **traditional** hanzi. User input is normalized via
  `toTraditional` before lookup; simplified is only for output.
- Weights are shown as percentages (0–100); a curated default reading is ~100.
- No test suite. Verify JS edits with `node --check <file>` and by opening
  `index.html`; the generators print entry-count summaries you can sanity-check.
- Reply, and write any docs, in the same language the user used.
