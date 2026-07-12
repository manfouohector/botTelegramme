const Groq = require('groq-sdk');

class GroqService {
  constructor() {
    this.apiKey = process.env.GROQ_API_KEY;
    this.model = process.env.GROQ_MODEL || 'llama-3.1-8b-instant';
    if (this.apiKey) {
      this.groq = new Groq({ apiKey: this.apiKey });
    } else {
      console.warn("Warning: GROQ_API_KEY n'est pas configuré.");
    }
  }

  /**
   * Selects 3 to 5 predictable matches from a list of enriched matches
   * @param {Array} matches Enriched matches list
   */
  async selectTopMatches(matches) {
    if (!this.groq) {
      throw new Error("Groq API n'est pas initialisé (clé d'API manquante).");
    }

    if (!matches || matches.length === 0) {
      return { selected_matches: [] };
    }

    const systemPrompt = `Tu es un analyste de football professionnel et expert en pronostics sportifs.
Voici la liste des matchs de football programmés aujourd'hui avec le classement et la forme récente (5 derniers matchs) de chaque équipe.

Identifie entre 3 et 5 matchs dont le résultat te semble le plus probable et prévisible.
Retourne uniquement un objet JSON valide contenant une clé "selected_matches" qui est un tableau d'objets. Chaque objet doit contenir EXACTEMENT les clés suivantes :
- match_id : l'ID du match (nombre)
- home_team : le nom de l'équipe à domicile (string)
- away_team : le nom de l'équipe à l'extérieur (string)
- competition : le nom de la compétition (string)
- confidence_score : un score de confiance de 1 à 100 (nombre)
- bet_type : le type de pari suggéré en français (ex: "Victoire de Arsenal", "Plus de 2.5 buts", "Les deux équipes marquent")
- reasoning_brief : une phrase rapide résumant la raison de ce choix.

Le format de réponse DOIT être uniquement un objet JSON valide, sans markdown, sans \`\`\`json et sans texte avant ou après.`;

    const userPrompt = `Matchs du jour :\n${JSON.stringify(matches, null, 2)}`;

    try {
      const response = await this.groq.chat.completions.create({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        response_format: { type: 'json_object' },
        temperature: 0.2
      });

      const content = response.choices[0].message.content;
      return JSON.parse(content);
    } catch (error) {
      console.error('Erreur lors du tri Groq:', error.message);
      throw error;
    }
  }

  /**
   * Generates the final coupon formatted for Telegram using detailed Gemini analysis
   * @param {Array} analyses Selected matches with Gemini research details
   */
  async generateFinalCoupon(analyses) {
    if (!this.groq) {
      throw new Error("Groq API n'est pas initialisé (clé d'API manquante).");
    }

    if (!analyses || analyses.length === 0) {
      return "Désolé, aucun coupon n'a pu être généré aujourd'hui.";
    }

    const systemPrompt = `Tu es un pronostiqueur de football professionnel. Tu dois créer un coupon de pronostics quotidien en français pour un bot Telegram.
Voici les analyses détaillées de chaque match sélectionné :
${JSON.stringify(analyses, null, 2)}

Génère un message complet, engageant et clair, formaté pour Telegram.
Règles de style :
- Utilise des émojis pour rendre le message attractif (ex: ⚽, 🏆, 🔥, 📊, 📝).
- Mets en valeur les noms d'équipes et les championnats.
- Affiche le pronostic conseillé (avec type de pari et confiance) et un résumé synthétique de l'analyse pour chaque match.
- Ajoute obligatoirement à la fin un avertissement (warning) rappelant que les paris sportifs comportent des risques, que ce sont des estimations probabilistes et non des garanties de gain, et d'être responsable.
- Reste synthétique et clair pour respecter la limite de message Telegram (4096 caractères).`;

    try {
      const response = await this.groq.chat.completions.create({
        model: this.model,
        messages: [
          { role: 'user', content: systemPrompt }
        ],
        temperature: 0.7
      });

      return response.choices[0].message.content;
    } catch (error) {
      console.error('Erreur lors du formatage final du coupon par Groq:', error.message);
      throw error;
    }
  }

  /**
   * Selects and summarizes 5 tech news items from parsed RSS feed
   * @param {Array} newsItems RSS parsed news items
   */
  async summarizeTechNews(newsItems) {
    if (!this.groq) {
      throw new Error("Groq API n'est pas initialisé (clé d'API manquante).");
    }

    if (!newsItems || newsItems.length === 0) {
      return "Aucune actualité technologique n'est disponible aujourd'hui.";
    }

    const systemPrompt = `Tu es un vulgarisateur et expert tech de haut niveau. Voici une liste d'articles technologiques récents issus de flux RSS :
${JSON.stringify(newsItems, null, 2)}

Sélectionne les 5 actualités les plus importantes pour des développeurs ou utilisateurs passionnés de technologie.
Pour chacune des 5 actualités sélectionnées, explique-la en français de manière claire et pédagogique en 3-4 phrases en respectant la structure suivante :
1. Ce qui s'est passé (le fait d'actualité).
2. Pourquoi c'est important (la portée technique ou stratégique).
3. L'impact concret pour un développeur ou un utilisateur tech.

Formate le tout sous forme de message Telegram attrayant avec des émojis, des titres clairs en gras pour chaque actualité, et une séparation nette entre les sujets.
Ajoute un titre principal accrocheur (ex: "📰 TECH NEWS DU JOUR 📰") au tout début.
Ne mets pas de blabla d'introduction ou de conclusion inutile, va droit au but.`;

    try {
      const response = await this.groq.chat.completions.create({
        model: this.model,
        messages: [
          { role: 'user', content: systemPrompt }
        ],
        temperature: 0.5
      });

      return response.choices[0].message.content;
    } catch (error) {
      console.error('Erreur lors de la génération des actualités par Groq:', error.message);
      throw error;
    }
  }
}

module.exports = new GroqService();
