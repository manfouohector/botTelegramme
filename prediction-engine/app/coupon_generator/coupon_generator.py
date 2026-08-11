from typing import List, Dict, Any
from loguru import logger

class CouponGenerator:
    """
    Coupon Generator
    Prend les prédictions évaluées et les regroupe en différents tickets (Safe, Medium, High Odds).
    """
    def __init__(self):
        self.max_matches_per_coupon = 3
        
    def generate_coupons(self, evaluated_predictions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Génère les différents types de coupons.
        """
        logger.info("[CouponGenerator] Génération des coupons")
        
        # Filtre de base : exclure les paris suspects ou trop risqués
        valid_preds = [p for p in evaluated_predictions if not p.get('is_suspect', False)]
        
        # Tri par probabilité (décroissant pour safe, etc.)
        sorted_by_prob = sorted(valid_preds, key=lambda x: x.get('model_prob', 0), reverse=True)
        
        # 1. Ticket "Safe" (Confiance haute, petites cotes)
        safe_ticket = [p for p in sorted_by_prob if p.get('confidence') == 'haute'][:self.max_matches_per_coupon]
        
        # 2. Ticket "Medium" (Confiance moyenne, cotes value)
        medium_ticket = [p for p in sorted_by_prob if p.get('confidence') == 'moyenne' and p.get('is_value_bet')][:self.max_matches_per_coupon]
        
        # 3. Ticket "High Odds" (Confiance faible/moyenne, grosses cotes)
        high_odds_ticket = sorted([p for p in valid_preds if p.get('odds', 0) >= 2.0], key=lambda x: x.get('odds', 0), reverse=True)[:self.max_matches_per_coupon]
        
        coupons = {
            "safe": safe_ticket,
            "medium": medium_ticket,
            "high_odds": high_odds_ticket
        }
        
        logger.info(f"[CouponGenerator] Coupons générés: Safe({len(safe_ticket)}), Medium({len(medium_ticket)}), HighOdds({len(high_odds_ticket)})")
        
        return coupons

coupon_generator = CouponGenerator()
