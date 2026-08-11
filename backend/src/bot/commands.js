const logger = require('../utils/logger');
const { pool } = require('../db/index');

const ADMIN_ID = parseInt(process.env.TELEGRAM_ADMIN_ID || '0', 10);

function registerCommands(bot) {
  
  // Commande /start
  bot.start(async (ctx) => {
    const telegramId = ctx.from.id;
    const username = ctx.from.username || 'Utilisateur';
    
    try {
      // Upsert utilisateur
      await pool.query(`
        INSERT INTO users (telegram_id, username)
        VALUES ($1, $2)
        ON CONFLICT (telegram_id) DO UPDATE SET username = EXCLUDED.username
      `, [telegramId, username]);
      
      ctx.reply(
        `👋 Bienvenue ${username} sur DevMind Bot (IA de Prédictions Sportives) !\n\n` +
        `Je publie des analyses et pronostics gratuits régulièrement.\n` +
        `Pour accéder au Canal Premium (Coupons complets, Value Bets), tapez /premium.`
      );
    } catch (err) {
      logger.error(`[TelegramBot] Erreur /start: ${err.message}`);
    }
  });

  // Commande /premium
  bot.command('premium', (ctx) => {
    ctx.reply(
      "💎 **Canal Premium DevMind**\n\n" +
      "Abonnement : 2500 FCFA / mois\n" +
      "Paiement par Mobile Money (Wave, Orange, MTN, etc.)\n\n" +
      "👉 Pour vous abonner, contactez l'admin sur WhatsApp :\n" +
      "https://wa.me/237XXXXXXXX" // TODO: remplacer par le vrai numéro
    );
  });

  // Commande admin: /addpremium <telegram_id> <jours>
  bot.command('addpremium', async (ctx) => {
    const telegramId = ctx.from.id;
    if (telegramId !== ADMIN_ID && ADMIN_ID !== 0) {
      return ctx.reply("⛔ Non autorisé.");
    }

    const text = ctx.message.text.split(' ');
    if (text.length < 3) {
      return ctx.reply("Usage: /addpremium <telegram_id> <jours>");
    }

    const targetId = parseInt(text[1], 10);
    const days = parseInt(text[2], 10);

    if (isNaN(targetId) || isNaN(days)) {
      return ctx.reply("❌ Paramètres invalides.");
    }

    try {
      const untilDate = new Date();
      untilDate.setDate(untilDate.getDate() + days);

      await pool.query(`
        UPDATE users 
        SET is_premium = TRUE, premium_until = $1
        WHERE telegram_id = $2
      `, [untilDate, targetId]);

      ctx.reply(`✅ Utilisateur ${targetId} mis en Premium pour ${days} jours (jusqu'au ${untilDate.toLocaleDateString()}).\nAttention : il doit rejoindre le canal privé via un lien d'invitation.`);
    } catch (err) {
      logger.error(`[TelegramBot] Erreur /addpremium: ${err.message}`);
      ctx.reply("❌ Erreur de base de données.");
    }
  });

}

module.exports = { registerCommands };
