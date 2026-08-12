// src/collectors/footballDataClient.js
// Client minimal pour football-data.org (v4)
// Retourne les matchs du jour au même format que apiFootballClient

const axios = require('axios');
const logger = require('../utils/logger');
require('dotenv').config();

const API_KEY = process.env.FOOTBALL_DATA_ORG_KEY;
const BASE_URL = 'https://api.football-data.org/v4';

/**
 * Récupère les matchs d'une date donnée.
 * @param {string} targetDate - format YYYY-MM-DD
 * @returns {Promise<Array>} tableau de matchs au format attendu par le moteur
 */
async function getMatches(targetDate) {
  if (!API_KEY) {
    logger.error('[footballDataClient] FOOTBALL_DATA_API_KEY manquante dans .env');
    return [];
  }
  const url = `${BASE_URL}/matches?dateFrom=${targetDate}&dateTo=${targetDate}`;
  try {
    const response = await axios.get(url, {
      headers: { 'X-Auth-Token': API_KEY }
    });
    const remaining = response.headers['x-ratelimit-remaining'];
    logger.info(`[footballDataClient] Quota restant : ${remaining}`);
    // Normaliser le format (on ne garde que les champs nécessaires)
    const fixtures = response.data.matches.map(m => ({
      fixture: {
        id: m.id,
        date: m.utcDate,
        status: { short: m.status },
        venue: { name: m.venue }
      },
      league: {
        id: m.competition.id,
        name: m.competition.name,
        country: m.competition.area.name,
        season: m.season?.year || new Date().getFullYear()
      },
      teams: {
        home: { id: m.homeTeam.id, name: m.homeTeam.name, logo: m.homeTeam.crest },
        away: { id: m.awayTeam.id, name: m.awayTeam.name, logo: m.awayTeam.crest }
      },
      goals: { home: m.score.fullTime.homeTeam, away: m.score.fullTime.awayTeam },
      odds: [] // football-data.org ne fournit pas d'odds, on laissera vide (fallback utilisera API-Football)
    }));
    return fixtures;
  } catch (err) {
    logger.error(`[footballDataClient] Erreur lors de la récupération des matchs : ${err.message}`);
    return [];
  }
}

module.exports = { getMatches };
