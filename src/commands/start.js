const db = require('../db/database');

module.exports = async (ctx) => {
  const chatId = ctx.chat.id;
  const chatType = ctx.chat.type;

  // Enregistrer l'utilisateur dans les abonnés
  db.addSubscriber(chatId, chatType);

  const welcomeMessage = `👋 *Bienvenue sur le Bot de Pronostics & Actualités Tech !*

Je suis votre assistant tech quotidien, propulsé par IA (Gemini + Groq).

━━━━━━━━━━━━━━━━━━━━
🤖 *Ce que je sais faire :*
━━━━━━━━━━━━━━━━━━━━
⚽ *Pronostics Football* — coupons générés par IA avec analyse approfondie chaque matin à *8h00*.
📰 *Actualités Tech* — sélection quotidienne des meilleures news tech en français à *9h00*.
💬 *Assistant Tech* — posez-moi n'importe quelle question technique, je répondrai en direct !

━━━━━━━━━━━━━━━━━━━━
📋 *Commandes disponibles :*
━━━━━━━━━━━━━━━━━━━━
/coupon — Coupon football du jour (généré à 8h00)
/matchs — Matchs analysés du jour avec statistiques
/historique — 5 derniers coupons de football
/technews — Actualités tech du jour (catégorisées + TL;DR)
/aide — Aide détaillée sur les commandes

━━━━━━━━━━━━━━━━━━━━
🔒 *Commandes admin :*
━━━━━━━━━━━━━━━━━━━━
/status — État du bot (SQLite, Cron, Webhook)

━━━━━━━━━━━━━━━━━━━━
💡 *Astuce :* Envoyez simplement votre question technique en message direct, je répondrai avec l'aide de Gemini & Groq !

_Les données sont générées automatiquement chaque jour pour optimiser les performances._`;

  try {
    await ctx.replyWithMarkdown(welcomeMessage);
  } catch (error) {
    console.error('Erreur lors de la réponse au /start:', error.message);
    // Retry without Markdown if it fails due to parse errors
    try {
      await ctx.reply('Bienvenue ! Utilisez /aide pour voir les commandes disponibles.');
    } catch (e) {
      console.error('Erreur critique lors du /start:', e.message);
    }
  }
};
