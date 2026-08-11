from typing import Dict, Any, Optional
from loguru import logger
from .poisson_model import poisson_model
from .xgboost_model import xgboost_model

class EnsembleModel:
    """
    Modèle Ensemble combinant les prédictions de Poisson (Statistique) et XGBoost (ML).
    Fournit la probabilité finale utilisée par le bot.
    """
    
    def __init__(self, poisson_weight: float = 0.6, xgb_weight: float = 0.4):
        self.version = "1.0"
        self.name = "ensemble"
        self.poisson_weight = poisson_weight
        self.xgb_weight = xgb_weight
        
    def _blend_probabilities(self, p1: float, p2: float, w1: float, w2: float) -> float:
        """Mélange deux probabilités selon leurs poids."""
        total_weight = w1 + w2
        return (p1 * w1 + p2 * w2) / total_weight

    def predict_match(self, home_expected_goals: float, away_expected_goals: float, match_data: Dict[str, Any] = None) -> Dict[str, float]:
        """
        Génère la prédiction finale combinée.
        Si le modèle XGBoost n'est pas encore entraîné/disponible (V1), il utilise 100% Poisson.
        """
        logger.debug("[Ensemble] Démarrage prédiction conjointe")
        
        # 1. Obtenir les prédictions de base via Poisson (couvre tous les marchés)
        poisson_preds = poisson_model.predict_match(home_expected_goals, away_expected_goals)
        
        # 2. Obtenir les prédictions XGBoost (si disponibles, couvrent principalement 1X2)
        xgb_preds = None
        if match_data and xgboost_model.model is not None:
            xgb_preds = xgboost_model.predict_match(match_data)
            
        final_preds = poisson_preds.copy()
        
        # 3. Combiner les prédictions si XGBoost est disponible
        if xgb_preds:
            logger.debug("[Ensemble] Modèle XGBoost actif : blending des prédictions (Poisson + XGBoost)")
            for key in ['1X2_1', '1X2_X', '1X2_2']:
                final_preds[key] = self._blend_probabilities(
                    poisson_preds[key], 
                    xgb_preds[key], 
                    self.poisson_weight, 
                    self.xgb_weight
                )
            
            # Recalcul de Double Chance et DNB avec les nouvelles probas 1X2
            final_preds['DOUBLE_CHANCE_1X'] = final_preds['1X2_1'] + final_preds['1X2_X']
            final_preds['DOUBLE_CHANCE_X2'] = final_preds['1X2_X'] + final_preds['1X2_2']
            final_preds['DOUBLE_CHANCE_12'] = final_preds['1X2_1'] + final_preds['1X2_2']
            
            base_12 = final_preds['1X2_1'] + final_preds['1X2_2']
            final_preds['DRAW_NO_BET_1'] = final_preds['1X2_1'] / base_12 if base_12 > 0 else 0
            final_preds['DRAW_NO_BET_2'] = final_preds['1X2_2'] / base_12 if base_12 > 0 else 0
        else:
            logger.debug("[Ensemble] Modèle XGBoost inactif : utilisation 100% Poisson")
            
        return final_preds

ensemble_model = EnsembleModel()
