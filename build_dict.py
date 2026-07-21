"""
Builds dict.js from two sources:
  1. wugniu_zaonhe_dic.yaml  - primary, curated character->pronunciation(+weight) data.
  2. wugniu_suwu.dict.yaml   - supplementary source used ONLY to (a) mark tone-1 (陰平)
     readings by embedding the accent directly into the stored pronunciation string
     (matching this app's existing accent convention - see applyTone1Accent/
     stripAccentTone1 in index.html), and (b) add pronunciations wugniu_zaonhe_dic.yaml
     is missing.

Output format is pronunciation-keyed (not character-keyed):
    WUGNIU_DICT = { "<pronunciation>": [{"c": char, "s": simp, "w": weight}, ...], ... }
Tone-1 readings get their own key (accented spelling), separate from the plain/other-tone
key for the same base - e.g. "tsy" and "tsý" are different keys. index.html builds a
character-keyed index from this once at load (mirrors how SIMP_MAP is already derived).
"""
import re, json, os
from opencc import OpenCC

ZAONHE_SRC = '/Users/subarupan/Developer/wugniu_zaonhe_dic.yaml'
SUWU_SRC = '/Users/subarupan/Developer/wugniu_suwu.dict.yaml'
# Companion word/phrase lists from the same repo as SUWU_SRC. Neither carries a pronunciation
# column (Rime derives a word's reading by concatenating its characters' own readings), so we
# do the same here using each character's already-merged default reading.
WORD_SRCS = [
    '/Users/subarupan/Developer/wuphin.word.dict.yaml',
    '/Users/subarupan/Developer/wuphin.phrases.dict.yaml',
]
# These are synthetic (concatenated, not independently attested) readings with no frequency
# data of their own, so they're weighted well below the ~100 baseline used by genuinely curated
# primary entries (zaonhe) - present and matchable, but never outrank a real curated reading.
NEW_WORD_WEIGHT = 50
OUT = '/Users/subarupan/Developer/zaonheghaegho-siaukasan/dict.js'

# Hand-curated entries not present in any source YAML (verified readings supplied directly).
# {char/word: [(pronunciation, weight), ...]}. Applied last, overriding any auto-derived entry
# for the same key so these readings are authoritative.
MANUAL_ENTRIES = {
    '𡋤': [('he', 100)],           # replicated-form final of "在", reads he
    '垃𡋤': [('laq he', 100)],     # "在" (replicated form)
    '垃垓': [('laq ke', 100)],     # "在" (replicated form); 垓 here reads ke, not the dict's ké
}
# Simp/trad exceptions come from the shared overrides file (same file the runtime converter,
# build_convert.py, reads) so the dict's stored 's' field and the on-page converter can't drift.
# 'invariant' chars are never converted in either direction; here that means the stored simplified
# form = the char itself. Explicit t2s remaps also apply to the 's' field.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simp_trad_overrides.json'),
          encoding='utf-8') as _f:
    _ov = json.load(_f)
SIMP_OVERRIDES = {ch: ch for ch in _ov.get('invariant', [])}
SIMP_OVERRIDES.update(_ov.get('t2s', {}))

WUGNIU_INITIALS_SINITIC = ["ph", "p", "b", "m", "f", "v", "mh", "th", "t", "d", "n", "l",
    "nh", "nk", "lh", "tsh", "ts", "s", "z", "ch", "c", "j", "gn", "sh", "zh",
    "kh", "k", "g", "gh", "ng", "h"]
W_INITS = sorted(WUGNIU_INITIALS_SINITIC, key=len, reverse=True)
WUGNIU_FINALS_SINITIC = set(["a", "o", "au", "eu", "e", "oe", "i", "ia", "io", "iau", "ieu",
    "ie", "u", "ua", "ue", "uoe", "iu", "ioe", "an", "aon", "en", "on", "aq", "oq", "eq",
    "ian", "iaon", "in", "ion", "iaq", "ioq", "iq", "uan", "uaon", "uen", "uaq", "ueq",
    "iun", "iuq", "er", "y"])
YANG_INITIALS = set(["b", "d", "v", "z", "j", "zh", "g", "gh", "gn", "m", "n", "l", "ng"])
# This app already has a dedicated "yin-forcing" spelling for tone-1 on these four yang
# initials (nhi = tone-1 "ni", not accented "ní" - see YIN_FORCING_INITIALS in index.html),
# so tone-1 readings on these initials must be canonicalized to that spelling, not accented,
# or they'd end up as silent duplicates of already-curated entries (nh/mh/lh/nk vs n/m/l/ng+accent).
YIN_FORCE_MAP = {"m": "mh", "n": "nh", "l": "lh", "ng": "nk"}
ACCENT_MAP = {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "y": "ý"}
DEACCENT_MAP = {v: k for k, v in ACCENT_MAP.items()}


def unsimplify_glides(rom):
    if rom.startswith("yi"):
        suf = rom[2:]
        if suf == "" or suf.startswith("n") or suf.startswith("q"):
            return "ghi" + suf
        return rom
    if rom.startswith("y"):
        return "ghi" + rom[1:]
    if rom.startswith("wu"):
        suf = rom[2:]
        if suf == "":
            return "ghu"
        return rom
    if rom.startswith("w"):
        return "ghu" + rom[1:]
    return rom


def split_init_final(rom):
    for init in W_INITS:
        if rom.startswith(init):
            return init, rom[len(init):]
    return "", rom


def normalize_final(rest):
    # wugniu_suwu spells a couple of finals more finely than this app's simplified
    # scheme distinguishes; both normalizations match how wugniu_zaonhe_dic.yaml
    # already spells the very same characters (verified against 知/之/支/朱, 捌/刮/甲).
    rest = re.sub(r'aeq$', 'aq', rest)
    rest = re.sub(r'(?<!i)yu$', 'y', rest)
    return rest


def deaccent(pron):
    return "".join(DEACCENT_MAP.get(ch, ch) for ch in pron)


FORCE_TO_PLAIN = {v: k for k, v in YIN_FORCE_MAP.items()}  # {"mh":"m","nh":"n","lh":"l","nk":"ng"}


def is_tone1_spelling(pron):
    """A reading is tone-1 if it carries a vowel accent, OR its initial is one of the
    yin-forcing spellings (nh/mh/lh/nk), which imply tone-1 without any accent mark."""
    if deaccent(pron) != pron:
        return True
    init, _ = split_init_final(pron)
    return init in FORCE_TO_PLAIN


def canonical_base(pron):
    """Base spelling for matching readings across tone-1 encodings: strips vowel accents
    and normalizes a yin-forcing initial back to its plain yang counterpart, so "ní", "ni"
    and "nhi" (three ways this app / new source can spell the same syllable) all compare
    equal regardless of how tone-1 happens to be marked on it."""
    plain = deaccent(pron)
    init, rest = split_init_final(plain)
    if init in FORCE_TO_PLAIN:
        return FORCE_TO_PLAIN[init] + rest
    return plain


def apply_tone1_accent(plain_syl):
    init, rest = split_init_final(plain_syl)
    # Devoiced initials already fully express tone-1 on their own (see the "yin" check at each
    # call site) - accenting on top would be redundant/wrong, so leave them untouched.
    if init in FORCE_TO_PLAIN:
        return plain_syl
    # A leading i/u in the final is a glide (onset), not the syllable nucleus, whenever another
    # accentable vowel follows it (ia -> nucleus a, uaon -> nucleus a); accent that vowel instead
    # of the glide. Otherwise (bare i/u, or i/u followed only by a consonant coda) the i/u IS the
    # nucleus and gets accented directly.
    start = 1 if len(rest) >= 2 and rest[0] in ("i", "u") and rest[1] in ACCENT_MAP else 0
    for i in range(start, len(rest)):
        if rest[i] in ACCENT_MAP:
            return init + rest[:i] + ACCENT_MAP[rest[i]] + rest[i + 1:]
    for i, ch in enumerate(rest):
        if ch in ACCENT_MAP:
            return init + rest[:i] + ACCENT_MAP[ch] + rest[i + 1:]
    return plain_syl


def parse_register(base):
    """Returns (register, normalized_final) or (None, None) if unparseable."""
    rom = unsimplify_glides(base)
    init, rest = split_init_final(rom)
    rest = normalize_final(rest)
    if rest not in WUGNIU_FINALS_SINITIC:
        return None, None
    register = "yang" if init in YANG_INITIALS else "yin"
    return register, rest


# ---------- Step 1: parse primary zaonhe source (same logic as inject_dict.py) ----------
dict_data = {}
with open(ZAONHE_SRC, encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        word = parts[0].strip()
        pronunciation = parts[1].strip()
        weight = 100
        is_percentage = True
        if len(parts) >= 3:
            weight_str = parts[2].strip()
            if weight_str:
                is_percentage = '%' in weight_str
                weight_str_clean = weight_str.replace('%', '')
                try:
                    weight = float(weight_str_clean)
                except ValueError:
                    weight = 100
                    is_percentage = True
        if word not in dict_data:
            dict_data[word] = []
        existing = [p['pronunciation'] for p in dict_data[word]]
        if pronunciation not in existing:
            dict_data[word].append({'pronunciation': pronunciation, 'weight': weight, 'is_percentage': is_percentage})

print(f"[zaonhe] {len(dict_data)} words loaded")

# ---------- Step 1.5: merge intra-source duplicate readings ----------
# wugniu_zaonhe_dic.yaml sometimes lists both the plain and devoiced/yin-forcing spelling of
# the exact same underlying reading as separate entries (e.g. 咪 has both "mi" and "mhi", 姆 has
# both "m" and "mh") - collapse each such group to one entry per canonical base, preferring the
# tone-1-marked (devoiced) spelling when the group has one, since that's the more informative
# spelling. Doing this before the wugniu_suwu merge below also prevents it from creating fresh
# duplicates: without this, two pre-existing entries sharing a canonical base would collide in
# existing_by_base (whichever is built last silently wins), so an upgrade could land on the
# wrong one and leave the other as an untouched, now-redundant leftover.
self_dedup_merged = 0
for word, entries in dict_data.items():
    by_base = {}
    for e in entries:
        # canonical_base assumes a single syllable (one initial + one final); multi-syllable
        # phrase pronunciations ("iq fen") would collide on it spuriously (e.g. two candidate
        # readings differing only in which syllable carries a tone-1 accent), so only dedupe
        # single-syllable entries here.
        key = canonical_base(e['pronunciation']) if ' ' not in e['pronunciation'] else e['pronunciation']
        by_base.setdefault(key, []).append(e)
    if all(len(group) == 1 for group in by_base.values()):
        continue
    new_entries = []
    for base, group in by_base.items():
        if len(group) == 1:
            new_entries.append(group[0])
            continue
        self_dedup_merged += len(group) - 1
        tone1_variant = next((e for e in group if is_tone1_spelling(e['pronunciation'])), None)
        winner = tone1_variant if tone1_variant is not None else group[0]
        winner['weight'] = max(e['weight'] for e in group)
        new_entries.append(winner)
    dict_data[word] = new_entries

print(f"[dedup] merged {self_dedup_merged} intra-source duplicate readings (same base, different spelling)")

# ---------- Step 2: parse wugniu_suwu.dict.yaml ----------
# char -> { normalized_pron (accented if tone1): occurrence_count }
suwu_readings = {}
# char -> total occurrence count (for tone1-dominance probability)
suwu_totals = {}
suwu_tone1 = {}

stats = {'total': 0, 'skipped_multichar': 0, 'skipped_etymological': 0,
         'skipped_unparseable': 0, 'skipped_register_mismatch': 0,
         'skipped_no_tone1_notation': 0, 'kept': 0}

with open(SUWU_SRC, encoding='utf-8') as f:
    for line in f:
        line = line.rstrip('\n')
        if not line or line.startswith('#') or line.startswith('---') or line.startswith('...'):
            continue
        parts = line.split('\t')
        if len(parts) < 2:
            continue
        char, pron = parts[0], parts[1]
        m = re.match(r'^([a-zA-Z]+)([0-9])$', pron)
        if not m:
            continue
        stats['total'] += 1
        base, digit = m.group(1), m.group(2)

        if len(parts) >= 4:
            comment = parts[3]
            if '又音' not in comment:
                stats['skipped_etymological'] += 1
                continue

        if len(char) != 1:
            stats['skipped_multichar'] += 1
            continue

        register, norm_final = parse_register(base)
        if register is None:
            stats['skipped_unparseable'] += 1
            continue

        expected = "yin" if digit in "1357" else "yang"
        if digit != "1" and register != expected:
            stats['skipped_register_mismatch'] += 1
            continue

        init, _ = split_init_final(unsimplify_glides(base))
        plain_pron = init + norm_final
        is_tone1 = (digit == "1")
        # An accent mark signals "this yin syllable, whose tone would otherwise be ambiguous,
        # is specifically tone-1" - it's only meaningful for yin syllables. A yang-register
        # syllable can only lexically be tone-1 via a devoiced (yin-forcing) spelling - m/n/l
        # all have one attested before a vowel (mhi, nha, lhu, ...); "nk" (ng's) is only ever
        # attested bare (五/伍/兒 = plain "ng"), never before a vowel. So a yang syllable with no
        # attested devoiced spelling for its position (e.g. "ngu1") has no established way to
        # mark tone-1 in this romanization - rather than invent one (accenting a yang vowel),
        # skip it and leave whatever reading is already on file untouched.
        if is_tone1 and register == "yin":
            final_pron = apply_tone1_accent(plain_pron)
        elif is_tone1 and init in YIN_FORCE_MAP and (init != "ng" or norm_final == ""):
            final_pron = YIN_FORCE_MAP[init] + norm_final
        elif is_tone1:
            stats['skipped_no_tone1_notation'] += 1
            continue
        else:
            final_pron = plain_pron

        suwu_totals[char] = suwu_totals.get(char, 0) + 1
        if is_tone1:
            suwu_tone1[char] = suwu_tone1.get(char, 0) + 1
        bucket = suwu_readings.setdefault(char, {})
        bucket[final_pron] = bucket.get(final_pron, 0) + 1
        stats['kept'] += 1

print(f"[suwu] {stats}")
print(f"[suwu] distinct characters with usable readings: {len(suwu_readings)}")

# ---------- Step 3+4: merge into dict_data ----------
new_chars = 0
upgraded = 0
added_readings = 0
promoted = 0

for char, bucket in suwu_readings.items():
    total_occ = suwu_totals[char]
    tone1_occ = suwu_tone1.get(char, 0)
    tone1_frac = tone1_occ / total_occ if total_occ else 0
    max_occ = max(bucket.values())

    if char not in dict_data:
        dict_data[char] = []
        new_chars += 1

    entries = dict_data[char]
    existing_by_base = {canonical_base(e['pronunciation']): e for e in entries}

    promoted_pron = None
    for pron, occ in bucket.items():
        base = canonical_base(pron)
        is_tone1 = is_tone1_spelling(pron)
        existing = existing_by_base.get(base)
        if existing is not None:
            if is_tone1 and not is_tone1_spelling(existing['pronunciation']):
                existing['pronunciation'] = pron
                existing_by_base[base] = existing
                upgraded += 1
            if is_tone1:
                promoted_pron = existing_by_base[base]
        else:
            weight = round(100 * occ / max_occ) if not entries else max(5, round(40 * occ / max_occ))
            new_entry = {'pronunciation': pron, 'weight': weight, 'is_percentage': True}
            entries.append(new_entry)
            existing_by_base[base] = new_entry
            added_readings += 1
            if is_tone1:
                promoted_pron = new_entry

    if tone1_frac >= 0.5 and promoted_pron is not None:
        current_max = max((e['weight'] for e in entries), default=0)
        if promoted_pron['weight'] <= current_max:
            # Promote to the top without ever exceeding 100 (weights are displayed as
            # percentages) - demote whichever sibling(s) were tied for the old max so the
            # promoted tone-1 reading is unambiguously the new default.
            for e in entries:
                if e is not promoted_pron and e['weight'] >= 100:
                    e['weight'] = 90
            promoted_pron['weight'] = 100
            promoted += 1

print(f"[merge] new characters added: {new_chars}, existing readings upgraded to tone1: {upgraded}, "
      f"new readings added: {added_readings}, readings promoted to dominant: {promoted}")


def default_reading(char):
    entries = dict_data.get(char)
    if not entries:
        return None
    return max(entries, key=lambda e: e['weight'])['pronunciation']


# ---------- Step 4.5: absorb multi-character words (improves phrase segmentation) ----------
# Run after the character-level merge above so every character's reading set (existing +
# wugniu_suwu-derived) is already final before we borrow from it.
words_added = 0
words_extended = 0
words_skipped_missing_char = 0

for src in WORD_SRCS:
    with open(src, encoding='utf-8') as f:
        past_frontmatter = False
        for line in f:
            line = line.rstrip('\n')
            if not past_frontmatter:
                if line == '...':
                    past_frontmatter = True
                continue
            word = line.split('\t')[0].strip()
            if len(word) < 2:
                continue
            readings = [default_reading(c) for c in word]
            if any(r is None for r in readings):
                words_skipped_missing_char += 1
                continue
            pron = ' '.join(readings)
            if word not in dict_data:
                dict_data[word] = [{'pronunciation': pron, 'weight': NEW_WORD_WEIGHT, 'is_percentage': True}]
                words_added += 1
            else:
                existing_prons = [e['pronunciation'] for e in dict_data[word]]
                if pron not in existing_prons:
                    dict_data[word].append({'pronunciation': pron, 'weight': NEW_WORD_WEIGHT, 'is_percentage': True})
                    words_extended += 1

print(f"[words] added {words_added} new word entries, extended {words_extended} existing words "
      f"with an alternate reading, skipped {words_skipped_missing_char} (a character had no dict data)")

# ---------- Step 4.6: apply hand-curated overrides ----------
# Last write wins: fully replace any auto-derived entry so the supplied readings are canonical.
for key, readings in MANUAL_ENTRIES.items():
    dict_data[key] = [{'pronunciation': p, 'weight': w, 'is_percentage': True} for p, w in readings]
print(f"[manual] applied {len(MANUAL_ENTRIES)} hand-curated entries")

# ---------- Step 4.7: merge rime ie -> i (accent é->í), preserving 廿 ----------
# This variety does not contrast final -ie against -i, so collapse every syllable-final `ie`/`ié`
# onto `i`/`í`. ONLY the character 廿 (reads "gnie") keeps its ie; every other char on a gnie/*ie
# reading converts (gnie->gni, pié->pí, ...). `ieu`/`ien`/`ieq` are NOT final-ie (they end u/n/q),
# so a suffix test on 'ie'/'ié' leaves them untouched. Run here, before Step 5, so per-char weight
# percentages re-normalize naturally and Step 6 inversion aggregates collisions (pié ∪ pí) for free.
IE_FREEZE_CHARS = {'廿'}

def merge_ie_final(syl):
    if syl.endswith('ié'):
        return syl[:-2] + 'í'
    if syl.endswith('ie'):
        return syl[:-2] + 'i'
    return syl

_ie_words = 0
_ie_collapsed = 0
for word, entries in dict_data.items():
    chars = list(word)
    changed = False
    for e in entries:
        syls = e['pronunciation'].split(' ')
        if len(syls) == len(chars):        # 1:1 syllable<->char: freeze only the 廿 slot
            new = [s if chars[i] in IE_FREEZE_CHARS else merge_ie_final(s) for i, s in enumerate(syls)]
        elif word in IE_FREEZE_CHARS:       # standalone 廿 (any spacing): never touch
            new = syls
        else:                               # count mismatch (rare): transform all syllables
            new = [merge_ie_final(s) for s in syls]
        np = ' '.join(new)
        if np != e['pronunciation']:
            e['pronunciation'] = np
            changed = True
    if not changed:
        continue
    _ie_words += 1
    seen = {}                               # dedup readings that collapsed onto one pron (max weight)
    for e in entries:
        p = e['pronunciation']
        if p in seen:
            seen[p]['weight'] = max(seen[p]['weight'], e['weight'])
            _ie_collapsed += 1
        else:
            seen[p] = e
    dict_data[word] = list(seen.values())

print(f"[ie->i] rewrote {_ie_words} words, collapsed {_ie_collapsed} duplicate readings; 廿 preserved")

# ---------- Step 5: finalize per-character records (mirrors inject_dict.py tail) ----------
cc = OpenCC('t2s')
final_dict = {}
for word in dict_data:
    dict_data[word].sort(key=lambda x: x['weight'], reverse=True)
    prons = [x['pronunciation'] for x in dict_data[word]]

    numericals = [x['weight'] for x in dict_data[word] if not x['is_percentage']]
    total_numerical = sum(numericals)

    pws = []
    for x in dict_data[word]:
        if x['is_percentage']:
            pws.append(round(x['weight']))
        else:
            pws.append(round((x['weight'] / total_numerical) * 100) if total_numerical > 0 else 100)

    max_weight = dict_data[word][0]['weight'] if dict_data[word] else 100
    # Normally convert the whole word (keeps OpenCC's phrase-level context). Only when the word
    # contains an override char (e.g. 睏) do we go per-char so that char can be pinned without
    # disturbing OpenCC's handling of the rest.
    if any(ch in SIMP_OVERRIDES for ch in word):
        simp = ''.join(SIMP_OVERRIDES.get(ch, cc.convert(ch)) for ch in word)
    else:
        simp = cc.convert(word)
    final_dict[word] = {"s": simp, "p": prons, "pw": pws, "w": max_weight}

print(f"[final] {len(final_dict)} character/word entries")

# ---------- Step 6: invert into pronunciation-keyed structure ----------
pron_dict = {}
for char, data in final_dict.items():
    for pron, w in zip(data['p'], data['pw']):
        pron_dict.setdefault(pron, []).append({"c": char, "s": data['s'], "w": w})

for pron in pron_dict:
    pron_dict[pron].sort(key=lambda e: e['w'], reverse=True)

print(f"[pron-keyed] {len(pron_dict)} distinct pronunciation keys")

js_dict = json.dumps(pron_dict, ensure_ascii=False)
js_content = f"const WUGNIU_PRON_DICT = {js_dict};\n"
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(js_content)

print("Dictionary written to dict.js successfully")
