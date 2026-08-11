import os
# pyrefly: ignore [missing-import]
from loguru import logger
# pyrefly: ignore [missing-import]
import groq

class LLMService:
    """
    Service LLM (Groq primaire, Gemini fallback).
    Rôle : 
    - Expliquer une prédiction en langage naturel pour les coupons Premium
    - (Optionnel) Extraire des infos non-structurées sur les blessures
    """
    
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.client = None
        
        if self.groq_api_key:
            try:
                self.client = groq.Groq(api_key=self.groq_api_key)
            except Exception as e:
                logger.error(f"[LLM] Erreur init Groq: {e}")
        else:
            logger.warning("[LLM] GROQ_API_KEY non définie, le service LLM est inactif.")

    def generate_explanation(self, match_str: str, prediction_data: dict) -> str:
        """
        Génère une phrase d'explication pour un pari.
        """
        if not self.client:
            return "Explication non disponible (LLM désactivé)."
            
        logger.debug(f"[LLM] Génération explication pour {match_str}")
        
        prompt = f"""
        Tu es un expert en paris sportifs. Explique brièvement en 1 ou 2 phrases percutantes pourquoi ce pari est intéressant, basé sur ces probabilités mathématiques :
        Match: {match_str}
        Probabilités: {prediction_data}
        Ne mentionne pas directement les pourcentages exacts, parle de la dynamique attendue (ex: "Match fermé attendu", "Domination locale probable").
        Réponds uniquement l'explication, sans introduction ni conclusion.
        """
        
        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-8b-8192",
                temperature=0.7,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"[LLM] Erreur lors de la génération: {e}")
            return "Explication non disponible suite à une erreur."

llm_service = LLMService()
