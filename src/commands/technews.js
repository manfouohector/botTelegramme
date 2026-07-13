const db = require('../db/database');

function getLocalDateString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const { runTechNewsPipeline } = require('../services/pipeline');

module.exports = async (ctx) => {
  const todayStr = getLocalDateString();
  
  try {
    let news = db.getTechNews(todayStr);
    
    if (!news || !news.contenu) {
      // Get current hour in UTC+1
      const hourUTC1 = (new Date().getUTCHours() + 1) % 24;
      if (hourUTC1 >= 9) {
        await ctx.reply("🔄 L'actualité tech d'aujourd'hui n'est pas encore prête. Lancement de la génération automatique (cela prend environ 30 secondes), veuillez patienter...");
        const result = await runTechNewsPipeline(todayStr);
        if (result && result.error) {
          return ctx.reply("❌ Une erreur est survenue lors de la génération automatique des actualités. Veuillez réessayer dans quelques instants.");
        }
        news = db.getTechNews(todayStr);
      } else {
        return ctx.reply("L'actualité tech d'aujourd'hui n'est pas encore prête, réessaie après 9h00.");
      }
    }
    
    let articles = [];
    let isJson = false;
    try {
      if (news.contenu.trim().startsWith('[')) {
        articles = JSON.parse(news.contenu);
        isJson = Array.isArray(articles);
      }
    } catch (e) {
      // Not JSON
    }

    if (isJson && articles.length > 0) {
      await ctx.reply(`📰 *TECH NEWS DU ${todayStr}* 📰\nVoici la sélection du jour :`, { parse_mode: 'Markdown' });
      for (const article of articles) {
        const messageText = `📁 *Catégorie :* ${article.category}\n🔥 *${article.title}*\n\n💡 *TL;DR :*\n${article.tldr}`;
        await ctx.reply(messageText, {
          parse_mode: 'Markdown',
          reply_markup: {
            inline_keyboard: [
              [
                { text: 'Lire l’article complet 🔗', url: article.url }
              ]
            ]
          }
        });
      }
    } else {
      // Fallback
      await ctx.reply(news.contenu, { parse_mode: 'Markdown' });
    }
  } catch (error) {
    console.error('Erreur lors du traitement de /technews:', error.message);
    await ctx.reply("Désolé, une erreur est survenue lors de la récupération des actualités.");
  }
};
