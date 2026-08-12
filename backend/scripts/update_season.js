// scripts/update_season.js
// Tiny helper to run the season‑update migration on Neon via the pg pool defined in src/db/index.js

require('dotenv').config();
const { query } = require('../src/db');

(async () => {
  try {
    const res = await query(
      `UPDATE league
       SET season = CASE
         WHEN EXTRACT(MONTH FROM CURRENT_DATE) >= 7 THEN EXTRACT(YEAR FROM CURRENT_DATE)::int
         ELSE (EXTRACT(YEAR FROM CURRENT_DATE) - 1)::int
       END
       RETURNING *;`
    );
    console.log(`[migration] Updated ${res.rowCount} rows in league table.`);
    console.log('Sample rows:', res.rows.slice(0, 5));
    process.exit(0);
  } catch (err) {
    console.error('[migration] Error:', err.message);
    process.exit(1);
  }
})();
