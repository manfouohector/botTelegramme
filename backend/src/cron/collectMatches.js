/**
 * src/cron/collectMatches.js
 * Cron job quotidien pour collecter les matchs du jour.
 */
const cron = require('node-cron');
const { collectDailyData } = require('../collectors/dataCollector');
const { getPredictionForMatch } = require('../services/predictionService');
const { publishFreeCoupon, publishPremiumCoupon } = require('../services/publisherService');
const { extractOdds } = require('../utils/oddsParser');
const logger = require('../utils/logger');

function initCronJobs() {
  // Tourne tous les jours à 01:00 AM
  cron.schedule('0 1 * * *', async () => {
    logger.info('[CRON] ⏰ Démarrage de la tâche quotidienne de collecte et publication des coupons');
    try {
      const { generateAndPublishToday } = require('../services/publisherService');
      await generateAndPublishToday();
      logger.info('[CRON] ✅ Publication des coupons terminée.');
    } catch (err) {
      logger.error(`[CRON] Erreur lors de la génération/publishing : ${err.message}`);
    }
    try {
      const result = await collectDailyData();
      
      if (result.error) {
        logger.error(`[CRON] Erreur lors de la collecte: ${result.error}`);
        return;
      }
      
      logger.info(`[CRON] ✅ Collecte terminée.`);
      logger.info(`[CRON] Matches récupérés: ${result.matches.length}`);
      
      // --- Traitement des prédictions (Module 8 & 13) ---
      const predictionsToPublish = [];
      
      for (const match of result.matches) {
        // Appeler le Prediction Engine
        const predResult = await getPredictionForMatch(match);
        if (!predResult || !predResult.probabilities) continue;
        
        // Trouver la probabilité la plus élevée (logique simplifiée MVP)
        let bestMarket = null;
        let highestProb = 0;
        
        for (const [market, prob] of Object.entries(predResult.probabilities)) {
          if (prob > highestProb) {
            highestProb = prob;
            bestMarket = market;
          }
        }
        
        if (bestMarket && highestProb > 0.55) { // Confiance minimale
          predictionsToPublish.push({
            home_team_name: match.home_team_name || 'Home',
            away_team_name: match.away_team_name || 'Away',
            outcome_predicted: bestMarket,
            cote_marche: extractOdds(match.odds, bestMarket) || 1.80, // Si API absente, fallback à 1.80
            llm_explanation: predResult.llm_explanation || "Analyse IA non disponible."
          });
        }
      }
      
      // Publication sur Telegram si on a des pronostics
      if (predictionsToPublish.length > 0) {
        // Création du coupon gratuit (1 match safe)
        const freeCoupon = {
          title: "DevMind Selection - Safe du Jour",
          predictions: [predictionsToPublish[0]]
        };
        await publishFreeCoupon(freeCoupon);
        
        // Création du coupon VIP (tous les matchs trouvés, max 3 pour l'exemple)
        if (predictionsToPublish.length > 1) {
          const premiumCoupon = {
            title: "DevMind Selection - VIP Ticket",
            predictions: predictionsToPublish.slice(0, 3)
          };
          await publishPremiumCoupon(premiumCoupon);
        }
      } else {
        logger.info('[CRON] Aucun pronostic jugé assez fiable aujourd\'hui.');
      }
    } catch (err) {
      logger.error(`[CRON] Erreur fatale: ${err.message}`);
    }
  }, {
    scheduled: true,
    timezone: "UTC"
  });
  
  logger.info('[CRON] Jobs initialisés (Collecte: 01:00 AM UTC)');
}

module.exports = { initCronJobs };
