/**
 * src/collectors/dataCollector.js
 * Orchestrateur principal du Data Collector
 *
 * Flux :
 * 1. Vérifie le quota API-Football
 * 2. Récupère les fixtures du jour (API-Football ou fallback FD.org)
 * 3. Pour chaque match : vérifie le cache, récupère stats/lineups/blessures/cotes
 * 4. Sauvegarde en base PostgreSQL
 * 5. Retourne la liste des matchs prêts pour le moteur de prédiction
 */

const logger = require('../utils/logger');
const { canMakeRequests, getQuotaStatus } = require('./quotaTracker');
const {
  getFixturesToday,
  getFixtureStatistics,
  getFixtureLineups,
  getFixtureInjuries,
  getFixtureOdds,
} = require('./apiFootballClient');
const { getMatches } = require('./footballDataClient');
const {
  getCachedMatch,
  upsertMatchFromApiFootball,
  upsertMatchFromFallback,
  updateMatchDetails,
  getTodayMatches,
} = require('./matchRepository');

// Délai entre chaque appel API pour éviter de dépasser le rate limit
const REQUEST_DELAY_MS = 500;

/**
 * Attend N millisecondes
 */
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

/**
 * Point d'entrée principal du Data Collector.
 * Appelé par le cron quotidien.
 *
 * @param {string} date - YYYY-MM-DD (optionnel, défaut: aujourd'hui)
 * @returns {Promise<{matches: Array, quota: Object, source: string}>}
 */
async function collectDailyData(date = null) {
  const targetDate = date || new Date().toISOString().slice(0, 10);
  logger.info(`\n${'='.repeat(60)}`);
  logger.info(`[DataCollector] 🚀 Démarrage de la collecte pour le ${targetDate}`);
  logger.info(`${'='.repeat(60)}`);

  // --- Étape 1 : Vérification du quota ---
  const quotaStatus = await getQuotaStatus();
  logger.info(`[DataCollector] 📊 Quota API-Football : ${quotaStatus.used}/${quotaStatus.limit} (seuil: ${quotaStatus.threshold})`);

  if (quotaStatus.exhausted) {
    logger.warn('[DataCollector] ⛔ Quota déjà épuisé — passage en mode fallback');
    return await collectViaFallback(targetDate);
  }

  // --- Étape 2 : Récupération des matchs via football-data.org (source principale) ---
  let fixtures = [];
  let usedApiFootball = false;

  try {
    fixtures = await getMatches(targetDate);
    if (fixtures.length > 0) {
      logger.info(`[DataCollector] ✅ ${fixtures.length} match(s) trouvé(s) via football-data.org`);
    } else {
      logger.info('[DataCollector] Aucun match trouvé via football-data.org – passage au fallback API-Football');
      // fallback to API-Football for historical/season out of range
      fixtures = await getFixturesToday(targetDate);
      usedApiFootball = true;
    }
  } catch (err) {
    logger.error(`[DataCollector] Erreur football-data.org : ${err.message} – passage en fallback API-Football`);
    // fallback to API-Football (could be quota issue or network)
    fixtures = await getFixturesToday(targetDate);
    usedApiFootball = true;
  }

  // --- Étape 3 : Aucun match aujourd'hui (comportement normal) ---
  if (!fixtures || fixtures.length === 0) {
    logger.info('[DataCollector] ℹ️  Aucun match prévu dans les championnats couverts — collecte terminée normalement');
    const finalQuota = await getQuotaStatus();
    return { matches: [], quota: finalQuota, source: 'api_football', noMatchDay: true };
  }

  logger.info(`[DataCollector] ✅ ${fixtures.length} match(s) trouvé(s) via API-Football`);

  // --- Étape 4 : Traitement de chaque match ---
  const savedMatches = [];

  for (const fixtureData of fixtures) {
    const fixtureId = fixtureData.fixture?.id;
    const externalId = String(fixtureId);

    if (!fixtureId) {
      logger.warn('[DataCollector] Fixture sans ID — ignorée');
      continue;
    }

    try {
      // Vérifier le cache : si données fraîches, on évite des appels API inutiles
      const cached = await getCachedMatch(externalId);
      if (cached) {
        logger.debug(`[DataCollector] Cache valide pour match ${externalId} — skip API`);
        savedMatches.push(cached);
        continue;
      }

      // Upsert des données de base du match
      const savedMatch = await upsertMatchFromApiFootball(fixtureData);
      if (!savedMatch) {
        logger.debug(`[DataCollector] Match ${externalId} non sauvegardé (ligue non couverte ?)`);
        continue;
      }

      await sleep(REQUEST_DELAY_MS);

      // Récupérer les données enrichies (stats, lineups, blessures, cotes)
      // Chaque appel vérifie le quota avant de s'exécuter
      const enrichments = {};

      try {
        const stats = await getFixtureStatistics(fixtureId);
        enrichments.raw_stats = stats || {};
        await sleep(REQUEST_DELAY_MS);
      } catch (err) {
        if (err.code === 'QUOTA_EXHAUSTED') { logger.warn('[DataCollector] Quota épuisé pendant enrichissement — arrêt'); break; }
        logger.warn(`[DataCollector] Stats non disponibles pour ${externalId}: ${err.message}`);
      }

      try {
        const lineups = await getFixtureLineups(fixtureId);
        enrichments.lineups = lineups || {};
        await sleep(REQUEST_DELAY_MS);
      } catch (err) {
        if (err.code === 'QUOTA_EXHAUSTED') { logger.warn('[DataCollector] Quota épuisé pendant enrichissement — arrêt'); break; }
        logger.warn(`[DataCollector] Lineups non disponibles pour ${externalId}: ${err.message}`);
      }

      try {
        const injuries = await getFixtureInjuries(fixtureId);
        enrichments.injuries = injuries || {};
        await sleep(REQUEST_DELAY_MS);
      } catch (err) {
        if (err.code === 'QUOTA_EXHAUSTED') { logger.warn('[DataCollector] Quota épuisé pendant enrichissement — arrêt'); break; }
        logger.warn(`[DataCollector] Blessures non disponibles pour ${externalId}: ${err.message}`);
      }

      try {
        const odds = await getFixtureOdds(fixtureId);
        enrichments.odds = odds || {};
        await sleep(REQUEST_DELAY_MS);
      } catch (err) {
        if (err.code === 'QUOTA_EXHAUSTED') { logger.warn('[DataCollector] Quota épuisé pendant enrichissement — arrêt'); break; }
        logger.warn(`[DataCollector] Cotes non disponibles pour ${externalId}: ${err.message}`);
      }

      // Sauvegarder les enrichissements si on en a
      if (Object.keys(enrichments).length > 0) {
        await updateMatchDetails(externalId, enrichments);
      }

      savedMatches.push(savedMatch);
      logger.info(`[DataCollector] ✅ Match sauvegardé : ${externalId} (${savedMatch.home_team_id} vs ${savedMatch.away_team_id})`);

    } catch (err) {
      logger.error(`[DataCollector] Erreur pour match ${externalId}: ${err.message}`);
      // Continue avec le match suivant
    }
  }

  // --- Étape 5 : Résumé ---
  const finalQuota = await getQuotaStatus();
  logger.info(`\n[DataCollector] 📋 Résumé :`);
  logger.info(`   - Matches traités : ${savedMatches.length}/${fixtures.length}`);
  logger.info(`   - Quota utilisé   : ${finalQuota.used}/${finalQuota.limit}`);
  logger.info(`   - Quota restant   : ${finalQuota.remaining} requêtes`);

  // Récupérer les matchs complets depuis la base (avec jointures)
  const matchesForEngine = await getTodayMatches(targetDate);

  return {
    matches: matchesForEngine,
    quota: finalQuota,
    source: 'api_football',
    noMatchDay: savedMatches.length === 0,
  };
}

/**
 * Collecte en mode fallback via football-data.org.
 * Appelé si API-Football est indisponible ou quota épuisé.
 */
async function collectViaFallback(date) {
  logger.info(`[DataCollector] 🔄 Mode fallback football-data.org pour le ${date}`);

  try {
    const matches = await getFixturesToday(date);

    if (matches.length === 0) {
      logger.info('[DataCollector] ℹ️  Aucun match via fallback API-Football');
      return { matches: [], quota: await getQuotaStatus(), source: 'api_football', noMatchDay: true };
    }

    const saved = [];
    for (const match of matches) {
      try {
        const savedMatch = await upsertMatchFromFallback(match);
        if (savedMatch) saved.push(savedMatch);
      } catch (err) {
        logger.error(`[DataCollector] Erreur fallback pour ${match.external_id}: ${err.message}`);
      }
    }

    logger.info(`[DataCollector] Fallback : ${saved.length} match(s) sauvegardé(s)`);
    const matchesForEngine = await getTodayMatches(date);

    return {
      matches: matchesForEngine,
      quota: await getQuotaStatus(),
      source: 'api_football',
      noMatchDay: saved.length === 0,
    };
  } catch (err) {
    logger.error(`[DataCollector] Erreur fatale fallback: ${err.message}`);
    return { matches: [], quota: await getQuotaStatus(), source: 'none', error: err.message };
  }
}

module.exports = { collectDailyData };
