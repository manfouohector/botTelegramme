/**
 * src/collectors/apiFootballClient.js
 * Client HTTP pour l'API-Football (RapidAPI)
 * Gère automatiquement le quota via quotaTracker
 */

const axios = require('axios');
const { canMakeRequests, incrementUsed } = require('./quotaTracker');
const logger = require('../utils/logger');

const BASE_URL = 'https://v3.football.api-sports.io';
const API_KEY = process.env.API_FOOTBALL_KEY;

// IDs API-Football des championnats couverts en V1
const COVERED_LEAGUES = {
  61:  'Ligue 1',
  39:  'Premier League',
  140: 'La Liga',
  135: 'Serie A',
  78:  'Bundesliga',
  2:   'UEFA Champions League',
  531: 'UEFA Super Cup',
};

/**
 * Effectue un appel GET à l'API-Football avec gestion du quota.
 * Lance une erreur QuotaExhaustedError si le quota est atteint.
 * @param {string} endpoint - ex: '/fixtures'
 * @param {Object} params - paramètres de requête
 */
async function apiGet(endpoint, params = {}) {
  if (!await canMakeRequests(1)) {
    const err = new Error('Quota API-Football épuisé pour aujourd\'hui');
    err.code = 'QUOTA_EXHAUSTED';
    throw err;
  }

  try {
    const response = await axios.get(`${BASE_URL}${endpoint}`, {
      params,
      headers: {
        'x-apisports-key': API_KEY,
        'Accept': 'application/json',
      },
      timeout: 10000,
    });

    await incrementUsed(1);

    // L'API-Football retourne les erreurs dans response.data.errors
    if (response.data.errors && Object.keys(response.data.errors).length > 0) {
      const errMsg = JSON.stringify(response.data.errors);
      logger.error(`[API-Football] Erreur API: ${errMsg}`);

      // Détecter l'erreur de restriction de plan (date hors fenêtre gratuite)
      if (errMsg.includes('plan') || errMsg.includes('date')) {
        const planErr = new Error(`API-Football restriction plan: ${errMsg}`);
        planErr.code = 'PLAN_RESTRICTION';
        throw planErr;
      }

      throw new Error(`API-Football erreur: ${errMsg}`);
    }

    return response.data.response;

  } catch (err) {
    if (err.code === 'QUOTA_EXHAUSTED' || err.code === 'PLAN_RESTRICTION') throw err;
    if (err.response) {
      logger.error(`[API-Football] HTTP ${err.response.status} sur ${endpoint}: ${err.response.statusText}`);
    } else {
      logger.error(`[API-Football] Erreur réseau sur ${endpoint}: ${err.message}`);
    }
    throw err;
  }
}

/**
 * Récupère les matchs du jour pour tous les championnats couverts.
 * @param {string} date - Format YYYY-MM-DD (défaut: aujourd'hui)
 * @returns {Promise<Array>} Liste des fixtures API-Football
 */
async function getFixturesToday(date = null) {
  const targetDate = date || new Date().toISOString().slice(0, 10);
  const leagueIds = Object.keys(COVERED_LEAGUES);
  const allFixtures = [];

  // ⚠️ Plan gratuit API-Football : accès limité aux saisons 2022-2024
  // À mettre à jour vers new Date().getFullYear() après upgrade du plan
  const season = parseInt(process.env.API_FOOTBALL_SEASON || '2024', 10);

  logger.info(`[API-Football] Récupération des matchs pour le ${targetDate} — saison ${season} (${leagueIds.length} ligues)`);

  for (const leagueId of leagueIds) {
    try {
      logger.debug(`[API-Football] Ligues : ${COVERED_LEAGUES[leagueId]} (ID: ${leagueId})`);
      const fixtures = await apiGet('/fixtures', {
        league: leagueId,
        season,          // ← Paramètre obligatoire pour le plan gratuit
        date: targetDate,
        timezone: 'UTC',
      });

      if (fixtures && fixtures.length > 0) {
        allFixtures.push(...fixtures);
        logger.info(`[API-Football] ${COVERED_LEAGUES[leagueId]} : ${fixtures.length} match(s) trouvé(s)`);
      } else {
        logger.debug(`[API-Football] ${COVERED_LEAGUES[leagueId]} : aucun match ce jour`);
      }
    } catch (err) {
      if (err.code === 'QUOTA_EXHAUSTED') {
        logger.warn(`[API-Football] Quota épuisé — arrêt de la collecte pour le reste des ligues`);
        break;
      }
      if (err.code === 'PLAN_RESTRICTION') {
        logger.warn(`[API-Football] ⚠️  Restriction de plan détectée (date hors fenêtre gratuite) — arrêt immédiat sans tester les autres ligues`);
        break; // Inutile d'essayer les autres ligues, c'est une restriction globale
      }
      logger.error(`[API-Football] Erreur sur ligue ${leagueId}: ${err.message}`);
      // Continue sur les autres ligues si c'est une erreur individuelle
    }
  }

  return allFixtures;
}

/**
 * Récupère les statistiques d'équipe pour un match donné.
 * @param {number} fixtureId - ID du match API-Football
 */
async function getFixtureStatistics(fixtureId) {
  logger.debug(`[API-Football] Stats pour fixture ${fixtureId}`);
  return apiGet('/fixtures/statistics', { fixture: fixtureId });
}

/**
 * Récupère les compositions (lineups) pour un match.
 * @param {number} fixtureId
 */
async function getFixtureLineups(fixtureId) {
  logger.debug(`[API-Football] Lineups pour fixture ${fixtureId}`);
  return apiGet('/fixtures/lineups', { fixture: fixtureId });
}

/**
 * Récupère les blessures/suspensions pour un match.
 * @param {number} fixtureId
 */
async function getFixtureInjuries(fixtureId) {
  logger.debug(`[API-Football] Blessures pour fixture ${fixtureId}`);
  return apiGet('/injuries', { fixture: fixtureId });
}

/**
 * Récupère les cotes bookmakers pour un match.
 * @param {number} fixtureId
 */
async function getFixtureOdds(fixtureId) {
  logger.debug(`[API-Football] Cotes pour fixture ${fixtureId}`);
  return apiGet('/odds', { fixture: fixtureId });
}

/**
 * Récupère les statistiques de forme d'une équipe (derniers matchs).
 * @param {number} teamId - ID de l'équipe
 * @param {number} leagueId - ID de la ligue
 * @param {number} season - Saison (ex: 2024)
 * @param {number} last - Nombre de derniers matchs (défaut: 5)
 */
async function getTeamForm(teamId, leagueId, season = 2024, last = 5) {
  logger.debug(`[API-Football] Forme équipe ${teamId} (${last} derniers matchs)`);
  return apiGet('/fixtures', {
    team: teamId,
    league: leagueId,
    season,
    last,
  });
}

/**
 * Récupère les confrontations directes entre deux équipes.
 * @param {number} h2hStr - Format "teamId1-teamId2"
 * @param {number} last - Nombre de matchs (défaut: 10)
 */
async function getH2H(h2hStr, last = 10) {
  logger.debug(`[API-Football] H2H: ${h2hStr}`);
  return apiGet('/fixtures/headtohead', { h2h: h2hStr, last });
}

module.exports = {
  apiGet,
  getFixturesToday,
  getFixtureStatistics,
  getFixtureLineups,
  getFixtureInjuries,
  getFixtureOdds,
  getTeamForm,
  getH2H,
  COVERED_LEAGUES,
};
