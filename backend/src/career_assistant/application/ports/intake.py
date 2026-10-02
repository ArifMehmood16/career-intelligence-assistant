"""Document parsing boundary: only immutable bytes/options enter a CPU worker."""

from dataclasses import dataclass
from typing import Protocol

from career_assistant.application.intake.admission import AdmissionLimits
from career_assistant.domain.documents import DocumentKind, ParsedDocument


@dataclass(frozen=True, slots=True)
class UploadDocument:
    data: bytes
    filename: str
    kind: DocumentKind
    declared_media_type: str | None
    limits: AdmissionLimits


class UploadParser(Protocol):
    def parse(self, upload: UploadDocument) -> ParsedDocument: ...
