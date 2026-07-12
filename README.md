# Bot Telegram de Pronostics Sportifs & Actualités Tech

Ce projet est un bot Telegram Node.js complet qui propose deux fonctionnalités principales :
1. **Des pronostics de football** générés par l'IA (tri rapide Groq et analyse approfondie Gemini avec recherche web Google Search Grounding).
2. **Des actualités technologiques** hebdomadaires/quotidiennes extraites de flux RSS et synthétisées en français pour les développeurs.

Le bot est optimisé pour maîtriser les coûts des API en fonctionnant en mode "données pré-générées" (mises en cache quotidiennement dans SQLite via des tâches cron). Il répond aux requêtes en privé (messages directs / DM).

---

## 🛠️ Stack Technique
- **Runtime** : Node.js + Express
- **Bot Framework** : Telegraf
- **Base de données** : SQLite via `better-sqlite3` (fichier `data/bot.db` créé automatiquement)
- **Tâches planifiées** : `node-cron`
- **Clients API IA** : `groq-sdk` (Llama-3) et `@google/generative-ai` (Gemini avec Grounding)
- **Réseau & RSS** : `axios` et `rss-parser`

---

## 📋 Prérequis & Configuration

### 1. Clés d'API nécessaires
Vous devez obtenir les clés suivantes :
- **Telegram Bot Token** : Obtenu auprès du `@BotFather` sur Telegram en créant un bot.
- **Groq API Key** : Créez un compte sur [Groq Console](https://console.groq.com/) pour générer une clé.
- **Gemini API Key** : Obtenu sur Google AI Studio.
- **Football Data API Key** : Inscrivez-vous gratuitement sur [football-data.org](https://www.football-data.org/) pour obtenir une clé d'accès gratuite.

### 2. Variables d'environnement
Créez un fichier `.env` à la racine du projet (ou copiez le fichier `.env.example`) :
```env
TELEGRAM_BOT_TOKEN=ton_token_bot_telegram
GROQ_API_KEY=ta_cle_groq
GEMINI_API_KEY=ta_cle_gemini
FOOTBALL_DATA_API_KEY=ta_cle_football_data
PORT=3000
```

---

## 🚀 Démarrage

### Installation des dépendances
```bash
npm install
```

### Lancement en mode développement (avec rechargement automatique)
```bash
npm run dev
```

### Lancement en production
```bash
npm start 
```

---

## 🤖 Commandes du Bot Telegram

- `/start` : Démarre le bot, enregistre l'utilisateur en privé pour recevoir les futures diffusions automatiques, et affiche un message de bienvenue.
- `/coupon` : Récupère le coupon de pronostics du jour (généré à 8h00). Si le coupon n'est pas encore prêt, le bot invite à réessayer plus tard.
- `/matchs` : Affiche la liste des matchs analysés pour la journée (sans le détail complet du pronostic).
- `/technews` : Récupère les actualités tech synthétisées du jour (généré à 9h00).
- `/aide` : Affiche la liste des commandes disponibles et leur description.

*Note : Conformément aux exigences, le bot diffuse les résultats uniquement aux abonnés en privé (DM) et pas dans les groupes.*

---

## ⚙️ Tâches Planifiées (Cron)
- **Coupon Football** : Généré automatiquement à **08h00** tous les jours.
- **Actualités Tech** : Générées automatiquement à **09h00** tous les jours.

---

## 🩺 Endpoints HTTP & Déclenchements Manuels (Express)
Pour faciliter le développement et les tests, le serveur Express expose les points d'accès suivants sur le port configuré (par défaut 3000) :

- **Health Check** : `GET http://localhost:3000/health`
- **Déclencher le pipeline Football manuellement** :
  ```bash
  curl -X POST http://localhost:3000/api/trigger/coupon
  ```
  *(Optionnel)* Vous pouvez forcer une date spécifique en passant un paramètre de requête ou un corps JSON (format `YYYY-MM-DD`) :
  ```bash
  curl -X POST http://localhost:3000/api/trigger/coupon?date=2026-07-12
  ```
- **Déclencher le pipeline Tech News manuellement** :
  ```bash
  curl -X POST http://localhost:3000/api/trigger/technews
  ```

---

## 🧪 Tests Automatisés
Les tests utilisent le framework de test natif de Node.js (disponible depuis Node 18+). Les appels d'API et le comportement du bot sont mockés pour s'exécuter hors ligne et sans coût d'API.

Pour exécuter les tests :
```bash
npm test
```

Les fichiers de test se trouvent dans le dossier `/tests` :
- `db.test.js` : Teste les opérations CRUD de la base SQLite.
- `rss.test.js` : Teste l'agrégation et le tri chronologique des flux RSS de manière mockée.
- `pipelines.test.js` : Teste l'orchestration complète des deux pipelines avec mock des réponses Groq, Gemini et Football-Data.
- `bot.test.js` : Teste les réponses des commandes du bot en simulant le contexte Telegraf.
