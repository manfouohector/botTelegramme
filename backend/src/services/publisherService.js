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

/**
 * Génère et publie les coupons du jour (utilisé par le cron et la commande admin).
 * Respecte le nombre maximal de coupons (env COUPON_MAX_DAILY) et le filtre de cote minimale.
 */
async function generateAndPublishToday() {
  const MAX_DAILY_COUPONS = parseInt(process.env.COUPON_MAX_DAILY || '10', 10);
  const MIN_ODDS = parseFloat(process.env.COUPON_MIN_ODDS || '2.0');

  const { collectDailyData } = require('../collectors/dataCollector');
  const { getPredictionForMatch } = require('../services/predictionService');
  const { extractOdds } = require('../utils/oddsParser');
  const logger = require('../utils/logger');

  const result = await collectDailyData();
  if (result.error) {
    logger.error(`[Publisher] Erreur collecte : ${result.error}`);
    return;
  }

  const predictionsToPublish = [];
  for (const match of result.matches) {
    const predResult = await getPredictionForMatch(match);
    if (!predResult || !predResult.probabilities) continue;
    let bestMarket = null;
    let highestProb = 0;
    for (const [market, prob] of Object.entries(predResult.probabilities)) {
      if (prob > highestProb) { highestProb = prob; bestMarket = market; }
    }
    if (bestMarket && highestProb > 0.55) {
      const odds = extractOdds(match.odds, bestMarket) || 1.80;
      if (odds >= MIN_ODDS) {
        predictionsToPublish.push({
          home_team_name: match.home_team_name || 'Home',
          away_team_name: match.away_team_name || 'Away',
          outcome_predicted: bestMarket,
          cote_marche: odds,
          llm_explanation: predResult.llm_explanation || 'Analyse IA non disponible.'
        });
      }
    }
  }

  // Trier par valeur (cote * probabilité approximée)
  predictionsToPublish.sort((a, b) => (b.cote_marche * b.probability || 0) - (a.cote_marche * a.probability || 0));

  const coupons = [];
  let count = 0;
  // Free coupons – un par prédiction
  for (let i = 0; i < predictionsToPublish.length && count < MAX_DAILY_COUPONS; i++) {
    coupons.push({ type: 'free', title: 'DevMind Selection - Safe du Jour', predictions: [predictionsToPublish[i]] });
    count++;
  }
  // Premium coupons – groupes de 3
  for (let i = 0; i < predictionsToPublish.length && count < MAX_DAILY_COUPONS; i += 3) {
    const slice = predictionsToPublish.slice(i, i + 3);
    if (slice.length === 0) break;
    coupons.push({ type: 'premium', title: 'DevMind Selection - VIP Ticket', predictions: slice });
    count++;
  }

  // Publication réelle
  for (const cp of coupons) {
    if (cp.type === 'free') await publishFreeCoupon({ title: cp.title, predictions: cp.predictions });
    else await publishPremiumCoupon({ title: cp.title, predictions: cp.predictions });
  }
  logger.info(`[Publisher] Publication terminée – ${coupons.length} coupon(s) généré(s).`);
}

module.exports = {
  formatCouponMessage,
  publishFreeCoupon,
  publishPremiumCoupon,
  generateAndPublishToday
};
