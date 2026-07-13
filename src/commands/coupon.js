const db = require('../db/database');

function getLocalDateString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const { runFootballPipeline } = require('../services/pipeline');

module.exports = async (ctx) => {
  const todayStr = getLocalDateString();
  
  try {
    let coupon = db.getCoupon(todayStr);
    
    if (!coupon || !coupon.contenu) {
      // Get current hour in UTC+1
      const hourUTC1 = (new Date().getUTCHours() + 1) % 24;
      if (hourUTC1 >= 8) {
        await ctx.reply("🔄 Le coupon du jour n'est pas encore prêt. Lancement de la génération automatique (cela prend environ 30 secondes), veuillez patienter...");
        const result = await runFootballPipeline(todayStr);
        if (result && result.error) {
          return ctx.reply("❌ Une erreur est survenue lors de la génération automatique du coupon. Veuillez réessayer dans quelques instants.");
        }
        coupon = db.getCoupon(todayStr);
      } else {
        return ctx.reply("Le coupon du jour n'est pas encore prêt, réessaie après 8h00.");
      }
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
