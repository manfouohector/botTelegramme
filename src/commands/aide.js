module.exports = async (ctx) => {
  const helpMessage = `💡 *Liste des commandes disponibles :*

/start - Démarre le bot et affiche le message d'accueil
/coupon - Affiche le coupon de pronostics football du jour (généré à 8h00)
/matchs - Affiche la liste simplifiée des matchs analysés du jour
/technews - Affiche le résumé des actualités tech du jour (généré à 9h00)
/aide - Affiche ce message d'aide

Les résultats sont générés automatiquement chaque matin. Si un coupon ou des actualités ne sont pas encore prêts, le bot vous le signalera.`;

  try {
    await ctx.replyWithMarkdown(helpMessage);
  } catch (error) {
    console.error('Erreur lors de la réponse au /aide:', error.message);
  }
};
