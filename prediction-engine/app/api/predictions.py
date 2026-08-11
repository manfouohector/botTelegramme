from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from loguru import logger
from app.models.ensemble_model import ensemble_model
from app.llm_service.llm_client import llm_service

router = APIRouter(prefix="/predict", tags=["Predictions"])

class PredictionRequest(BaseModel):
    match_id: str = Field(..., description="ID externe du match")
    home_expected_goals: float = Field(..., description="xG calculés pour l'équipe à domicile")
    away_expected_goals: float = Field(..., description="xG calculés pour l'équipe à l'extérieur")
    match_data: Optional[Dict[str, Any]] = Field(None, description="Données brutes (stats, H2H, forme) pour XGBoost")

class PredictionResponse(BaseModel):
    match_id: str
    model_version: str
    probabilities: Dict[str, float]
    llm_explanation: Optional[str] = None

@router.post("/", response_model=PredictionResponse)
async def predict_match(request: PredictionRequest):
    """
    Reçoit les paramètres d'un match et retourne les probabilités des marchés de paris.
    Appelé par le backend Node.js.
    """
    logger.info(f"Requête de prédiction reçue pour match {request.match_id}")
    
    try:
        # Obtenir les probabilités via le modèle Ensemble
        probs = ensemble_model.predict_match(
            home_expected_goals=request.home_expected_goals,
            away_expected_goals=request.away_expected_goals,
            match_data=request.match_data
        )
        
        # Générer l'explication avec Groq/LLM
        match_str = f"Match ID {request.match_id}"
        explanation = llm_service.generate_explanation(match_str, probs)
        
        return PredictionResponse(
            match_id=request.match_id,
            model_version=ensemble_model.version,
            probabilities=probs,
            llm_explanation=explanation
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la prédiction pour le match {request.match_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
