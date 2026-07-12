const { Telegraf } = require('telegraf');
const db = require('./db/database');
// Admin Telegram user IDs (comma‑separated in .env e.g. ADMIN_TELEGRAM_IDS=123456,789012)
const ADMIN_IDS = (process.env.ADMIN_TELEGRAM_IDS || '').split(',').map(id => parseInt(id)).filter(Boolean);

// Keywords to detect in free‑text messages (lower‑case)
const TECH_KEYWORDS = [
  'ia', 'intelligence artificielle', 'cybersécurité', 'framework', 'frameworks web', 'cloud', 'dev',
  'programmation', 'docker', 'node.js', 'linux', 'api', 'express', 'mysql', 'php', 'java',
  'kubernetes', 'git', 'vs code', 'sql', 'sécurité réseau', 'bases de données', 'devops', 'mobile'
];

let bot = null;

function initBot() {
  const token = process.env.TELEGRAM_BOT_TOKEN;
  if (!token) {
    console.warn("Warning: TELEGRAM_BOT_TOKEN n'est pas configuré. Le bot ne démarrera pas.");
    return null;
  }
  
  bot = new Telegraf(token);
  // Configure webhook for Render deployment
  const webhookUrl = process.env.WEBHOOK_URL || 'https://bottelegramme.onrender.com/bot';
  bot.telegram.setWebhook(webhookUrl);
  console.log(`🔗 Webhook configuré : ${webhookUrl}`);

  // Register commands
  // Register commands
  bot.command('start', require('./commands/start'));
  bot.command('coupon', require('./commands/coupon'));
  bot.command('matchs', require('./commands/matchs'));
  bot.command('technews', require('./commands/technews'));
  bot.command('aide', require('./commands/aide'));
  // New admin‑only commands
  bot.command('status', require('./commands/status'));
  bot.command('historique', require('./commands/historique'));
  bot.command('refresh_coupon', require('./commands/refresh_coupon'));


  // Text message handler – respond only to tech‑related content
  bot.on('text', async (ctx) => {
    const text = (ctx.message.text || '').toLowerCase();
    const isTech = TECH_KEYWORDS.some(kw => text.includes(kw));
    if (isTech) {
      await ctx.reply('Voici une ressource utile sur ce sujet : https://example.com');
    } else {
      await ctx.reply('⚠️ Désolé, je ne peux répondre qu\'aux messages techniques.');
    }
  });

  // Catch errors to prevent bot crashes
  bot.catch((err, ctx) => {
    console.error(`[TELEGRAF] Erreur pour la mise à jour de type ${ctx.updateType}:`, err.message);
  });

  console.log('Bot Telegram configuré et commandes enregistrées.');
  return bot;
}

/**
 * Broadcasts a message to all private chats registered in the database
 * @param {string} text Markdown formatted message
 */
async function broadcast(text) {
  if (!bot) {
    console.warn("[BROADCAST] Le bot n'est pas initialisé ou en cours d'exécution. Impossible de diffuser.");
    return;
  }

  const subscribers = db.getSubscribers();
  console.log(`[BROADCAST] Début de la diffusion du message à ${subscribers.length} abonnés...`);
  
  let successCount = 0;
  let failCount = 0;

  for (const sub of subscribers) {
    // Requirements: "le bot envoie les resultats en prive pas de groupe telegramm"
    if (sub.type !== 'private') {
      console.log(`[BROADCAST] Ignore le chat ${sub.chat_id} car son type est '${sub.type}' (non privé).`);
      continue;
    }

    try {
      await bot.telegram.sendMessage(sub.chat_id, text, { parse_mode: 'Markdown' });
      successCount++;
      // Limit to 30 messages/sec to respect Telegram rate limits
      await new Promise(resolve => setTimeout(resolve, 50));
    } catch (error) {
      failCount++;
      console.error(`[BROADCAST] Échec d'envoi vers le chat ${sub.chat_id}:`, error.message);
      
      // Cleanup subscriber if they blocked the bot or chat doesn't exist
      if (
        error.code === 403 || 
        error.message.includes('blocked') || 
        error.message.includes('chat not found') ||
        error.message.includes('user is deactivated')
      ) {
        console.log(`[BROADCAST] Suppression du chat ${sub.chat_id} de la base de données.`);
        db.removeSubscriber(sub.chat_id);
      }
    }
  }

  console.log(`[BROADCAST] Diffusion terminée : ${successCount} réussites, ${failCount} échecs.`);
}

function getBotInstance() {
  return bot;
}

module.exports = {
  initBot,
  broadcast,
  getBotInstance
};
