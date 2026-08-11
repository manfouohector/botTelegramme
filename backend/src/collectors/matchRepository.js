/**
 * src/collectors/matchRepository.js
 * Couche d'accès aux données pour les matchs, équipes et ligues.
 * Gère le cache (last_fetched_at), la déduplication par external_id,
 * et la synchronisation des équipes/ligues.
 */

const { query, withTransaction } = require('../db/index');
const logger = require('../utils/logger');

// Durée de fraîcheur du cache en minutes (on ne re-fetch pas si les données ont < N minutes)
const CACHE_TTL_MINUTES = parseInt(process.env.CACHE_TTL_MINUTES || '120', 10);

/**
 * Vérifie si les données d'un match sont encore fraîches dans le cache.
 * @param {string} externalId - ID externe du match
 * @returns {Promise<Object|null>} Le match si en cache, null sinon
 */
async function getCachedMatch(externalId) {
  const { rows } = await query(
    `SELECT * FROM matches
     WHERE external_id = $1
       AND last_fetched_at > NOW() - INTERVAL '${CACHE_TTL_MINUTES} minutes'`,
    [externalId]
  );
  return rows[0] || null;
}

/**
 * Upsert (insert ou update) d'un match normalisé API-Football en base.
 * @param {Object} fixtureData - Données brutes API-Football
 * @returns {Promise<Object>} Le match enregistré
 */
async function upsertMatchFromApiFootball(fixtureData) {
  const fixture = fixtureData.fixture;
  const league = fixtureData.league;
  const teams = fixtureData.teams;
  const goals = fixtureData.goals;

  // S'assurer que la ligue est connue en base
  const leagueRow = await ensureLeague(league);
  if (!leagueRow) return null;

  // S'assurer que les équipes sont connues en base
  const homeTeamRow = await ensureTeam(teams.home, leagueRow.id);
  const awayTeamRow = await ensureTeam(teams.away, leagueRow.id);

  const externalId = String(fixture.id);
  const matchDate = new Date(fixture.date).toISOString();
  const status = mapApiFootballStatus(fixture.status?.short);

  const { rows } = await query(
    `INSERT INTO matches (
        external_id, league_id, home_team_id, away_team_id,
        match_date, status, home_score, away_score,
        referee, venue, data_source, last_fetched_at,
        raw_stats, lineups, injuries, odds
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW(), $12, $13, $14, $15)
      ON CONFLICT (external_id) DO UPDATE SET
        status          = EXCLUDED.status,
        home_score      = EXCLUDED.home_score,
        away_score      = EXCLUDED.away_score,
        referee         = EXCLUDED.referee,
        venue           = EXCLUDED.venue,
        data_source     = EXCLUDED.data_source,
        last_fetched_at = NOW(),
        updated_at      = NOW()
      RETURNING *`,
    [
      externalId,
      leagueRow.id,
      homeTeamRow?.id || null,
      awayTeamRow?.id || null,
      matchDate,
      status,
      goals?.home ?? null,
      goals?.away ?? null,
      fixture.referee || null,
      fixture.venue?.name || null,
      'api_football',
      JSON.stringify(fixtureData.statistics || {}),
      JSON.stringify(fixtureData.lineups || {}),
      JSON.stringify(fixtureData.injuries || {}),
      JSON.stringify(fixtureData.odds || {}),
    ]
  );

  return rows[0];
}

/**
 * Upsert d'un match normalisé depuis football-data.org (fallback).
 * @param {Object} normalizedMatch - Résultat de footballDataClient.normalizeMatch()
 */
async function upsertMatchFromFallback(normalizedMatch) {
  const leagueRow = await query(
    'SELECT id FROM leagues WHERE external_id = $1',
    [normalizedMatch.league_external_id]
  );
  if (!leagueRow.rows[0]) return null;

  const { rows } = await query(
    `INSERT INTO matches (
        external_id, league_id, home_team_id, away_team_id,
        match_date, status, home_score, away_score,
        referee, venue, data_source, last_fetched_at,
        raw_stats, lineups, injuries, odds
      ) VALUES ($1, $2, NULL, NULL, $3, $4, $5, $6, $7, $8, 'football_data', NOW(),
                '{}', '{}', '{}', '{}')
      ON CONFLICT (external_id) DO UPDATE SET
        status          = EXCLUDED.status,
        home_score      = EXCLUDED.home_score,
        away_score      = EXCLUDED.away_score,
        referee         = EXCLUDED.referee,
        data_source     = 'football_data',
        last_fetched_at = NOW(),
        updated_at      = NOW()
      RETURNING *`,
    [
      normalizedMatch.external_id,
      leagueRow.rows[0].id,
      normalizedMatch.match_date,
      normalizedMatch.status,
      normalizedMatch.home_score,
      normalizedMatch.away_score,
      normalizedMatch.referee,
      normalizedMatch.venue,
    ]
  );

  return rows[0];
}

/**
 * Met à jour les stats détaillées d'un match existant (stats, lineups, blessures, cotes).
 * @param {string} externalId
 * @param {Object} updates - { raw_stats, lineups, injuries, odds }
 */
async function updateMatchDetails(externalId, { raw_stats, lineups, injuries, odds }) {
  await query(
    `UPDATE matches SET
       raw_stats       = COALESCE($2, raw_stats),
       lineups         = COALESCE($3, lineups),
       injuries        = COALESCE($4, injuries),
       odds            = COALESCE($5, odds),
       last_fetched_at = NOW(),
       updated_at      = NOW()
     WHERE external_id = $1`,
    [
      externalId,
      raw_stats ? JSON.stringify(raw_stats) : null,
      lineups ? JSON.stringify(lineups) : null,
      injuries ? JSON.stringify(injuries) : null,
      odds ? JSON.stringify(odds) : null,
    ]
  );
}

/**
 * Retourne tous les matchs du jour qui sont scheduled ou live.
 * @param {string} date - YYYY-MM-DD (défaut: aujourd'hui)
 */
async function getTodayMatches(date = null) {
  const targetDate = date || new Date().toISOString().slice(0, 10);

  const { rows } = await query(
    `SELECT m.*, 
            l.name AS league_name, l.external_id AS league_external_id,
            ht.name AS home_team_name, ht.external_id AS home_team_external_id,
            at.name AS away_team_name, at.external_id AS away_team_external_id
     FROM matches m
     LEFT JOIN leagues l ON m.league_id = l.id
     LEFT JOIN teams ht ON m.home_team_id = ht.id
     LEFT JOIN teams at ON m.away_team_id = at.id
     WHERE DATE(m.match_date AT TIME ZONE 'UTC') = $1
       AND m.status IN ('scheduled', 'live')
     ORDER BY m.match_date ASC`,
    [targetDate]
  );

  return rows;
}

/**
 * Retourne les matchs terminés sans résultats vérifiés (pour le cron post-matchs).
 */
async function getFinishedUnverifiedMatches() {
  const { rows } = await query(
    `SELECT m.*, l.external_id AS league_external_id
     FROM matches m
     LEFT JOIN leagues l ON m.league_id = l.id
     WHERE m.status = 'finished'
       AND m.id IN (
         SELECT DISTINCT p.match_id FROM predictions p
         WHERE p.match_id NOT IN (
           SELECT pr.prediction_id FROM prediction_results pr
           INNER JOIN predictions p2 ON pr.prediction_id = p2.id
           WHERE p2.match_id = p.match_id
         )
       )
     ORDER BY m.match_date DESC
     LIMIT 50`
  );
  return rows;
}

// ============================================================================
// Helpers privés
// ============================================================================

async function ensureLeague(leagueData) {
  const { rows } = await query(
    `SELECT id FROM leagues WHERE external_id = $1`,
    [leagueData.id]
  );
  if (rows[0]) return rows[0];

  // Si la ligue n'est pas dans nos couverts, on l'ignore
  logger.debug(`[MatchRepo] Ligue ${leagueData.id} (${leagueData.name}) non couverte — ignorée`);
  return null;
}

async function ensureTeam(teamData, leagueId) {
  if (!teamData?.id) return null;

  const { rows } = await query(
    `INSERT INTO teams (external_id, name, short_name, league_id, logo_url)
     VALUES ($1, $2, $3, $4, $5)
     ON CONFLICT (external_id) DO UPDATE SET
       name      = EXCLUDED.name,
       logo_url  = EXCLUDED.logo_url,
       updated_at = NOW()
     RETURNING id`,
    [
      teamData.id,
      teamData.name,
      teamData.name?.substring(0, 50) || null,
      leagueId,
      teamData.logo || null,
    ]
  );
  return rows[0];
}

function mapApiFootballStatus(shortStatus) {
  const map = {
    'TBD': 'scheduled', 'NS': 'scheduled',
    '1H': 'live', 'HT': 'live', '2H': 'live', 'ET': 'live', 'P': 'live', 'BT': 'live',
    'FT': 'finished', 'AET': 'finished', 'PEN': 'finished',
    'SUSP': 'cancelled', 'INT': 'live', 'PST': 'postponed',
    'CANC': 'cancelled', 'ABD': 'cancelled', 'AWD': 'finished', 'WO': 'finished',
  };
  return map[shortStatus] || 'scheduled';
}

module.exports = {
  getCachedMatch,
  upsertMatchFromApiFootball,
  upsertMatchFromFallback,
  updateMatchDetails,
  getTodayMatches,
  getFinishedUnverifiedMatches,
};
