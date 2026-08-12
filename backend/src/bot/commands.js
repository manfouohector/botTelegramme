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
    const price = process.env.SUBSCRIPTION_PRICE_FCFA || '2500';
    const duration = process.env.SUBSCRIPTION_DURATION_DAYS || '30';
    const provider = process.env.MOBILE_MONEY_PROVIDER || 'Mobile Money';
    const waNumber = process.env.WHATSAPP_NUMBER || '237XXXXXXXX';
    
    ctx.reply(
      "💎 **Canal Premium DevMind**\n\n" +
      `Abonnement : ${price} FCFA / ${duration} jours\n` +
      `Paiement par : ${provider}\n\n` +
      "👉 Pour vous abonner, contactez l'admin sur WhatsApp :\n" +
      `https://wa.me/${waNumber}`
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

  // --------------------------
  // ADMIN COMMAND: /couponstatus – Affiche l'état du coupon du jour
  // --------------------------
  bot.command('couponstatus', async (ctx) => {
    const telegramId = ctx.from.id;
    if (telegramId !== ADMIN_ID && ADMIN_ID !== 0) {
      return ctx.reply('⛔ Non autorisé.');
    }
    try {
      const today = new Date().toISOString().slice(0, 10);
      const res = await pool.query('SELECT id, type, predictions FROM coupons WHERE created_at::date = $1', [today]);
      if (res.rowCount === 0) {
        return ctx.reply('🗓 Aucun coupon publié aujourd\'hui.');
      }
      let msg = `📊 Coupons du ${today}:\n`;
      res.rows.forEach((c) => {
        const preds = JSON.parse(c.predictions);
        const count = preds.length;
        const oddsInfo = preds.map(p => `${p.cote_marche || 'N/A'}`).join(', ');
        msg += `- ${c.type.toUpperCase()} (ID ${c.id}) – ${count} sélection(s) – Cotes: ${oddsInfo}\n`;
      });
      ctx.reply(msg);
    } catch (err) {
      logger.error(`[TelegramBot] Erreur /couponstatus: ${err.message}`);
      ctx.reply('❌ Erreur lors de la récupération des coupons.');
    }
  });

  // --------------------------
  // ADMIN COMMAND: /gencoupon – Génère le coupon du jour manuellement
  // --------------------------
  const { generateAndPublishToday } = require('../services/publisherService');
  bot.command('gencoupon', async (ctx) => {
    const telegramId = ctx.from.id;
    if (telegramId !== ADMIN_ID && ADMIN_ID !== 0) {
      return ctx.reply('⛔ Non autorisé.');
    }
    try {
      await generateAndPublishToday();
      ctx.reply('✅ Coupon du jour généré et publié avec succès.');
    } catch (err) {
      logger.error(`[TelegramBot] Erreur /gencoupon: ${err.message}`);
      ctx.reply('❌ Erreur lors de la génération du coupon.');
    }
  });

}

module.exports = { registerCommands };
