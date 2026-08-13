"""Constantes xG — types Sportmonks et modes."""

# Type IDs documentés Sportmonks (fixture statistics)
# Shots = 42, Shots on target = 49
STAT_TYPE_SHOTS = "type_42"
STAT_TYPE_SHOTS_ON_TARGET = "type_49"

# Modèles xG supportés
MODEL_UNAVAILABLE = "UNAVAILABLE"
MODEL_SHOT_PROXY = "SHOT_PROXY_POISSON"
MODEL_SPORTMONKS_XG = "SPORTMONKS_XG"  # réservé si xGFixture disponible (premium)

# Version du proxy shots
PROXY_MODEL_VERSION = "v1.0"
