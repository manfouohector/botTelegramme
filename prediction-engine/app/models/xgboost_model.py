import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional
from loguru import logger
import xgboost as xgb

class XGBoostModel:
    """
    Modèle de Machine Learning basé sur XGBoost.
    Utilisé pour prédire l'issue du match (1X2) à partir des statistiques historiques
    (forme, face-à-face, domicile/extérieur, classements...).
    """
    
    def __init__(self, model_dir: str = "./app/models/saved"):
        self.version = "1.0"
        self.name = "xgboost"
        self.model_dir = model_dir
        self.model = None
        
        # Le modèle sera chargé plus tard s'il existe (non bloquant en V1 si pas encore entraîné)
        self._load_model()
        
    def _load_model(self):
        """Tente de charger le modèle XGBoost entraîné depuis le disque."""
        model_path = os.path.join(self.model_dir, f"xgb_{self.version}.joblib")
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                logger.info(f"[XGBoost] Modèle v{self.version} chargé avec succès.")
            except Exception as e:
                logger.error(f"[XGBoost] Erreur lors du chargement du modèle: {e}")
        else:
            logger.warning(f"[XGBoost] Modèle v{self.version} non trouvé à {model_path}. "
                           "Le modèle ML est inactif (besoin d'entraînement).")

    def extract_features(self, match_data: Dict[str, Any]) -> pd.DataFrame:
        """
        Extrait les features pertinentes depuis les données brutes du match.
        (À enrichir avec les données de l'API-Football).
        """
        # Pour la V1 et avant l'entraînement, on simule une extraction basique
        features = {
            'home_win_streak': match_data.get('home_form', {}).get('win_streak', 0),
            'away_win_streak': match_data.get('away_form', {}).get('win_streak', 0),
            'home_goals_avg_for': match_data.get('home_stats', {}).get('goals_avg_for', 1.0),
            'away_goals_avg_for': match_data.get('away_stats', {}).get('goals_avg_for', 1.0),
            'home_goals_avg_against': match_data.get('home_stats', {}).get('goals_avg_against', 1.0),
            'away_goals_avg_against': match_data.get('away_stats', {}).get('goals_avg_against', 1.0),
            'h2h_home_wins': match_data.get('h2h', {}).get('home_wins', 0),
            'h2h_away_wins': match_data.get('h2h', {}).get('away_wins', 0),
        }
        return pd.DataFrame([features])

    def predict_match(self, match_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Prédit les probabilités 1X2 pour un match.
        :param match_data: Dictionnaire contenant les stats du match
        :return: Dictionnaire des probabilités ou None si le modèle n'est pas chargé
        """
        if self.model is None:
            logger.debug("[XGBoost] Modèle non disponible pour la prédiction.")
            return None
            
        try:
            features_df = self.extract_features(match_data)
            # Prédiction des probabilités (classes : 0=Home, 1=Draw, 2=Away par exemple)
            # xgb_model.predict_proba retourne typiquement un array 2D
            probs = self.model.predict_proba(features_df)[0]
            
            # Assumons l'ordre des classes : 0 -> 1, 1 -> X, 2 -> 2
            return {
                '1X2_1': float(probs[0]),
                '1X2_X': float(probs[1]),
                '1X2_2': float(probs[2])
            }
        except Exception as e:
            logger.error(f"[XGBoost] Erreur lors de la prédiction: {e}")
            return None

xgboost_model = XGBoostModel()
