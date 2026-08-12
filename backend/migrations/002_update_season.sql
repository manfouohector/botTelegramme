-- =============================================================================
-- 002_update_season.sql — Met à jour la colonne saison des ligues pour refléter la saison courante
-- =============================================================================

-- Cette migration ajuste automatiquement la saison en fonction de la date du serveur.
-- Si le mois actuel est >= juillet (7), on utilise l'année courante, sinon on utilise l'année précédente.
-- Cela permet de synchroniser les enregistrements existants avec la logique dynamique introduite
-- dans le client API‑Football.

UPDATE league
SET season = CASE
    WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 7 THEN EXTRACT(YEAR FROM CURRENT_DATE)::int
    ELSE (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::int
  END;
