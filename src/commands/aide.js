module.exports = async (ctx) => {
  const helpMessage = `💡 *Liste des commandes disponibles :*

/start - Démarre le bot et affiche le message d'accueil
/coupon - Affiche le coupon de pronostics football du jour (généré à 8h00)
/matchs - Affiche la liste simplifiée des matchs analysés du jour
/technews - Affiche le résumé des actualités tech du jour (généré à 9h00)
/historique - Affiche l'historique des 5 derniers coupons
/aide - Affiche ce message d'aide

🔒 *Commandes Administrateur :*
/status - Affiche l'état du système (Base de données, Cron, Webhook)
/refresh_coupon - Force la régénération manuelle du coupon football

_Note : Les résultats normaux (coupons et news) sont générés automatiquement chaque matin. L'assistant Tech est aussi disponible en m'envoyant un message direct !_`;

  try {
    await ctx.replyWithMarkdown(helpMessage);
  } catch (error) {
    console.error('Erreur lors de la réponse au /aide:', error.message);
  }
};
