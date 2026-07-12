const db = require('../db/database');

module.exports = async (ctx) => {
  const chatId = ctx.chat.id;
  const chatType = ctx.chat.type;

  // Enregistrer l'utilisateur dans les abonnés
  db.addSubscriber(chatId, chatType);

  const welcomeMessage = `👋 *Bienvenue sur le Bot de Pronostics & Actualités Tech !*

Je suis votre assistant quotidien. Voici mes fonctionnalités :
⚽ *Pronostics Football* : Des pronostics générés par IA et grounded par recherche en ligne.
📰 *Actualités Tech* : Un condensé quotidien en français des actus tech majeures.

💡 *Commandes disponibles :*
/coupon - Récupère le coupon de pronostics du jour (généré à 8h00)
/matchs - Affiche la liste des matchs analysés du jour
/technews - Récupère les actualités tech du jour (généré à 9h00)
/aide - Affiche la liste des commandes et des explications

_Note : Toutes les données sont pré-générées quotidiennement pour optimiser les performances et maîtriser les coûts._`;

  try {
    await ctx.replyWithMarkdown(welcomeMessage);
  } catch (error) {
    console.error('Erreur lors de la réponse au /start:', error.message);
  }
};
