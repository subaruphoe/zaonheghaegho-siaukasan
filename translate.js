// AUTO-LOADED after dict.js + convert.js. Mandarin -> Shanghainese shallow transfer.
// Pipeline: [0] normalize (toTraditional, convert.js) -> [1] tokenize + coarse tag ->
// [2] structural reorder rules -> [3] lexical substitution -> Shanghainese hanzi.
// [4] Wugniu/IPA reuses the existing dictionary+sandhi engine on the output string.
// This file covers [1]-[3]; stage [2] currently has ONE rule: motion-verb postposition
// (他去上海 -> 伊到上海去; bare 伊去上海 is ungrammatical in Shanghainese).

// ===== [1]/[3] seed lexicon: Mandarin word -> {tag, wu?} =================
// tag = coarse POS for the chunker/rules. wu = Shanghainese form emitted in [3];
// absent = keep original chars (word shared by both varieties). STARTER table (M1 expands
// it); every wu form here is verified against dict.js or supplied by the user.
const WU_LEX = {};
// OpenCC s2t picks some less-common traditional variants (为->爲, 里->裏), but a user typing
// traditional directly may use 為/裡. Collapse such variants to one canonical form for lexicon
// KEYS and LOOKUPS only (output tokens are unaffected), so either input variant matches.
const CHARVAR = { "爲": "為", "裏": "裡", "羣": "群", "峯": "峰", "衆": "眾" };
function _canon(s) { let o = ""; for (const c of s) o += CHARVAR[c] || c; return o; }
// wu may be a string or an array [primary, ...alternates]; several Mandarin words have >1 valid
// Shanghainese form (錢 = 銅鈿/鈔票). We emit the primary; alts are kept for a future UI chooser.
function _wl(tag, words, wu) {
    for (const w of words) {
        const rec = { tag };
        if (wu) { const a = Array.isArray(wu) ? wu : [wu]; rec.wu = a[0]; if (a.length > 1) rec.alts = a.slice(1); }
        WU_LEX[_canon(w)] = rec;
    }
}
function _lex(tok) { return WU_LEX[_canon(tok)]; }   // variant-tolerant lookup

_wl("V_MOTION", ["去", "來"]);          // trigger the postposition rule
_wl("COV", ["到"]);                      // coverb the rule inserts before the place
_wl("PRON", ["他", "她", "它"], "伊");   // 3sg -> 伊 (user-confirmed)
_wl("PRON", ["你"], "儂");               // 2sg -> 儂
_wl("PRON", ["我們", "咱們"], "阿拉");   // 1pl -> 阿拉
_wl("PRON", ["你們"], "㑚");             // 2pl -> 㑚 (na)
_wl("PRON", ["他們", "她們", "它們"], "伊拉"); // 3pl -> 伊拉 (matches 伊)
_wl("PRON", ["我"]);                     // 1sg kept as-is
// place nouns (help the reorder guard recognise a directional complement)
_wl("N_PLACE", ["上海", "北京", "蘇州", "杭州", "南京", "香港", "學校", "公司",
    "醫院", "銀行", "飯店", "商店", "市場", "車站", "機場", "家", "屋裏", "辦公室"]);
// common verbs — listed so a verb right after 去/來 is recognised as NOT a place
// (去買菜 = purposive V+VP, must NOT reorder), which is the rule's key guard.
_wl("V", ["買", "賣", "喫", "吃", "看", "白相", "玩", "做", "寫", "讀", "學",
    "走", "跑", "坐", "等", "工作", "上班", "睏覺", "睡覺", "困覺", "洗澡", "燒飯"]);
// Proximal demonstrative (這) series — all dict-verified (搿 geq / 迭 diq root, 迭 as alt).
// Distal (那) series is intentionally NOT here yet: no 那-compound has a verified Wu reading
// and the attested "that one" 伊個 collides with 伊=3sg — awaiting the user's dialectal call.
_wl("DEM", ["這", "這個"], ["搿個", "迭個"]);   // this / this one
_wl("DEM", ["這樣", "這麼", "這麼樣"], ["搿能", "迭能"]); // this way/so
_wl("N_PLACE", ["這裡", "這兒", "這邊"], ["搿搭", "搿邊"]); // here (搿搭 geq taq, user pref; 搿邊 alt)
_wl("ADV", ["現在", "目前"], ["箇歇", "現在"]);          // now (箇歇 geq shiq; 現在 yi ze both OK)
// Distal (那) series — user: give both roots, 埃(é) primary + 伊(yi) as an alternate. Compounds
// aren't in dict.js as whole entries but read char-wise (埃個 = é ku, 埃搭 = é taq, 埃能 = é nen).
_wl("DEM", ["那", "那個"], ["埃個", "伊個"]);   // that / that one (伊個 = attested yi gheq)
_wl("DEM", ["那樣", "那麼", "那麼樣"], ["埃能", "伊能"]); // that way/so
_wl("N_PLACE", ["那裡", "那兒", "那邊"], ["埃搭", "埃邊"]); // there (mirrors 搿搭)
// wh-words (all dict-verified). 為什麼->為啥 (為=we 啥=sa, emitted char-wise).
_wl("PRON_WH", ["怎麼", "怎樣", "怎麼樣"], "哪能");
_wl("PRON_WH", ["多少"], "幾化");
_wl("PRON_WH", ["為什麼", "為何"], "為啥");
// 什麼(what) series -> 啥. Idiomatic compounds have their own Wu word (什麼時候 = 啥辰光, not
// 啥時候); bare 什麼 -> 啥 catches the rest. 什麼 is a SPLIT_HEAD so ICU-glued 什麼X (e.g.
// 什麼顏色) that isn't a keyed compound splits and each half maps compositionally (啥顏色).
_wl("PRON_WH", ["什麼", "啥"], "啥");
_wl("N", ["什麼東西"], "啥物事");
_wl("N", ["什麼時候", "什麼時間"], "啥辰光");
_wl("N", ["什麼人", "誰"], "啥人");
// wh-place -> 何裏 (user; verified gha li), 啥地方 kept as alt. N_PLACE so motion reorder works
// (你去哪裡 -> 儂到何裏去).
_wl("N_PLACE", ["什麼地方", "哪裡", "哪兒"], ["何裏", "啥地方"]);
// negation (user orthography: 弗). Compounds glued by ICU need their own keys.
_wl("NEG", ["不要", "別"], "覅");
_wl("NEG", ["沒有", "沒"], "嘸沒");
_wl("NEG", ["不"], "弗");
_wl("NEG", ["不是"], "弗是");
_wl("NEG", ["不好"], "弗好");
// function words / boundaries
// Structural particle 的 -> 个 (gheq). Only a STANDALONE 的 token reaches here: ICU keeps bound
// 的 inside a word (目的/的確/似的) as one token, so _lex hits the compound first and never sees
// a particle. Glued possessives (我的) are peeled by TAIL below; ICU-split traps (是的/打的/的士,
// where 的 is NOT a particle) are re-merged & protected via their whole-word keys further down.
_wl("DE", ["的"], "个");
_wl("PART", ["有的"], ["有眼", "有點"]);   // "some" (user); NOT possessive-的
_wl("N", ["的士"]);   _wl("V", ["打的"]);   _wl("SFP", ["是的"]); // 的 here is bound, keep as-is
_wl("ASP", ["了", "著", "过", "過"]);
_wl("SFP", ["嗎"], "伐");                 // yes/no particle (compat orthography 伐)
_wl("SFP", ["呢", "吧"]);
_wl("PREP", ["把", "被", "比"]);
_wl("PROG", ["在", "正在"]);              // progressive; -> 垃拉 before a verb (rule, not blind sub)
_wl("DAT", ["給"], "撥");                 // give/dative; both 撥我本書 & 撥本書我 OK (variant swap)
_wl("CONN", ["和", "跟", "同"]);
// content-word substitutions - each verified in dict.js, no harmful homograph clash.
_wl("V", ["喜歡"], "歡喜");   _wl("V", ["知道"], "曉得");   _wl("V", ["說"], "講");
_wl("V", ["玩", "玩兒"], "白相"); _wl("V", ["找"], "尋");   _wl("V", ["藏"], "囥");
_wl("V", ["睡覺", "睡"], "睏覺");
_wl("N", ["東西"], "物事");   _wl("N", ["客人"], "人客");   _wl("N", ["熱鬧"], "鬧熱");
_wl("N", ["太陽"], "日頭");   _wl("N", ["今天"], "今朝");   _wl("N", ["明天"], "明朝");
_wl("N", ["昨天"], "昨日");   _wl("N", ["時候"], "辰光");   _wl("N", ["小孩", "小孩兒"], "小囡");
_wl("N", ["錢"], ["銅鈿", "鈔票"]);           // both valid (user)
_wl("N", ["玩具"], "白相幹");                 // 玩(白相)+具 differs; 玩具 has its own Wu word
// degree adverbs, layered (user): 很 -> 老 (everyday); 非常/特別/十分 -> 交關/邪氣 (stronger)
_wl("ADV", ["很"], ["老", "交關"]);
_wl("ADV", ["非常", "特別", "十分", "極"], ["交關", "邪氣"]);

// place-name/locative suffix heuristic for OOV nouns (≥2 chars ending in these count as a place:
// used both by the motion reorder and to keep locative 在 from being read as progressive).
const PLACE_SUFFIX = new Set(["市", "省", "縣", "区", "區", "州", "路", "街", "村", "鎮", "國",
    "館", "院", "室", "廳", "場", "樓", "房", "園", "所", "站", "廠", "局", "店", "校", "司"]);
// numeral chars (numbers + measure words read as nominal by the chunker)
const NUMERALS = new Set("零一二三四五六七八九十百千萬兩几幾".split(""));
const MEASURES = new Set("個个隻只張张本杯碗條条塊块".split(""));
// ===== [1] tokenize =====================================================
function _isHan(cp) {
    return (cp >= 0x3400 && cp <= 0x9FFF) || (cp >= 0xF900 && cp <= 0xFAFF) ||
           (cp >= 0x20000 && cp <= 0x2FA1F); // incl. CJK ext-B (surrogate pairs)
}
// Base segmentation = Intl.Segmenter (ICU's own Mandarin word dictionary). We deliberately
// do NOT segment with WUGNIU_DICT: that's a *pronunciation* dict full of Shanghainese
// collocations (你去, 去學…) that would wrongly glue Mandarin word boundaries.
// Then one re-chunk pass merges adjacent segments that form a WU_LEX multi-char key (ICU
// splits e.g. 睏覺->睏|覺, but we want it whole for tagging/substitution).
let _wlMax = 1;
function _wlMaxLen() {
    if (_wlMax > 1) return _wlMax;
    for (const k of Object.keys(WU_LEX)) { const n = [...k].length; if (n > _wlMax) _wlMax = n; }
    return _wlMax;
}
const _segmenter = (typeof Intl !== "undefined" && Intl.Segmenter)
    ? new Intl.Segmenter("zh", { granularity: "word" }) : null;

// ICU sometimes glues a closed-class rightward-attaching head onto its complement
// (不知道, 很好, 多少錢). Peel these heads so the head token can be tagged/substituted.
// 很/多少 are safe to peel whenever the whole isn't itself a lexicon entry (they almost never
// start a bound word). 不 is peeled only if it's not a known 不-compound (NOPEEL) — those are
// non-compositional ("不過"=however, not "not-pass"). Content heads (玩, 別) are NOT listed,
// so 玩具/別人 stay whole.
const SPLIT_HEADS = ["什麼", "多少", "很", "不"];   // longest-first
const NOPEEL = new Set(["不過", "不但", "不僅", "不管", "不論", "不如", "不妨", "不料", "不必"]);
// 在 (progressive) and 的 (possessive particle) both get glued by ICU onto a preceding pronoun
// (我在, 我的, 他的). Peel them off the END only when the leading part is itself a lexicon word (a
// pronoun) — so 現在/存在 and 目的/的確 (prefix not in lex) stay whole. 的 then -> 个 via lexSub.
const TAIL = new Set(["在", "的"]);
// ICU also glues 什麼 onto a PRECEDING verb as its object (做什麼, 幹什麼, 說什麼). Peel a trailing
// 什麼 off the END so it maps to 啥 (做什麼 -> 做啥). Unlike 在, the prefix need NOT be a lexicon
// word (幹 isn't listed). Keyed 什麼-compounds (為什麼->為啥) are already returned whole above.
const TAIL_WH = "什麼";
const PRON_HEADS = new Set(["他", "她", "它", "你", "我"]);   // singular; plurals are keyed & safe
function _peel(tok) {
    if (_lex(tok) || NOPEEL.has(_canon(tok))) return [tok];
    const cps = [...tok];
    const wh = [...TAIL_WH];
    if (cps.length > wh.length && cps.slice(-wh.length).join("") === TAIL_WH)
        return [..._peel(cps.slice(0, -wh.length).join("")), TAIL_WH];
    if (cps.length >= 2 && TAIL.has(cps[cps.length - 1]) && _lex(cps.slice(0, -1).join("")))
        return [..._peel(cps.slice(0, -1).join("")), cps[cps.length - 1]];
    // ICU glues some singular-pronoun + verb pairs (他說, 你說) but not others (他喫). Peel a
    // leading singular pronoun off when the remainder is a lexicon VERB — so 他說->他+說 (->伊講)
    // but 他人/他鄉 (人/鄉 not verbs) and keyed plurals 他們/你們 (returned whole above) stay intact.
    if (cps.length >= 2 && PRON_HEADS.has(cps[0])) {
        const rest = cps.slice(1).join(""), rl = _lex(rest);
        if (rl && (rl.tag === "V" || rl.tag === "V_MOTION")) return [cps[0], ..._peel(rest)];
    }
    for (const h of SPLIT_HEADS) {
        const hcps = [...h];
        if (cps.length > hcps.length && cps.slice(0, hcps.length).join("") === h)
            return [h, ...(_peel(cps.slice(hcps.length).join("")))]; // recurse on remainder
    }
    return [tok];
}
function tokenize(text) {
    let base;
    if (_segmenter) base = [..._segmenter.segment(text)].map(s => s.segment);
    else base = [...text];                                // fallback: per-codepoint
    base = base.flatMap(_peel);
    // longest-match merge over WU_LEX keys (variant-tolerant)
    const max = _wlMaxLen(), out = [];
    let i = 0;
    while (i < base.length) {
        let merged = null;
        for (let L = Math.min(max, base.length - i); L >= 2; L--) {
            const cand = base.slice(i, i + L).join("");
            if (_lex(cand)) { merged = cand; i += L; break; }
        }
        if (merged) { out.push(merged); continue; }
        out.push(base[i]); i++;
    }
    return out;
}
// ===== [1] tag ==========================================================
function tag(tok) {
    const hit = _lex(tok); if (hit) return hit.tag;
    const cps = [...tok];
    if (cps.length && !_isHan(cps[0].codePointAt(0))) return "PUNCT";
    if (cps.every(c => NUMERALS.has(c) || MEASURES.has(c))) return "NUM";
    if (cps.length >= 2 && PLACE_SUFFIX.has(cps[cps.length - 1])) return "N_PLACE";
    return "N"; // default: treat OOV Han word as a noun
}
// A token counts as "nominal" for the directional complement chunk.
function _isNominal(t) {
    return t === "N" || t === "N_PLACE" || t === "NUM" || t === "PRON" || t === "DE";
}

// ===== [2] structural rule: motion-verb postposition ====================
// V_MOTION(去/來) + [nominal chunk] -> 到 + [chunk] + V_MOTION.
// The chunk is the maximal nominal run after the verb; if it's empty (a verb follows,
// e.g. 去買菜) we DON'T reorder — that stays a purposive V+VP.
function applyMotionRule(toks) {
    const tags = toks.map(tag), out = [];
    let i = 0;
    while (i < toks.length) {
        if (tags[i] === "V_MOTION") {
            let j = i + 1, sawNoun = false;
            while (j < toks.length && _isNominal(tags[j])) {
                // a PRON after we've already taken a noun is likely the next clause's subject
                if (tags[j] === "PRON" && sawNoun) break;
                if (tags[j] === "N" || tags[j] === "N_PLACE") sawNoun = true;
                j++;
            }
            const chunk = toks.slice(i + 1, j);
            const hasPlace = chunk.some((_, k) => tags[i + 1 + k] === "N_PLACE");
            if (chunk.length && hasPlace) {                 // reorder
                out.push("到", ...chunk, toks[i]);
                i = j; continue;
            }
        }
        out.push(toks[i]); i++;
    }
    return out;
}

// ===== [2] structural rule: progressive aspect ==========================
// PROG(在/正在) + V -> 垃拉 + V (preverbal; user: 垃拉 is normally preverbal). Only fires when a
// verb follows, so locative 在 (在上海, 在家) is left untouched — that's a different construction.
// (垃垓/垃𡋤 are also valid and can be pre- OR post-verbal per the user; kept for a later option.)
function applyProgressiveRule(toks) {
    const tags = toks.map(tag), out = [];
    for (let i = 0; i < toks.length; i++) {
        // 在 + place  = locative -> keep 在.  在 + (verb / activity noun) = progressive -> 垃拉.
        // We only KEEP 在 when the complement is clearly a place; everything else (incl. VO
        // compounds like 喫飯 tagged N) is treated as progressive.
        if (tags[i] === "PROG" && i + 1 < toks.length) {
            const nxt = tags[i + 1];
            const locative = nxt === "N_PLACE";
            if (!locative) { out.push("垃拉"); continue; }
        }
        out.push(toks[i]);
    }
    return out;
}

// Ordered stage-[2] rule pipeline. Rules are independent here (different triggers), but order
// is explicit so future interacting rules compose predictably.
const REORDER_RULES = [applyMotionRule, applyProgressiveRule];
function applyRules(toks) { return REORDER_RULES.reduce((t, rule) => rule(t), toks); }

// ===== syntactic variants ==============================================
// Shanghainese sometimes allows >1 grammatical word order where Mandarin has one. We surface
// these as alternates (the UI highlights the *syntax* difference). Each variant = a different
// token order; lexSub is applied after. Returns [{tokens, note}] alternates (NOT incl. primary).
// (1) DATIVE double-object swap: 撥 IO DO  <->  撥 DO IO  (user: both 撥我本書 & 撥本書我 OK).
function datativeSwap(toks) {
    const tags = toks.map(tag), alts = [];
    for (let i = 0; i < toks.length; i++) {
        if (tags[i] !== "DAT") continue;
        // IO = one pronoun/noun right after 撥; DO = the following nominal run (num+measure+noun)
        if (i + 1 >= toks.length || !_isNominal(tags[i + 1])) continue;
        const io = i + 1;
        let j = io + 1;
        while (j < toks.length && _isNominal(tags[j]) && tags[j] !== "PRON") j++;
        if (j === io + 1) continue;                       // no DO to move
        const swapped = toks.slice(0, io)
            .concat(toks.slice(io + 1, j))                // DO first
            .concat(toks[io])                             // then IO
            .concat(toks.slice(j));
        alts.push({ tokens: swapped, note: "雙賓語：直接賓語前置（撥＋物＋人）" });
    }
    return alts;
}
const VARIANT_RULES = [datativeSwap];
function genVariants(toks) { return VARIANT_RULES.flatMap(r => r(toks)); }

// ===== [3] lexical substitution =========================================
function lexSub(toks) {
    return toks.map(t => { const h = _lex(t); return (h && h.wu) ? h.wu : t; });
}

// ===== public entry =====================================================
// Returns {input, normalized, tokens, reordered, output}. output = Shanghainese hanzi
// (traditional); feed it to the existing dictionary/sandhi engine for Wugniu/IPA.
function translateToWu(text) {
    const normalized = (typeof toTraditional === "function") ? toTraditional(text) : text;
    const tokens = tokenize(normalized);
    const reordered = applyRules(tokens);
    const output = lexSub(reordered).join("");
    // Alternate FULL-sentence translations, each with a note on what differs. Two sources:
    // (1) syntactic variants (different word order); (2) lexical alternates (a word with >1 valid
    //     Wu form) -> emit the full sentence with just that one word swapped to each alt.
    const alts = [];
    const push = (text, note) => {
        if (text !== output && !alts.some(a => a.text === text)) alts.push({ text, note });
    };
    for (const v of genVariants(reordered)) push(lexSub(v.tokens).join(""), v.note);
    for (let i = 0; i < reordered.length; i++) {
        const h = _lex(reordered[i]);
        if (!(h && h.wu && h.alts)) continue;
        const base = lexSub(reordered);
        for (const alt of h.alts) {
            const swapped = base.slice(); swapped[i] = alt;
            push(swapped.join(""), `「${reordered[i]}」→「${alt}」（首選「${h.wu}」）`);
        }
    }
    return { input: text, normalized, tokens, reordered, output, alts };
}

if (typeof module !== "undefined" && module.exports) {
    module.exports = { translateToWu, tokenize, tag, applyMotionRule, applyProgressiveRule, lexSub, WU_LEX };
}
