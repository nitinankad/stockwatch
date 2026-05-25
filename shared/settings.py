from __future__ import annotations

from typing import Any

from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings


def _patch_csv(source: Any) -> None:
    """Monkey-patch an EnvSettingsSource so CSV strings pass through to field validators.

    pydantic-settings tries json.loads() on every list/set/dict field before field
    validators run.  A comma-separated value like "AAPL,TSLA" is not valid JSON, so it
    raises before the _split_csv validator ever sees it.  This patch catches that error
    and returns the raw string instead, letting the existing field_validator handle it.
    """
    original = source.prepare_field_value

    def patched(field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        if value_is_complex and isinstance(value, str):
            try:
                return original(field_name, field, value, value_is_complex)
            except Exception:
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
