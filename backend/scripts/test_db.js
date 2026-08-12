// backend/scripts/test_db.js
require('dotenv').config({ path: '../.env' });
const { Pool } = require('pg');
(async () => {
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false }
  });
  try {
    const res = await pool.query('SELECT NOW()');
    console.log('✅ Connexion OK, now:', res.rows[0].now);
  } catch (e) {
    console.error('❌ Connexion échouée :', e.message);
  } finally {
    await pool.end();
  }
})();
