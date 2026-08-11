/**
 * src/services/publisherService.js
 * Publication automatique des pronostics et coupons sur Telegram
 */

const { bot } = require('../bot/index');
const logger = require('../utils/logger');

const FREE_CHANNEL_ID = process.env.TELEGRAM_FREE_CHANNEL_ID;
const PREMIUM_GROUP_ID = process.env.TELEGRAM_PREMIUM_GROUP_ID;

/**
 * Formate un coupon sous forme de message Telegram attrayant
 */
function formatCouponMessage(coupon, isPremium = false) {
  const emojiTier = isPremium ? '💎 [COUPON PREMIUM VIP]' : '⚽ [PRONOSTIC GRATUIT DU JOUR]';
  
  let message = `${emojiTier}\n`;
  message += `🏆 **${coupon.title || 'DevMind Selection'}**\n`;
  message += `------------------------------------\n\n`;

  let totalOdds = 1.0;

  if (coupon.predictions && coupon.predictions.length > 0) {
    coupon.predictions.forEach((p, idx) => {
      const matchName = `${p.home_team_name} vs ${p.away_team_name}`;
      const outcome = p.outcome_predicted;
      const odds = p.cote_marche ? p.cote_marche.toFixed(2) : '1.50';
      totalOdds *= parseFloat(odds);

      message += `📌 **Match ${idx + 1}** : ${matchName}\n`;
      message += `👉 **Pari** : \`${outcome}\` | Cote : **${odds}**\n`;
      
      if (isPremium && p.llm_explanation) {
        message += `💡 *Analyse IA* : ${p.llm_explanation}\n`;
      }
      message += `\n`;
    });
  }

  message += `------------------------------------\n`;
  message += `💰 **Cote Totale Estimée** : **${totalOdds.toFixed(2)}**\n`;
  
  if (!isPremium) {
    message += `\n🔥 Pour accéder aux coupons VIP complets (Safe, Value Bets, High Odds), rejoignez le Premium avec /premium !`;
  }

  return message;
}

/**
 * Publie le coupon gratuit du jour sur le canal public
 */
async function publishFreeCoupon(coupon) {
  if (!FREE_CHANNEL_ID) {
    logger.warn('[Publisher] ⚠️ TELEGRAM_FREE_CHANNEL_ID non configuré.');
    return false;
  }

  try {
    const text = formatCouponMessage(coupon, false);
    await bot.telegram.sendMessage(FREE_CHANNEL_ID, text, { parse_mode: 'Markdown' });
    logger.info(`[Publisher] ✅ Coupon gratuit publié sur le canal ${FREE_CHANNEL_ID}`);
    return true;
  } catch (err) {
    logger.error(`[Publisher] Erreur lors de la publication gratuite: ${err.message}`);
    return false;
  }
}

/**
 * Publie les coupons VIP sur le groupe Premium
 */
async function publishPremiumCoupon(coupon) {
  if (!PREMIUM_GROUP_ID) {
    logger.warn('[Publisher] ⚠️ TELEGRAM_PREMIUM_GROUP_ID non configuré.');
    return false;
  }

  try {
    const text = formatCouponMessage(coupon, true);
    await bot.telegram.sendMessage(PREMIUM_GROUP_ID, text, { parse_mode: 'Markdown' });
    logger.info(`[Publisher] 💎 Coupon Premium publié sur le groupe ${PREMIUM_GROUP_ID}`);
    return true;
  } catch (err) {
    logger.error(`[Publisher] Erreur lors de la publication Premium: ${err.message}`);
    return false;
  }
}

module.exports = {
  formatCouponMessage,
  publishFreeCoupon,
  publishPremiumCoupon
};
