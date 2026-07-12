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
    
    if (!coupon || !coupon.contenu) {
      return ctx.reply("Le coupon du jour n'est pas encore prêt, réessaie après 8h.");
    }
    
    let couponText = coupon.contenu;
    
    if (coupon.matchs_json) {
      try {
        const matches = JSON.parse(coupon.matchs_json);
        if (Array.isArray(matches) && matches.length > 0) {
          let statsText = '\n\n📊 *Statistiques récentes des équipes :*\n';
          for (const m of matches) {
            statsText += `\n⚽ *${m.home_team}* vs *${m.away_team}*\n`;
            if (m.home_form) {
              statsText += `  - Forme ${m.home_team} : \`${m.home_form}\` (Pos: ${m.home_position || 'N/A'})\n`;
            }
            if (m.away_form) {
              statsText += `  - Forme ${m.away_team} : \`${m.away_form}\` (Pos: ${m.away_position || 'N/A'})\n`;
            }
          }
          couponText += statsText;
        }
      } catch (e) {
        console.error('Erreur lors du parsing des stats du coupon:', e.message);
      }
    }
    
    // Send the coupon content
    await ctx.reply(couponText, { parse_mode: 'Markdown' });
  } catch (error) {
    console.error('Erreur lors du traitement de /coupon:', error.message);
    await ctx.reply("Désolé, une erreur est survenue lors de la récupération du coupon.");
  }
};
