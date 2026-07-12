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
    
    // Send the coupon content
    await ctx.reply(coupon.contenu, { parse_mode: 'Markdown' });
  } catch (error) {
    console.error('Erreur lors du traitement de /coupon:', error.message);
    await ctx.reply("Désolé, une erreur est survenue lors de la récupération du coupon.");
  }
};
