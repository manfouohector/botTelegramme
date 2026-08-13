-- Migration 001 : schéma initial PostgreSQL
-- Module 2 — Football Prediction Bot MVP

BEGIN;

-- Suivi des migrations appliquées
CREATE TABLE IF NOT EXISTS schema_migrations (
    id          SERIAL PRIMARY KEY,
    filename    VARCHAR(255) NOT NULL UNIQUE,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Utilisateurs Telegram
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    telegram_id BIGINT NOT NULL UNIQUE,
    username    VARCHAR(255),
    first_name  VARCHAR(255),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id);

-- Abonnements
CREATE TABLE IF NOT EXISTS subscriptions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan        VARCHAR(50) NOT NULL DEFAULT 'premium',
    date_debut  TIMESTAMPTZ NOT NULL,
    date_fin    TIMESTAMPTZ NOT NULL,
    statut      VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_id ON subscriptions (user_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_date_fin ON subscriptions (date_fin);
CREATE INDEX IF NOT EXISTS idx_subscriptions_statut ON subscriptions (statut);

-- Paiements
CREATE TABLE IF NOT EXISTS payments (
    id                    SERIAL PRIMARY KEY,
    user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount                NUMERIC(12, 2) NOT NULL,
    currency              VARCHAR(10) NOT NULL DEFAULT 'XAF',
    method                VARCHAR(30) NOT NULL DEFAULT 'manuel_whatsapp',
    payment_status        VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    reference_transaction VARCHAR(255),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments (user_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments (payment_status);

-- Compétitions
CREATE TABLE IF NOT EXISTS competitions (
    id          SERIAL PRIMARY KEY,
    external_id INTEGER NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    country     VARCHAR(100),
    code        VARCHAR(20),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_competitions_external_id ON competitions (external_id);

-- Saisons
CREATE TABLE IF NOT EXISTS seasons (
    id              SERIAL PRIMARY KEY,
    competition_id  INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    external_id     INTEGER NOT NULL,
    name            VARCHAR(100) NOT NULL,
    is_current      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (competition_id, external_id)
);
CREATE INDEX IF NOT EXISTS idx_seasons_competition_id ON seasons (competition_id);

-- Équipes
CREATE TABLE IF NOT EXISTS teams (
    id          SERIAL PRIMARY KEY,
    external_id INTEGER NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    short_name  VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_teams_external_id ON teams (external_id);

-- Matchs
CREATE TABLE IF NOT EXISTS matches (
    id                  SERIAL PRIMARY KEY,
    external_match_id   INTEGER NOT NULL UNIQUE,
    competition_id      INTEGER NOT NULL REFERENCES competitions(id) ON DELETE RESTRICT,
    season_id           INTEGER NOT NULL REFERENCES seasons(id) ON DELETE RESTRICT,
    home_team_id        INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    away_team_id        INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    scheduled_at        TIMESTAMPTZ NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'SCHEDULED',
    home_score          INTEGER,
    away_score          INTEGER,
    last_fetched_at     TIMESTAMPTZ,
    data_status         VARCHAR(20) NOT NULL DEFAULT 'MISSING',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_matches_external_match_id ON matches (external_match_id);
CREATE INDEX IF NOT EXISTS idx_matches_scheduled_at ON matches (scheduled_at);
CREATE INDEX IF NOT EXISTS idx_matches_status ON matches (status);
CREATE INDEX IF NOT EXISTS idx_matches_competition_id ON matches (competition_id);
CREATE INDEX IF NOT EXISTS idx_matches_season_id ON matches (season_id);

-- Statistiques match
CREATE TABLE IF NOT EXISTS match_statistics (
    id          SERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id     INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    stats       JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, team_id)
);
CREATE INDEX IF NOT EXISTS idx_match_statistics_match_id ON match_statistics (match_id);

-- Joueurs
CREATE TABLE IF NOT EXISTS players (
    id          SERIAL PRIMARY KEY,
    external_id INTEGER NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    team_id     INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    position    VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_players_external_id ON players (external_id);

-- Blessures
CREATE TABLE IF NOT EXISTS injuries (
    id          SERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    player_id   INTEGER REFERENCES players(id) ON DELETE SET NULL,
    team_id     INTEGER REFERENCES teams(id) ON DELETE SET NULL,
    injury_type VARCHAR(100),
    status      VARCHAR(50),
    reliability VARCHAR(20) NOT NULL DEFAULT 'OFFICIAL',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_injuries_match_id ON injuries (match_id);

-- Compositions
CREATE TABLE IF NOT EXISTS lineups (
    id          SERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    team_id     INTEGER NOT NULL REFERENCES teams(id) ON DELETE RESTRICT,
    formation   VARCHAR(20),
    players     JSONB NOT NULL DEFAULT '{}',
    reliability VARCHAR(20) NOT NULL DEFAULT 'PROBABLE',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, team_id)
);
CREATE INDEX IF NOT EXISTS idx_lineups_match_id ON lineups (match_id);

-- Marchés
CREATE TABLE IF NOT EXISTS markets (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(50) NOT NULL UNIQUE,
    name        VARCHAR(100) NOT NULL,
    active      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_markets_code ON markets (code);

-- Cotes
CREATE TABLE IF NOT EXISTS odds (
    id                  SERIAL PRIMARY KEY,
    match_id            INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    market_id           INTEGER NOT NULL REFERENCES markets(id) ON DELETE RESTRICT,
    bookmaker           VARCHAR(100) NOT NULL,
    selection           VARCHAR(100) NOT NULL,
    odds                NUMERIC(10, 4) NOT NULL,
    implied_probability NUMERIC(8, 6),
    opening_odds        NUMERIC(10, 4),
    closing_odds        NUMERIC(10, 4),
    fetched_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (match_id, market_id, bookmaker, selection, fetched_at)
);
CREATE INDEX IF NOT EXISTS idx_odds_match_id ON odds (match_id);
CREATE INDEX IF NOT EXISTS idx_odds_market_id ON odds (market_id);
CREATE INDEX IF NOT EXISTS idx_odds_fetched_at ON odds (fetched_at);

-- Modèles IA
CREATE TABLE IF NOT EXISTS ai_models (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    version     VARCHAR(50) NOT NULL,
    type        VARCHAR(50) NOT NULL,
    metrics     JSONB,
    trained_at  TIMESTAMPTZ,
    active      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_models_active ON ai_models (active);

-- Features modèle
CREATE TABLE IF NOT EXISTS model_features (
    id            SERIAL PRIMARY KEY,
    model_id      INTEGER NOT NULL REFERENCES ai_models(id) ON DELETE CASCADE,
    feature_name  VARCHAR(100) NOT NULL,
    importance    NUMERIC(10, 6),
    metadata_json JSONB,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_model_features_model_id ON model_features (model_id);

-- Prédictions
CREATE TABLE IF NOT EXISTS predictions (
    id                  SERIAL PRIMARY KEY,
    match_id            INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    market_id           INTEGER NOT NULL REFERENCES markets(id) ON DELETE RESTRICT,
    model_id            INTEGER NOT NULL REFERENCES ai_models(id) ON DELETE RESTRICT,
    model_version       VARCHAR(50) NOT NULL,
    selection           VARCHAR(100) NOT NULL,
    probability         NUMERIC(8, 6) NOT NULL,
    odds                NUMERIC(10, 4),
    implied_probability NUMERIC(8, 6),
    value_edge          NUMERIC(8, 6),
    confidence          VARCHAR(10) NOT NULL DEFAULT 'MEDIUM',
    features_snapshot   JSONB,
    risk_decision       VARCHAR(20),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_predictions_match_id ON predictions (match_id);
CREATE INDEX IF NOT EXISTS idx_predictions_market_id ON predictions (market_id);
CREATE INDEX IF NOT EXISTS idx_predictions_model_id ON predictions (model_id);
CREATE INDEX IF NOT EXISTS idx_predictions_created_at ON predictions (created_at);

-- Résultats prédictions
CREATE TABLE IF NOT EXISTS prediction_results (
    id              SERIAL PRIMARY KEY,
    prediction_id   INTEGER NOT NULL UNIQUE REFERENCES predictions(id) ON DELETE CASCADE,
    actual_result   VARCHAR(100) NOT NULL,
    is_correct      BOOLEAN NOT NULL,
    clv             NUMERIC(8, 6),
    settled_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_prediction_results_prediction_id ON prediction_results (prediction_id);

-- Facteurs de contexte
CREATE TABLE IF NOT EXISTS context_factors (
    id          SERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    factor_name VARCHAR(100) NOT NULL,
    value       NUMERIC(10, 4) NOT NULL DEFAULT 0,
    source      VARCHAR(100),
    reliability VARCHAR(20) NOT NULL DEFAULT 'OFFICIAL',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_context_factors_match_id ON context_factors (match_id);
CREATE INDEX IF NOT EXISTS idx_context_factors_factor_name ON context_factors (factor_name);

-- Facteurs de risque
CREATE TABLE IF NOT EXISTS risk_factors (
    id          SERIAL PRIMARY KEY,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    factor      VARCHAR(100) NOT NULL,
    impact      VARCHAR(255),
    severity    VARCHAR(20) NOT NULL DEFAULT 'LOW',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_risk_factors_match_id ON risk_factors (match_id);

-- Coupons
CREATE TABLE IF NOT EXISTS coupons (
    id            SERIAL PRIMARY KEY,
    type          VARCHAR(20) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    version       INTEGER NOT NULL DEFAULT 1,
    published_at  TIMESTAMPTZ,
    change_reason TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_coupons_type ON coupons (type);
CREATE INDEX IF NOT EXISTS idx_coupons_status ON coupons (status);
CREATE INDEX IF NOT EXISTS idx_coupons_published_at ON coupons (published_at);

-- Liaison coupon ↔ prédiction
CREATE TABLE IF NOT EXISTS coupon_predictions (
    id            SERIAL PRIMARY KEY,
    coupon_id     INTEGER NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
    prediction_id INTEGER NOT NULL REFERENCES predictions(id) ON DELETE CASCADE,
    position      INTEGER NOT NULL,
    UNIQUE (coupon_id, position)
);
CREATE INDEX IF NOT EXISTS idx_coupon_predictions_coupon_id ON coupon_predictions (coupon_id);
CREATE INDEX IF NOT EXISTS idx_coupon_predictions_prediction_id ON coupon_predictions (prediction_id);

-- Versions de coupons
CREATE TABLE IF NOT EXISTS coupon_versions (
    id            SERIAL PRIMARY KEY,
    coupon_id     INTEGER NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
    version       INTEGER NOT NULL,
    change_reason TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_coupon_versions_coupon_id ON coupon_versions (coupon_id);

-- Usage API
CREATE TABLE IF NOT EXISTS api_usage (
    id              SERIAL PRIMARY KEY,
    provider        VARCHAR(50) NOT NULL,
    date            DATE NOT NULL,
    request_count   INTEGER NOT NULL DEFAULT 0,
    last_request_at TIMESTAMPTZ,
    UNIQUE (provider, date)
);
CREATE INDEX IF NOT EXISTS idx_api_usage_provider ON api_usage (provider);

-- Exécutions système
CREATE TABLE IF NOT EXISTS system_runs (
    id                  SERIAL PRIMARY KEY,
    run_type            VARCHAR(50) NOT NULL,
    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,
    status              VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
    error_message       TEXT,
    matches_processed   INTEGER NOT NULL DEFAULT 0,
    predictions_created INTEGER NOT NULL DEFAULT 0,
    coupons_created     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_system_runs_run_type ON system_runs (run_type);
CREATE INDEX IF NOT EXISTS idx_system_runs_started_at ON system_runs (started_at);

COMMIT;
