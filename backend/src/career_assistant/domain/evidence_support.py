"""Domain rules for what may justify a met or partial assessment.

A citation proves a span exists. These checks decide whether that span can
count as evidence of work. A line must show a responsibility, a qualification
or an outcome. Location lines, contact details, profile headlines, reference
lines and bare employment titles name the candidate; they do not show the work.
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
    r"(?:"
    r"@|"
    r"\b(?:tel|phone|email)\b|"
    # Profile handles/URLs only — not product names like "GitHub Actions".
    r"\b(?:linkedin|github)\s*[:/]|"
    r"(?:linkedin|github)\.com\b|"
    r"https?://"
    r")",
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
_NON_EVIDENCE = re.compile(
    r"\b(?:references?\s+available|available\s+(?:on|upon)\s+request|"
    r"hobbies|interests\s+include|personal\s+profile)\b",
    re.IGNORECASE,
)
_WORK = re.compile(
    r"\b(?:"
    r"built|build|building|owned|owning|designed|designing|led|leading|"
    r"developed|developing|implemented|implementing|shipped|shipping|"
    r"maintained|maintaining|wrote|writing|created|creating|delivered|"
    r"delivering|reviewed|reviewing|paired|pairing|tested|testing|"
    r"deployed|deploying|operated|operating|migrated|migrating|"
    r"administer(?:ed|ing)|ran|running|mentored|mentoring|"
    r"reduced|reducing|improved|improving|managed|managing|"
    r"supported|supporting|tuned|tuning|chaired|chairing|"
    r"presented|presenting|organised|organized|organising|organizing|"
    r"kept|keeping|judged|judging|set\s+up|looked\s+after|"
    r"partnered|partnering|authored|authoring|coordinated|coordinating|"
    r"assisted|assisting|shadowed|shadowing|collected|collecting|"
    r"cleaned|cleaning|prepared|preparing|documented|documenting|"
    r"published|publishing|"
    r"split|splitting|chose|choosing|compared|comparing|traced|tracing|"
    r"optimi[sz]ed|optimi[sz]ing|generated|generating|introduced|introducing|"
    r"rebuilt|rebuilding|redirected|redirecting|automated|automating|"
    r"integrated|integrating|specified|specifying|trained|"
    r"act(?:ed|s)?\s+as|acting\s+as|"
    r"experience|proficien|familiar|certified|certification|degree|"
    r"diploma|bachelor|portfolio|internship|open[- ]source"
    r")\b",
    re.IGNORECASE,
)
# Present-tense duty verbs count only as the opening word: "own" and "lead"
# are also an adjective and a noun ("your own machine", "the team lead").
_LEADING_DUTY = re.compile(r"^(?:[-*]\s*)?(?:own|owns|lead|leads)\b", re.IGNORECASE)
_OUTCOME = re.compile(r"\b\d+(?:\.\d+)?\s*%")
_DELIVERABLE = _WORK
_EMPLOYER_SEP = re.compile(r"\s+[—–-]\s+")


def is_evidential_support(text: str) -> bool:
    """True when the span can justify a met or partial mapping."""
    plain = " ".join(text.split()).strip()
    if len(plain) < 8:
        return False
    if _NON_EVIDENCE.search(plain):
        return False
    if _LOCATION.match(plain):
        return False
    if _CONTACT.search(plain) and len(plain) < 80:
        return False
    if _PROFILE_HEADLINE.match(plain):
        return False
    if _ROLE_HEADING.search(plain) and _EMPLOYER_SEP.search(plain):
        if not _WORK.search(plain):
            return False
    if _LEADING_DUTY.match(plain):
        return True
    if not _WORK.search(plain) and not _OUTCOME.search(plain):
        return False
    return True
