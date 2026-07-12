// Charger les variables d'environnement
require('dotenv').config();

const { initDatabase } = require('./db/database');
const { initBot } = require('./bot');
const { initScheduler } = require('./services/scheduler');
const { createServer } = require('./server');

async function main() {
  console.log('--- DÉMARRAGE DE L\'APPLICATION ---');

  try {
    // 1. Initialiser la base de données SQLite
    initDatabase();

    // 2. Initialiser le bot Telegram
    const bot = initBot();
    if (bot) {
      // Démarrer Telegraf
      if (process.env.WEBHOOK_URL) {
        // Webhook mode – no polling launch
        console.log('🤖 Bot en mode webhook, démarrage par Render');
      } else {
        bot.launch()
          .then(() => console.log('🤖 Le Bot Telegram est en ligne (polling)'))
          .catch(err => console.error('❌ Échec du démarrage du Bot Telegram:', err.message));
      }

      // Gérer l'arrêt propre
      process.once('SIGINT', () => bot.stop('SIGINT'));
      process.once('SIGTERM', () => bot.stop('SIGTERM'));
    } else {
      console.warn("⚠️ Le Bot Telegram n'a pas été lancé (TELEGRAM_BOT_TOKEN manquant).");
    }

    // 3. Initialiser le planificateur de tâches (cron)
    initScheduler();

    // 4. Démarrer le serveur Express
    const app = createServer();
    const port = process.env.PORT || 3000;
    app.listen(port, () => {
      console.log(`🌐 Serveur Express actif sur http://localhost:${port}`);
      console.log(`Diagnostic : http://localhost:${port}/health`);
    });

  } catch (error) {
    console.error('❌ Erreur critique lors du démarrage:', error.message);
    process.exit(1);
  }
}

main();
