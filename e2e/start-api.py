"""Start only a dedicated loopback E2E database with hermetic production wiring."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from tempfile import TemporaryDirectory

from career_assistant.adapters.persistence.migrate import upgrade_head
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def main() -> None:
    raw = os.environ.get("E2E_DATABASE_URL", "")
    try:
        url = make_url(raw)
    except ArgumentError, ValueError:
        raise SystemExit("Provide a valid dedicated E2E_DATABASE_URL") from None
    if (
        url.drivername != "postgresql+psycopg"
        or url.host not in {"localhost", "127.0.0.1"}
        or not url.database
        or not url.database.endswith("_e2e")
    ):
        raise SystemExit(
            "E2E_DATABASE_URL must name a dedicated loopback *_e2e database"
        )
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "SYSTEMROOT"}
    }
    env.update(
        {
            "DATABASE_URL": raw,
            "TEST_DATABASE_URL": url.set(
                database=f"{url.database}_guard"
            ).render_as_string(hide_password=False),
            "COMPLETION_PROVIDER": "hermetic",
            "EMBEDDING_PROVIDER": "hermetic",
            "ALLOW_HOSTED_PROVIDERS": "false",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "PROVIDER_ALLOW_LOCAL_FALLBACK": "false",
            "LOG_LEVEL": "WARNING",
        }
    )
    os.environ.clear()
    os.environ.update(env)
    port = "18002"

    def stop(signum: int, frame: object) -> None:
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stop)
    with TemporaryDirectory(prefix="career-e2e-api-") as cwd:
        os.chdir(cwd)
        upgrade_head(raw)
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "career_assistant.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                port,
            ],
            cwd=cwd,
            env=env,
        )
        try:
            raise SystemExit(process.wait())
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == "__main__":
    main()
