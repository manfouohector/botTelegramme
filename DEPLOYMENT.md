# 🚀 Guide de Déploiement Gratuit — DevMind Bot Telegram

Ce guide explique pas à pas comment héberger gratuitement le backend **Node.js**, le moteur IA **Python (FastAPI)** et la base de données **PostgreSQL** sans débourser un centime.

---

## 1. Base de données PostgreSQL (Neon.tech)
1. Créez un compte gratuit sur [Neon.tech](https://neon.tech).
2. Créez un nouveau projet (ex: `devmind-bot`).
3. Copiez la chaîne de connexion SQL (ex: `postgres://user:password@ep-xyz.tech/neondb?sslmode=require`).
4. Dans votre console locale, exécutez les migrations :
   ```bash
   cd backend
   npm run migrate
   ```

---

## 2. Déploiement du moteur IA Python (Render.com)
1. Poussez votre code sur un dépôt **GitHub** (privé ou public).
2. Allez sur [Render.com](https://render.com) et créez un **Web Service**.
3. Connectez votre dépôt GitHub.
4. **Paramètres du service Python** :
   - **Name** : `devmind-prediction-engine`
   - **Root Directory** : `prediction-engine`
   - **Environment** : `Python 3`
   - **Build Command** : `pip install -r requirements.txt`
   - **Start Command** : `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Variables d'environnement (Environment Variables)** :
   - `DATABASE_URL` : (votre URL Neon.tech)
   - `INTERNAL_API_KEY` : (votre clé secrète générée, ex: `super_secret_devmind_key_2026`)
   - `GROQ_API_KEY` : (votre clé API Groq gratuite)

---

## 3. Déploiement du Backend Node.js & Bot (Render.com)
1. Sur Render.com, créez un second **Web Service**.
2. **Paramètres du service Node.js** :
   - **Name** : `devmind-backend`
   - **Root Directory** : `backend`
   - **Environment** : `Node`
   - **Build Command** : `npm install`
   - **Start Command** : `npm start`
3. **Variables d'environnement (Environment Variables)** :
   - `DATABASE_URL` : (votre URL Neon.tech)
   - `INTERNAL_API_KEY` : (la même clé secrète que Python)
   - `PREDICTION_ENGINE_URL` : `https://devmind-prediction-engine.onrender.com` (l'URL fournie par Render pour votre service Python)
   - `API_FOOTBALL_KEY` : (votre clé API-Football)
   - `TELEGRAM_BOT_TOKEN` : (votre token BotFather)
   - `TELEGRAM_FREE_CHANNEL_ID` : (ID numérique négatif du canal gratuit, ex: `-1001234567890`)
   - `TELEGRAM_PREMIUM_GROUP_ID` : (ID numérique négatif du groupe VIP, ex: `-1009876543210`)
   - `TELEGRAM_ADMIN_ID` : (votre ID Telegram personnel pour la commande `/addpremium`)

---

## 4. Configuration finale du Bot Telegram
1. Dans Telegram, créez un canal public et un groupe privé VIP.
2. Ajoutez votre bot (`@devmind_bot`) en tant qu'**Administrateur** avec le droit de publier des messages dans les deux canaux.
3. Obtenez les IDs des canaux en transférant un message de chaque canal au bot `@userinfobot`.

---

## 5. Résumé des Cron Jobs automatiques
Une fois le backend démarré, 2 tâches tournent en arrière-plan :
- **01:00 AM UTC** : Collecte des matchs du jour, génération des prédictions IA, création des coupons et publication automatique sur Telegram.
- **00:05 AM UTC** : Vérification des abonnements expirés, suppression des droits Premium et envoi d'un message d'avertissement aux utilisateurs concernés.
