"""Pruebas unitarias para src/common/validation.py."""

from common.validation import validate_rows

# ---------------------------------------------------------------------------
# Esquemas de prueba
# ---------------------------------------------------------------------------

SCHEMA_SIMPLE = {
    "type": "record",
    "name": "Alumno",
    "fields": [
        {"name": "nombre", "type": "string"},
        {"name": "edad", "type": "int"},
        {"name": "promedio", "type": "double"},
        {"name": "activo", "type": "boolean"},
    ],
}

SCHEMA_CON_NULLABLE = {
    "type": "record",
    "name": "Alumno",
    "fields": [
        {"name": "nombre", "type": "string"},
        {"name": "telefono", "type": ["null", "string"]},
    ],
}

SCHEMA_CON_ENUM = {
    "type": "record",
    "name": "Alumno",
    "fields": [
        {"name": "nombre", "type": "string"},
        {
            "name": "nivel",
            "type": {
                "type": "enum",
                "name": "Nivel",
                "symbols": ["BASICO", "MEDIO", "AVANZADO"],
            },
        },
    ],
}

SCHEMA_CON_QUALITY_RULES = {
    "type": "record",
    "name": "Alumno",
    "fields": [
        {"name": "nombre", "type": "string"},
        {"name": "edad", "type": "int"},
    ],
    "qualityRules": [
        {"field": "nombre", "type": "minLength", "value": 2},
        {"field": "edad", "type": "min", "value": 0},
        {"field": "edad", "type": "max", "value": 120},
    ],
}


# ---------------------------------------------------------------------------
# Caso 1: todas las filas válidas
# ---------------------------------------------------------------------------


class TestTodasLasFilasValidas:
    """Cuando todas las filas cumplen el esquema."""

    def test_retorna_filas_convertidas(self) -> None:
        """Debe retornar las filas convertidas al tipo correcto."""
        rows = [
            {"nombre": "Ana", "edad": "20", "promedio": "9.5", "activo": "true"},
            {"nombre": "Luis", "edad": "22", "promedio": "8.0", "activo": "false"},
        ]
        valid, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert len(valid) == 2
        assert len(errors) == 0
        assert valid[0]["edad"] == 20
        assert valid[0]["promedio"] == 9.5
        assert valid[0]["activo"] is True
        assert valid[1]["activo"] is False

    def test_sin_inconsistencias(self) -> None:
        """La lista de inconsistencias debe estar vacía."""
        rows = [{"nombre": "Ana", "edad": "20", "promedio": "9.5", "activo": "true"}]
        _, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert errors == []


# ---------------------------------------------------------------------------
# Caso 2: tipo incorrecto
# ---------------------------------------------------------------------------


class TestTipoIncorrecto:
    """Cuando una fila tiene un campo con tipo incorrecto."""

    def test_fila_excluida_del_avro(self) -> None:
        """La fila con tipo incorrecto no debe aparecer en valid_rows."""
        rows = [
            {
                "nombre": "Ana",
                "edad": "no-es-numero",
                "promedio": "9.5",
                "activo": "true",
            }
        ]
        valid, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert len(valid) == 0
        assert len(errors) == 1

    def test_error_registra_columna_y_valor(self) -> None:
        """El error debe indicar la columna y el valor incorrecto."""
        rows = [{"nombre": "Ana", "edad": "abc", "promedio": "9.5", "activo": "true"}]
        _, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert errors[0]["column"] == "edad"
        assert errors[0]["value"] == "abc"
        assert "int" in errors[0]["error"]

    def test_numero_de_fila_correcto(self) -> None:
        """El número de fila debe reflejar la posición real (base 1)."""
        rows = [
            {"nombre": "Ana", "edad": "20", "promedio": "9.5", "activo": "true"},
            {"nombre": "Luis", "edad": "xx", "promedio": "8.0", "activo": "false"},
        ]
        _, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert errors[0]["row"] == 2


# ---------------------------------------------------------------------------
# Caso 3: valor fuera de enumeración
# ---------------------------------------------------------------------------


class TestEnumInvalido:
    """Cuando un campo enum recibe un valor no permitido."""

    def test_fila_excluida(self) -> None:
        """La fila con enum inválido no debe estar en valid_rows."""
        rows = [{"nombre": "Ana", "nivel": "EXPERTO"}]
        valid, errors = validate_rows(rows, SCHEMA_CON_ENUM)
        assert len(valid) == 0
        assert len(errors) == 1

    def test_error_menciona_enumeracion(self) -> None:
        """El error debe mencionar los valores permitidos."""
        rows = [{"nombre": "Ana", "nivel": "EXPERTO"}]
        _, errors = validate_rows(rows, SCHEMA_CON_ENUM)
        assert "enumeración" in errors[0]["error"]

    def test_valor_valido_de_enum_pasa(self) -> None:
        """Un valor dentro del enum debe pasar sin error."""
        rows = [{"nombre": "Ana", "nivel": "AVANZADO"}]
        valid, errors = validate_rows(rows, SCHEMA_CON_ENUM)
        assert len(valid) == 1
        assert errors == []


# ---------------------------------------------------------------------------
# Caso 4: campo nulo no permitido
# ---------------------------------------------------------------------------


class TestCampoNuloNoPermitido:
    """Cuando un campo no nullable llega vacío."""

    def test_fila_excluida(self) -> None:
        """La fila con campo nulo no permitido no debe estar en valid_rows."""
        rows = [{"nombre": "", "edad": "20", "promedio": "9.5", "activo": "true"}]
        valid, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert len(valid) == 0
        assert len(errors) == 1

    def test_error_indica_campo_nulo(self) -> None:
        """El error debe indicar que el campo no permite nulos."""
        rows = [{"nombre": "", "edad": "20", "promedio": "9.5", "activo": "true"}]
        _, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert errors[0]["column"] == "nombre"
        assert "nulo" in errors[0]["error"].lower()

    def test_campo_nullable_acepta_vacio(self) -> None:
        """Un campo nullable debe aceptar valor vacío sin error."""
        rows = [{"nombre": "Ana", "telefono": ""}]
        valid, errors = validate_rows(rows, SCHEMA_CON_NULLABLE)
        assert len(valid) == 1
        assert valid[0]["telefono"] is None
        assert errors == []


# ---------------------------------------------------------------------------
# Caso 5: incumplimiento de qualityRules
# ---------------------------------------------------------------------------


class TestQualityRules:
    """Cuando un campo incumple una qualityRule."""

    def test_minlength_excluye_fila(self) -> None:
        """Una cadena más corta que minLength debe excluir la fila."""
        rows = [{"nombre": "A", "edad": "20"}]
        valid, errors = validate_rows(rows, SCHEMA_CON_QUALITY_RULES)
        assert len(valid) == 0
        assert "minLength" in errors[0]["error"]

    def test_min_numerico_excluye_fila(self) -> None:
        """Un número menor que min debe excluir la fila."""
        rows = [{"nombre": "Ana", "edad": "-1"}]
        valid, errors = validate_rows(rows, SCHEMA_CON_QUALITY_RULES)
        assert len(valid) == 0
        assert "mínimo" in errors[0]["error"]

    def test_max_numerico_excluye_fila(self) -> None:
        """Un número mayor que max debe excluir la fila."""
        rows = [{"nombre": "Ana", "edad": "200"}]
        valid, errors = validate_rows(rows, SCHEMA_CON_QUALITY_RULES)
        assert len(valid) == 0
        assert "máximo" in errors[0]["error"]

    def test_fila_que_cumple_quality_rules_pasa(self) -> None:
        """Una fila que cumple todas las qualityRules debe pasar."""
        rows = [{"nombre": "Ana", "edad": "20"}]
        valid, errors = validate_rows(rows, SCHEMA_CON_QUALITY_RULES)
        assert len(valid) == 1
        assert errors == []


# ---------------------------------------------------------------------------
# Caso 6: todas las filas inválidas
# ---------------------------------------------------------------------------


class TestTodasLasFilasInvalidas:
    """Cuando ninguna fila pasa la validación."""

    def test_valid_rows_vacio(self) -> None:
        """valid_rows debe estar vacío si todas las filas fallan."""
        rows = [
            {"nombre": "", "edad": "20", "promedio": "9.5", "activo": "true"},
            {"nombre": "Luis", "edad": "xx", "promedio": "8.0", "activo": "false"},
        ]
        valid, errors = validate_rows(rows, SCHEMA_SIMPLE)
        assert valid == []
        assert len(errors) == 2

    def test_inconsistencies_tiene_todas_las_filas(self) -> None:
        """Cada fila inválida debe tener al menos una entrada en inconsistencies."""
        rows = [
            {"nombre": "", "edad": "20", "promedio": "9.5", "activo": "true"},
            {"nombre": "Luis", "edad": "xx", "promedio": "8.0", "activo": "false"},
        ]
        _, errors = validate_rows(rows, SCHEMA_SIMPLE)
        filas_con_error = {e["row"] for e in errors}
        assert filas_con_error == {1, 2}
