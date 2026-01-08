"""Policy data models for content filtering and synonym handling.

Defines rules for:
- Synonyms (동의어): Words treated as equivalent
- Prohibited words (금칙어): Banned words that trigger filtering
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SynonymGroup(BaseModel):
    """Group of synonymous words.

    Example:
        계좌, 통장, 어카운트 → all treated as "account"
    """

    canonical: str = Field(..., description="표준 용어 (Canonical term)")
    synonyms: list[str] = Field(default_factory=list, description="동의어 목록 (List of synonyms)")

    class Config:
        json_schema_extra = {"example": {"canonical": "계좌", "synonyms": ["통장", "어카운트", "account"]}}


class ProhibitedWord(BaseModel):
    """Prohibited word configuration.

    Words in this list will trigger content filtering.
    """

    word: str = Field(..., description="금칙어 (Prohibited word)")
    category: str | None = Field(None, description="금칙어 분류 (Category: abusive, spam, etc.)")
    severity: str = Field(default="medium", description="심각도 (Severity: low, medium, high)")

    class Config:
        json_schema_extra = {"example": {"word": "욕설", "category": "abusive", "severity": "high"}}


class ContentPolicy(BaseModel):
    """Content filtering and synonym policy configuration.

    Attributes:
        synonym_groups: 동의어 그룹 목록
        prohibited_words: 금칙어 목록
        case_sensitive: 대소문자 구분 여부
        partial_match: 부분 매칭 여부
    """

    synonym_groups: list[SynonymGroup] = Field(default_factory=list, description="동의어 그룹 목록 (Synonym groups)")
    prohibited_words: list[ProhibitedWord] = Field(default_factory=list, description="금칙어 목록 (Prohibited words)")
    case_sensitive: bool = Field(default=False, description="대소문자 구분 여부 (Case sensitivity)")
    partial_match: bool = Field(default=True, description="부분 매칭 여부 (Allow partial matching)")

    def check_prohibited(self, text: str) -> tuple[bool, list[str]]:
        """Check if text contains prohibited words.

        Args:
            text: Text to check

        Returns:
            Tuple of (contains_prohibited, matched_words)
        """
        matched = []
        check_text = text if self.case_sensitive else text.lower()

        for pw in self.prohibited_words:
            word = pw.word if self.case_sensitive else pw.word.lower()
            if self.partial_match:
                if word in check_text:
                    matched.append(pw.word)
            else:
                if word == check_text or f" {word} " in f" {check_text} ":
                    matched.append(pw.word)

        return (len(matched) > 0, matched)

    def normalize_synonyms(self, text: str) -> str:
        """Replace synonyms with canonical terms.

        Args:
            text: Text to normalize

        Returns:
            Normalized text with synonyms replaced
        """
        normalized = text

        for group in self.synonym_groups:
            for synonym in group.synonyms:
                # Replace whole word matches
                normalized = normalized.replace(synonym, group.canonical)

        return normalized

    def get_canonical_term(self, word: str) -> str | None:
        """Get canonical term for a word.

        Args:
            word: Word to look up

        Returns:
            Canonical term if word is a synonym, None otherwise
        """
        check_word = word if self.case_sensitive else word.lower()

        for group in self.synonym_groups:
            synonyms_to_check = group.synonyms if self.case_sensitive else [s.lower() for s in group.synonyms]
            if check_word in synonyms_to_check or check_word == (group.canonical if self.case_sensitive else group.canonical.lower()):
                return group.canonical

        return None

    class Config:
        json_schema_extra = {
            "example": {
                "synonym_groups": [
                    {"canonical": "계좌", "synonyms": ["통장", "어카운트"]},
                    {"canonical": "이체", "synonyms": ["송금", "입금", "transfer"]},
                ],
                "prohibited_words": [
                    {"word": "욕설", "category": "abusive", "severity": "high"},
                    {"word": "스팸", "category": "spam", "severity": "medium"},
                ],
                "case_sensitive": False,
                "partial_match": True,
            }
        }
