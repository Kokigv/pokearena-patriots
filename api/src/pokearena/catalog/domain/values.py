"""Validaciones reutilizables de valores simples."""

from enum import Enum

from pokearena.shared.errors import FieldError


def check_int_range(
    errors: list[FieldError], field: str, value: object, low: int, high: int
) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        errors.append(FieldError(field, "debe ser un número entero"))
        return None
    if not low <= value <= high:
        errors.append(FieldError(field, f"debe estar entre {low} y {high}"))
        return None
    return value


def check_enum[E: Enum](
    errors: list[FieldError], field: str, value: object, enum: type[E]
) -> E | None:
    try:
        return enum(value)
    except ValueError:
        allowed = ", ".join(str(member.value) for member in enum)
        errors.append(FieldError(field, f"valor no permitido; use uno de: {allowed}"))
        return None


def check_text(
    errors: list[FieldError], field: str, value: object, max_length: int, required: bool = True
) -> str | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            errors.append(FieldError(field, "es obligatorio"))
        return None
    if not isinstance(value, str):
        errors.append(FieldError(field, "debe ser texto"))
        return None
    text = value.strip()
    if len(text) > max_length:
        errors.append(FieldError(field, f"máximo {max_length} caracteres"))
        return None
    return text
