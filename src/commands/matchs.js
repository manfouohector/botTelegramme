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
    const coupon = db.getCoupon(todayStr);
    
    if (!coupon || !coupon.matchs_json) {
      return ctx.reply("Aucun match n'a été analysé pour aujourd'hui ou le coupon n'est pas encore prêt. Réessaye après 8h.");
    }
    
    let matches = [];
    try {
      matches = JSON.parse(coupon.matchs_json);
    } catch (e) {
      console.error('Erreur lors du parsing des matchs JSON:', e.message);
    }
    
    if (!Array.isArray(matches) || matches.length === 0) {
      return ctx.reply("Aucun match n'a été analysé aujourd'hui (aucun match éligible trouvé).");
    }
    
    let message = `📊 *Matchs analysés aujourd'hui (${todayStr}) :*\n\n`;
    for (const m of matches) {
      message += `🏆 *${m.competition}*\n`;
      message += `⚽ ${m.home_team} vs ${m.away_team}\n`;
      message += `🎯 Pari : *${m.bet_type}* (Confiance: ${m.confidence_score}%)\n`;
      message += `💡 Indice : _${m.reasoning_brief}_\n\n`;
    }
    
    await ctx.replyWithMarkdown(message);
  } catch (error) {
    console.error('Erreur lors du traitement de /matchs:', error.message);
    await ctx.reply("Désolé, une erreur est survenue lors de la récupération des matchs.");
  }
};
