// backend/scripts/run_migration_001.js
require('dotenv').config({ path: '../.env' });
const { Pool } = require('pg');
const fs = require('fs');
const path = require('path');

(async () => {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });
  const sql = fs.readFileSync(path.resolve(__dirname, '../migrations/001_init.sql'), 'utf8');
  try {
    await pool.query(sql);
    console.log('✅ Migration 001_init.sql exécutée avec succès');
  } catch (err) {
    console.error('❌ Erreur lors de la migration :', err.message);
    console.error(err.stack);
  } finally {
    await pool.end();
  }
})();
