/**
 * src/cron/checkSubscriptions.js
 * Vérifie quotidiennement les abonnements Premium expirés et met à jour la base.
 */
const cron = require('node-cron');
const logger = require('../utils/logger');
const { pool } = require('../db/index');
const { bot } = require('../bot/index');

function initSubscriptionCron() {
  // Tourne tous les jours à 00:05 AM
  cron.schedule('5 0 * * *', async () => {
    logger.info('[CRON] ⏰ Démarrage de la vérification des abonnements Premium...');
    try {
      // Rechercher les utilisateurs expirés
      const result = await pool.query(`
        UPDATE users 
        SET is_premium = FALSE 
        WHERE is_premium = TRUE 
        AND premium_until < NOW()
        RETURNING telegram_id
      `);

      const expiredUsers = result.rows;
      logger.info(`[CRON] ✅ ${expiredUsers.length} abonnement(s) expiré(s) révoqué(s).`);

      // Notifier les utilisateurs expirés si le bot est actif
      if (process.env.TELEGRAM_BOT_TOKEN) {
        for (const user of expiredUsers) {
          try {
            await bot.telegram.sendMessage(
              user.telegram_id,
              "⚠️ Votre abonnement Premium DevMind est expiré.\n\n" +
              "Vous n'avez plus accès au canal privé. Pour vous réabonner, tapez /premium et contactez l'admin."
            );
          } catch (err) {
            logger.warn(`[CRON] Impossible de notifier l'utilisateur ${user.telegram_id} : ${err.message}`);
          }
        }
      }
    } catch (err) {
      logger.error(`[CRON] Erreur lors de la vérification des abonnements: ${err.message}`);
    }
  }, {
    scheduled: true,
    timezone: "UTC"
  });
  
  logger.info('[CRON] Job Abonnements initialisé (00:05 AM UTC)');
}

module.exports = { initSubscriptionCron };
