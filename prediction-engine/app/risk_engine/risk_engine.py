from typing import Dict, Any, List
from loguru import logger

class RiskEngine:
    """
    Risk Engine
    Évalue le risque associé à une prédiction en fonction de plusieurs critères:
    - Écart avec le marché (suspect si > 20%)
    - Facteurs externes (Derby, Coupe, etc.)
    - Fiabilité des données (compos probables vs officielles)
    
    Attribue un niveau de confiance : Haute (Safe), Moyenne (Medium), Faible (High Odds / Risky).
    """
    def __init__(self):
        self.version = "1.0"
        
    def evaluate_risk(self, prediction_data: Dict[str, Any], match_context: Dict[str, Any] = None) -> str:
        """
        Évalue le risque et retourne le niveau de confiance.
        :param prediction_data: Dict contenant 'is_suspect', 'model_prob', etc.
        :param match_context: Dict contenant infos sur derby, enjeu, etc.
        :return: 'haute', 'moyenne' ou 'faible'
        """
        logger.debug("[RiskEngine] Évaluation du risque")
        
        confidence = "moyenne" # Par défaut
        risk_flags = []
        
        # 1. Vérification des données suspectes
        if prediction_data.get('is_suspect', False):
            risk_flags.append("Écart suspect avec le marché (>20%)")
            confidence = "faible"
            
        # 2. Contexte du match (ex: Derby, Coupe de la Ligue = + de risque)
        if match_context:
            if match_context.get('is_derby', False):
                risk_flags.append("Derby (imprévisible)")
                if confidence == "haute": confidence = "moyenne"
            
            if match_context.get('competition_type') == 'cup':
                risk_flags.append("Match de coupe (turnover fréquent)")
                if confidence == "haute": confidence = "moyenne"
                
        # 3. Fiabilité de la prédiction (probabilité de base)
        base_prob = prediction_data.get('model_prob', 0.0)
        if base_prob > 0.70 and not risk_flags:
            confidence = "haute"
        elif base_prob < 0.40:
            confidence = "faible"
            
        logger.info(f"[RiskEngine] Confiance évaluée : {confidence} | Flags: {risk_flags}")
        
        return confidence, risk_flags

risk_engine = RiskEngine()
