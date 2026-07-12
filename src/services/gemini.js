const { GoogleGenerativeAI } = require('@google/generative-ai');

class GeminiService {
  constructor() {
    this.apiKey = process.env.GEMINI_API_KEY;
    this.modelName = process.env.GEMINI_MODEL || 'gemini-1.5-flash';
    if (this.apiKey) {
      this.genAI = new GoogleGenerativeAI(this.apiKey);
      // Initialize the model with Google Search grounding enabled
      this.model = this.genAI.getGenerativeModel({
        model: this.modelName,
        tools: [{ googleSearch: {} }]
      });
    } else {
      console.warn("Warning: GEMINI_API_KEY n'est pas configuré.");
    }
  }

  /**
   * Performs deep analysis of a match using Google Search grounding
   * @param {Object} match Selected match from Groq selection
   */
  async analyzeMatch(match) {
    if (!this.model) {
      console.warn("Gemini model n'est pas initialisé (clé manquante). Utilisation du fallback.");
      return this.getFallbackAnalysis(match);
    }

    const prompt = `Fais une recherche web sur le match de football "${match.home_team} vs ${match.away_team}" dans le championnat "${match.competition}" qui se joue très prochainement ou aujourd'hui.
Recherche les informations récentes et fiables suivantes :
1. Compositions probables des deux équipes.
2. Absences majeures (blessés, suspendus de dernière minute).
3. Forme récente et dynamique des deux équipes.
4. Contexte du match et motivation (lutte pour le titre, maintien, derby, fatigue suite à d'autres coupes).

Fais une synthèse structurée et concise en français (environ 150-200 mots) de tes trouvailles pour ce match.
Termine par une conclusion rapide en français sur la cohérence du pronostic envisagé : "${match.bet_type}".`;

    try {
      console.log(`Gemini analyse le match: ${match.home_team} vs ${match.away_team} avec Search Grounding...`);
      const result = await this.model.generateContent(prompt);
      const response = await result.response;
      
      let text = response.text();
      
      // Attempt to extract citations/sources if grounding metadata is available
      try {
        const candidate = response.candidates && response.candidates[0];
        const groundingMetadata = candidate && candidate.groundingMetadata;
        if (groundingMetadata && groundingMetadata.groundingChunks) {
          const sources = groundingMetadata.groundingChunks
            .map(chunk => {
              if (chunk.web && chunk.web.uri) {
                return `[${chunk.web.title || 'Source'}](${chunk.web.uri})`;
              }
              return null;
            })
            .filter(Boolean);
          
          const uniqueSources = [...new Set(sources)];
          if (uniqueSources.length > 0) {
            text += `\n\n*Sources consultées :*\n- ${uniqueSources.join('\n- ')}`;
          }
        }
      } catch (metadataError) {
        // Logging metadata parsing issues, but do not fail the request
        console.warn('Erreur lors de la lecture des métadonnées de grounding:', metadataError.message);
      }

      return text;
    } catch (error) {
      console.error(`Erreur lors de l'analyse Gemini pour ${match.home_team} vs ${match.away_team}:`, error.message);
      // Return a fallback analysis based on the brief reasoning from Groq
      return this.getFallbackAnalysis(match);
    }
  }

  /**
   * Fallback method if Gemini API call fails or key is missing
   */
  getFallbackAnalysis(match) {
    return `Analyse pour ${match.home_team} vs ${match.away_team} (${match.competition}) :
- Pronostic suggéré : ${match.bet_type}
- Confiance : ${match.confidence_score}%
- Contexte : ${match.reasoning_brief || 'Aucune information supplémentaire disponible.'}
- Note : L'analyse en ligne n'a pas pu être effectuée en raison d'une indisponibilité technique de l'API de recherche.`;
  }
}

module.exports = new GeminiService();
