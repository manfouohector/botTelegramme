const db = require('../db/database');
const { isSchedulerActive } = require('../services/scheduler');

module.exports = async (ctx) => {
  // Check admin authorization
  const adminIdsEnv = process.env.ADMIN_TELEGRAM_IDS || '';
  const adminIds = adminIdsEnv.split(',').map(id => parseInt(id.trim(), 10)).filter(Boolean);
  
  if (adminIds.length > 0 && !adminIds.includes(ctx.from.id)) {
    return ctx.reply("⚠️ Désolé, cette commande est réservée aux administrateurs.");
  }

  // Verify SQLite Connection
  let sqliteStatus = '❌ SQLite KO';
  try {
    const rawDb = db.getDb();
    if (rawDb) {
      // Execute simple query
      rawDb.prepare('SELECT 1').get();
      sqliteStatus = '✅ SQLite OK';
    }
  } catch (error) {
    console.error('Erreur lors de la vérification de SQLite:', error.message);
  }

  // Verify Cron Scheduler
  let cronStatus = '❌ Cron KO';
  try {
    if (typeof isSchedulerActive === 'function' && isSchedulerActive()) {
      cronStatus = '✅ Cron actif';
    }
  } catch (error) {
    console.error('Erreur lors de la vérification du planificateur:', error.message);
  }

  // Webhook URL status
  const webhookUrl = process.env.WEBHOOK_URL;
  const webhookDisplay = webhookUrl ? webhookUrl : '⚠️ non configurée';

  const message = [
    sqliteStatus,
    cronStatus,
    `🔗 Webhook : ${webhookDisplay}`
  ].join('\n');

  await ctx.replyWithMarkdown(message);
};
