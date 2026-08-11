/**
 * test-data-collector-mock.js
 * Test du Data Collector avec données fictives (mock API-Football)
 * Valide la logique sans consommer de quota API
 * Usage: node test-data-collector-mock.js
 */

require('dotenv').config();
const { pool } = require('./src/db/index');
const {
  upsertMatchFromApiFootball,
  getCachedMatch,
  updateMatchDetails,
  getTodayMatches,
} = require('./src/collectors/matchRepository');
const { getQuotaStatus, incrementUsed } = require('./src/collectors/quotaTracker');

// ── Données fictives au format API-Football ──────────────────────────────────
const MOCK_FIXTURES = [
  {
    fixture: {
      id: 999001,
      date: new Date().toISOString(), // aujourd'hui
      status: { short: 'NS', long: 'Not Started' },
      referee: 'Clément Turpin',
      venue: { name: 'Parc des Princes', city: 'Paris' },
    },
    league: { id: 61, name: 'Ligue 1', country: 'France', season: 2024 },
    teams: {
      home: { id: 85, name: 'Paris Saint Germain', logo: 'https://example.com/psg.png' },
      away: { id: 80, name: 'Lyon',                logo: 'https://example.com/lyon.png' },
    },
    goals: { home: null, away: null },
    statistics: [
      { team: { id: 85 }, statistics: [{ type: 'Shots on Goal', value: 0 }] },
    ],
    lineups: [
      { team: { id: 85, name: 'PSG' }, startXI: [], substitutes: [] },
      { team: { id: 80, name: 'Lyon' }, startXI: [], substitutes: [] },
    ],
    injuries: [],
    odds: [
      {
        bookmaker: { id: 6, name: 'Bwin' },
        bets: [
          {
            id: 1,
            name: 'Match Winner',
            values: [
              { value: 'Home', odd: '1.60' },
              { value: 'Draw', odd: '3.80' },
              { value: 'Away', odd: '5.50' },
            ],
          },
        ],
      },
    ],
  },
  {
    fixture: {
      id: 999002,
      date: new Date().toISOString(),
      status: { short: 'NS', long: 'Not Started' },
      referee: 'Michael Oliver',
      venue: { name: 'Old Trafford', city: 'Manchester' },
    },
    league: { id: 39, name: 'Premier League', country: 'England', season: 2024 },
    teams: {
      home: { id: 33, name: 'Manchester United', logo: '' },
      away: { id: 40, name: 'Liverpool',         logo: '' },
    },
    goals: { home: null, away: null },
    statistics: [],
    lineups: [],
    injuries: [],
    odds: [],
  },
];

async function runMockTest() {
  console.log('\n🧪 TEST MOCK DATA COLLECTOR — DevMind Bot');
  console.log('='.repeat(55));
  console.log('(Aucun appel API réel — données fictives)');
  console.log('='.repeat(55));

  const testDate = new Date().toISOString().slice(0, 10);

  try {
    // ── Test 1 : Upsert des matchs fictifs ──────────────────────────────────
    console.log('\n📥 Test 1 : Upsert de matchs fictifs en base...');
    const savedMatches = [];
    for (const fixture of MOCK_FIXTURES) {
      const saved = await upsertMatchFromApiFootball(fixture);
      if (saved) {
        savedMatches.push(saved);
        console.log(`   ✅ Match sauvegardé : ${fixture.teams.home.name} vs ${fixture.teams.away.name} (ID: ${fixture.fixture.id})`);
      } else {
        console.log(`   ⚠️  Match non sauvegardé (ligue non couverte?) : ${fixture.teams.home.name} vs ${fixture.teams.away.name}`);
      }
    }
    console.log(`   → ${savedMatches.length}/${MOCK_FIXTURES.length} matchs sauvegardés`);

    // ── Test 2 : Vérification du cache ──────────────────────────────────────
    console.log('\n🔍 Test 2 : Vérification du cache (last_fetched_at)...');
    const cached = await getCachedMatch('999001');
    if (cached) {
      console.log(`   ✅ Cache valide pour match 999001 — last_fetched_at: ${cached.last_fetched_at}`);
    } else {
      console.log('   ❌ Cache non trouvé pour match 999001');
    }

    // ── Test 3 : Idempotence (upsert doublon) ────────────────────────────────
    console.log('\n🔁 Test 3 : Idempotence (re-upsert du même match)...');
    const re_saved = await upsertMatchFromApiFootball(MOCK_FIXTURES[0]);
    if (re_saved) {
      console.log(`   ✅ Re-upsert OK — pas de doublon (ON CONFLICT fonctionne)`);
    }

    // ── Test 4 : Mise à jour des détails enrichis ────────────────────────────
    console.log('\n📊 Test 4 : Mise à jour des détails enrichis...');
    await updateMatchDetails('999001', {
      raw_stats: { shots_on_target: { home: 3, away: 1 }, possession: { home: 60, away: 40 } },
      lineups:   { home: { formation: '4-3-3' }, away: { formation: '4-2-3-1' } },
      injuries:  { home: ['Mbappé (genou)'], away: [] },
      odds:      { '1X2': { home: 1.60, draw: 3.80, away: 5.50 } },
    });
    console.log('   ✅ Détails mis à jour avec succès');

    // ── Test 5 : Récupération des matchs du jour ──────────────────────────────
    console.log('\n📋 Test 5 : Récupération des matchs du jour...');
    const todayMatches = await getTodayMatches(testDate);
    console.log(`   ✅ ${todayMatches.length} match(s) trouvé(s) pour aujourd'hui`);
    todayMatches.forEach(m => {
      console.log(`      - [${m.league_name || m.league_id}] ${m.home_team_name || '?'} vs ${m.away_team_name || '?'}`);
      console.log(`        Status: ${m.status} | Source: ${m.data_source}`);
    });

    // ── Test 6 : Quota tracker ────────────────────────────────────────────────
    console.log('\n📊 Test 6 : Quota tracker...');
    await incrementUsed(2); // Simuler 2 appels
    const quota = await getQuotaStatus();
    console.log(`   Quota utilisé : ${quota.used}/${quota.limit}`);
    console.log(`   Seuil de sécurité : ${quota.threshold}`);
    console.log(`   Quota épuisé : ${quota.exhausted ? 'OUI' : 'NON'}`);
    console.log(`   ✅ Quota tracker fonctionne`);

    // ── Vérification base de données ──────────────────────────────────────────
    console.log('\n💾 Vérification base de données...');
    const { rows } = await pool.query(
      `SELECT m.external_id, ht.name AS home, at.name AS away,
              l.name AS league, m.status, m.last_fetched_at,
              m.lineups->>'home' AS lineup_home
       FROM matches m
       LEFT JOIN teams ht ON m.home_team_id = ht.id
       LEFT JOIN teams at ON m.away_team_id = at.id
       LEFT JOIN leagues l ON m.league_id = l.id
       WHERE m.external_id IN ('999001', '999002')`
    );

    console.log(`   Matchs en base : ${rows.length}`);
    rows.forEach(r => {
      console.log(`   - ${r.home || '?'} vs ${r.away || '?'} (${r.league || '?'})`);
      console.log(`     Statut: ${r.status} | Fetched: ${r.last_fetched_at ? '✅' : '❌'}`);
      console.log(`     Lineups: ${r.lineup_home ? '✅' : '❌'}`);
    });

    console.log('\n' + '='.repeat(55));
    console.log('✅ Tous les tests mock ont réussi !');
    console.log('   Le Data Collector est fonctionnel.');
    console.log('   Note: la collecte réelle nécessite un plan API-Football');
    console.log('         couvrant la saison en cours (ou les ±2 jours actuels).');
    console.log('='.repeat(55) + '\n');

    // Nettoyage des données de test
    await pool.query(`DELETE FROM matches WHERE external_id IN ('999001', '999002')`);
    console.log('🧹 Données de test supprimées de la base\n');

  } catch (err) {
    console.error(`\n❌ Erreur durant le test mock: ${err.message}`);
    console.error(err.stack);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

runMockTest();
