"""Catálogos cerrados del contenido del juego."""

from enum import StrEnum


class CardType(StrEnum):
    FUEGO = "FUEGO"
    AGUA = "AGUA"
    PLANTA = "PLANTA"
    ELECTRICO = "ELECTRICO"
    PSIQUICO = "PSIQUICO"
    LUCHA = "LUCHA"

    @property
    def abbreviation(self) -> str:
        return _ABBREVIATIONS[self]


_ABBREVIATIONS = {
    CardType.FUEGO: "FUE",
    CardType.AGUA: "AGU",
    CardType.PLANTA: "PLA",
    CardType.ELECTRICO: "ELE",
    CardType.PSIQUICO: "PSI",
    CardType.LUCHA: "LUC",
}


class Rarity(StrEnum):
    COMUN = "COMUN"
    POCO_COMUN = "POCO_COMUN"
    RARA = "RARA"
    LEGENDARIA = "LEGENDARIA"


class Trigger(StrEnum):
    AL_REVELARSE = "AL_REVELARSE"
    CONTINUO = "CONTINUO"
    NINGUNO = "NINGUNO"  # solo para HAB-000 Sin Habilidad


class EffectKind(StrEnum):
    SIN_EFECTO = "SIN_EFECTO"
    MODIFICAR_PODER = "MODIFICAR_PODER"
    MODIFICAR_COSTO = "MODIFICAR_COSTO"
    GANAR_ENERGIA = "GANAR_ENERGIA"
    MOVER = "MOVER"
    DESTRUIR = "DESTRUIR"
    DESCARTAR = "DESCARTAR"
    EVOLUCIONAR = "EVOLUCIONAR"


class ImageStatus(StrEnum):
    PENDING = "PENDING"
    READY = "READY"
    FAILED = "FAILED"
