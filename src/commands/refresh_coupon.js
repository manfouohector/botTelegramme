const { runFootballPipeline } = require('../services/pipeline');
const { getLocalDateString } = require('../services/scheduler');

module.exports = async (ctx) => {
  // Check admin authorization
  const adminIdsEnv = process.env.ADMIN_TELEGRAM_IDS || '';
  const adminIds = adminIdsEnv.split(',').map(id => parseInt(id.trim(), 10)).filter(Boolean);
  
  if (adminIds.length > 0 && !adminIds.includes(ctx.from.id)) {
    return ctx.reply("⚠️ Désolé, cette commande est réservée aux administrateurs.");
  }

  await ctx.reply("🔄 Régénération du coupon de football en cours... Veuillez patienter.");
  
  try {
    const todayStr = getLocalDateString();
    const result = await runFootballPipeline(todayStr);
    
    if (result && result.error) {
      return ctx.reply(`❌ Erreur lors de la génération : ${result.error}`);
    }
    
    await ctx.reply("✅ Le coupon de football a été régénéré et diffusé avec succès !");
  } catch (error) {
    console.error("Erreur lors de la régénération manuelle du coupon:", error.message);
    await ctx.reply(`❌ Une erreur critique est survenue : ${error.message}`);
  }
};
