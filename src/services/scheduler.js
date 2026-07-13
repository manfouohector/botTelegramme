let schedulerActive = false;

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

  schedulerActive = true;
  console.log('Tâches planifiées (cron) initialisées :');
  console.log(' - Coupon Football : tous les jours à 08h00');
  console.log(' - Actualités Tech : tous les jours à 09h00');
}

async function checkAndGenerateMissing() {
  const db = require('../db/database');
  const todayStr = getLocalDateString();
  const hourUTC1 = (new Date().getUTCHours() + 1) % 24;

  console.log(`[SCHEDULER] Vérification des données manquantes au démarrage (Heure locale estimée: ${hourUTC1}h)...`);

  // Check Football (target 8h00)
  if (hourUTC1 >= 8) {
    try {
      const coupon = db.getCoupon(todayStr);
      if (!coupon || !coupon.contenu) {
        console.log(`[SCHEDULER] Coupon du jour manquant après 8h00. Lancement de la génération en tâche de fond...`);
        runFootballPipeline(todayStr).catch(err => {
          console.error('[SCHEDULER] Échec de la génération automatique du coupon au démarrage:', err.message);
        });
      }
    } catch (e) {
      console.error('[SCHEDULER] Erreur lors de la vérification du coupon au démarrage:', e.message);
    }
  }

  // Check Tech News (target 9h00)
  if (hourUTC1 >= 9) {
    try {
      const news = db.getTechNews(todayStr);
      if (!news || !news.contenu) {
        console.log(`[SCHEDULER] Actualités tech manquantes après 9h00. Lancement de la génération en tâche de fond...`);
        runTechNewsPipeline(todayStr).catch(err => {
          console.error('[SCHEDULER] Échec de la génération automatique des actualités au démarrage:', err.message);
        });
      }
    } catch (e) {
      console.error('[SCHEDULER] Erreur lors de la vérification des actualités au démarrage:', e.message);
    }
  }
}

module.exports = {
  initScheduler,
  checkAndGenerateMissing,
  getLocalDateString,
  isSchedulerActive: () => schedulerActive
};
