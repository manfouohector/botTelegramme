const { Telegraf } = require('telegraf');
const logger = require('../utils/logger');
const { registerCommands } = require('./commands');
require('dotenv').config();

const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

function initBot() {
  if (!process.env.TELEGRAM_BOT_TOKEN) {
    logger.warn('[TelegramBot] ⚠️ TELEGRAM_BOT_TOKEN non défini, bot inactif.');
    return;
  }

  // --- Enregistrement des commandes ---
  registerCommands(bot);

  // --- Gestion des erreurs ---
  bot.catch((err, ctx) => {
    logger.error(`[TelegramBot] Erreur pour ${ctx.updateType}: ${err}`);
  });

  // Démarrage du bot en mode polling pour le dev (Webhook sera utilisé sur Render)
  bot.launch().then(() => {
    logger.info('[TelegramBot] 🤖 Bot démarré avec succès.');
  }).catch((err) => {
    logger.error(`[TelegramBot] Erreur au lancement: ${err.message}`);
  });

  // Enable graceful stop
  process.once('SIGINT', () => bot.stop('SIGINT'));
  process.once('SIGTERM', () => bot.stop('SIGTERM'));
}

module.exports = { initBot, bot };
