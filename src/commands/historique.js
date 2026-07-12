const db = require('../db/database');

module.exports = async (ctx) => {
  try {
    const rawDb = db.getDb();
    if (!rawDb) {
      return ctx.reply("❌ Base de données inaccessible.");
    }

    const stmt = rawDb.prepare(`
      SELECT date, contenu FROM coupons 
      ORDER BY date DESC 
      LIMIT 5
    `);
    const recentCoupons = stmt.all();

    if (!recentCoupons || recentCoupons.length === 0) {
      return ctx.reply("Aucun coupon n'est enregistré dans l'historique.");
    }

    let replyMessage = "📅 *Historique des 5 derniers coupons :*\n\n";
    for (const coupon of recentCoupons) {
      // Strip markdown characters to prevent parsing issues on truncated text
      const cleanContent = coupon.contenu.replace(/[*_`[\]()]/g, '');
      const preview = cleanContent.length > 150 
        ? cleanContent.substring(0, 150) + '...' 
        : cleanContent;
      
      replyMessage += `🔹 *Coupon du ${coupon.date}* :\n${preview}\n\n`;
    }

    await ctx.replyWithMarkdown(replyMessage);
  } catch (error) {
    console.error("Erreur lors de la récupération de l'historique:", error.message);
    await ctx.reply("Désolé, une erreur est survenue lors de la récupération de l'historique.");
  }
};
