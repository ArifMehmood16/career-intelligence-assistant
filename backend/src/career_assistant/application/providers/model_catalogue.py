"""Per-model limits and capabilities, read from configuration.

A tag the catalogue names uses its own row; any other tag uses its provider's
defaults. A row overrides the defaults field by field, so a new model needs only
the values that differ.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

from career_assistant.application.ports.types import ModelProfile

_FIELD_TYPES: dict[str, type] = {
    field.name: type(getattr(ModelProfile(0, 0), field.name))
    for field in fields(ModelProfile)
}
_REQUIRED = ("context_window_tokens", "max_output_tokens")


class ModelCatalogueError(ValueError):
    """The catalogue cannot describe the requested provider or row."""


@dataclass(frozen=True, slots=True)
class ModelCatalogue:
    version: str
    defaults: Mapping[str, Mapping[str, Any]]
    models: Mapping[str, Mapping[str, Mapping[str, Any]]]

    def profile(self, provider_id: str, model_tag: str) -> ModelProfile:
        base = self.defaults.get(provider_id)
        if base is None:
            raise ModelCatalogueError(f"no model defaults for provider {provider_id!r}")
        row = self.models.get(provider_id, {}).get(model_tag, {})
        return _profile_from({**base, **row}, provider_id=provider_id)

    def names(self, provider_id: str, model_tag: str) -> bool:
        return model_tag in self.models.get(provider_id, {})


def load_model_catalogue(path: Path | str) -> ModelCatalogue:
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return ModelCatalogue(
        version=str(data["version"]),
        defaults=data.get("defaults", {}),
        models=data.get("models", {}),
    )


def _profile_from(values: Mapping[str, Any], *, provider_id: str) -> ModelProfile:
    unknown = set(values) - set(_FIELD_TYPES)
    if unknown:
        raise ModelCatalogueError(
            f"unknown model catalogue fields for {provider_id!r}: {sorted(unknown)}"
        )
    missing = [name for name in _REQUIRED if name not in values]
    if missing:
        raise ModelCatalogueError(f"{provider_id!r} is missing {missing}")
    for name, value in values.items():
        if type(value) is not _FIELD_TYPES[name]:
            raise ModelCatalogueError(
                f"{provider_id!r} field {name!r} has the wrong type"
            )
    return ModelProfile(**values)
