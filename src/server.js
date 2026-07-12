const express = require('express');
const { runFootballPipeline, runTechNewsPipeline } = require('./services/pipeline');
const { getLocalDateString } = require('./services/scheduler');

function createServer() {
  const app = express();
  app.use(express.json());
  // Attach Telegraf webhook for /bot route
  const { getBotInstance } = require('./bot');
  const bot = getBotInstance();
  if (bot) {
    app.use(bot.webhookCallback('/bot'));
  }

  // Health check endpoint
  app.get('/health', (req, res) => {
    res.json({
      status: 'healthy',
      timestamp: new Date().toISOString(),
      uptime: process.uptime()
    });
  });

  // Trigger manual generation of the Football coupon
  app.post('/api/trigger/coupon', async (req, res) => {
    // Allows custom date via query param or body, defaults to today
    const dateStr = req.query.date || req.body.date || getLocalDateString();
    console.log(`[HTTP] Déclenchement manuel du coupon Football pour la date : ${dateStr}...`);

    try {
      const result = await runFootballPipeline(dateStr);
      if (result.error) {
        return res.status(500).json({
          status: 'error',
          message: 'Erreur lors de la génération du coupon.',
          error: result.error
        });
      }
      res.json({
        status: 'success',
        date: dateStr,
        matches_count: result.matches ? result.matches.length : 0,
        coupon: result.coupon
      });
    } catch (err) {
      console.error('[HTTP] Erreur route trigger/coupon:', err.message);
      res.status(500).json({ status: 'error', error: err.message });
    }
  });

  // Trigger manual generation of Tech News
  app.post('/api/trigger/technews', async (req, res) => {
    const dateStr = req.query.date || req.body.date || getLocalDateString();
    console.log(`[HTTP] Déclenchement manuel des Tech News pour la date : ${dateStr}...`);

    try {
      const result = await runTechNewsPipeline(dateStr);
      if (result.error) {
        return res.status(500).json({
          status: 'error',
          message: 'Erreur lors de la génération des actualités.',
          error: result.error
        });
      }
      res.json({
        status: 'success',
        date: dateStr,
        news: result.news
      });
    } catch (err) {
      console.error('[HTTP] Erreur route trigger/technews:', err.message);
      res.status(500).json({ status: 'error', error: err.message });
    }
  });

  return app;
}

module.exports = {
  createServer
};
