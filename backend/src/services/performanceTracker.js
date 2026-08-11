/**
 * src/services/performanceTracker.js
 * Tracking et calcul de performance des prédictions (Win Rate, ROI)
 */

const { pool } = require('../db/index');
const logger = require('../utils/logger');

/**
 * Évalue si le résultat d'un match valide une prédiction donnée
 */
function evaluateOutcome(outcomePredicted, homeScore, awayScore) {
  if (homeScore === null || awayScore === null) return null;

  const totalGoals = homeScore + awayScore;

  switch (outcomePredicted) {
    case '1X2_1':
    case '1':
      return homeScore > awayScore;

    case '1X2_X':
    case 'X':
      return homeScore === awayScore;

    case '1X2_2':
    case '2':
      return awayScore > homeScore;

    case 'BTTS_YES':
      return homeScore > 0 && awayScore > 0;

    case 'BTTS_NO':
      return homeScore === 0 || awayScore === 0;

    case 'OVER_2_5':
      return totalGoals > 2.5;

    case 'UNDER_2_5':
      return totalGoals < 2.5;

    case 'OVER_3_5':
      return totalGoals > 3.5;

    case 'UNDER_3_5':
      return totalGoals < 3.5;

    case 'DOUBLE_CHANCE_1X':
    case '1X':
      return homeScore >= awayScore;

    case 'DOUBLE_CHANCE_X2':
    case 'X2':
      return awayScore >= homeScore;

    case 'DOUBLE_CHANCE_12':
    case '12':
      return homeScore !== awayScore;

    case 'DRAW_NO_BET_1':
      return homeScore > awayScore;

    case 'DRAW_NO_BET_2':
      return awayScore > homeScore;

    default:
      return null;
  }
}

/**
 * Vérifie toutes les prédictions en attente pour des matchs terminés
 */
async function verifyPendingPredictions() {
  logger.info('[PerformanceTracker] 🔍 Vérification des prédictions des matchs terminés...');

  try {
    const { rows: unverified } = await pool.query(`
      SELECT 
        p.id AS prediction_id,
        p.outcome_predicted,
        p.market_id,
        p.cote_marche,
        m.home_score,
        m.away_score,
        m.status
      FROM predictions p
      JOIN matches m ON p.match_id = m.id
      LEFT JOIN prediction_results pr ON p.id = pr.prediction_id
      WHERE m.status = 'finished'
        AND pr.id IS NULL
        AND m.home_score IS NOT NULL
        AND m.away_score IS NOT NULL
    `);

    if (unverified.length === 0) {
      logger.info('[PerformanceTracker] ℹ️ Aucune prédiction en attente de vérification.');
      return { verified: 0 };
    }

    let correctCount = 0;
    let failedCount = 0;

    for (const pred of unverified) {
      const isCorrect = evaluateOutcome(pred.outcome_predicted, pred.home_score, pred.away_score);
      if (isCorrect === null) continue;

      const actualOutcome = `${pred.home_score}-${pred.away_score}`;

      await pool.query(`
        INSERT INTO prediction_results (prediction_id, actual_outcome, is_correct)
        VALUES ($1, $2, $3)
        ON CONFLICT (prediction_id) DO NOTHING
      `, [pred.prediction_id, actualOutcome, isCorrect]);

      if (isCorrect) correctCount++;
      else failedCount++;
    }

    logger.info(`[PerformanceTracker] ✅ Vérification terminée: ${correctCount} GAGNANTS, ${failedCount} PERDANTS sur ${unverified.length} traités.`);

    // Recalculer les statistiques agrégées
    await updatePerformanceStats();

    return { verified: unverified.length, correct: correctCount, failed: failedCount };
  } catch (err) {
    logger.error(`[PerformanceTracker] Erreur lors de la vérification: ${err.message}`);
    throw err;
  }
}

/**
 * Recalcule et met à jour les stats agrégées (Win Rate, ROI) dans performance_stats
 */
async function updatePerformanceStats() {
  logger.info('[PerformanceTracker] 📊 Recalcul des statistiques de performance...');

  try {
    const today = new Date().toISOString().slice(0, 10);

    // Agrégation par marché
    const { rows: stats } = await pool.query(`
      SELECT 
        p.market_id,
        COUNT(pr.id) AS total_predictions,
        COUNT(CASE WHEN pr.is_correct = TRUE THEN 1 END) AS correct_predictions,
        COALESCE(SUM(CASE WHEN pr.is_correct = TRUE THEN COALESCE(p.cote_marche, 1.5) - 1 ELSE -1 END), 0) AS profit
      FROM prediction_results pr
      JOIN predictions p ON pr.prediction_id = p.id
      GROUP BY p.market_id
    `);

    for (const stat of stats) {
      const total = parseInt(stat.total_predictions, 10);
      const correct = parseInt(stat.correct_predictions, 10);
      const profit = parseFloat(stat.profit);
      const roi = total > 0 ? profit / total : 0;

      await pool.query(`
        INSERT INTO performance_stats (market_id, period, period_type, total_predictions, correct_predictions, roi)
        VALUES ($1, $2, 'daily', $3, $4, $5)
        ON CONFLICT (market_id, period, period_type) 
        DO UPDATE SET 
          total_predictions = EXCLUDED.total_predictions,
          correct_predictions = EXCLUDED.correct_predictions,
          roi = EXCLUDED.roi,
          calculated_at = NOW()
      `, [stat.market_id, today, total, correct, roi]);
    }

    logger.info('[PerformanceTracker] 📊 Statistiques de performance mises à jour.');
  } catch (err) {
    logger.error(`[PerformanceTracker] Erreur lors de la mise à jour des stats: ${err.message}`);
  }
}

module.exports = {
  verifyPendingPredictions,
  updatePerformanceStats,
  evaluateOutcome
};
