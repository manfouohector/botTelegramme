const cron = require('node-cron');
const { runFootballPipeline, runTechNewsPipeline } = require('./pipeline');

/**
 * Utility to get today's date in local time as YYYY-MM-DD
 */
function getLocalDateString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function initScheduler() {
  // Coupon Football tous les jours à 8h00
  cron.schedule('0 8 * * *', async () => {
    const todayStr = getLocalDateString();
    console.log(`[SCHEDULER] Lancement planifié du pipeline Football pour ${todayStr} (8h00)...`);
    try {
      await runFootballPipeline(todayStr);
      console.log('[SCHEDULER] Fin du pipeline Football planifié.');
    } catch (error) {
      console.error('[SCHEDULER] Erreur dans le pipeline Football planifié:', error.message);
    }
  });

  // Actualités Tech tous les jours à 9h00
  cron.schedule('0 9 * * *', async () => {
    const todayStr = getLocalDateString();
    console.log(`[SCHEDULER] Lancement planifié du pipeline Tech News pour ${todayStr} (9h00)...`);
    try {
      await runTechNewsPipeline(todayStr);
      console.log('[SCHEDULER] Fin du pipeline Tech News planifié.');
    } catch (error) {
      console.error('[SCHEDULER] Erreur dans le pipeline Tech News planifié:', error.message);
    }
  });

  console.log('Tâches planifiées (cron) initialisées :');
  console.log(' - Coupon Football : tous les jours à 08h00');
  console.log(' - Actualités Tech : tous les jours à 09h00');
}

module.exports = {
  initScheduler,
  getLocalDateString
};
