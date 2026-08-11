const path = require('path');
const fs = require('fs');

// ⚠️ Charger dotenv EN PREMIER, avant tout require qui utilise process.env
require('dotenv').config({ path: path.join(__dirname, '../../.env') });

const { pool } = require('./index');


const MIGRATIONS_DIR = path.join(__dirname, '../../migrations');

async function runMigrations() {
  const client = await pool.connect();

  try {
    // Créer la table de suivi des migrations si elle n'existe pas
    await client.query(`
      CREATE TABLE IF NOT EXISTS _migrations (
        id         SERIAL      PRIMARY KEY,
        filename   VARCHAR(200) NOT NULL UNIQUE,
        applied_at TIMESTAMPTZ  DEFAULT NOW()
      );
    `);

    // Lire tous les fichiers .sql dans le dossier migrations (ordre alphabétique)
    const files = fs.readdirSync(MIGRATIONS_DIR)
      .filter(f => f.endsWith('.sql'))
      .sort();

    if (files.length === 0) {
      console.log('[Migrate] Aucun fichier de migration trouvé.');
      return;
    }

    for (const file of files) {
      // Vérifier si la migration a déjà été appliquée
      const { rows } = await client.query(
        'SELECT id FROM _migrations WHERE filename = $1',
        [file]
      );

      if (rows.length > 0) {
        console.log(`[Migrate] ✅ Déjà appliquée : ${file}`);
        continue;
      }

      // Lire et exécuter le fichier SQL
      const sqlPath = path.join(MIGRATIONS_DIR, file);
      const sql = fs.readFileSync(sqlPath, 'utf-8');

      console.log(`[Migrate] 🔄 Application de : ${file} ...`);

      await client.query('BEGIN');
      try {
        await client.query(sql);
        await client.query(
          'INSERT INTO _migrations (filename) VALUES ($1)',
          [file]
        );
        await client.query('COMMIT');
        console.log(`[Migrate] ✅ Migration appliquée avec succès : ${file}`);
      } catch (err) {
        await client.query('ROLLBACK');
        console.error(`[Migrate] ❌ Erreur sur ${file}:`, err.message);
        throw err;
      }
    }

    console.log('\n[Migrate] 🎉 Toutes les migrations ont été appliquées.');

  } finally {
    client.release();
    await pool.end();
  }
}

runMigrations().catch(err => {
  console.error('[Migrate] Erreur fatale:', err.message);
  process.exit(1);
});
