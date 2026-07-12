const axios = require('axios');

// Default competitions covered by the free tier
const FREE_COMPETITIONS = 'PL,ELC,CL,BL1,DED,PD,FL1,SA,PPL,CLI';

class FootballService {
  constructor() {
    this.apiKey = process.env.FOOTBALL_DATA_API_KEY;
    this.client = axios.create({
      baseURL: 'https://api.football-data.org/v4',
      headers: {
        'X-Auth-Token': this.apiKey || ''
      },
      timeout: 10000
    });
    // Standing cache during a single run to avoid rate limits
    this.standingsCache = {};
  }

  // Delay helper to prevent hitting the 10 req/min limit
  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Fetches matches for a specific date range (or today)
   * @param {string} dateStr Format YYYY-MM-DD
   */
  async fetchMatchesOfTheDay(dateStr) {
    if (!this.apiKey) {
      console.warn("Warning: FOOTBALL_DATA_API_KEY n'est pas configuré.");
      return [];
    }

    try {
      console.log(`Récupération des matchs pour la date: ${dateStr}...`);
      const response = await this.client.get('/matches', {
        params: {
          competitions: FREE_COMPETITIONS,
          dateFrom: dateStr,
          dateTo: dateStr
        }
      });

      return response.data.matches || [];
    } catch (error) {
      console.error('Erreur lors de la récupération des matchs:', error.message);
      if (error.response) {
        console.error('API Response status:', error.response.status);
      }
      throw error;
    }
  }

  /**
   * Fetches standings for a competition and caches it
   * @param {string} competitionCode e.g. 'PL'
   */
  async fetchStandings(competitionCode) {
    if (this.standingsCache[competitionCode]) {
      return this.standingsCache[competitionCode];
    }

    if (!this.apiKey) {
      return null;
    }

    try {
      console.log(`Récupération du classement pour la compétition: ${competitionCode}...`);
      const response = await this.client.get(`/competitions/${competitionCode}/standings`);
      this.standingsCache[competitionCode] = response.data.standings || [];
      return this.standingsCache[competitionCode];
    } catch (error) {
      console.error(`Erreur récupération classement pour ${competitionCode}:`, error.message);
      // Don't fail the pipeline completely if one standings request fails, return null
      return null;
    }
  }

  /**
   * Helper to look up team's position and form from standings
   */
  findTeamInStandings(standings, teamId) {
    if (!standings || !Array.isArray(standings)) {
      return { position: 'N/A', form: 'N/A' };
    }

    for (const standing of standings) {
      // Standings can be type 'TOTAL', 'HOME', 'AWAY'
      if (standing.type !== 'TOTAL') continue;
      
      const table = standing.table;
      if (!table || !Array.isArray(table)) continue;

      const teamRow = table.find(row => row.team && row.team.id === teamId);
      if (teamRow) {
        return {
          position: teamRow.position || 'N/A',
          form: teamRow.form || 'N/A'
        };
      }
    }

    return { position: 'N/A', form: 'N/A' };
  }

  /**
   * Fetches and compiles all matches enriched with standings and team forms
   * @param {string} dateStr Format YYYY-MM-DD
   */
  async getEnrichedMatches(dateStr) {
    // Clear standings cache at start of run
    this.standingsCache = {};

    const matches = await this.fetchMatchesOfTheDay(dateStr);
    if (!matches || matches.length === 0) {
      console.log(`Aucun match trouvé pour la date ${dateStr}.`);
      return [];
    }

    console.log(`${matches.length} matchs trouvés. Enrichessement avec classement et forme...`);
    
    // Identify unique competitions code in today's matches
    const competitionCodes = [...new Set(matches.map(m => m.competition.code))];

    // Fetch standings for each unique competition with rate-limit spacing
    for (const code of competitionCodes) {
      await this.fetchStandings(code);
      // Wait 1.5 seconds between standings requests to avoid rate limit (10 requests per minute)
      await this.delay(1500);
    }

    const enrichedMatches = [];

    for (const match of matches) {
      const compCode = match.competition.code;
      const standings = this.standingsCache[compCode];

      const homeDetails = this.findTeamInStandings(standings, match.homeTeam.id);
      const awayDetails = this.findTeamInStandings(standings, match.awayTeam.id);

      enrichedMatches.push({
        id: match.id,
        competition: {
          id: match.competition.id,
          name: match.competition.name,
          code: compCode
        },
        utcDate: match.utcDate,
        status: match.status,
        homeTeam: {
          id: match.homeTeam.id,
          name: match.homeTeam.name,
          shortName: match.homeTeam.shortName,
          tla: match.homeTeam.tla,
          position: homeDetails.position,
          form: homeDetails.form
        },
        awayTeam: {
          id: match.awayTeam.id,
          name: match.awayTeam.name,
          shortName: match.awayTeam.shortName,
          tla: match.awayTeam.tla,
          position: awayDetails.position,
          form: awayDetails.form
        }
      });
    }

    return enrichedMatches;
  }
}

module.exports = new FootballService();
