"""Domain rules for what may justify a met or partial assessment.

A citation proves a span exists. These checks decide whether that span can
count as evidence of work. Location lines, contact details, profile headlines
and bare employment titles name the candidate; they do not show the work.
"""

from __future__ import annotations

import re

_LOCATION = re.compile(
    r"^(?:"
    r"[A-Za-z][A-Za-z .'/-]{1,40},\s*[A-Za-z]{2,3}\b|"
    r"(?:United Kingdom|UK|USA|United States|England|Scotland|Wales|"
    r"Northern Ireland|Remote)\b"
    r")\.?$",
    re.IGNORECASE,
)
_CONTACT = re.compile(
    r"(?:@|\b(?:tel|phone|email|linkedin|github)\b|https?://)",
    re.IGNORECASE,
)
_PROFILE_HEADLINE = re.compile(
    r"^[A-Z0-9][A-Z0-9 &/+'.,-]{8,}(?:\s*[·|•/]\s*[A-Z0-9 &/+'.,-]+)+$"
)
_ROLE_HEADING = re.compile(
    r"(?:"
    r"\b(?:19|20)\d{2}\b|"
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\b|"
    r"\bPresent\b"
    r")",
    re.IGNORECASE,
)
_DELIVERABLE = re.compile(
    r"\b(?:"
    r"built|build|building|owned|owning|designed|designing|led|leading|"
    r"developed|developing|implemented|implementing|shipped|shipping|"
    r"maintained|maintaining|wrote|writing|created|creating|delivered|"
    r"delivering|reviewed|reviewing|paired|pairing|tested|testing|"
    r"deployed|deploying|operated|operating|migrated|migrating|"
    r"experience|proficien|familiar|certified|certification|degree|"
    r"portfolio|internship|open[- ]source"
    r")\b",
    re.IGNORECASE,
)
_EMPLOYER_SEP = re.compile(r"\s+[—–-]\s+")


def is_evidential_support(text: str) -> bool:
    """True when the span can justify a met or partial mapping."""
    plain = " ".join(text.split()).strip()
    if len(plain) < 8:
        return False
    if _LOCATION.match(plain):
        return False
    if _CONTACT.search(plain) and len(plain) < 80:
        return False
    if _PROFILE_HEADLINE.match(plain):
        return False
    if _ROLE_HEADING.search(plain) and _EMPLOYER_SEP.search(plain):
        if not _DELIVERABLE.search(plain):
            return False
    return True
