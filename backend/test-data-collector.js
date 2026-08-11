/**
 * test-data-collector.js
 * Test du Data Collector avec une date récente (matchs déjà joués = résultats connus)
 * Usage: node test-data-collector.js [YYYY-MM-DD]
 */

require('dotenv').config();
const { collectDailyData } = require('./src/collectors/dataCollector');
const { getQuotaStatus } = require('./src/collectors/quotaTracker');
const { pool } = require('./src/db/index');

async function runTest() {
  // Date de test : hier (matchs déjà joués) ou date passée fournie en argument
  const testDate = process.argv[2] || (() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().slice(0, 10);
  })();

  console.log('\n🧪 TEST DATA COLLECTOR — DevMind Bot');
  console.log('='.repeat(50));
  console.log(`📅 Date de test : ${testDate}`);
  console.log('='.repeat(50));

  // Quota avant collecte
  const quotaBefore = await getQuotaStatus();
  console.log(`\n📊 Quota avant collecte : ${quotaBefore.used}/${quotaBefore.limit} (seuil: ${quotaBefore.threshold})`);

  if (quotaBefore.exhausted) {
    console.log('\n⛔ Quota épuisé — le test utilisera le fallback football-data.org');
  }

  console.log('\n🚀 Démarrage de la collecte...\n');

  try {
    const result = await collectDailyData(testDate);

    console.log('\n' + '='.repeat(50));
    console.log('📋 RÉSULTAT DE LA COLLECTE');
    console.log('='.repeat(50));
    console.log(`Source utilisée : ${result.source}`);
    console.log(`Jour sans match : ${result.noMatchDay ? 'OUI (normal)' : 'NON'}`);
    console.log(`Matches récupérés : ${result.matches.length}`);

    if (result.matches.length > 0) {
      console.log('\n⚽ Matches trouvés :');
      result.matches.forEach((m, i) => {
        console.log(`  ${i + 1}. [${m.league_name || '?'}] ${m.home_team_name || '?'} vs ${m.away_team_name || '?'}`);
        console.log(`     Date: ${new Date(m.match_date).toLocaleString('fr-FR')}`);
        console.log(`     Statut: ${m.status} | Score: ${m.home_score ?? '-'} / ${m.away_score ?? '-'}`);
        console.log(`     Source données: ${m.data_source}`);
        console.log(`     Lineups: ${m.lineups && Object.keys(m.lineups).length > 0 ? '✅' : '❌'}`);
        console.log(`     Stats: ${m.raw_stats && Object.keys(m.raw_stats).length > 0 ? '✅' : '❌'}`);
        console.log(`     Cotes: ${m.odds && Object.keys(m.odds).length > 0 ? '✅' : '❌'}`);
        console.log('');
      });
    }

    // Vérification en base
    const { rows: dbCount } = await pool.query(
      `SELECT COUNT(*) as total FROM matches WHERE DATE(match_date AT TIME ZONE 'UTC') = $1`,
      [testDate]
    );
    console.log(`\n💾 Vérification base de données :`);
    console.log(`   Matches en base pour ${testDate} : ${dbCount[0].total}`);

    // Quota après collecte
    const quotaAfter = await getQuotaStatus();
    console.log(`\n📊 Quota après collecte : ${quotaAfter.used}/${quotaAfter.limit}`);
    console.log(`   Requêtes utilisées ce test : ${quotaAfter.used - quotaBefore.used}`);
    console.log(`   Requêtes restantes : ${quotaAfter.remaining}`);

    if (result.error) {
      console.log(`\n⚠️  Erreur signalée : ${result.error}`);
    }

    console.log('\n✅ Test du Data Collector terminé avec succès !\n');

  } catch (err) {
    console.error(`\n❌ Erreur durant le test : ${err.message}`);
    console.error(err.stack);
    process.exit(1);
  } finally {
    await pool.end();
  }
}

runTest();
