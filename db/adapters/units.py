"""Area units, in ONE place. Everything inside LandStack is square metres (sq m).

An adapter converts a state's unit to sq m once, when it reads the file (the "edge").
After that, no other code ever sees hectares, ares, acres or guntas.
"""

SQM_PER_ARE = 100.0
SQM_PER_HECTARE = 10_000.0          # 1 hectare = 100 ares
SQM_PER_ACRE = 4046.8564224
SQM_PER_GUNTHA = 101.17             # Karnataka: about 40 guntas to the acre


# ---- to square metres (used by the adapters when reading) ----

def hectares_ares_to_sqm(hectares, ares):
    return hectares * SQM_PER_HECTARE + ares * SQM_PER_ARE


def acres_guntas_to_sqm(acres, guntas):
    return acres * SQM_PER_ACRE + guntas * SQM_PER_GUNTHA


def hectares_to_sqm(hectares):
    return hectares * SQM_PER_HECTARE


# ---- from square metres (used only by make_samples.py, to write the demo files) ----

def sqm_to_hectares_ares(sqm):
    hectares = int(sqm // SQM_PER_HECTARE)
    return hectares, (sqm - hectares * SQM_PER_HECTARE) / SQM_PER_ARE


def sqm_to_acres_guntas(sqm):
    acres = int(sqm // SQM_PER_ACRE)
    return acres, (sqm - acres * SQM_PER_ACRE) / SQM_PER_GUNTHA


def sqm_to_hectares(sqm):
    return sqm / SQM_PER_HECTARE
