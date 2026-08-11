const { Pool } = require('pg');
require('dotenv').config();

// Neon.tech (et la plupart des PostgreSQL hébergés) requiert SSL en toutes circonstances
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
  max: 10,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 0, // 0 = pas de timeout de connexion (utile pour Neon.tech)
});

// Test de connexion au démarrage
pool.on('connect', () => {
  // Connexion établie silencieusement
});

pool.on('error', (err) => {
  console.error('[DB] Erreur inattendue sur le pool PostgreSQL:', err.message);
});

/**
 * Exécute une requête SQL avec paramètres
 * @param {string} text - Requête SQL
 * @param {Array} params - Paramètres
 */
const query = async (text, params) => {
  const start = Date.now();
  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[DB] Requête exécutée en ${duration}ms — rows: ${res.rowCount}`);
    }
    return res;
  } catch (err) {
    console.error('[DB] Erreur de requête:', err.message);
    console.error('[DB] SQL:', text);
    throw err;
  }
};

/**
 * Exécute plusieurs requêtes dans une transaction atomique
 * @param {Function} callback - Fonction recevant le client de transaction
 */
const withTransaction = async (callback) => {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    const result = await callback(client);
    await client.query('COMMIT');
    return result;
  } catch (err) {
    await client.query('ROLLBACK');
    throw err;
  } finally {
    client.release();
  }
};

module.exports = { pool, query, withTransaction };
