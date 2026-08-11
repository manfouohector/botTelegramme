# DevMind Bot — Bot Telegram de Prédictions Sportives IA

## 📁 Structure du projet

```
botTelegramme/
├── backend/                    # Service Node.js/Express (Render #1)
│   ├── migrations/
│   │   └── 001_init.sql        # Schéma PostgreSQL complet (15 tables)
│   ├── src/
│   │   ├── db/
│   │   │   ├── index.js        # Pool de connexion PostgreSQL
│   │   │   └── migrate.js      # Runner de migrations SQL
│   │   ├── utils/
│   │   │   └── logger.js       # Logger Winston
│   │   └── index.js            # Serveur Express principal
│   ├── test-db-connection.js   # Script de test de connexion DB
│   ├── package.json
│   └── .env.example
│
├── prediction-engine/          # Service Python/FastAPI (Render #2)
│   ├── app/
│   │   ├── db/
│   │   │   └── database.py     # Connexion SQLAlchemy
│   │   └── main.py             # Application FastAPI
│   ├── test_db_connection.py   # Script de test de connexion DB
│   ├── requirements.txt
│   └── .env.example
│
└── README.md
```

## 🚀 Démarrage rapide

### Prérequis
- Node.js >= 20
- Python >= 3.11
- Une base PostgreSQL (Neon.tech ou Supabase — gratuit)

### 1. Configuration de l'environnement

```bash
# Backend Node.js
cd backend
cp .env.example .env
# Remplissez .env avec vos valeurs

# Prediction Engine Python
cd ../prediction-engine
cp .env.example .env
# Remplissez .env avec vos valeurs
```

### 2. Installation des dépendances

```bash
# Backend Node.js
cd backend
npm install

# Prediction Engine Python
cd ../prediction-engine
pip install -r requirements.txt
```

### 3. Migration de la base de données

```bash
cd backend
npm run migrate
```

### 4. Test de connexion

```bash
# Test Node.js
cd backend
node test-db-connection.js

# Test Python
cd ../prediction-engine
python test_db_connection.py
```

### 5. Démarrage en développement

```bash
# Terminal 1 — Backend Node.js
cd backend
npm run dev

# Terminal 2 — Prediction Engine Python
cd prediction-engine
python app/main.py
```

## 🏗️ Architecture

| Service | Technologie | Port |
|---|---|---|
| Backend principal | Node.js 20 + Express + Telegraf | 3000 |
| Moteur prédiction | Python 3.11 + FastAPI | 8000 |
| Base de données | PostgreSQL (Neon.tech) | 5432 |

## 🗄️ Tables de base de données

| Table | Description |
|---|---|
| `ai_models` | Versions des modèles IA (Poisson, XGBoost, Ensemble) |
| `leagues` | Championnats couverts (Ligue 1, PL, Liga, Serie A, Bundesliga, UCL) |
| `teams` | Équipes |
| `users` | Utilisateurs Telegram |
| `subscriptions` | Abonnements Premium (1 mois = 2500 FCFA) |
| `payments` | Paiements (V1: manuel WhatsApp) |
| `matches` | Matchs du jour avec cache `last_fetched_at` |
| `api_quota_tracker` | Compteur strict quotidien API-Football (seuil 90/100) |
| `markets` | Types de paris (1X2, BTTS, Over/Under, etc.) |
| `predictions` | Prédictions avec probabilités modèle vs marché |
| `risk_factors` | Facteurs de risque par match |
| `coupons` | Tickets regroupés (Safe/Medium/High Odds) |
| `coupon_predictions` | Jointure coupon ↔ prédictions |
| `prediction_results` | Résultats réels vs prédictions |
| `performance_stats` | Stats de performance agrégées |

## ⚙️ Variables d'environnement

Voir `backend/.env.example` et `prediction-engine/.env.example` pour la liste complète.

## 🚢 Déploiement sur Render

*(Instructions complètes à venir lors de l'étape finale)*

**Service 1 — Backend Node.js**
- Build command: `npm install`
- Start command: `node src/index.js`

**Service 2 — Prediction Engine Python**
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

*DevMind Bot — Développé module par module, testé à chaque étape.*
