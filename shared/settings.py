from __future__ import annotations

import ast
from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings


def _patch_csv(source: Any) -> None:
    """Monkey-patch an EnvSettingsSource so CSV strings pass through to field validators.

    pydantic-settings tries json.loads() on every list/set/dict field before field
    validators run.  Values like "AAPL,TSLA" or "['AAPL','TSLA']" are not valid JSON,
    so this patch intercepts the failure and normalises the value to a plain list so
    the field_validator can receive it cleanly.
    """
    original = source.prepare_field_value

    def patched(field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        if value_is_complex and isinstance(value, str):
            try:
                return original(field_name, field, value, value_is_complex)
            except Exception:
                # Try Python literal syntax first (e.g. ['AAPL','MSFT']).
                stripped = value.strip()
                if stripped.startswith("[") or stripped.startswith("("):
                    try:
                        parsed = ast.literal_eval(stripped)
                        if isinstance(parsed, (list, tuple, set)):
                            return list(parsed)
                    except Exception:
                        pass
                # Fall back to raw string so the field_validator can split on commas.
                return value
        return original(field_name, field, value, value_is_complex)

    source.prepare_field_value = patched


class CsvAwareSettings(BaseSettings):
    """Drop-in replacement for BaseSettings that accepts CSV env vars for list fields."""

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        _patch_csv(env_settings)
        _patch_csv(dotenv_settings)
        return (init_settings, env_settings, dotenv_settings, file_secret_settings)
