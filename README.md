# Football Prediction Bot — MVP

Système de prédictions football pour Telegram, basé sur statistiques + Machine Learning.

## Stack

- **Python 3.11+**
- **FastAPI** (API interne si nécessaire)
- **PostgreSQL**
- **Sportmonks** (données football)
- **The Odds API** (cotes bookmakers)
- **python-telegram-bot**
- **scikit-learn / XGBoost**
- **Render** (hébergement prévu)

## Structure du projet

```
app/
├── bot/           # Bot Telegram
├── api/           # API FastAPI interne
├── config/        # Configuration (.env)
├── database/      # Connexion PostgreSQL, sessions
├── models/        # Modèles SQLAlchemy / domaine
├── repositories/  # Accès données
├── services/      # Logique métier transverse
├── collectors/    # Data Collector Sportmonks
├── prediction/    # Prediction Engine
├── features/      # Feature Engineering
├── context/       # Context Engine
├── xg/            # xG Engine
├── value/         # Value Engine
├── risk/          # Risk Engine
├── coupons/       # Coupon Generator
├── tracking/      # Tracking résultats
├── backtesting/   # Backtesting + évaluation
├── jobs/          # Tâches planifiées (cron)
└── utils/         # Logging, helpers

migrations/        # Migrations SQL PostgreSQL
models/            # Artifacts ML entraînés (.pkl, etc.)
scripts/           # Scripts utilitaires
tests/
├── unit/
├── integration/
└── fixtures/
```

## Installation locale

```bash
# 1. Cloner le repo
cd botTelegramme

# 2. Créer un environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer l'environnement
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
# Renseigner les variables dans .env (voir section ci-dessous)

# 5. Vérifier le démarrage
python -m app.main

# 6. Lancer les tests
pytest
```

## Variables d'environnement

Copier `.env.example` vers `.env` et renseigner les valeurs.
**Ne jamais committer `.env`.**

Voir `.env.example` pour la liste complète des variables.

## Module 1 — Statut

- [x] Structure du projet
- [x] Configuration centralisée (`app/config/settings.py`)
- [x] Logging structuré (`app/utils/logging.py`)
- [x] `.env.example` (noms uniquement, valeurs vides)
- [x] `.gitignore`
- [x] `requirements.txt`
- [x] Tests unitaires et d'intégration Module 1

## Module 2 — Statut

- [x] Connexion PostgreSQL (`app/database/session.py`)
- [x] Base SQLAlchemy + enums (`app/database/base.py`, `enums.py`)
- [x] 24 modèles ORM (`app/models/`)
- [x] Migration SQL initiale (`migrations/001_init_schema.sql`)
- [x] Script de migration (`scripts/run_migrations.py`)
- [x] Tests modèles, migrations et session (19 tests Module 2)

## Module 3 — Statut

- [x] Client Sportmonks HTTP (`app/collectors/sportmonks_client.py`)
- [x] Normalizers (`app/collectors/normalizers.py`)
- [x] Data Collector (`app/collectors/data_collector.py`)
- [x] Repositories football + api_usage
- [x] Script CLI (`scripts/run_collector.py`)
- [x] Tests unitaires avec fixtures mock (30 tests Module 3)

## Module 4 — Statut

- [x] Schemas features (`app/features/schemas.py`)
- [x] MatchHistoryRepository anti-leakage (`app/repositories/match_history_repository.py`)
- [x] Calculateurs : forme, domicile/extérieur, attaque/défense, H2H
- [x] FeatureEngine (`app/features/feature_engine.py`)
- [x] Export dict + vecteur plat pour ML
- [x] Tests unitaires (21 tests Module 4)

### Features calculées

| Catégorie | Features |
|---|---|
| Forme | wins, draws, losses, points/match, buts M/E, séries |
| Domicile/Extérieur | performance par venue |
| Attaque/Défense | buts M/E, tirs si disponibles (type_42/49) |
| H2H | victoires, nuls, buts moyens (fenêtre limitée) |

Anti-leakage : uniquement matchs `FINISHED` avec `scheduled_at < match cible`.

## Module 5 — Statut

- [x] Calcul classement depuis PostgreSQL (`app/context/standings.py`)
- [x] Facteurs numériques (`title_race`, `relegation_battle`, `european_race`, `derby`, `high_stakes`…)
- [x] ContextEngine (`app/context/context_engine.py`)
- [x] Persistance table `context_factors` (`ContextRepository`)
- [x] Export dict + vecteur plat pour ML
- [x] Tests unitaires (15 tests Module 5)

### Facteurs de contexte calculés

| Facteur | Description |
|---|---|
| `title_race` | Course au titre (top N configurable) |
| `relegation_battle` | Lutte pour le maintien (bottom N) |
| `european_race` | Qualification européenne |
| `derby` | Paire configurée via `CONTEXT_DERBY_PAIRS` |
| `cup_match` | Détection coupe via nom compétition |
| `high_stakes` | Enjeu élevé (titre/maintien/derby/coupe) |
| `matches_remaining` | Matchs SCHEDULED restants |
| `home/away_position`, `points_gap`, `gap_to_leader` | Classement |

### Utilisation

```python
from app.context import ContextEngine
from app.database.session import session_scope

with session_scope() as session:
    engine = ContextEngine(session)
    ctx = engine.build_context(match_id=123, persist=True)
    print(ctx.get_factor("high_stakes"))
    print(ctx.flat_features())
```

## Module 6 — Statut

- [x] Extraction stats tirs Sportmonks (`type_42`, `type_49`)
- [x] Modèle proxy Poisson calibré sur la saison (`app/xg/proxy_model.py`)
- [x] XGEngine (`app/xg/xg_engine.py`)
- [x] Export dict + vecteur plat pour ML
- [x] Tests unitaires (15 tests Module 6)

### Limitation importante

Sportmonks **xGFixture** (xG shot-level) nécessite un plan premium.
Ce module produit un **proxy xG** basé sur tirs/tirs cadrés, calibré via régression Poisson sur les buts réels de la saison.
`is_true_xg=False` est toujours renvoyé pour ce modèle.

Si les données sont insuffisantes, le statut est `UNAVAILABLE` — aucune formule arbitraire inventée.

### Variables d'environnement

| Variable | Description |
|---|---|
| `XG_FORM_WINDOW` | Fenêtre matchs pour moyennes tirs (défaut: 5) |
| `XG_MIN_MATCHES` | Minimum matchs avec stats tirs par équipe |
| `XG_MIN_TRAINING_SAMPLES` | Minimum échantillons saison pour entraîner le proxy |
| `XG_ENABLE_SHOT_PROXY` | Activer/désactiver le modèle proxy |

### Utilisation

```python
from app.xg import XGEngine
from app.database.session import session_scope

with session_scope() as session:
    engine = XGEngine(session)
    xg = engine.build_xg(match_id=123)
    print(xg.home_xg, xg.away_xg, xg.xg_difference)
    print(xg.flat_features())
```

## Module 7 — Statut

- [x] Poisson + Dixon-Coles (`app/prediction/poisson.py`, `dixon_coles.py`)
- [x] Estimation lambdas depuis features + xG proxy (`app/prediction/lambdas.py`)
- [x] Marchés : 1X2, BTTS, Over/Under 2.5 (`app/prediction/markets.py`)
- [x] ML 1X2 optionnel (LogisticRegression) + ensemble simple
- [x] Confiance distincte de la probabilité (`app/prediction/confidence.py`)
- [x] PredictionEngine + persistance PostgreSQL (`PredictionRepository`)
- [x] Tests unitaires (15 tests Module 7)

### Pipeline

```
Features (M4) + Context (M5) + xG (M6)
        ↓
Lambdas (buts attendus)
        ↓
Matrice Poisson → Dixon-Coles
        ↓
Marchés (1X2, BTTS, OU2.5)
        ↓
[+ ML 1X2 si ≥ N échantillons] → ensemble
        ↓
Confiance (HIGH / MEDIUM / LOW)
```

### Probabilité vs confiance

| Concept | Signification |
|---|---|
| `probability` | Estimation du modèle (ex. HOME = 0.68) |
| `confidence` | Qualité/coherence des données (HIGH/MEDIUM/LOW) |

La calibration (Platt, Isotonic) est implémentée au **Module 8**.

### Utilisation

```python
from app.prediction import PredictionEngine
from app.database.session import session_scope

with session_scope() as session:
    engine = PredictionEngine(session)
    pred = engine.build_prediction(match_id=123, persist=True)
    print(pred.get_probability("1X2", "HOME"))
    print(pred.confidence)
    print(pred.flat_probabilities())
```

## Module 8 — Statut

- [x] Métriques Brier, Log Loss, ECE (`app/calibration/metrics.py`)
- [x] Calibrateurs Platt + Isotonic par issue (`app/calibration/calibrators.py`)
- [x] CalibrationEngine — fit, calibrate, evaluate (`app/calibration/calibration_engine.py`)
- [x] Évaluation historique via PredictionEngine (`app/calibration/evaluator.py`)
- [x] Persistance artifacts (`models/calibration/`)
- [x] Tests unitaires (15 tests Module 8)

### Pipeline

```
Prédiction brute (Module 7)
        ↓
Calibration Platt / Isotonic (par issue, renormalisation)
        ↓
Probabilités calibrées → Value Engine (Module 9)
```

### Métriques évaluées

| Métrique | Description |
|---|---|
| Brier Score | Erreur quadratique des probabilités |
| Log Loss | Pénalité logarithmique |
| ECE | Expected Calibration Error (bins configurables) |

### Utilisation

```python
from app.calibration import CalibrationEngine
from app.prediction import PredictionEngine
from app.database.session import session_scope

with session_scope() as session:
    pred_engine = PredictionEngine(session)
    cal_engine = CalibrationEngine(session, prediction_engine=pred_engine)

    # Entraîner sur l'historique saison
    cal_engine.fit_from_season(season_id=1, before_date=target_date)

    # Prédire + calibrer
    raw = pred_engine.build_prediction(match_id=123)
    calibrated = cal_engine.calibrate(raw)

    # Évaluer
    report = cal_engine.evaluate_season(season_id=1, before_date=target_date)
    cal_engine.save()
```

## Module 9 — Statut

- [x] Client The Odds API v4 (`app/value/odds_api_client.py`)
- [x] Normalizer + persistance cotes PostgreSQL (`OddsRepository`)
- [x] Odds Collector (`app/value/odds_collector.py`)
- [x] Probabilités implicites + normalisation overround (`app/value/implied.py`)
- [x] ValueEngine — edge configurable (`app/value/value_engine.py`)
- [x] Script CLI `scripts/run_odds_collector.py`
- [x] Tests unitaires (16 tests Module 9)

### Pipeline

```
MODÈLE (calibré) → probabilité
        ↓
The Odds API → cotes bookmakers → table `odds`
        ↓
ValueEngine : edge = P_modèle − P_marché (normalisée)
        ↓
Risk Engine (Module 10)
```

### Exemple value

| | Valeur |
|---|---|
| Modèle PSG HOME | 68% |
| Cote bookmaker | 1.70 |
| Implicite brute | 58.8% |
| Edge | **+9.2%** (si ≥ seuil → value) |

### Utilisation

```python
from app.value import ValueEngine, OddsCollector
from app.prediction import PredictionEngine
from app.database.session import session_scope

with session_scope() as session:
    # 1. Collecter cotes
    OddsCollector(session).collect_for_sport("soccer_france_ligue_one")

    # 2. Analyser value
    pred = PredictionEngine(session).build_prediction(match_id=123)
    analysis = ValueEngine(session).analyze(pred)
    if analysis.has_value:
        print(analysis.best_value.to_dict())
```

```bash
python scripts/run_odds_collector.py --sport soccer_france_ligue_one
python scripts/run_odds_collector.py --sport soccer_epl --match-id 42
```

## Module 10 — Statut

- [x] Règles de risque configurables (`app/risk/rules.py`)
- [x] RiskEngine — APPROVE / WARNING / REJECT (`app/risk/risk_engine.py`)
- [x] Persistance table `risk_factors` (`RiskRepository`)
- [x] Contrôles : confiance, données, value, edge extrême, contexte, blessures/compositions
- [x] Tests unitaires (15 tests Module 10)

### Décisions

| Décision | Signification |
|---|---|
| `APPROVE` | Publiable |
| `WARNING` | Publiable avec prudence |
| `REJECT` | Non publiable (ex. confiance LOW, données incomplètes) |

### Pipeline

```
ValueEngine → opportunité value
        ↓
RiskEngine (confiance + données + edge + contexte)
        ↓
APPROVE / WARNING / REJECT → Coupon Generator (Module 11)
```

### Utilisation

```python
from app.risk import RiskEngine
from app.prediction import PredictionEngine
from app.value import ValueEngine

pred = PredictionEngine(session).build_prediction(match_id=123)
analysis = ValueEngine(session).analyze(pred)
assessment = RiskEngine(session).assess(pred, analysis, persist=True)

if assessment.publishable:
    print(assessment.decision, assessment.selections)
```

## Module 11 — Statut

- [x] Sélecteurs SAFE / VALUE / HIGH_ODDS / FREE (`app/coupons/selectors.py`)
- [x] CouponGenerator — 0 à 4 coupons selon qualité (`app/coupons/coupon_generator.py`)
- [x] Builder candidats depuis pipeline (`app/coupons/candidate_builder.py`)
- [x] Persistance coupons + versions (`CouponRepository`)
- [x] Tests unitaires (20 tests Module 11) — **210/210** suite complète

### Types de coupons

| Type | Sélections | Critères |
|---|---|---|
| `FREE` | 3–4 | Vitrine gratuite, confiance HIGH/MEDIUM, APPROVE |
| `SAFE` | 3–5 | Probabilité élevée, cotes modérées, confiance HIGH |
| `VALUE` | 2–5 | Edge value ≥ seuil, sélections `is_value` |
| `HIGH_ODDS` | 4–7 | Cotes individuelles élevées, combinée ≥ 15 |

Le générateur **ne remplit jamais artificiellement** un coupon : si les critères ne sont pas atteints, le type est ignoré (`skipped=True`).

### Pipeline

```
RiskEngine (publishable)
        ↓
CouponCandidate[]
        ↓
CouponGenerator → FREE / SAFE / VALUE / HIGH_ODDS
        ↓
CouponRepository (coupons + coupon_predictions + coupon_versions)
```

### Utilisation

```python
from app.coupons import CouponGenerator
from app.coupons.candidate_builder import build_candidate
from app.prediction import PredictionEngine
from app.value import ValueEngine
from app.risk import RiskEngine

pred = PredictionEngine(session).build_prediction(match_id=123)
analysis = ValueEngine(session).analyze(pred)
assessment = RiskEngine(session).assess(pred, analysis)

if assessment.publishable and analysis.best_value:
    candidate = build_candidate(pred, analysis.best_value, assessment)
    result = CouponGenerator(session).generate([candidate], persist=True)
    print(result.coupons_created, result.to_dict())
```

## Module 12 — Statut

- [x] Résolution résultats réels 1X2 / BTTS / OU25 (`app/tracking/outcome_resolver.py`)
- [x] TrackingEngine — settlement prédictions + coupons (`app/tracking/tracking_engine.py`)
- [x] Métriques : accuracy, ROI, Brier, Log Loss, CLV (`app/tracking/metrics.py`)
- [x] Persistance `prediction_results` + historique (`TrackingRepository`)
- [x] Breakdown par marché, type de coupon, version modèle
- [x] Script CLI (`scripts/run_settlement.py`)
- [x] Tests unitaires (26 tests Module 12) — **236/236** suite complète

### Settlement

Chaque prédiction publiée est comparée au résultat réel après le match :

```
Match FINISHED (scores connus)
        ↓
resolve_market_outcome → actual_result
        ↓
is_correct = (selection == actual_result)
        ↓
prediction_results (+ CLV si cote clôture disponible)
        ↓
Coupon SETTLED si toutes les sélections réglées
```

Les mauvais résultats sont **conservés** — transparence totale.

### Métriques calculées

| Métrique | Description |
|---|---|
| Accuracy | Taux de réussite des sélections |
| ROI théorique | Profit unitaire moyen (mise = 1) |
| Brier / Log Loss | Qualité probabiliste binaire |
| CLV | (cote prise / cote clôture) − 1 |
| By market / coupon / model | Breakdowns configurables |

### Utilisation

```python
from app.tracking import TrackingEngine

engine = TrackingEngine(session)

# Batch quotidien (matchs terminés + coupons publiés)
batch = engine.settle_pending()
session.commit()

# Métriques et historique
metrics = engine.get_metrics(days_back=30)
history = engine.get_history(limit=20)
print(metrics.accuracy, len(history))
```

### Lancer le settlement

```bash
# Tous les matchs/coupons en attente
python scripts/run_settlement.py

# Fenêtre personnalisée
python scripts/run_settlement.py --days-back 7

# Un match spécifique
python scripts/run_settlement.py --match-id 42
```

## Module 13 — Statut

- [x] Factory Application PTB (`app/bot/application.py`)
- [x] Runner polling / webhook (`app/bot/runner.py`)
- [x] Middleware tracking utilisateur → table `users`
- [x] Gestion globale des erreurs
- [x] Handler `/ping` + fallback commandes inconnues
- [x] `UserRepository` + script CLI (`scripts/run_bot.py`)
- [x] Tests unitaires (22 tests Module 13) — **254/254** suite complète

### Architecture

```
TELEGRAM_BOT_TOKEN + DATABASE_URL
        ↓
create_application() → handlers + middleware
        ↓
run_bot() → polling (défaut) ou webhook
        ↓
Chaque update → ensure_user() en base
```

Les commandes `/start`, `/free`, `/premium` sont implémentées au **Module 14**.

### Utilisation

```python
from app.bot import create_application, run_bot

# Démarrage complet (polling)
run_bot()

# Ou construction manuelle pour tests
app = create_application()
app.run_polling()
```

### Lancer le bot

```bash
# 1. Renseigner TELEGRAM_BOT_TOKEN et DATABASE_URL dans .env
# 2. Lancer en polling (développement local)
python scripts/run_bot.py
```

Variables utiles : `TELEGRAM_BOT_MODE`, `TELEGRAM_WEBHOOK_URL`, `TELEGRAM_DROP_PENDING_UPDATES`.

## Module 14 — Statut

- [x] `/start` — accueil + boutons Canal Gratuit / Premium (`app/bot/handlers/commands.py`)
- [x] `/free` — lien canal gratuit (`TELEGRAM_FREE_CHANNEL_ID`)
- [x] `/premium` — prix, durée, Mobile Money, lien WhatsApp dynamique
- [x] Callbacks inline pour les boutons (`app/bot/handlers/callbacks.py`)
- [x] Builders liens t.me et wa.me (`app/bot/utils/links.py`)
- [x] Tests unitaires (18 tests Module 14) — **270/270** suite complète

### Commandes V1

| Commande | Action |
|---|---|
| `/start` | Présentation produit + clavier inline |
| `/free` | Lien vers le canal gratuit |
| `/premium` | Offre Premium + bouton WhatsApp pré-rempli |

Pas de `/stats` ni `/account` en V1.

### Lien WhatsApp dynamique

```
https://wa.me/{WHATSAPP_PHONE}?text=Bonjour...ID Telegram...username...
```

Variables : `WHATSAPP_PHONE`, `PREMIUM_PRICE`, `PREMIUM_DURATION_DAYS`, `MOBILE_MONEY_NUMBER`.

## Module 15 — Statut

- [x] `PremiumService` — activation, prolongation, statut (`app/services/premium_service.py`)
- [x] Repositories `subscriptions` + `payments`
- [x] Commande admin `/activate <telegram_id>` (`app/bot/handlers/admin.py`)
- [x] Vérification `ADMIN_TELEGRAM_ID` (`app/bot/auth.py`)
- [x] Invitation groupe Premium via lien unique (`app/bot/services/group_service.py`)
- [x] `/premium` affiche le statut si déjà abonné
- [x] Tests unitaires (15 tests Module 15) — **282/282** suite complète

### Flux paiement V1

```
Utilisateur → /premium → WhatsApp → Mobile Money → preuve
        ↓
Admin vérifie → /activate 123456789
        ↓
Abonnement ACTIVE + payment SUCCESS + invitation groupe Premium
```

### Commande admin

```
/activate 123456789
```

Réservée à `ADMIN_TELEGRAM_ID`. Crée l'utilisateur en base s'il n'existe pas encore.

Variables : `ADMIN_TELEGRAM_ID`, `TELEGRAM_PREMIUM_GROUP_ID`, `PREMIUM_DURATION_DAYS`, `PREMIUM_AMOUNT`.

## Module 16 — Statut

- [x] Détection abonnements expirés (`date_fin <= now`, statut ACTIVE)
- [x] `SubscriptionExpirationService` — expiration + retrait groupe + notification
- [x] Enregistrement dans `system_runs` (type `SUBSCRIPTION_EXPIRATION`)
- [x] Job + script CLI (`scripts/run_expiration.py`)
- [x] Tests unitaires (11 tests Module 16) — **293/293** suite complète

### Comportement

Chaque jour (cron à `SUBSCRIPTION_EXPIRATION_TIME`, timezone `TIMEZONE`) :

```
Abonnements ACTIVE + date_fin dépassée
        ↓
statut → EXPIRED
        ↓
Retrait du groupe Premium (ban/unban)
        ↓
Message privé optionnel (/premium pour renouveler)
        ↓
Log system_runs
```

Indépendant du paiement — basé uniquement sur `date_fin`.

### Lancer l'expiration

```bash
# Complet (DB + Telegram si TELEGRAM_BOT_TOKEN configuré)
python scripts/run_expiration.py

# Base de données uniquement
python scripts/run_expiration.py --db-only

# Sans notification privée
python scripts/run_expiration.py --no-notify
```

Variables : `SUBSCRIPTION_EXPIRATION_TIME`, `SUBSCRIPTION_EXPIRATION_NOTIFY`, `TIMEZONE`.

## Module 17 — Statut

- [x] `/generate` — pipeline complet manuel (`GenerationService`)
- [x] `/status` — état génération du jour (`StatusService` + `system_runs`)
- [x] `/history` — historique sélections réglées (`HistoryService`)
- [x] Vérification `ADMIN_TELEGRAM_ID` sur toutes les commandes admin
- [x] Script CLI (`scripts/run_generation.py`)
- [x] Tests unitaires (17 tests Module 17) — **310/310** suite complète

### Commandes admin V1

| Commande | Action |
|---|---|
| `/activate <telegram_id>` | Active Premium (Module 15) |
| `/generate` | Lance Collector → Prediction → Calibration → Value → Risk → Coupons |
| `/status` | Statut du jour (matchs, prédictions, coupons créés/envoyés) |
| `/history [YYYY-MM-DD]` | Résultats des coupons réglés |

Réservées à `ADMIN_TELEGRAM_ID`. Pas de `/admin`, `/broadcast`, `/stats`, `/account`.

### Pipeline `/generate`

```
Data Collector (Sportmonks)
        ↓
Odds Collector (The Odds API)
        ↓
Prediction → Calibration → Value → Risk
        ↓
Coupon Generator (FREE / SAFE / VALUE / HIGH_ODDS)
        ↓
Publication Telegram (Module 18)
        ↓
Résultat envoyé en privé à l'admin
```

### Lancer la génération (CLI)

```bash
# Génération du jour
python scripts/run_generation.py

# Date spécifique
python scripts/run_generation.py --date 2026-08-13

# Sans collecte externe (matchs/cotes déjà en base)
python scripts/run_generation.py --skip-collector --skip-odds

# Avec publication Telegram
python scripts/run_generation.py --publish --phase free
python scripts/run_generation.py --publish --phase premium
```

Log `system_runs` : type `DAILY_GENERATION`.

## Module 18 — Statut

- [x] `PublicationService` — envoi Telegram canal Free + groupe Premium
- [x] Formatage messages FREE (vitrine) et Premium (détaillé)
- [x] Détection doublons — « Coupon confirmé — aucun changement majeur. »
- [x] Intégration `/generate` + CLI `--publish --phase`
- [x] Log `system_runs` type `TELEGRAM_PUBLICATION`
- [x] Tests unitaires (10 tests Module 18) — **320/320** suite complète

### Destinations

| Type coupon | Destination |
|---|---|
| `FREE` | `TELEGRAM_FREE_CHANNEL_ID` |
| `SAFE`, `VALUE`, `HIGH_ODDS` | `TELEGRAM_PREMIUM_GROUP_ID` |

### Phases de publication

| Phase | Moment (spec) | Contenu |
|---|---|---|
| `free` | Matin (~08h00) | Coupon gratuit vitrine |
| `premium` | Avant matchs | SAFE, VALUE, HIGH_ODDS |
| `all` | `/generate` manuel | Tous les coupons créés |

Si le contenu est identique au dernier coupon publié du jour, le système envoie une confirmation sans republier le coupon complet.

Variables : `PUBLICATION_ENABLE`, `PUBLICATION_CONFIRM_IF_UNCHANGED`, `TELEGRAM_FREE_CHANNEL_ID`, `TELEGRAM_PREMIUM_GROUP_ID`, `TELEGRAM_BOT_TOKEN`.

## Module 19 — Statut

- [x] Scheduler APScheduler (`app/jobs/scheduler.py`)
- [x] 6 tâches planifiées (`app/jobs/tasks.py`)
- [x] Script CLI `scripts/run_scheduler.py` (daemon + exécution manuelle)
- [x] Phases génération `free` / `premium` dans `GenerationService`
- [x] Tests unitaires (8 tests Module 19) — **328/328** suite complète

### Tâches planifiées

| # | Job | Horaire / fréquence | Action |
|---|---|---|---|
| 1 | `daily_analysis` | `DAILY_ANALYSIS_TIME` | Collecte → analyse → coupon FREE → publication canal |
| 2 | `final_analysis` | Toutes les `FINAL_ANALYSIS_CHECK_INTERVAL_MINUTES` | Si match dans `FINAL_ANALYSIS_MINUTES_BEFORE` → Premium + publication groupe |
| 3 | `results_collection` | `RESULTS_COLLECTION_TIME` | Récupération scores/résultats (hier + aujourd'hui) |
| 4 | `settlement` | `SETTLEMENT_TIME` | Règlement prédictions et coupons |
| 5 | `subscription_expiration` | `SUBSCRIPTION_EXPIRATION_TIME` | Expiration Premium |
| 6 | `maintenance` | 03:00 (timezone) | Santé PostgreSQL + log |

Tous les horaires utilisent `TIMEZONE` (jamais hardcodé).

### Lancer le scheduler

```bash
# Processus daemon (Render worker / VPS)
python scripts/run_scheduler.py

# Lister les jobs configurés
python scripts/run_scheduler.py --list

# Exécuter un job immédiatement
python scripts/run_scheduler.py --run daily_analysis
python scripts/run_scheduler.py --run final_analysis
python scripts/run_scheduler.py --run results_collection
python scripts/run_scheduler.py --run settlement
python scripts/run_scheduler.py --run subscription_expiration
python scripts/run_scheduler.py --run maintenance
```

Variables : `SCHEDULER_ENABLE`, `DAILY_ANALYSIS_TIME`, `FINAL_ANALYSIS_MINUTES_BEFORE`, `FINAL_ANALYSIS_CHECK_INTERVAL_MINUTES`, `RESULTS_COLLECTION_TIME`, `SETTLEMENT_TIME`, `SUBSCRIPTION_EXPIRATION_TIME`, `TIMEZONE`.

Log `system_runs` : `DAILY_ANALYSIS`, `FINAL_ANALYSIS`, `RESULTS_COLLECTION`, `SETTLEMENT`, `SUBSCRIPTION_EXPIRATION`, `MAINTENANCE`.

## Module 20 — Statut

- [x] Backtest walk-forward sans data leakage (`app/backtesting/backtest_engine.py`)
- [x] Comparaison variantes Poisson / Dixon-Coles / Ensemble
- [x] Model Registry — versions persistées, jamais écrasées (`app/backtesting/model_registry.py`)
- [x] CLV — opening/published + closing odds (`app/backtesting/clv_service.py`)
- [x] Hook publication → enregistrement cotes opening (`PublicationService`)
- [x] Scripts CLI `scripts/run_backtest.py`, `scripts/run_clv_update.py`
- [x] Tests unitaires (13 tests Module 20) — **341/341** suite complète

### Backtesting walk-forward

Anti-leakage : pour chaque match terminé, `as_of = scheduled_at` (via `PredictionEngine`).

```bash
# Backtest simple (saison + date limite)
python scripts/run_backtest.py --season-id 1 --before 2026-08-22

# Comparer les variantes
python scripts/run_backtest.py --season-id 1 --before 2026-08-22 --compare

# Enregistrer dans le Model Registry
python scripts/run_backtest.py --season-id 1 --compare --register
```

### Model Registry

Chaque backtest peut être enregistré comme version (`ai_models.metrics` JSON).
Les versions antérieures restent en base — `upsert` met à jour une version existante uniquement si `(name, version)` est identique.

### CLV (Closing Line Value)

`CLV = (cote publiée / cote clôture) - 1`

```bash
# Mettre à jour closing odds (matchs imminents)
python scripts/run_clv_update.py

# Avec analyse agrégée
python scripts/run_clv_update.py --analyze
```

Variables : `BACKTEST_MIN_MATCHES`, `BACKTEST_DEFAULT_LIMIT`, `CLV_UPDATE_HOURS_BEFORE_KICKOFF`.

Log `system_runs` : `BACKTEST`, `CLV_UPDATE`.

## Module 21 — Statut

- [x] Suite tests d'intégration (`tests/integration/`)
- [x] Pipeline complet Features → Context → xG → Prediction → Value → Risk
- [x] Cycle génération → publication → settlement → historique / CLV
- [x] Jobs settlement + CLV refresh (session réelle)
- [x] Premium activation → expiration
- [x] Admin `/status` + `/history` bout en bout
- [x] Backtest → Model Registry
- [x] Corrections bugs détectés (Risk + CalibratedMatchPrediction, Premium timezone, enum CouponType SQLite)
- [x] Tests — **355/355** suite complète (14 tests d'intégration Module 21)

### Fichiers d'intégration

| Fichier | Flux testé |
|---|---|
| `test_prediction_pipeline.py` | Feature → Context → xG → Prediction → Value → Risk → candidats |
| `test_generation_lifecycle.py` | GenerationService → Publication → Settlement → History / CLV |
| `test_jobs_integration.py` | `run_settlement`, `run_job_sync`, refresh CLV |
| `test_premium_lifecycle.py` | Activation → prolongation → expiration |
| `test_admin_workflow.py` | StatusService + HistoryService |
| `test_backtest_integration.py` | Backtest → enregistrement registry |

Fixtures partagées : `tests/integration/conftest.py` (`integration_settings`, `seeded_match_day`).

```bash
# Lancer uniquement les tests d'intégration
pytest tests/integration/ -v

# Suite complète
pytest
```

## Module 22 — Statut

- [x] Blueprint Render (`render.yaml`) — PostgreSQL + Web + Worker scheduler
- [x] Service web FastAPI (`app/api/web_app.py`) — `/health` + webhook Telegram
- [x] Script `scripts/run_web.py` (uvicorn, port `$PORT`)
- [x] `runtime.txt` Python 3.12.7
- [x] Normalisation `postgres://` → `postgresql://` (Render DATABASE_URL)
- [x] Migrations auto au déploiement (`preDeployCommand`)
- [x] Tests unitaires (9 tests Module 22) — **364/364** suite complète

### Architecture Render

| Service | Type | Rôle |
|---|---|---|
| `football-bot-db` | PostgreSQL | Base de données |
| `football-bot-web` | Web | Health check + webhook Telegram |
| `football-bot-scheduler` | Worker | APScheduler (analyses, settlement, expiration) |

### Déployer sur Render

1. Pousser le repo sur GitHub/GitLab
2. Render Dashboard → **New Blueprint** → sélectionner le repo (`render.yaml`)
3. Renseigner les variables `sync: false` :
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_URL` → `https://<football-bot-web>.onrender.com/telegram`
   - `TELEGRAM_FREE_CHANNEL_ID`, `TELEGRAM_PREMIUM_GROUP_ID`
   - `ADMIN_TELEGRAM_ID`
   - `SPORTMONKS_API_TOKEN`, `SPORTMONKS_LEAGUE_IDS`
   - `ODDS_API_KEY`, `ODDS_API_SPORT_KEYS`
4. Déployer — les migrations s'exécutent automatiquement avant le web service

### Variables production essentielles

```
APP_ENV=production
TELEGRAM_BOT_MODE=webhook
TELEGRAM_WEBHOOK_PATH=telegram
TELEGRAM_WEBHOOK_URL=https://football-bot-web.onrender.com/telegram
SCHEDULER_ENABLE=false          # web service
SCHEDULER_ENABLE=true           # worker scheduler
PUBLICATION_ENABLE=true
TIMEZONE=Africa/Douala
```

### Vérifier le déploiement

```bash
curl https://<football-bot-web>.onrender.com/health
# {"status":"ok","database_ok":true,...}
```

Bot Telegram : envoyer `/ping` au bot — doit répondre.

### Développement local (webhook simulé)

```bash
python scripts/run_web.py
# Health : http://localhost:8000/health
```

### Lancer le Data Collector

```bash
# Collecte du jour (timezone configurée)
python scripts/run_collector.py

# Date spécifique
python scripts/run_collector.py --date 2026-08-13

# Plage de dates
python scripts/run_collector.py --start 2026-08-10 --end 2026-08-13

# Forcer re-fetch (ignorer cache TTL)
python scripts/run_collector.py --force
```

### Migration PostgreSQL

```bash
# 1. Renseigner DATABASE_URL dans .env
# 2. Exécuter les migrations
python scripts/run_migrations.py
```

Format `DATABASE_URL` :
```
postgresql://user:password@host:5432/dbname
```

### Tables créées (24 + schema_migrations)

`users`, `subscriptions`, `payments`, `competitions`, `seasons`, `teams`,
`matches`, `match_statistics`, `players`, `injuries`, `lineups`, `markets`,
`odds`, `ai_models`, `model_features`, `predictions`, `prediction_results`,
`context_factors`, `risk_factors`, `coupons`, `coupon_predictions`,
`coupon_versions`, `api_usage`, `system_runs`

## Développement module par module

Le projet est développé strictement module par module.
Ne pas passer au module suivant sans validation du précédent.

Ordre prévu :
1. Structure + config ✅
2. PostgreSQL + migrations ✅
3. Data Collector Sportmonks ✅
4. Feature Engineering ✅
5. Context Engine ✅
6. xG Engine ✅
7. Prediction Engine ✅
8. Calibration ✅
9. Value Engine + Odds API ✅
10. Risk Engine ✅
11. Coupon Generator ✅
12. Tracking ✅
13. Bot Telegram ✅
14. Commandes utilisateurs ✅
15. Premium + /activate ✅
16. Expiration abonnements ✅
17. Commandes admin ✅
18. Publication automatique ✅
19. Cron / automatisation ✅
20. Backtesting + Model Registry + CLV ✅
21. Tests d'intégration complets ✅
22. Déploiement Render ✅

## Licence

Projet privé — tous droits réservés.
