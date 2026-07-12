const db = require('../db/database');
const footballService = require('./football');
const groqService = require('./groq');
const geminiService = require('./gemini');
const rssService = require('./rss');

/**
 * Orchestrates the daily football coupon generation pipeline
 * @param {string} dateStr Format YYYY-MM-DD
 */
async function runFootballPipeline(dateStr) {
  console.log(`[PIPELINE] Lancement du pipeline Football pour le ${dateStr}...`);
  let selectedMatches = [];
  let couponText = '';

  try {
    // Étape 1: Récupération des données brutes
    const enrichedMatches = await footballService.getEnrichedMatches(dateStr);
    
    if (!enrichedMatches || enrichedMatches.length === 0) {
      couponText = `⚽ **Pronostics du ${dateStr}** ⚽\n\n Aucun match n'est programmé aujourd'hui dans les championnats majeurs couverts par le service gratuit. Profitez-en pour vous reposer !`;
      db.saveCoupon(dateStr, couponText, JSON.stringify([]));
      console.log(`[PIPELINE] Aucun match aujourd'hui. Coupon vide enregistré.`);
      await broadcastMessage(couponText);
      return { coupon: couponText, matches: [] };
    }

    // Étape 2: Tri rapide (Groq)
    console.log(`[PIPELINE] Sélection des meilleurs matchs par Groq...`);
    const selection = await groqService.selectTopMatches(enrichedMatches);
    selectedMatches = (selection.selected_matches || []).map(selected => {
      const original = enrichedMatches.find(m => m.id === selected.match_id);
      if (original) {
        return {
          ...selected,
          home_position: original.homeTeam.position,
          home_form: original.homeTeam.form,
          away_position: original.awayTeam.position,
          away_form: original.awayTeam.form
        };
      }
      return selected;
    });

    if (selectedMatches.length === 0) {
      couponText = `⚽ **Pronostics du ${dateStr}** ⚽\n\n Aucun match ne présente un indice de confiance suffisant aujourd'hui pour générer des pronostics fiables. À demain !`;
      db.saveCoupon(dateStr, couponText, JSON.stringify([]));
      console.log(`[PIPELINE] Aucun match sélectionné par l'IA. Coupon vide enregistré.`);
      await broadcastMessage(couponText);
      return { coupon: couponText, matches: [] };
    }

    console.log(`[PIPELINE] ${selectedMatches.length} matchs sélectionnés pour l'analyse approfondie.`);

    // Étape 3: Analyse approfondie (Gemini avec Search grounding)
    const analyses = [];
    for (const match of selectedMatches) {
      try {
        const analysis = await geminiService.analyzeMatch(match);
        analyses.push({
          match_id: match.match_id,
          home_team: match.home_team,
          away_team: match.away_team,
          competition: match.competition,
          confidence_score: match.confidence_score,
          bet_type: match.bet_type,
          reasoning_brief: match.reasoning_brief,
          deep_analysis: analysis
        });
        // Espacer légèrement les appels Gemini pour le confort de l'API
        await new Promise(resolve => setTimeout(resolve, 1000));
      } catch (err) {
        console.error(`[PIPELINE] Échec de l'analyse Gemini pour le match ${match.home_team} vs ${match.away_team}:`, err.message);
        // Fallback
        analyses.push({
          ...match,
          deep_analysis: geminiService.getFallbackAnalysis(match)
        });
      }
    }

    // Étape 4: Formatage final (Groq)
    console.log(`[PIPELINE] Formatage final du coupon par Groq...`);
    couponText = await groqService.generateFinalCoupon(analyses);

    // Étape 5: Stockage
    db.saveCoupon(dateStr, couponText, JSON.stringify(selectedMatches));
    console.log(`[PIPELINE] Coupon enregistré dans la base de données avec succès.`);

    // Étape 6: Publication automatique
    await broadcastMessage(couponText);

    return { coupon: couponText, matches: selectedMatches };
  } catch (error) {
    console.error(`[PIPELINE] Erreur critique dans le pipeline football:`, error.message);
    // Enregistrer un message d'erreur pour aujourd'hui pour ne pas laisser la base vide
    const errorText = `⚽ **Pronostics du ${dateStr}** ⚽\n\nUne erreur technique est survenue lors de la génération du coupon d'aujourd'hui. Nos équipes travaillent à sa résolution.`;
    db.saveCoupon(dateStr, errorText, JSON.stringify([]));
    return { error: error.message };
  }
}

/**
 * Orchestrates the daily tech news generation pipeline
 * @param {string} dateStr Format YYYY-MM-DD
 */
async function runTechNewsPipeline(dateStr) {
  console.log(`[PIPELINE] Lancement du pipeline Tech News pour le ${dateStr}...`);

  try {
    // Étape 1: Récupérer les articles depuis les flux RSS
    const newsItems = await rssService.fetchTechNews();

    if (!newsItems || newsItems.length === 0) {
      const fallbackText = `📰 **Actualités Tech du ${dateStr}** 📰\n\nAucune actualité technologique récente n'a pu être récupérée aujourd'hui.`;
      db.saveTechNews(dateStr, fallbackText);
      console.log(`[PIPELINE] Aucun article RSS trouvé. Actualité vide enregistrée.`);
      await broadcastMessage(fallbackText);
      return { news: fallbackText };
    }

    // Étape 2: Générer la synthèse (Groq)
    console.log(`[PIPELINE] Sélection et résumé des actualités par Groq...`);
    const newsText = await groqService.summarizeTechNews(newsItems);

    // Étape 3: Stockage
    db.saveTechNews(dateStr, newsText);
    console.log(`[PIPELINE] Actualités enregistrées avec succès dans la base.`);

    // Étape 4: Publication automatique
    await broadcastMessage(newsText);

    return { news: newsText };
  } catch (error) {
    console.error(`[PIPELINE] Erreur critique dans le pipeline tech news:`, error.message);
    const errorText = `📰 **Actualités Tech du ${dateStr}** 📰\n\nUne erreur technique est survenue lors de la génération des actualités.`;
    db.saveTechNews(dateStr, errorText);
    return { error: error.message };
  }
}

/**
 * Helper to broadcast the generated content to all private subscribers in the database
 * @param {string} text Message content
 */
async function broadcastMessage(text) {
  try {
    // Dynamic require to avoid circular dependencies with bot.js
    const botModule = require('../bot');
    if (botModule && typeof botModule.broadcast === 'function') {
      await botModule.broadcast(text);
    } else {
      console.log('[PIPELINE] Le bot Telegram n\'est pas encore démarré ou n\'a pas de fonction de broadcast.');
    }
  } catch (error) {
    console.error('[PIPELINE] Erreur lors de la diffusion du message:', error.message);
  }
}

module.exports = {
  runFootballPipeline,
  runTechNewsPipeline
};
