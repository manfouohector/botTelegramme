/**
 * src/collectors/footballDataClient.js
 * Client HTTP pour football-data.org (source de secours / fallback)
 * Utilisé UNIQUEMENT si API-Football est indisponible ou quota dépassé.
 * Plan gratuit : 10 req/minute, ligues européennes majeures uniquement.
 */

const axios = require('axios');
const logger = require('../utils/logger');

const BASE_URL = 'https://api.football-data.org/v4';
const API_KEY = process.env.FOOTBALL_DATA_ORG_KEY;

// Correspondance entre les IDs API-Football et les codes football-data.org
// Seulement les ligues disponibles sur les deux sources
const LEAGUE_MAP = {
  61:  'FL1',  // Ligue 1
  39:  'PL',   // Premier League
  140: 'PD',   // La Liga
  135: 'SA',   // Serie A
  78:  'BL1',  // Bundesliga
  2:   'CL',   // Champions League
};

/**
 * Effectue un appel GET à football-data.org.
 * @param {string} endpoint
 * @param {Object} params
 */
async function fdGet(endpoint, params = {}) {
  try {
    const response = await axios.get(`${BASE_URL}${endpoint}`, {
      params,
      headers: {
        'X-Auth-Token': API_KEY,
        'Accept': 'application/json',
      },
      timeout: 10000,
    });
    return response.data;
  } catch (err) {
    if (err.response) {
      logger.error(`[FD.org] HTTP ${err.response.status} sur ${endpoint}: ${err.response.statusText}`);
      if (err.response.status === 429) {
        logger.warn('[FD.org] Rate limit atteint (10 req/min)');
      }
    } else {
      logger.error(`[FD.org] Erreur réseau: ${err.message}`);
    }
    throw err;
  }
}

/**
 * Convertit un match football-data.org au format normalisé commun.
 * Facilite la déduplication avec les données API-Football.
 */
function normalizeMatch(fdMatch, leagueExternalId) {
  return {
    external_id: `fd_${fdMatch.id}`,   // Préfixe pour éviter collision avec API-Football IDs
    source: 'football_data',
    league_external_id: leagueExternalId,
    match_date: fdMatch.utcDate,
    status: mapStatus(fdMatch.status),
    home_team: {
      external_id: `fd_team_${fdMatch.homeTeam.id}`,
      name: fdMatch.homeTeam.name,
      short_name: fdMatch.homeTeam.shortName,
    },
    away_team: {
      external_id: `fd_team_${fdMatch.awayTeam.id}`,
      name: fdMatch.awayTeam.name,
      short_name: fdMatch.awayTeam.shortName,
    },
    home_score: fdMatch.score?.fullTime?.home ?? null,
    away_score: fdMatch.score?.fullTime?.away ?? null,
    raw_stats: {},    // football-data.org ne fournit pas de stats détaillées (plan gratuit)
    lineups: {},      // Non disponible sur plan gratuit
    injuries: {},     // Non disponible
    odds: {},         // Non disponible
    referee: fdMatch.referees?.[0]?.name || null,
    venue: null,      // Non disponible sur plan gratuit
  };
}

function mapStatus(fdStatus) {
  const statusMap = {
    'SCHEDULED': 'scheduled',
    'TIMED': 'scheduled',
    'IN_PLAY': 'live',
    'PAUSED': 'live',
    'FINISHED': 'finished',
    'CANCELLED': 'cancelled',
    'POSTPONED': 'postponed',
    'SUSPENDED': 'cancelled',
  };
  return statusMap[fdStatus] || 'scheduled';
}

/**
 * Récupère les matchs du jour pour les ligues disponibles sur football-data.org.
 * Utilisé en fallback quand API-Football est indisponible.
 * @param {string} date - Format YYYY-MM-DD
 * @param {number[]} leagueExternalIds - IDs API-Football pour lesquels on veut le fallback
 * @returns {Promise<Array>} Matchs normalisés
 */
async function getMatchesFallback(date = null, leagueExternalIds = null) {
  const targetDate = date || new Date().toISOString().slice(0, 10);
  const leaguesToFetch = leagueExternalIds || Object.keys(LEAGUE_MAP).map(Number);
  const allMatches = [];

  logger.info(`[FD.org] 🔄 Fallback activé — récupération des matchs pour le ${targetDate}`);

  for (const leagueId of leaguesToFetch) {
    const fdCode = LEAGUE_MAP[leagueId];
    if (!fdCode) {
      logger.debug(`[FD.org] Pas de mapping pour la ligue ${leagueId} — ignorée`);
      continue;
    }

    try {
      const data = await fdGet(`/competitions/${fdCode}/matches`, {
        dateFrom: targetDate,
        dateTo: targetDate,
      });

      if (data.matches && data.matches.length > 0) {
        const normalized = data.matches.map(m => normalizeMatch(m, leagueId));
        allMatches.push(...normalized);
        logger.info(`[FD.org] ${fdCode} : ${normalized.length} match(s) trouvé(s)`);
      } else {
        logger.debug(`[FD.org] ${fdCode} : aucun match ce jour`);
      }

      // Respecter la limite de 10 req/min du plan gratuit
      await new Promise(resolve => setTimeout(resolve, 6500));

    } catch (err) {
      logger.error(`[FD.org] Erreur sur ${fdCode}: ${err.message}`);
      // Continue avec les autres ligues
    }
  }

  logger.info(`[FD.org] Total matchs récupérés en fallback : ${allMatches.length}`);
  return allMatches;
}

module.exports = { getMatchesFallback, normalizeMatch, LEAGUE_MAP };
