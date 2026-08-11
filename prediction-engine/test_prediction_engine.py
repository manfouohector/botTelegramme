import asyncio
from app.models.poisson_model import poisson_model
from app.models.xgboost_model import xgboost_model
from app.models.ensemble_model import ensemble_model

def test_models():
    print("--- Test des Modeles du Prediction Engine ---\n")
    
    home_xg = 1.8
    away_xg = 1.2
    
    print(f"--- Modèle Poisson (xG Home: {home_xg}, xG Away: {away_xg}) ---")
    poisson_preds = poisson_model.predict_match(home_xg, away_xg)
    for k, v in poisson_preds.items():
        if "1X2" in k or "BTTS" in k or "OVER" in k:
            print(f"{k}: {v:.2%}")
            
    print("\n--- Modèle XGBoost ---")
    print(f"Modèle chargé: {xgboost_model.model is not None}")
    
    print("\n--- Modèle Ensemble ---")
    ensemble_preds = ensemble_model.predict_match(home_xg, away_xg, match_data={})
    for k, v in ensemble_preds.items():
        if "1X2" in k or "BTTS" in k or "OVER" in k:
            print(f"{k}: {v:.2%}")
            
    print("\nSUCCESS: Test reussi.")

if __name__ == "__main__":
    test_models()
