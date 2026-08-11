-- =============================================================================
-- 001_init.sql — Bot Telegram Prédictions Sportives IA (DevMind)
-- Migration initiale — toutes les tables dans l'ordre de dépendance
-- =============================================================================

-- Extension UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE match_status AS ENUM ('scheduled', 'live', 'finished', 'cancelled', 'postponed');
CREATE TYPE confidence_level AS ENUM ('haute', 'moyenne', 'faible');
CREATE TYPE subscription_status AS ENUM ('actif', 'expire', 'annule');
CREATE TYPE payment_method AS ENUM ('manuel_whatsapp', 'mtn_momo', 'orange_money');
CREATE TYPE payment_status AS ENUM ('PENDING', 'SUCCESS', 'FAILED', 'EXPIRED');
CREATE TYPE coupon_type AS ENUM ('safe', 'medium', 'high_odds');
CREATE TYPE coupon_tier AS ENUM ('free', 'premium');
CREATE TYPE llm_reliability AS ENUM ('officiel', 'probable', 'rumeur');
CREATE TYPE market_code AS ENUM (
  '1X2', 'BTTS', 'OVER_UNDER_2_5', 'OVER_UNDER_3_5',
  'CORNERS', 'CARDS', 'FIRST_SCORER', 'DOUBLE_CHANCE',
  'DRAW_NO_BET', 'ASIAN_HANDICAP'
);

-- =============================================================================
-- TABLE 1 : ai_models
-- =============================================================================
CREATE TABLE IF NOT EXISTS ai_models (
  id                  SERIAL PRIMARY KEY,
  name                VARCHAR(100) NOT NULL,
  version             VARCHAR(20)  NOT NULL,
  description         TEXT,
  performance_metrics JSONB        DEFAULT '{}',
  is_active           BOOLEAN      DEFAULT TRUE,
  created_at          TIMESTAMPTZ  DEFAULT NOW(),
  UNIQUE(name, version)
);

-- Seed modèles V1
INSERT INTO ai_models (name, version, description) VALUES
  ('poisson', '1.0', 'Distribution de Poisson pour prédiction de buts'),
  ('xgboost', '1.0', 'XGBoost pour classification issue du match (1/X/2)'),
  ('ensemble', '1.0', 'Combinaison pondérée Poisson + XGBoost')
ON CONFLICT (name, version) DO NOTHING;

-- =============================================================================
-- TABLE 2 : leagues
-- =============================================================================
CREATE TABLE IF NOT EXISTS leagues (
  id           SERIAL PRIMARY KEY,
  external_id  INTEGER     NOT NULL UNIQUE, -- ID API-Football
  name         VARCHAR(100) NOT NULL,
  country      VARCHAR(100),
  season       INTEGER      NOT NULL DEFAULT 2024,
  covered      BOOLEAN      DEFAULT FALSE,   -- TRUE = couvert en V1
  logo_url     VARCHAR(500),
  created_at   TIMESTAMPTZ  DEFAULT NOW(),
  updated_at   TIMESTAMPTZ  DEFAULT NOW()
);

-- Seed championnats V1 couverts (IDs API-Football)
INSERT INTO leagues (external_id, name, country, season, covered) VALUES
  (61,  'Ligue 1',            'France',      2024, TRUE),
  (39,  'Premier League',     'England',     2024, TRUE),
  (140, 'La Liga',            'Spain',       2024, TRUE),
  (135, 'Serie A',            'Italy',       2024, TRUE),
  (78,  'Bundesliga',         'Germany',     2024, TRUE),
  (2,   'UEFA Champions League', 'Europe',  2024, TRUE),
  (531, 'UEFA Super Cup',     'Europe',      2024, TRUE)
ON CONFLICT (external_id) DO NOTHING;

-- =============================================================================
-- TABLE 3 : teams
-- =============================================================================
CREATE TABLE IF NOT EXISTS teams (
  id          SERIAL PRIMARY KEY,
  external_id INTEGER      NOT NULL UNIQUE,
  name        VARCHAR(150) NOT NULL,
  short_name  VARCHAR(50),
  league_id   INTEGER      REFERENCES leagues(id) ON DELETE SET NULL,
  logo_url    VARCHAR(500),
  country     VARCHAR(100),
  created_at  TIMESTAMPTZ  DEFAULT NOW(),
  updated_at  TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_teams_external_id ON teams(external_id);
CREATE INDEX IF NOT EXISTS idx_teams_league_id ON teams(league_id);

-- =============================================================================
-- TABLE 4 : users
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
  id             UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  telegram_id    BIGINT       NOT NULL UNIQUE,
  username       VARCHAR(100),
  first_name     VARCHAR(100),
  last_name      VARCHAR(100),
  is_premium     BOOLEAN      DEFAULT FALSE,
  is_admin       BOOLEAN      DEFAULT FALSE,
  language_code  VARCHAR(10)  DEFAULT 'fr',
  created_at     TIMESTAMPTZ  DEFAULT NOW(),
  last_active_at TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_is_premium ON users(is_premium);

-- =============================================================================
-- TABLE 5 : subscriptions
-- =============================================================================
CREATE TABLE IF NOT EXISTS subscriptions (
  id                    UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID              NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_name             VARCHAR(50)       NOT NULL DEFAULT '1_mois',
  montant               INTEGER           NOT NULL DEFAULT 2500, -- en FCFA
  devise                VARCHAR(10)       NOT NULL DEFAULT 'FCFA',
  date_debut            TIMESTAMPTZ       NOT NULL,
  date_fin              TIMESTAMPTZ       NOT NULL,
  statut                subscription_status NOT NULL DEFAULT 'actif',
  auto_renewed          BOOLEAN           DEFAULT FALSE,
  telegram_group_added  BOOLEAN           DEFAULT FALSE,
  expiry_notif_sent     BOOLEAN           DEFAULT FALSE, -- notification envoyée avant expiration
  created_at            TIMESTAMPTZ       DEFAULT NOW(),
  updated_at            TIMESTAMPTZ       DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_date_fin ON subscriptions(date_fin);
CREATE INDEX IF NOT EXISTS idx_subscriptions_statut ON subscriptions(statut);

-- =============================================================================
-- TABLE 6 : payments
-- =============================================================================
CREATE TABLE IF NOT EXISTS payments (
  id                    UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID            NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  subscription_id       UUID            REFERENCES subscriptions(id) ON DELETE SET NULL,
  montant               INTEGER         NOT NULL,
  devise                VARCHAR(10)     NOT NULL DEFAULT 'FCFA',
  methode               payment_method  NOT NULL DEFAULT 'manuel_whatsapp',
  payment_status        payment_status  NOT NULL DEFAULT 'PENDING',
  reference_transaction VARCHAR(200),   -- référence Mobile Money ou autre
  activated_by_admin    BIGINT,         -- telegram_id de l'admin qui a activé
  notes                 TEXT,
  created_at            TIMESTAMPTZ     DEFAULT NOW(),
  updated_at            TIMESTAMPTZ     DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(payment_status);

-- =============================================================================
-- TABLE 7 : matches
-- =============================================================================
CREATE TABLE IF NOT EXISTS matches (
  id              UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id     VARCHAR(50)   NOT NULL UNIQUE, -- ID externe API-Football
  league_id       INTEGER       REFERENCES leagues(id) ON DELETE SET NULL,
  home_team_id    INTEGER       REFERENCES teams(id) ON DELETE SET NULL,
  away_team_id    INTEGER       REFERENCES teams(id) ON DELETE SET NULL,
  match_date      TIMESTAMPTZ   NOT NULL,
  status          match_status  NOT NULL DEFAULT 'scheduled',
  home_score      INTEGER,
  away_score      INTEGER,
  -- Données collectées
  raw_stats       JSONB         DEFAULT '{}',   -- stats d'équipe, xG, possession, etc.
  lineups         JSONB         DEFAULT '{}',   -- compositions officielles
  injuries        JSONB         DEFAULT '{}',   -- blessés / suspendus
  odds            JSONB         DEFAULT '{}',   -- cotes bookmakers
  referee         VARCHAR(150),
  venue           VARCHAR(200),
  -- Contrôle quota & fraîcheur
  last_fetched_at TIMESTAMPTZ,
  data_source     VARCHAR(50),                  -- 'api_football' | 'football_data'
  created_at      TIMESTAMPTZ   DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_matches_external_id ON matches(external_id);
CREATE INDEX IF NOT EXISTS idx_matches_match_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_league_id ON matches(league_id);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status);

-- =============================================================================
-- TABLE 8 : api_quota_tracker
-- Compteur strict de requêtes API par jour
-- =============================================================================
CREATE TABLE IF NOT EXISTS api_quota_tracker (
  id                  SERIAL       PRIMARY KEY,
  api_name            VARCHAR(50)  NOT NULL,   -- 'api_football' | 'football_data'
  date                DATE         NOT NULL,
  requests_used       INTEGER      NOT NULL DEFAULT 0,
  daily_limit         INTEGER      NOT NULL DEFAULT 100,
  safety_threshold    INTEGER      NOT NULL DEFAULT 90, -- seuil d'arrêt
  quota_exhausted     BOOLEAN      NOT NULL DEFAULT FALSE,
  last_updated_at     TIMESTAMPTZ  DEFAULT NOW(),
  UNIQUE(api_name, date)
);

-- =============================================================================
-- TABLE 9 : markets
-- =============================================================================
CREATE TABLE IF NOT EXISTS markets (
  id          SERIAL       PRIMARY KEY,
  code        VARCHAR(30)  NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL,
  description TEXT,
  is_active   BOOLEAN      DEFAULT TRUE
);

-- Seed marchés de paris
INSERT INTO markets (code, name, description) VALUES
  ('1X2',           'Résultat final 1X2',       'Victoire domicile / Nul / Victoire extérieur'),
  ('BTTS',          'Les deux équipes marquent', 'Les deux équipes inscrivent au moins 1 but'),
  ('OVER_UNDER_2_5','Plus/Moins 2.5 buts',       'Total buts dans le match'),
  ('OVER_UNDER_3_5','Plus/Moins 3.5 buts',       'Total buts dans le match'),
  ('DOUBLE_CHANCE', 'Double chance',             '1X / X2 / 12'),
  ('DRAW_NO_BET',   'Remboursé si nul',          '1 ou 2, remboursé en cas de nul'),
  ('CORNERS',       'Paris sur corners',         'Total corners dans le match'),
  ('CARDS',         'Paris sur cartons',         'Total cartons jaunes/rouges'),
  ('FIRST_SCORER',  'Premier buteur',            'Joueur à marquer en premier'),
  ('ASIAN_HANDICAP','Handicap asiatique',        'Handicap asiatique sur le résultat')
ON CONFLICT (code) DO NOTHING;

-- =============================================================================
-- TABLE 10 : predictions
-- =============================================================================
CREATE TABLE IF NOT EXISTS predictions (
  id                        UUID              PRIMARY KEY DEFAULT gen_random_uuid(),
  match_id                  UUID              NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  market_id                 INTEGER           NOT NULL REFERENCES markets(id),
  model_id                  INTEGER           NOT NULL REFERENCES ai_models(id),
  outcome_predicted         VARCHAR(50)       NOT NULL, -- ex: '1', 'X', '2', 'BTTS_YES', 'OVER'
  probability_model         FLOAT             NOT NULL CHECK (probability_model BETWEEN 0 AND 1),
  probability_implicit_market FLOAT           CHECK (probability_implicit_market BETWEEN 0 AND 1),
  cote_marche               FLOAT,
  ecart_value               FLOAT,            -- probabilite_model - probabilite_implicite_marche
  is_value_bet              BOOLEAN           DEFAULT FALSE,
  niveau_confiance          confidence_level  NOT NULL DEFAULT 'moyenne',
  llm_explanation           TEXT,             -- explication en langage naturel
  llm_reliability_tag       llm_reliability,  -- officiel/probable/rumeur
  risk_flags                JSONB             DEFAULT '[]',
  published                 BOOLEAN           DEFAULT FALSE,
  created_at                TIMESTAMPTZ       DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions(match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_market_id ON predictions(market_id);
CREATE INDEX IF NOT EXISTS idx_predictions_confiance ON predictions(niveau_confiance);
CREATE INDEX IF NOT EXISTS idx_predictions_value_bet ON predictions(is_value_bet);

-- =============================================================================
-- TABLE 11 : risk_factors
-- =============================================================================
CREATE TABLE IF NOT EXISTS risk_factors (
  id          SERIAL       PRIMARY KEY,
  match_id    UUID         NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
  facteur     VARCHAR(100) NOT NULL, -- ex: 'derby', 'finale', 'enjeu_classement'
  impact      VARCHAR(20)  NOT NULL, -- 'positif' | 'negatif' | 'neutre'
  description TEXT,
  created_at  TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_risk_factors_match_id ON risk_factors(match_id);

-- =============================================================================
-- TABLE 12 : coupons
-- =============================================================================
CREATE TABLE IF NOT EXISTS coupons (
  id                    UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
  type                  coupon_type   NOT NULL DEFAULT 'safe',
  tier                  coupon_tier   NOT NULL DEFAULT 'free',
  title                 VARCHAR(200),
  total_odds            FLOAT,
  confidence_score      FLOAT,        -- score agrégé de confiance (0-1)
  published_at          TIMESTAMPTZ,
  published_to_channel  BOOLEAN       DEFAULT FALSE,
  published_to_group    BOOLEAN       DEFAULT FALSE,
  telegram_message_id   BIGINT,       -- ID du message Telegram pour édition future
  created_at            TIMESTAMPTZ   DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coupons_tier ON coupons(tier);
CREATE INDEX IF NOT EXISTS idx_coupons_type ON coupons(type);
CREATE INDEX IF NOT EXISTS idx_coupons_published_at ON coupons(published_at);

-- =============================================================================
-- TABLE 13 : coupon_predictions (table de jointure)
-- =============================================================================
CREATE TABLE IF NOT EXISTS coupon_predictions (
  coupon_id     UUID     NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
  prediction_id UUID     NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
  position      INTEGER  NOT NULL DEFAULT 1, -- ordre d'affichage dans le coupon
  PRIMARY KEY (coupon_id, prediction_id)
);

CREATE INDEX IF NOT EXISTS idx_coupon_predictions_coupon ON coupon_predictions(coupon_id);
CREATE INDEX IF NOT EXISTS idx_coupon_predictions_pred ON coupon_predictions(prediction_id);

-- =============================================================================
-- TABLE 14 : prediction_results
-- Comparaison prédiction vs résultat réel
-- =============================================================================
CREATE TABLE IF NOT EXISTS prediction_results (
  id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  prediction_id   UUID         NOT NULL UNIQUE REFERENCES predictions(id) ON DELETE CASCADE,
  actual_outcome  VARCHAR(50)  NOT NULL, -- résultat réel (ex: '1', 'X', 'BTTS_YES')
  is_correct      BOOLEAN      NOT NULL,
  verified_at     TIMESTAMPTZ  DEFAULT NOW(),
  source          VARCHAR(50)  DEFAULT 'api_football', -- source du résultat
  created_at      TIMESTAMPTZ  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prediction_results_pred_id ON prediction_results(prediction_id);
CREATE INDEX IF NOT EXISTS idx_prediction_results_correct ON prediction_results(is_correct);

-- =============================================================================
-- TABLE 15 : performance_stats
-- Stats agrégées par marché et par période
-- =============================================================================
CREATE TABLE IF NOT EXISTS performance_stats (
  id                  SERIAL       PRIMARY KEY,
  market_id           INTEGER      REFERENCES markets(id) ON DELETE CASCADE,
  period              DATE         NOT NULL, -- date de la période (jour ou mois)
  period_type         VARCHAR(10)  NOT NULL DEFAULT 'daily', -- 'daily' | 'monthly'
  total_predictions   INTEGER      NOT NULL DEFAULT 0,
  correct_predictions INTEGER      NOT NULL DEFAULT 0,
  success_rate        FLOAT        GENERATED ALWAYS AS (
                        CASE WHEN total_predictions > 0
                        THEN correct_predictions::FLOAT / total_predictions
                        ELSE 0 END
                      ) STORED,
  roi                 FLOAT        DEFAULT 0, -- Return on Investment estimé
  calculated_at       TIMESTAMPTZ  DEFAULT NOW(),
  UNIQUE(market_id, period, period_type)
);

CREATE INDEX IF NOT EXISTS idx_perf_stats_market ON performance_stats(market_id);
CREATE INDEX IF NOT EXISTS idx_perf_stats_period ON performance_stats(period);

-- =============================================================================
-- TRIGGERS : updated_at automatique
-- =============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_leagues_updated_at
  BEFORE UPDATE ON leagues
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_teams_updated_at
  BEFORE UPDATE ON teams
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_matches_updated_at
  BEFORE UPDATE ON matches
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_subscriptions_updated_at
  BEFORE UPDATE ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER trg_payments_updated_at
  BEFORE UPDATE ON payments
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- FIN DE LA MIGRATION 001
-- =============================================================================
