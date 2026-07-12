const db = require('../db/database');

function getLocalDateString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

module.exports = async (ctx) => {
  const todayStr = getLocalDateString();
  
  try {
    const news = db.getTechNews(todayStr);
    
    if (!news || !news.contenu) {
      return ctx.reply("L'actualité tech d'aujourd'hui n'est pas encore prête, réessaie après 9h.");
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
