"""Bounded spawned CPU workers for PDF/DOCX parsing, separate from model I/O."""

from concurrent.futures import ProcessPoolExecutor, TimeoutError
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass
from multiprocessing import get_context
from threading import BoundedSemaphore, Lock

from career_assistant.application.intake.admission import admit_upload
from career_assistant.application.intake.errors import IntakeError, IntakeErrorCode
from career_assistant.application.ports.intake import UploadDocument
from career_assistant.domain.documents import DocumentFormat, ParsedDocument
from career_assistant.parsing.pipeline import parse_document


@dataclass(frozen=True, slots=True)
class _ParseResult:
    document: ParsedDocument | None = None
    error: IntakeErrorCode | None = None


def _parse(upload: UploadDocument) -> _ParseResult:
    try:
        return _ParseResult(
            document=parse_document(
                upload.data,
                filename=upload.filename,
                kind=upload.kind,
                declared_media_type=upload.declared_media_type,
                limits=upload.limits,
            )
        )
    except IntakeError as exc:
        return _ParseResult(error=exc.code)


class ProcessUploadParser:
    """A lazy, process-lifetime pool; no database connection or model crosses it."""

    def __init__(self, *, workers: int = 2, timeout_seconds: float = 60) -> None:
        if workers < 1 or timeout_seconds <= 0:
            raise ValueError("parser workers and timeout must be positive")
        self._workers = workers
        self._timeout = timeout_seconds
        self._slots = BoundedSemaphore(workers)
        self._lock = Lock()
        self._pool: ProcessPoolExecutor | None = None

    def parse(self, upload: UploadDocument) -> ParsedDocument:
        admitted = admit_upload(
            upload.data,
            filename=upload.filename,
            declared_media_type=upload.declared_media_type,
            limits=upload.limits,
        )
        if admitted.format is DocumentFormat.PLAIN_TEXT:
            return _unwrap(_parse(upload))
        with self._slots:
            try:
                return _unwrap(
                    self._executor()
                    .submit(_parse, upload)
                    .result(timeout=self._timeout)
                )
            except (BrokenProcessPool, TimeoutError) as exc:
                self.close()
                raise IntakeError(
                    IntakeErrorCode.DOCUMENT_UNREADABLE,
                    "Document parsing failed. Try a plain text copy.",
                ) from exc

    def _executor(self) -> ProcessPoolExecutor:
        with self._lock:
            if self._pool is None:
                self._pool = ProcessPoolExecutor(
                    max_workers=self._workers, mp_context=get_context("spawn")
                )
            return self._pool

    def close(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            pool.terminate_workers()


def _unwrap(result: _ParseResult) -> ParsedDocument:
    if result.document is not None:
        return result.document
    code = result.error or IntakeErrorCode.DOCUMENT_UNREADABLE
    messages = {
        IntakeErrorCode.DOCUMENT_TOO_LARGE: "Document exceeds the configured limits.",
        IntakeErrorCode.DOCUMENT_UNSUPPORTED: "Unsupported document format.",
        IntakeErrorCode.DOCUMENT_UNREADABLE: "Document has no extractable content.",
    }
    raise IntakeError(code, messages[code])
