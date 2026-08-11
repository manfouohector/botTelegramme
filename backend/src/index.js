/**
 * src/index.js — Point d'entrée principal du backend DevMind Bot
 */

require('dotenv').config();
const express = require('express');
const cors = require('cors');
const logger = require('./utils/logger');
const { initCronJobs } = require('./cron/collectMatches');
const { initSubscriptionCron } = require('./cron/checkSubscriptions');
const { initBot } = require('./bot/index');

const app = express();
const PORT = process.env.PORT || 3000;

// ---- Middleware ----
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Middleware de logging des requêtes HTTP
app.use((req, _res, next) => {
  logger.debug(`${req.method} ${req.path}`);
  next();
});

// ---- Route de santé (health check) ----
app.get('/health', (_req, res) => {
  res.json({
    status: 'ok',
    service: 'devmind-backend',
    version: '1.0.0',
    timestamp: new Date().toISOString(),
  });
});

// ---- Gestion 404 ----
app.use((_req, res) => {
  res.status(404).json({ error: 'Route non trouvée' });
});

// ---- Gestion des erreurs globales ----
app.use((err, _req, res, _next) => {
  logger.error(`Erreur non gérée: ${err.message}`, { stack: err.stack });
  res.status(500).json({ error: 'Erreur interne du serveur' });
});

// ---- Démarrage du serveur ----
app.listen(PORT, () => {
  logger.info(`🚀 DevMind Backend démarré sur le port ${PORT}`);
  logger.info(`   Environnement : ${process.env.NODE_ENV || 'development'}`);
  
  // Démarrer le cron job de collecte (Module 13)
  initCronJobs();
  
  // Démarrer le cron de vérification des abonnements (Module 11)
  initSubscriptionCron();
  
  // Démarrer le bot Telegram (Module 9)
  initBot();
});

module.exports = app;
