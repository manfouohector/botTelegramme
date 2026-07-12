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

  async summarizeTechNews(newsItems) {
    if (!this.groq) {
      throw new Error("Groq API n'est pas initialisé (clé d'API manquante).");
    }

    if (!newsItems || newsItems.length === 0) {
      return JSON.stringify([]);
    }

    const inputItems = newsItems.map((item, idx) => ({
      id: idx,
      source: item.source,
      title: item.title,
      content: item.content
    }));

    const systemPrompt = `Tu es un vulgarisateur et expert tech de haut niveau.
Voici une liste d'articles technologiques récents au format JSON.
Sélectionne les 5 actualités les plus importantes pour des développeurs ou utilisateurs passionnés de technologie.

Pour chaque actualité sélectionnée, tu dois :
1. Catégoriser l'article parmi les catégories suivantes : "IA", "Cybersécurité", "Frameworks Web", "Cloud", "DevOps", "Mobile", "Bases de données".
2. Traduire et adapter le titre en français.
3. Rédiger un résumé "TL;DR" en français de 3 lignes concises (chaque ligne doit être une phrase courte et informative).

Tu dois renvoyer obligatoirement un objet JSON contenant une clé "news" qui est un tableau d'objets. Chaque objet doit avoir la structure suivante :
- id : l'identifiant (nombre correspondant à l'id de l'article d'origine)
- category : la catégorie (string parmi la liste ci-dessus)
- title : le titre en français (string)
- tldr : le résumé TL;DR de 3 lignes (string avec des retours à la ligne ou une liste à puces)

Exemple de format attendu :
{
  "news": [
    {
      "id": 0,
      "category": "IA",
      "title": "Lancement de GPT-5 par OpenAI",
      "tldr": "- OpenAI annonce officiellement le lancement de son nouveau modèle de langage.\\n- Ce modèle offre des performances de raisonnement avancées et un support multimodal amélioré.\\n- Les développeurs peuvent y accéder dès aujourd'hui via l'API officielle."
    }
  ]
}

Le format de réponse DOIT être uniquement un objet JSON valide, sans markdown, sans \`\`\`json et sans texte avant ou après.`;

    const userPrompt = `Articles :\n${JSON.stringify(inputItems, null, 2)}`;

    try {
      const response = await this.groq.chat.completions.create({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        response_format: { type: 'json_object' },
        temperature: 0.3
      });

      const content = response.choices[0].message.content;
      const parsed = JSON.parse(content);
      
      const finalArticles = (parsed.news || []).map(item => {
        const original = newsItems[item.id] || {};
        return {
          category: item.category || 'Tech',
          title: item.title || original.title || 'Actualité',
          tldr: item.tldr || '',
          url: original.link || 'https://techcrunch.com'
        };
      });

      return JSON.stringify(finalArticles);
    } catch (error) {
      console.error('Erreur lors de la génération des actualités par Groq:', error.message);
      throw error;
    }
  }
  /**
   * Answers a free tech question from a Telegram user using Groq (fallback to Gemini)
   * @param {string} userQuestion The user's raw message text
   * @returns {{ isTech: boolean, answer: string }}
   */
  async answerTechQuestion(userQuestion) {
    if (!this.groq) {
      return { isTech: false, answer: null };
    }

    const systemPrompt = `Tu es un assistant technique expert et passionné de technologie. 
Un utilisateur t'a posé la question suivante en français.

Tu dois :
1. Déterminer si la question est liée à la technologie (IA, programmation, cybersécurité, cloud, DevOps, mobile, bases de données, réseaux, hardware, logiciels, frameworks, etc.).
2. Si oui : apporte une réponse claire, structurée et pédagogique en français. Formate la réponse pour Telegram en Markdown (*gras*, _italique_, etc.).
3. Si non : réponds UNIQUEMENT avec le JSON {"isTech":false}

Retourne TOUJOURS un objet JSON valide avec la structure suivante :
- {"isTech":true,"answer":"ta réponse en Markdown"} si c'est une question tech
- {"isTech":false} si ce n'est pas une question tech

Le JSON doit être la réponse entière, sans texte avant ou après.`;

    try {
      const response = await this.groq.chat.completions.create({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userQuestion }
        ],
        response_format: { type: 'json_object' },
        temperature: 0.4
      });

      const content = response.choices[0].message.content;
      const parsed = JSON.parse(content);
      return {
        isTech: parsed.isTech === true,
        answer: parsed.answer || null
      };
    } catch (error) {
      console.error('[GROQ] Erreur lors de la réponse à la question libre:', error.message);
      return { isTech: false, answer: null };
    }
  }
}

module.exports = new GroqService();
