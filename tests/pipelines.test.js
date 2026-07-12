const test = require('node:test');
const assert = require('node:assert');
const db = require('../src/db/database');
const pipeline = require('../src/services/pipeline');

// Import services to mock
const footballService = require('../src/services/football');
const groqService = require('../src/services/groq');
const geminiService = require('../src/services/gemini');
const rssService = require('../src/services/rss');

test('Pipelines Orchestration Test Suite', async (t) => {
  db.initDatabase();

  const dummyDate = '2099-12-31'; // Future date for testing

  const cleanUp = () => {
    const sqlite = db.getDb();
    sqlite.prepare('DELETE FROM coupons WHERE date = ?').run(dummyDate);
    sqlite.prepare('DELETE FROM technews WHERE date = ?').run(dummyDate);
  };

  cleanUp();

  await t.test('Football prediction pipeline - Success flow', async (t) => {
    // 1. Mock footballService to return 1 match
    t.mock.method(footballService, 'getEnrichedMatches', async (date) => {
      return [
        {
          id: 101,
          competition: { name: 'Premier League', code: 'PL' },
          homeTeam: { name: 'Arsenal', position: 1, form: 'W,W,W' },
          awayTeam: { name: 'Chelsea', position: 10, form: 'L,D,L' }
        }
      ];
    });

    // 2. Mock Groq selection
    t.mock.method(groqService, 'selectTopMatches', async (matches) => {
      return {
        selected_matches: [
          {
            match_id: 101,
            home_team: 'Arsenal',
            away_team: 'Chelsea',
            competition: 'Premier League',
            confidence_score: 90,
            bet_type: 'Victoire Arsenal',
            reasoning_brief: 'Arsenal est en pleine forme.'
          }
        ]
      };
    });

    // 3. Mock Gemini analysis
    t.mock.method(geminiService, 'analyzeMatch', async (match) => {
      return 'Analyse détaillée Gemini pour Arsenal vs Chelsea.';
    });

    // 4. Mock Groq final coupon formatting
    t.mock.method(groqService, 'generateFinalCoupon', async (analyses) => {
      return '⚽ COUPON DU JOUR ⚽\n- Arsenal gagne contre Chelsea (90%)\nBonne chance !';
    });

    // Run the pipeline
    const result = await pipeline.runFootballPipeline(dummyDate);

    // Assertions
    assert.ok(result);
    assert.strictEqual(result.matches.length, 1);
    assert.strictEqual(result.matches[0].home_team, 'Arsenal');
    assert.ok(result.coupon.includes('COUPON DU JOUR'));

    // Check DB
    const saved = db.getCoupon(dummyDate);
    assert.ok(saved);
    assert.strictEqual(saved.contenu, result.coupon);
    assert.ok(saved.matchs_json.includes('Arsenal'));
  });

  await t.test('Football prediction pipeline - Empty matches handling', async (t) => {
    // Mock to return empty matches
    t.mock.method(footballService, 'getEnrichedMatches', async (date) => {
      return [];
    });

    const result = await pipeline.runFootballPipeline(dummyDate);

    assert.ok(result);
    assert.strictEqual(result.matches.length, 0);
    assert.ok(result.coupon.includes("Aucun match n'est programmé aujourd'hui"));

    const saved = db.getCoupon(dummyDate);
    assert.ok(saved);
    assert.ok(saved.contenu.includes("Aucun match n'est programmé aujourd'hui"));
  });

  await t.test('Tech news pipeline - Success flow', async (t) => {
    // 1. Mock RSS feed fetching
    t.mock.method(rssService, 'fetchTechNews', async () => {
      return [
        { source: 'TechCrunch', title: 'New AI model', content: 'Groq released Llama 3', link: 'link' }
      ];
    });

    // 2. Mock Groq news summarizer
    t.mock.method(groqService, 'summarizeTechNews', async (items) => {
      return '📰 ACTUALITÉS TECH 📰\n- Lancement du nouveau modèle IA de Groq...';
    });

    const result = await pipeline.runTechNewsPipeline(dummyDate);

    assert.ok(result);
    assert.ok(result.news.includes('ACTUALITÉS TECH'));

    // Check DB
    const saved = db.getTechNews(dummyDate);
    assert.ok(saved);
    assert.strictEqual(saved.contenu, result.news);
  });

  cleanUp();
});
