import numpy as np
from scipy.stats import poisson
from loguru import logger
from typing import Dict, Any, Tuple

class PoissonModel:
    """
    Modèle statistique basé sur la distribution de Poisson.
    Utilisé pour estimer la probabilité du nombre de buts marqués par chaque équipe
    et en déduire les marchés de base (1X2, Over/Under, BTTS).
    """
    
    def __init__(self, max_goals: int = 10):
        self.max_goals = max_goals
        self.version = "1.0"
        self.name = "poisson"
        
    def predict_match(self, home_expected_goals: float, away_expected_goals: float) -> Dict[str, float]:
        """
        Calcule les probabilités de tous les marchés à partir des xG (Expected Goals).
        
        :param home_expected_goals: Moyenne attendue de buts pour l'équipe à domicile
        :param away_expected_goals: Moyenne attendue de buts pour l'équipe à l'extérieur
        :return: Dictionnaire des probabilités pour chaque marché
        """
        if home_expected_goals < 0 or away_expected_goals < 0:
            raise ValueError("Les expected goals doivent être positifs")
            
        logger.debug(f"[Poisson] Prédiction pour xG(Home)={home_expected_goals:.2f}, xG(Away)={away_expected_goals:.2f}")
        
        # 1. Matrice des scores exacts (probabilités conjointes)
        # On fait l'hypothèse d'indépendance pour la V1 (modèle Poisson standard)
        home_probs = poisson.pmf(np.arange(self.max_goals + 1), home_expected_goals)
        away_probs = poisson.pmf(np.arange(self.max_goals + 1), away_expected_goals)
        
        score_matrix = np.outer(home_probs, away_probs)
        
        # 2. Marché 1X2 (Résultat final)
        prob_home = float(np.sum(np.tril(score_matrix, -1)))
        prob_draw = float(np.sum(np.diag(score_matrix)))
        prob_away = float(np.sum(np.triu(score_matrix, 1)))
        
        # 3. Marché BTTS (Les deux équipes marquent)
        prob_home_scores = float(1 - home_probs[0])
        prob_away_scores = float(1 - away_probs[0])
        prob_btts_yes = prob_home_scores * prob_away_scores
        prob_btts_no = 1 - prob_btts_yes
        
        # 4. Marchés Over/Under
        prob_under_2_5 = 0.0
        prob_under_3_5 = 0.0
        
        for i in range(self.max_goals + 1):
            for j in range(self.max_goals + 1):
                total_goals = i + j
                prob = score_matrix[i, j]
                
                if total_goals < 2.5:
                    prob_under_2_5 += prob
                if total_goals < 3.5:
                    prob_under_3_5 += prob
                    
        prob_over_2_5 = 1 - prob_under_2_5
        prob_over_3_5 = 1 - prob_under_3_5
        
        # 5. Double Chance
        prob_1x = prob_home + prob_draw
        prob_x2 = prob_draw + prob_away
        prob_12 = prob_home + prob_away
        
        # 6. Draw No Bet (Remboursé si nul)
        prob_dnb_home = prob_home / (prob_home + prob_away) if (prob_home + prob_away) > 0 else 0
        prob_dnb_away = prob_away / (prob_home + prob_away) if (prob_home + prob_away) > 0 else 0
        
        return {
            '1X2_1': prob_home,
            '1X2_X': prob_draw,
            '1X2_2': prob_away,
            'BTTS_YES': prob_btts_yes,
            'BTTS_NO': prob_btts_no,
            'OVER_2_5': prob_over_2_5,
            'UNDER_2_5': prob_under_2_5,
            'OVER_3_5': prob_over_3_5,
            'UNDER_3_5': prob_under_3_5,
            'DOUBLE_CHANCE_1X': prob_1x,
            'DOUBLE_CHANCE_X2': prob_x2,
            'DOUBLE_CHANCE_12': prob_12,
            'DRAW_NO_BET_1': prob_dnb_home,
            'DRAW_NO_BET_2': prob_dnb_away
        }

poisson_model = PoissonModel()
