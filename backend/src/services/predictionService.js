const axios = require('axios');
const logger = require('../utils/logger');
require('dotenv').config();

const PREDICTION_ENGINE_URL = process.env.PREDICTION_ENGINE_URL || 'http://localhost:8000';
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY;

/**
 * Appelle le Prediction Engine (Python) pour un match
 * @param {Object} match Données du match venant de notre DB
 */
async function getPredictionForMatch(match) {
  try {
    // Calcul basique d'xG pour le MVP (à améliorer avec le vrai modèle ML plus tard)
    // Ici on simule une moyenne basée sur les stats brutes ou on donne des valeurs par défaut
    const homeXg = match.raw_stats?.shots_on_target?.home ? match.raw_stats.shots_on_target.home * 0.3 : 1.5;
    const awayXg = match.raw_stats?.shots_on_target?.away ? match.raw_stats.shots_on_target.away * 0.3 : 1.2;

    const response = await axios.post(
      `${PREDICTION_ENGINE_URL}/predict/`,
      {
        match_id: match.external_id,
        home_expected_goals: homeXg,
        away_expected_goals: awayXg,
        match_data: {
          home_stats: match.raw_stats,
          away_stats: match.raw_stats, // Simplifié pour le MVP
        }
      },
      {
        headers: {
          'X-API-Key': INTERNAL_API_KEY,
          'Content-Type': 'application/json'
        },
        timeout: 10000
      }
    );

    return response.data;
  } catch (error) {
    logger.error(`[PredictionService] Erreur lors de la prédiction pour le match ${match.external_id}: ${error.message}`);
    return null;
  }
}

module.exports = {
  getPredictionForMatch
};
