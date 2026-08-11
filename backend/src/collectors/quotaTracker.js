/**
 * src/collectors/quotaTracker.js
 * Gestionnaire strict du quota API-Football (100 req/jour gratuit)
 * Arrête tous les appels API dès que le seuil de sécurité est atteint.
 */

const { query } = require('../db/index');
const logger = require('../utils/logger');

const API_NAME = 'api_football';
const DAILY_LIMIT = parseInt(process.env.QUOTA_DAILY_LIMIT || '100', 10);
const SAFETY_THRESHOLD = parseInt(process.env.QUOTA_SAFETY_THRESHOLD || '90', 10);

/**
 * Retourne la date du jour au format YYYY-MM-DD (UTC)
 */
function todayUTC() {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Récupère (ou crée) l'entrée de quota pour aujourd'hui.
 * @returns {Promise<{requests_used: number, quota_exhausted: boolean}>}
 */
async function getOrCreateTodayQuota() {
  const today = todayUTC();

  // Upsert : crée la ligne si elle n'existe pas, sinon la retourne
  const { rows } = await query(
    `INSERT INTO api_quota_tracker (api_name, date, requests_used, daily_limit, safety_threshold, quota_exhausted)
     VALUES ($1, $2, 0, $3, $4, FALSE)
     ON CONFLICT (api_name, date) DO UPDATE
       SET last_updated_at = NOW()
     RETURNING *`,
    [API_NAME, today, DAILY_LIMIT, SAFETY_THRESHOLD]
  );

  return rows[0];
}

/**
 * Vérifie si le quota est disponible pour effectuer `count` requêtes.
 * @param {number} count - Nombre de requêtes à effectuer (défaut: 1)
 * @returns {Promise<boolean>} true si on peut encore faire des appels
 */
async function canMakeRequests(count = 1) {
  const quota = await getOrCreateTodayQuota();

  if (quota.quota_exhausted) {
    logger.warn(`[QuotaTracker] ⛔ Quota API-Football épuisé pour aujourd'hui (${quota.requests_used}/${quota.daily_limit})`);
    return false;
  }

  if (quota.requests_used + count > SAFETY_THRESHOLD) {
    logger.warn(
      `[QuotaTracker] ⚠️  Seuil de sécurité atteint : ${quota.requests_used} utilisées, ` +
      `seuil=${SAFETY_THRESHOLD}. Arrêt des appels API pour aujourd'hui.`
    );
    // Marquer comme épuisé
    await query(
      `UPDATE api_quota_tracker
       SET quota_exhausted = TRUE, last_updated_at = NOW()
       WHERE api_name = $1 AND date = $2`,
      [API_NAME, todayUTC()]
    );
    return false;
  }

  return true;
}

/**
 * Incrémente le compteur de requêtes utilisées.
 * @param {number} count - Nombre de requêtes effectuées (défaut: 1)
 */
async function incrementUsed(count = 1) {
  const today = todayUTC();

  const { rows } = await query(
    `UPDATE api_quota_tracker
     SET requests_used = requests_used + $1,
         last_updated_at = NOW()
     WHERE api_name = $2 AND date = $3
     RETURNING requests_used, daily_limit, safety_threshold`,
    [count, API_NAME, today]
  );

  if (rows.length === 0) return;

  const { requests_used, safety_threshold } = rows[0];
  logger.debug(`[QuotaTracker] Quota API-Football : ${requests_used}/${DAILY_LIMIT} (seuil: ${safety_threshold})`);

  // Marquer comme épuisé si on dépasse le seuil
  if (requests_used >= safety_threshold) {
    await query(
      `UPDATE api_quota_tracker
       SET quota_exhausted = TRUE, last_updated_at = NOW()
       WHERE api_name = $1 AND date = $2`,
      [API_NAME, today]
    );
    logger.warn(`[QuotaTracker] ⛔ Seuil ${safety_threshold} atteint — quota marqué comme épuisé pour aujourd'hui.`);
  }
}

/**
 * Retourne le statut actuel du quota (pour logs et monitoring).
 */
async function getQuotaStatus() {
  const quota = await getOrCreateTodayQuota();
  return {
    date: quota.date,
    api: quota.api_name,
    used: quota.requests_used,
    limit: quota.daily_limit,
    threshold: quota.safety_threshold,
    exhausted: quota.quota_exhausted,
    remaining: Math.max(0, quota.safety_threshold - quota.requests_used),
  };
}

module.exports = { canMakeRequests, incrementUsed, getQuotaStatus, todayUTC };
