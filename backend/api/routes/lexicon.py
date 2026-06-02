"""Abuse Lexicon / Dictionary management API — view and add terms."""

import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth.middleware import get_current_user
from auth.rbac import require_admin
from database.models import User
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

_LEXICON_PATH = Path(__file__).resolve().parents[3] / "ai_models" / "configs" / "abuse_lexicon.json"
_GLOSSARY_PATH = Path(__file__).resolve().parents[3] / "ai_models" / "configs" / "abuse_term_glossary.json"
_MODELS_PATH = Path(__file__).resolve().parents[3] / "ai_models" / "configs" / "models.json"


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# ── Schemas ───────────────────────────────────────────────


class LexiconEntry(BaseModel):
    regex: str
    score: float = Field(ge=0.0, le=1.0)
    label: str


class GlossaryTerm(BaseModel):
    id: str
    detect: str
    display: str
    categories: list[str]
    meaning_en: str = ""
    offender_implication: str = ""
    also_blocks: list[str] = []


class AddTermRequest(BaseModel):
    """Payload for adding a new word to the abuse dictionary."""
    word: str = Field(min_length=1, description="The display word or phrase")
    regex: str = Field(min_length=1, description="Detection regex pattern")
    score: float = Field(ge=0.0, le=1.0, default=0.8, description="Confidence score (0.0-1.0)")
    label: str = Field(min_length=1, description="Category label (hate_speech, threat, etc.)")
    meaning_en: Optional[str] = ""
    offender_implication: Optional[str] = ""


class DeleteTermRequest(BaseModel):
    """Payload for deleting a term from the dictionary."""
    id: str = Field(min_length=1, description="Term ID to delete")


# ── Endpoints ─────────────────────────────────────────────


@router.get("/full")
async def get_full_dictionary(_user: User = Depends(get_current_user)) -> dict:
    """
    Returns the full abuse dictionary: lexicon patterns + glossary terms + models info.
    Used by the frontend Dictionary page.
    """
    lexicon = _load_json(_LEXICON_PATH)
    glossary = _load_json(_GLOSSARY_PATH)
    models = _load_json(_MODELS_PATH)

    patterns = lexicon.get("patterns", [])
    terms = glossary.get("terms", [])
    phrases = glossary.get("phrases", [])

    return {
        "lexicon_version": lexicon.get("version", "unknown"),
        "glossary_version": glossary.get("version", "unknown"),
        "total_patterns": len(patterns),
        "total_terms": len(terms),
        "total_phrases": len(phrases),
        "patterns": patterns,
        "terms": terms,
        "phrases": phrases,
        "models": models.get("models", {}),
    }


@router.get("/patterns")
async def get_lexicon_patterns(_user: User = Depends(get_current_user)) -> dict:
    """Return just the lexicon patterns (regex-based detection rules)."""
    lexicon = _load_json(_LEXICON_PATH)
    return {
        "version": lexicon.get("version", "unknown"),
        "patterns": lexicon.get("patterns", []),
    }


@router.get("/glossary")
async def get_glossary(_user: User = Depends(get_current_user)) -> dict:
    """Return glossary terms and phrases with explanations."""
    glossary = _load_json(_GLOSSARY_PATH)
    return {
        "version": glossary.get("version", "unknown"),
        "terms": glossary.get("terms", []),
        "phrases": glossary.get("phrases", []),
    }


@router.get("/models")
async def get_models_info(_user: User = Depends(get_current_user)) -> dict:
    """Return info about the ML models used for classification."""
    models = _load_json(_MODELS_PATH)
    return models


@router.post("/add-term", status_code=status.HTTP_201_CREATED)
async def add_term(
    body: AddTermRequest,
    _user: User = Depends(require_admin),
) -> dict:
    """
    Add a new term/word to both the lexicon (for detection) and glossary (for display).
    The keyword_engine auto-reloads patterns on next classify call.
    """
    # Generate an ID from the word
    term_id = body.word.lower().replace(" ", "_").replace("/", "_")

    # 1. Add to abuse_lexicon.json (detection patterns)
    lexicon = _load_json(_LEXICON_PATH)
    patterns = lexicon.get("patterns", [])

    # Check for duplicate regex
    for p in patterns:
        if p["regex"] == body.regex:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Pattern '{body.regex}' already exists in lexicon",
            )

    patterns.append({
        "regex": body.regex,
        "score": body.score,
        "label": body.label,
    })
    lexicon["patterns"] = patterns
    _save_json(_LEXICON_PATH, lexicon)

    # 2. Add to abuse_term_glossary.json (explanations)
    glossary = _load_json(_GLOSSARY_PATH)
    terms = glossary.get("terms", [])

    # Check if term ID already exists
    if not any(t["id"] == term_id for t in terms):
        terms.append({
            "id": term_id,
            "detect": body.regex,
            "display": body.word,
            "categories": [body.label],
            "meaning_en": body.meaning_en or "",
            "offender_implication": body.offender_implication or "",
        })
        glossary["terms"] = terms
        _save_json(_GLOSSARY_PATH, glossary)

    # 3. Reload keyword engine patterns in memory
    _reload_keyword_engine()

    logger.info("Added abuse term: %s (label=%s, score=%.2f)", body.word, body.label, body.score)

    return {
        "success": True,
        "message": f"Term '{body.word}' added to dictionary",
        "term_id": term_id,
        "total_patterns": len(patterns),
    }


@router.delete("/remove-term")
async def remove_term(
    body: DeleteTermRequest,
    _user: User = Depends(require_admin),
) -> dict:
    """Remove a term from both lexicon and glossary by ID."""
    term_id = body.id

    # Remove from glossary
    glossary = _load_json(_GLOSSARY_PATH)
    terms = glossary.get("terms", [])
    phrases = glossary.get("phrases", [])
    found_glossary = False

    # Find the term's detect regex so we can remove from lexicon too
    detect_regex = None
    for t in terms:
        if t["id"] == term_id:
            detect_regex = t.get("detect")
            found_glossary = True
            break
    if not found_glossary:
        for p in phrases:
            if p["id"] == term_id:
                detect_regex = p.get("detect")
                found_glossary = True
                break

    if found_glossary:
        glossary["terms"] = [t for t in terms if t["id"] != term_id]
        glossary["phrases"] = [p for p in phrases if p["id"] != term_id]
        _save_json(_GLOSSARY_PATH, glossary)

    # Remove from lexicon
    removed_from_lexicon = False
    if detect_regex:
        lexicon = _load_json(_LEXICON_PATH)
        patterns = lexicon.get("patterns", [])
        new_patterns = [p for p in patterns if p["regex"] != detect_regex]
        if len(new_patterns) < len(patterns):
            removed_from_lexicon = True
            lexicon["patterns"] = new_patterns
            _save_json(_LEXICON_PATH, lexicon)

    if not found_glossary and not removed_from_lexicon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Term '{term_id}' not found in dictionary",
        )

    _reload_keyword_engine()
    logger.info("Removed abuse term: %s", term_id)

    return {
        "success": True,
        "message": f"Term '{term_id}' removed from dictionary",
    }


def _reload_keyword_engine() -> None:
    """Force reload of compiled patterns in the keyword engine."""
    try:
        import importlib
        import ai.keyword_engine as kw_mod
        importlib.reload(kw_mod)
    except Exception as exc:
        logger.warning("Could not hot-reload keyword engine: %s", exc)
