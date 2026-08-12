// scripts/set_season_2026.js
// Force la saison 2026 sur la table leagues (default + données existantes)
require('dotenv').config();
const { query } = require('../src/db');

(async () => {
  try {
    // 1️⃣ Mettre à jour le défaut de la colonne
    await query(`ALTER TABLE leagues ALTER COLUMN season SET DEFAULT 2026;`);
    // 2️⃣ Mettre à jour les lignes déjà présentes
    const res = await query(`UPDATE leagues SET season = 2026 WHERE season <> 2026 RETURNING id, season;`);
    console.log(`[migration] Saison mise à jour pour ${res.rowCount} lignes.`);
    console.log('Exemples:', res.rows.slice(0, 5));
    process.exit(0);
  } catch (err) {
    console.error('[migration] Erreur lors de la mise à jour de la saison :', err.message);
    process.exit(1);
  }
})();
