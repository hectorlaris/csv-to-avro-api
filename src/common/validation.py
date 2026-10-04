"""Módulo de validación: verifica cada fila CSV contra el esquema Avro y qualityRules."""

from typing import Any

# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

# Una fila válida es un dict {campo: valor} listo para serializar a Avro
ValidRow = dict[str, Any]

# Una inconsistencia registra el detalle del error por fila y columna
Inconsistency = dict[str, Any]


# ---------------------------------------------------------------------------
# Mapeo de tipos Avro → tipos Python
# ---------------------------------------------------------------------------
_AVRO_TO_PYTHON: dict[str, type | tuple] = {
    "string": str,
    "int": int,
    "long": int,
    "float": (float, int),
    "double": (float, int),
    "boolean": bool,
    "bytes": (bytes, str),
}


def _resolve_type(avro_type: Any) -> str | None:
    """Extrae el tipo base de un campo Avro (maneja unions con null).

    Args:
        avro_type: Tipo del campo tal como viene del esquema Avro.

    Returns:
        Nombre del tipo base, o None si es solo null.
    """
    if isinstance(avro_type, str):
        return None if avro_type == "null" else avro_type
    if isinstance(avro_type, list):
        non_null = [t for t in avro_type if t != "null"]
        return non_null[0] if non_null else None
    if isinstance(avro_type, dict):
        return avro_type.get("type")
    return None


def _is_nullable(avro_type: Any) -> bool:
    """Determina si un campo Avro admite null.

    Args:
        avro_type: Tipo del campo tal como viene del esquema Avro.

    Returns:
        True si el campo puede ser null.
    """
    if isinstance(avro_type, list):
        return "null" in avro_type
    return avro_type == "null"


def _get_symbols(avro_type: Any) -> list[str] | None:
    """Extrae los símbolos válidos de un campo enum Avro.

    Args:
        avro_type: Tipo del campo tal como viene del esquema Avro.

    Returns:
        Lista de símbolos o None si no es enum.
    """
    if isinstance(avro_type, dict) and avro_type.get("type") == "enum":
        return avro_type.get("symbols", [])
    if isinstance(avro_type, list):
        for t in avro_type:
            if isinstance(t, dict) and t.get("type") == "enum":
                return t.get("symbols", [])
    return None


def _coerce_value(raw: str, base_type: str) -> Any:
    """Convierte un valor string CSV al tipo Python correspondiente.

    Args:
        raw: Valor crudo leído del CSV (siempre string).
        base_type: Tipo Avro base al que convertir.

    Returns:
        Valor convertido al tipo Python adecuado.

    Raises:
        ValueError: Si la conversión falla.
    """
    if base_type in ("int", "long"):
        return int(raw)
    if base_type in ("float", "double"):
        return float(raw)
    if base_type == "boolean":
        if raw.lower() in ("true", "1", "yes"):
            return True
        if raw.lower() in ("false", "0", "no"):
            return False
        raise ValueError(f"Valor booleano inválido: '{raw}'")
    return raw  # string y bytes se dejan como str


def _check_quality_rules(
    field_name: str,
    value: Any,
    rules: list[dict],
) -> str | None:
    """Verifica las qualityRules definidas para un campo.

    Args:
        field_name: Nombre del campo a verificar.
        value: Valor ya convertido al tipo correcto.
        rules: Lista de reglas de calidad del esquema.

    Returns:
        Mensaje de error si falla alguna regla, None si todas pasan.
    """
    for rule in rules:
        if rule.get("field") != field_name:
            continue
        rule_type = rule.get("type")
        if rule_type == "minLength" and isinstance(value, str):
            if len(value) < rule.get("value", 0):
                return (
                    f"minLength {rule.get('value')} no cumplida (longitud {len(value)})"
                )
        elif rule_type == "maxLength" and isinstance(value, str):
            if len(value) > rule.get("value", 0):
                return f"maxLength {rule.get('value')} superada (longitud {len(value)})"
        elif rule_type == "pattern" and isinstance(value, str):
            import re

            if not re.fullmatch(rule.get("value", ""), value):
                return f"patrón '{rule.get('value')}' no cumplido"
        elif rule_type == "min" and isinstance(value, (int, float)):
            if value < rule.get("value", 0):
                return f"valor {value} menor que mínimo {rule.get('value')}"
        elif rule_type == "max" and isinstance(value, (int, float)):
            if value > rule.get("value", 0):
                return f"valor {value} mayor que máximo {rule.get('value')}"
    return None


def validate_rows(
    rows: list[dict[str, str]],
    schema: dict,
) -> tuple[list[ValidRow], list[Inconsistency]]:
    """Valida una lista de filas CSV contra el esquema Avro y qualityRules.

    Cada fila se valida campo a campo. Las filas que cumplen todos los
    criterios se incluyen en valid_rows con valores convertidos al tipo
    correcto. Las filas con al menos una inconsistencia se excluyen del
    Avro y se registran en inconsistencies.

    Args:
        rows: Lista de dicts {campo: valor_string} leídos del CSV.
        schema: Esquema Avro parseado como diccionario Python.

    Returns:
        Tupla (valid_rows, inconsistencies).
    """
    fields: list[dict] = schema.get("fields", [])
    quality_rules: list[dict] = schema.get("qualityRules", [])

    valid_rows: list[ValidRow] = []
    inconsistencies: list[Inconsistency] = []

    for row_index, raw_row in enumerate(rows, start=1):
        row_errors: list[dict] = []
        converted_row: ValidRow = {}

        for field in fields:
            field_name: str = field["name"]
            avro_type: Any = field["type"]
            raw_value: str = raw_row.get(field_name, "")

            # Verificar nulo
            is_empty = raw_value == "" or raw_value is None
            nullable = _is_nullable(avro_type)

            if is_empty:
                if nullable:
                    converted_row[field_name] = None
                    continue
                row_errors.append(
                    {
                        "column": field_name,
                        "value": raw_value,
                        "error": "Campo nulo no permitido",
                    }
                )
                continue

            base_type = _resolve_type(avro_type)

            # Verificar enum
            symbols = _get_symbols(avro_type)
            if symbols is not None:
                if raw_value not in symbols:
                    row_errors.append(
                        {
                            "column": field_name,
                            "value": raw_value,
                            "error": f"Valor fuera de enumeración {symbols}",
                        }
                    )
                    continue
                converted_row[field_name] = raw_value
                continue

            # Convertir al tipo base
            if base_type and base_type != "string":
                try:
                    converted_value = _coerce_value(raw_value, base_type)
                except (ValueError, TypeError):
                    row_errors.append(
                        {
                            "column": field_name,
                            "value": raw_value,
                            "error": f"Tipo inválido; se esperaba '{base_type}'",
                        }
                    )
                    continue
            else:
                converted_value = raw_value

            # Verificar qualityRules
            quality_error = _check_quality_rules(
                field_name, converted_value, quality_rules
            )
            if quality_error:
                row_errors.append(
                    {
                        "column": field_name,
                        "value": raw_value,
                        "error": f"qualityRule: {quality_error}",
                    }
                )
                continue

            converted_row[field_name] = converted_value

        if row_errors:
            for err in row_errors:
                inconsistencies.append(
                    {
                        "row": row_index,
                        "column": err["column"],
                        "value": err["value"],
                        "error": err["error"],
                    }
                )
        else:
            valid_rows.append(converted_row)

    return valid_rows, inconsistencies
