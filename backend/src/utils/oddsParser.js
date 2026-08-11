/**
 * src/utils/oddsParser.js
 * Fonction utilitaire pour extraire la cote d'un marché spécifique
 * depuis la structure complexe JSON de API-Football.
 */

const logger = require('./logger');

/**
 * Extrait la cote pour le marché donné.
 * @param {Object} oddsData JSON retourné par API-Football (enrichments.odds)
 * @param {string} bestMarket Le marché choisi par le Prediction Engine (ex: '1X2_1', 'OVER_2_5')
 * @returns {number|null} La cote (ex: 1.85) ou null si non trouvée
 */
function extractOdds(oddsData, bestMarket) {
  if (!oddsData || !Array.isArray(oddsData)) return null;
  if (oddsData.length === 0) return null;

  // oddsData est généralement un tableau contenant l'objet du match
  const matchOdds = oddsData[0];
  if (!matchOdds || !Array.isArray(matchOdds.bookmakers) || matchOdds.bookmakers.length === 0) {
    return null;
  }

  // On prend le premier bookmaker dispo (souvent bet365 ou 10Bet)
  const bookmaker = matchOdds.bookmakers[0];
  if (!Array.isArray(bookmaker.bets)) return null;

  try {
    if (bestMarket.startsWith('1X2_')) {
      const bet = bookmaker.bets.find(b => b.name === 'Match Winner');
      if (!bet) return null;
      
      let targetValue = 'Home';
      if (bestMarket === '1X2_X') targetValue = 'Draw';
      if (bestMarket === '1X2_2') targetValue = 'Away';
      
      const val = bet.values.find(v => v.value === targetValue);
      return val ? parseFloat(val.odd) : null;
    }
    
    if (bestMarket.startsWith('OVER_') || bestMarket.startsWith('UNDER_')) {
      const bet = bookmaker.bets.find(b => b.name === 'Goals Over/Under');
      if (!bet) return null;
      
      const parts = bestMarket.split('_'); // ['OVER', '2', '5']
      const targetStr = `${parts[0] === 'OVER' ? 'Over' : 'Under'} ${parts[1]}.${parts[2]}`;
      
      const val = bet.values.find(v => v.value === targetStr);
      return val ? parseFloat(val.odd) : null;
    }
    
    if (bestMarket.startsWith('BTTS_')) {
      const bet = bookmaker.bets.find(b => b.name === 'Both Teams Score');
      if (!bet) return null;
      
      const targetValue = bestMarket === 'BTTS_YES' ? 'Yes' : 'No';
      const val = bet.values.find(v => v.value === targetValue);
      return val ? parseFloat(val.odd) : null;
    }
  } catch (err) {
    logger.error(`[oddsParser] Erreur lors du parsing des cotes pour ${bestMarket} : ${err.message}`);
  }

  return null;
}

module.exports = { extractOdds };
