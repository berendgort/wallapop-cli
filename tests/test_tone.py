from walla.core.tone import human


def test_human_phone_style() -> None:
    long = "¡Hola! ¿Sigue disponible?   Te propongo 270 €."
    assert human(long) == "hola! Sigue disponible? Te propongo 270€"
    assert human("S23 Ultra disponible?") == "S23 Ultra disponible?"
    assert human("Genial!!!\nGracias.") == "genial! Gracias"
