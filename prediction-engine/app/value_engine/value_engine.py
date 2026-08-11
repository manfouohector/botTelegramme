from typing import Dict, Any, List, Optional
from loguru import logger

class ValueEngine:
    """
    Value Engine
    Convertit les cotes bookmakers en probabilités implicites.
    Compare ces probabilités implicites avec celles de notre modèle (Ensemble/Poisson)
    pour identifier des opportunités de "Value Bet" (pari de valeur).
    """
    
    def __init__(self, min_value_threshold: float = 0.05, max_value_threshold: float = 0.20):
        # Marge bénéficiaire standard des bookmakers (vig / overround), souvent autour de 5-7% pour le 1X2
        self.default_bookmaker_margin = 0.05
        # Seuil minimal d'écart pour considérer un pari comme "Value" (ex: 5%)
        self.min_value_threshold = min_value_threshold
        # Seuil maximal d'écart. Au-delà, c'est souvent suspect (infos que le modèle n'a pas, ex: équipe B alignée)
        self.max_value_threshold = max_value_threshold

    def calculate_implicit_probability(self, odds: float) -> float:
        """
        Calcule la probabilité implicite brute depuis une cote décimale.
        :param odds: Cote bookmaker (ex: 2.00)
        :return: Probabilité implicite (ex: 0.50)
        """
        if odds <= 1.0:
            return 0.0
        return 1.0 / odds

    def remove_margin(self, prob_home: float, prob_draw: float, prob_away: float) -> tuple:
        """
        Retire la marge du bookmaker (overround) des probabilités implicites brutes pour le 1X2.
        :return: (prob_home_real, prob_draw_real, prob_away_real)
        """
        implied_total = prob_home + prob_draw + prob_away
        if implied_total == 0:
            return 0.0, 0.0, 0.0
            
        return (
            prob_home / implied_total,
            prob_draw / implied_total,
            prob_away / implied_total
        )

    def analyze_value(self, model_probabilities: Dict[str, float], bookmaker_odds: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Analyse les probabilités du modèle par rapport aux cotes du marché pour trouver la "Value".
        :param model_probabilities: Probas du modèle (ex: {'1X2_1': 0.55, ...})
        :param bookmaker_odds: Cotes bookmaker (ex: {'1X2_1': 2.00, ...})
        :return: Liste des paris évalués, avec indicateur is_value_bet
        """
        logger.debug("[ValueEngine] Démarrage analyse de la valeur")
        evaluated_bets = []
        
        for market, odd in bookmaker_odds.items():
            if odd <= 1.0 or market not in model_probabilities:
                continue
                
            model_prob = model_probabilities[market]
            implicit_prob = self.calculate_implicit_probability(odd)
            
            # Écart de valeur: Probabilité de notre modèle - Probabilité implicite du marché
            # Si positif, notre modèle pense que l'événement a plus de chances de se produire que ce que dit la cote
            value_gap = model_prob - implicit_prob
            
            # Détection de la "Value"
            is_value = False
            suspect = False
            
            if self.min_value_threshold <= value_gap <= self.max_value_threshold:
                is_value = True
            elif value_gap > self.max_value_threshold:
                suspect = True # L'écart est trop grand, potentiellement suspect
                logger.warning(f"[ValueEngine] Écart suspect détecté sur le marché {market}: {value_gap:.2%} (Model: {model_prob:.2%}, Market: {implicit_prob:.2%})")

            evaluated_bets.append({
                "market": market,
                "model_prob": model_prob,
                "market_prob": implicit_prob,
                "odds": odd,
                "value_gap": value_gap,
                "is_value_bet": is_value,
                "is_suspect": suspect
            })
            
        return evaluated_bets

value_engine = ValueEngine()
