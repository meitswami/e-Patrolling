# PATROL — AI Pipeline Documentation
> **For AI Agents:** This doc explains the entire abuse detection pipeline.
> Read before touching any file in `backend/ai/`

## Overview

The AI pipeline is the core of PATROL. It takes raw social media text and produces a structured threat assessment in < 500ms.

```
Input Text
    │
    ▼
┌─────────────────────────────┐
│  1. language_detector.py    │  → "hindi" | "english" | "hinglish"
└──────────────┬──────────────┘
               │
    ▼
┌─────────────────────────────┐
│  2. keyword_engine.py       │  → Instant flag if explicit keyword match
│  (Fast pre-filter)          │  → Skips ML if obviously abusive
└──────────────┬──────────────┘
               │
    ▼
┌─────────────────────────────┐
│  3. classifier.py           │  → IndicBERT (Hindi/Hinglish)
│  (ML classification)        │     OR toxic-bert (English)
│                             │  → {is_abusive, confidence, categories}
└──────────────┬──────────────┘
               │
    ▼
┌─────────────────────────────┐
│  4. severity_engine.py      │  → LOW | MEDIUM | HIGH | CRITICAL
│                             │  → Based on: confidence + categories
└──────────────┬──────────────┘
               │
    ▼
┌─────────────────────────────┐
│  5. risk_scoring.py         │  → Composite score 0-100
│                             │  → Weights: severity + repeat + verified
└──────────────┬──────────────┘
               │
    ▼
┌─────────────────────────────┐
│  6. entity_detector.py      │  → Names, locations, phone numbers
│  (Optional, async)          │  → Doxxing detection
└──────────────┬──────────────┘
               │
    ▼
    AnalysisResult (stored in ai_results table)
```

---

## Models Used

### 1. IndicBERT — Hindi/Hinglish Primary
- **Model ID:** `ai4bharat/IndicBERT`
- **Task:** Sequence classification (toxic vs non-toxic)
- **Languages:** 12 Indian languages including Hindi
- **Memory:** ~500MB
- **Speed:** ~100ms per inference (CPU)
- **Fine-tuning note:** The base model needs fine-tuning on abuse-specific data. For MVP, we use zero-shot with prompt engineering.

### 2. Multilingual MiniLM — Embeddings + Similarity
- **Model ID:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- **Task:** Sentence embeddings for similarity matching
- **Use:** Compare against known abusive phrase vectors
- **Memory:** ~120MB
- **Speed:** ~20ms per inference

### 3. Toxic-BERT — English Fallback
- **Model ID:** `unitary/toxic-bert`
- **Task:** Toxicity classification (6 categories)
- **Categories:** toxic, severe_toxic, obscene, threat, insult, identity_hate
- **Memory:** ~440MB

### 4. Keyword Engine — Fast Pre-filter
- **Source:** `ai_models/configs/abuse_lexicon.json`
- **Type:** Regex patterns + exact match
- **Speed:** < 1ms
- **Languages:** Hindi (Devanagari + Romanized), English, Hinglish
- **Auto-flag:** Rape threats, death threats, explicit content

---

## Language Detection Logic

```python
# Pseudocode for language_detector.py

def detect_language(text: str) -> LanguageResult:
    # 1. Script detection (fastest)
    if contains_devanagari(text):
        return LanguageResult(language="hindi", confidence=0.95)
    
    # 2. Hinglish detection (Hindi words in Latin script)
    hinglish_score = count_hinglish_markers(text)  # "maa", "bhai", "teri", etc.
    if hinglish_score > 0.3:
        return LanguageResult(language="hinglish", confidence=hinglish_score)
    
    # 3. Library detection for remaining
    lang = langdetect.detect(text)
    if lang == "hi":
        return LanguageResult(language="hindi", confidence=0.85)
    elif lang == "en":
        return LanguageResult(language="english", confidence=0.90)
    
    return LanguageResult(language="unknown", confidence=0.0)
```

**Hinglish markers** (common Romanized Hindi):
`maa, baap, bhai, behen, teri, tere, sala, randi, kutte, harami, chutiya, madarchod, etc.`

**Important:** These markers are stored in the abuse lexicon, not hardcoded in classifier.py.

---

## Severity Mapping

```
Risk Score 0-100:
  0-40   → LOW      (borderline, might be sarcastic/non-abusive)
  41-65  → MEDIUM   (hate speech, bullying, mild threats)
  66-84  → HIGH     (sexual harassment, stalking, serious threats)
  85-100 → CRITICAL (rape threats, death threats, doxxing)

Category overrides:
  - Any rape/death threat → minimum HIGH, likely CRITICAL
  - Doxxing (personal info) → automatic HIGH
  - Repeat offender bonus: +10 to risk score
  - Verified account penalty: -5 to risk score (verified ≠ safe, but rarer)
```

---

## Composite Risk Score Formula

```python
def calculate_risk_score(
    severity_score: float,    # 0-1 from classifier
    confidence: float,        # 0-1 classifier confidence
    category_weights: dict,   # Category multipliers
    is_repeat_offender: bool,
    is_verified: bool,
    follower_count: int,
) -> int:
    
    base = severity_score * confidence * 70   # Max 70 points from AI
    
    # Category bonuses (max 20 points)
    bonus = 0
    if category_weights.get('rape_threat'): bonus += 20
    elif category_weights.get('death_threat'): bonus += 18
    elif category_weights.get('doxxing'): bonus += 15
    elif category_weights.get('sexual_harassment'): bonus += 12
    elif category_weights.get('stalking'): bonus += 10
    
    # Behavioral bonuses
    repeat_bonus = 10 if is_repeat_offender else 0
    
    # Account reach factor (high followers = more harm)
    reach_factor = min(follower_count / 1_000_000 * 5, 5)  # Max 5 points
    
    total = base + bonus + repeat_bonus + reach_factor
    return min(int(total), 100)
```

---

## Abuse Lexicon Structure

File: `ai_models/configs/abuse_lexicon.json`

```json
{
  "version": "1.0",
  "categories": {
    "rape_threat": {
      "hindi_devanagari": ["रेप", "बलात्कार"],
      "hindi_romanized": ["rape karunga", "balaatkar", "chhod dunga"],
      "english": ["will rape you", "going to rape", "rape threat"],
      "severity_override": "CRITICAL"
    },
    "sexual_harassment": {
      "hindi_romanized": ["randi", "..."],
      "english": ["..."],
      "severity_override": "HIGH"
    },
    "general_abuse": {
      "hindi_romanized": ["madarchod", "bhosdike", "..."],
      "english": ["..."],
      "severity_override": null
    }
  }
}
```

**Note:** The actual word lists are stored in the lexicon file, never in source code.

---

## Model Loading Strategy

```python
# model_loader.py — Lazy loading pattern

_model_registry = {}

async def get_model(model_name: str) -> Any:
    """Load model once, cache forever (per worker process)."""
    if model_name not in _model_registry:
        logger.info(f"Loading model: {model_name}")
        model = await _load_from_cache_or_download(model_name)
        _model_registry[model_name] = model
        logger.info(f"Model loaded: {model_name} ({get_model_size(model)}MB)")
    return _model_registry[model_name]
```

**CRITICAL:** Never import models at module level. Always use lazy loading.
First inference will be slow (~2-5s). Subsequent: < 100ms.

---

## Pipeline Entry Point

```python
# pipeline.py — The unified entry point

async def analyze_text(
    text: str,
    context: AnalysisContext,  # platform, accused_info, target_info
) -> AnalysisResult:
    """
    Single entry point for all AI analysis.
    Called by queue/consumer.py after comment is crawled.
    """
    # Run language detection + keyword check (fast, synchronous)
    language = language_detector.detect(text)
    keyword_result = keyword_engine.check(text, language)
    
    # If obvious keyword match, skip expensive ML
    if keyword_result.is_obvious_abuse:
        return AnalysisResult.from_keyword(keyword_result, context)
    
    # Run ML classifier (async, expensive)
    classification = await classifier.classify(text, language)
    
    # Skip evidence collection if below threshold
    if classification.confidence < settings.ABUSE_CONFIDENCE_THRESHOLD:
        return AnalysisResult(is_abusive=False, ...)
    
    # Compute severity and risk
    severity = severity_engine.compute(classification, keyword_result)
    risk = risk_scoring.compute(severity, context)
    
    # Entity detection (async, run concurrently)
    entities = await entity_detector.detect(text, language)
    
    return AnalysisResult(
        is_abusive=True,
        language=language,
        severity_level=severity.level,
        risk_score=risk.score,
        entities=entities,
        ...
    )
```

---

## Adding New Abuse Categories

1. Add keywords to `ai_models/configs/abuse_lexicon.json`
2. Add detection flag to `backend/database/schema.sql` (new boolean column on `ai_results`)
3. Add field to `keyword_engine.py` category mapping
4. Add field to severity override mapping in `severity_engine.py`
5. Create a DB migration in `backend/database/migrations/`
6. Update TypeScript types in `frontend/index.ts`

---

## Performance Benchmarks (Target)

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Language detection | < 5ms | < 10ms |
| Keyword engine | < 2ms | < 5ms |
| IndicBERT inference (CPU) | < 150ms | < 300ms |
| Full pipeline | < 500ms | < 1000ms |
| Throughput (single worker) | 100 comments/min | 50 comments/min |