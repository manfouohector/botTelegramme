/**
 * test-db-connection.js
 * Script de test de connexion à la base de données PostgreSQL
 * Usage: node test-db-connection.js
 */

const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env') });

const { Pool } = require('pg');

async function testConnection() {
  console.log('\n🔌 Test de connexion PostgreSQL (DevMind Bot Backend)\n');
  console.log(`DATABASE_URL: ${process.env.DATABASE_URL ? '✅ Définie' : '❌ Non définie'}`);

  if (!process.env.DATABASE_URL) {
    console.error('\n❌ DATABASE_URL non définie. Créez votre fichier .env à partir de .env.example\n');
    process.exit(1);
  }

  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    connectionTimeoutMillis: 15000,
  });

  try {
    const client = await pool.connect();
    console.log('\n✅ Connexion réussie à PostgreSQL !\n');

    // Test 1 : Version PostgreSQL
    const versionResult = await client.query('SELECT version()');
    console.log('📦 Version PostgreSQL:', versionResult.rows[0].version.split(' ').slice(0, 2).join(' '));

    // Test 2 : Lister les tables existantes
    const tablesResult = await client.query(`
      SELECT table_name
      FROM information_schema.tables
      WHERE table_schema = 'public'
      ORDER BY table_name;
    `);

    if (tablesResult.rows.length === 0) {
      console.log('\n⚠️  Aucune table trouvée — la migration n\'a pas encore été exécutée.');
      console.log('   Exécutez : npm run migrate\n');
    } else {
      console.log(`\n📋 Tables trouvées (${tablesResult.rows.length}) :`);
      tablesResult.rows.forEach(row => {
        console.log(`   - ${row.table_name}`);
      });

      // Test 3 : Vérifier les tables critiques
      const expectedTables = [
        'users', 'subscriptions', 'payments', 'matches', 'leagues',
        'teams', 'predictions', 'markets', 'coupons', 'coupon_predictions',
        'prediction_results', 'performance_stats', 'risk_factors',
        'ai_models', 'api_quota_tracker'
      ];

      const existingNames = tablesResult.rows.map(r => r.table_name);
      const missing = expectedTables.filter(t => !existingNames.includes(t));

      if (missing.length === 0) {
        console.log('\n✅ Toutes les tables requises sont présentes !');
      } else {
        console.log('\n⚠️  Tables manquantes :', missing.join(', '));
        console.log('   Exécutez : npm run migrate');
      }

      // Test 4 : Vérifier les seeds
      const modelsResult = await client.query('SELECT name, version FROM ai_models');
      if (modelsResult.rows.length > 0) {
        console.log(`\n🤖 Modèles IA enregistrés (${modelsResult.rows.length}) :`);
        modelsResult.rows.forEach(m => console.log(`   - ${m.name} v${m.version}`));
      }

      const leaguesResult = await client.query('SELECT name, country FROM leagues WHERE covered = TRUE');
      if (leaguesResult.rows.length > 0) {
        console.log(`\n⚽ Championnats couverts V1 (${leaguesResult.rows.length}) :`);
        leaguesResult.rows.forEach(l => console.log(`   - ${l.name} (${l.country})`));
      }

      const marketsResult = await client.query('SELECT code, name FROM markets');
      if (marketsResult.rows.length > 0) {
        console.log(`\n🎯 Marchés de paris (${marketsResult.rows.length}) :`);
        marketsResult.rows.forEach(m => console.log(`   - ${m.code}: ${m.name}`));
      }
    }

    client.release();
    console.log('\n✅ Tous les tests ont réussi !\n');

  } catch (err) {
    console.error('\n❌ Erreur de connexion:', err.message);
    console.error('\nVérifiez :');
    console.error('  1. Que DATABASE_URL est correctement définie dans .env');
    console.error('  2. Que votre base de données Neon.tech / Supabase est accessible');
    console.error('  3. Que les options SSL sont correctes\n');
    process.exit(1);
  } finally {
    await pool.end();
  }
}

testConnection();
