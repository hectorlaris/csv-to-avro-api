"""Pruebas basadas en propiedades (property-based) para validation.validate_rows.

A diferencia de las pruebas por casos de `test_validation.py`, aquí `hypothesis`
genera cientos de entradas aleatorias y verificamos **invariantes** que deben
cumplirse para cualquier entrada posible, no solo para ejemplos elegidos a mano.
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from common.validation import validate_rows

# ---------------------------------------------------------------------------
# Esquema de referencia para las propiedades
# ---------------------------------------------------------------------------

SCHEMA = {
    "type": "record",
    "name": "Alumno",
    "fields": [
        {"name": "nombre", "type": "string"},
        {"name": "edad", "type": "int"},
        {"name": "promedio", "type": "double"},
        {"name": "activo", "type": "boolean"},
    ],
    "qualityRules": [
        {"field": "nombre", "type": "minLength", "value": 2},
        {"field": "edad", "type": "min", "value": 0},
        {"field": "edad", "type": "max", "value": 120},
    ],
}

FIELD_NAMES = ["nombre", "edad", "promedio", "activo"]


# ---------------------------------------------------------------------------
# Estrategias
# ---------------------------------------------------------------------------

# Valores crudos arbitrarios (como vendrían de un CSV: siempre string)
_raw_values = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)), min_size=0, max_size=12
)

# Una fila arbitraria: cada campo del esquema con un valor string arbitrario
_arbitrary_row = st.fixed_dictionaries({name: _raw_values for name in FIELD_NAMES})

# Una lista de filas arbitrarias
_arbitrary_rows = st.lists(_arbitrary_row, min_size=0, max_size=20)


# Estrategia que genera SOLO filas válidas (respetan tipos y qualityRules)
_valid_row = st.fixed_dictionaries(
    {
        "nombre": st.text(min_size=2, max_size=10).filter(lambda s: s.strip() != ""),
        "edad": st.integers(min_value=0, max_value=120).map(str),
        "promedio": st.integers(min_value=0, max_value=100).map(lambda n: f"{n}.0"),
        "activo": st.sampled_from(["true", "false"]),
    }
)
_valid_rows = st.lists(_valid_row, min_size=1, max_size=15)


# ---------------------------------------------------------------------------
# Propiedad 1 — Conservación: válidas XOR inconsistentes = total de filas
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(rows=_arbitrary_rows)
def test_conservacion_de_filas(rows: list[dict[str, str]]) -> None:
    """El número de filas válidas más las filas con error debe igualar el total.

    Cada fila es válida O tiene al menos una inconsistencia, nunca ambas ni ninguna.
    """
    valid, inconsistencies = validate_rows(rows, SCHEMA)
    filas_con_error = {inc["row"] for inc in inconsistencies}
    assert len(valid) + len(filas_con_error) == len(rows)


# ---------------------------------------------------------------------------
# Propiedad 2 — Rango de los números de fila
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(rows=_arbitrary_rows)
def test_row_index_en_rango(rows: list[dict[str, str]]) -> None:
    """Todo número de fila reportado está entre 1 y len(rows)."""
    _, inconsistencies = validate_rows(rows, SCHEMA)
    for inc in inconsistencies:
        assert 1 <= inc["row"] <= len(rows)


# ---------------------------------------------------------------------------
# Propiedad 3 — Estructura de cada inconsistencia
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(rows=_arbitrary_rows)
def test_inconsistencias_bien_formadas(rows: list[dict[str, str]]) -> None:
    """Cada inconsistencia tiene row, column, value y error; column es del esquema."""
    _, inconsistencies = validate_rows(rows, SCHEMA)
    for inc in inconsistencies:
        assert set(inc.keys()) == {"row", "column", "value", "error"}
        assert inc["column"] in FIELD_NAMES
        assert isinstance(inc["error"], str) and inc["error"]


# ---------------------------------------------------------------------------
# Propiedad 4 — Toda fila válida tiene todos los campos del esquema
# ---------------------------------------------------------------------------


@settings(max_examples=200)
@given(rows=_arbitrary_rows)
def test_filas_validas_completas(rows: list[dict[str, str]]) -> None:
    """Cada fila válida contiene exactamente los campos definidos en el esquema."""
    valid, _ = validate_rows(rows, SCHEMA)
    for row in valid:
        assert set(row.keys()) == set(FIELD_NAMES)


# ---------------------------------------------------------------------------
# Propiedad 5 — Determinismo: validar dos veces da el mismo resultado
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(rows=_arbitrary_rows)
def test_determinismo(rows: list[dict[str, str]]) -> None:
    """La validación es determinista: misma entrada, mismo resultado."""
    valid1, inc1 = validate_rows(rows, SCHEMA)
    valid2, inc2 = validate_rows(rows, SCHEMA)
    assert valid1 == valid2
    assert inc1 == inc2


# ---------------------------------------------------------------------------
# Propiedad 6 — Las edades no numéricas siempre se excluyen
# ---------------------------------------------------------------------------


@settings(max_examples=150)
@given(
    rows=st.lists(
        st.fixed_dictionaries(
            {
                "nombre": st.text(min_size=2, max_size=8),
                # 'edad' con texto no convertible a int
                "edad": st.text(alphabet="abcdefABCDEF ", min_size=1, max_size=5),
                "promedio": st.just("9.0"),
                "activo": st.just("true"),
            }
        ),
        min_size=1,
        max_size=10,
    )
)
def test_edad_no_numerica_siempre_excluida(rows: list[dict[str, str]]) -> None:
    """Si 'edad' no es convertible a int, ninguna de esas filas entra al Avro."""
    valid, inconsistencies = validate_rows(rows, SCHEMA)
    assert valid == []
    # Cada fila debe tener al menos un error en la columna 'edad'
    filas_con_error_edad = {
        inc["row"] for inc in inconsistencies if inc["column"] == "edad"
    }
    assert filas_con_error_edad == set(range(1, len(rows) + 1))


# ---------------------------------------------------------------------------
# Propiedad 7 — Filas válidas generadas siempre pasan
# ---------------------------------------------------------------------------


@settings(max_examples=150)
@given(rows=_valid_rows)
def test_filas_validas_generadas_pasan(rows: list[dict[str, str]]) -> None:
    """Filas construidas para cumplir el esquema deben pasar todas, sin errores."""
    valid, inconsistencies = validate_rows(rows, SCHEMA)
    assert len(valid) == len(rows)
    assert inconsistencies == []
