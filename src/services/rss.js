const Parser = require('rss-parser');
const db = require('../db/database'); // Helper to access SQLite DB

// ── Default RSS feeds ────────────────────────────────────────────────────────
// International tech sources
const INTERNATIONAL_FEEDS = [
  { name: 'TechCrunch', url: 'https://techcrunch.com/feed/' },
  { name: 'The Verge', url: 'https://www.theverge.com/rss/index.xml' },
  { name: 'Ars Technica', url: 'https://feeds.arstechnica.com/arstechnica/index' },
  // Programming / development feeds
  { name: 'Hacker News', url: 'https://hnrss.org/frontpage' },
  { name: 'Dev.to', url: 'https://dev.to/feed' },
  { name: 'Node.js Blog', url: 'https://nodejs.org/en/feed/blog.xml' },
  { name: 'Python Software Foundation', url: 'https://feeds.feedburner.com/pythonsoftwarefoundation' },
  { name: 'PostgreSQL News', url: 'https://www.postgresql.org/rss/news.rss' },
  { name: 'Docker Blog', url: 'https://www.docker.com/feed' },
  { name: 'Rust Blog', url: 'https://blog.rust-lang.org/feed.xml' },
  { name: 'SQL Server Blog', url: 'https://feeds.feedburner.com/SQLServer' }
];

// Local / African tech sources (currently functional)
const LOCAL_FEEDS = [
  { name: 'Investir au Cameroun (TIC)', url: 'https://www.investiraucameroun.com/tic/feed' },
  { name: 'Digital Business Africa', url: 'https://www.digitalbusiness.africa/feed/' },
  { name: 'AITN (Afrique Innovation Tech)', url: 'https://aitn.africa/feed/' }
];

// Merge both arrays – order does not matter for deduplication
const DEFAULT_FEEDS = [...INTERNATIONAL_FEEDS, ...LOCAL_FEEDS];

class RssService {
  constructor() {
    this.parser = new Parser({
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      },
      timeout: 8000
    });
  }

  /**
   * Fetch recent articles from all configured RSS feeds.
   * Deduplicate using the `technews_history` table (last 7 days).
   * Insert fresh items into history for future runs.
   * @param {Array} feeds Optional custom feed list (defaults to DEFAULT_FEEDS)
   * @returns {Array} Up to 30 fresh article objects, newest first
   */
  async fetchTechNews(feeds = DEFAULT_FEEDS) {
    console.log('🔍 Début de la récupération des flux RSS tech...');
    const allItems = [];

    // 1️⃣ Collect items from each feed
    for (const feed of feeds) {
      try {
        console.log(`📡 Lecture du flux RSS: ${feed.name} (${feed.url})`);
        const feedData = await this.parser.parseURL(feed.url);
        if (feedData && feedData.items) {
          console.log(`${feedData.items.length} articles reçus de ${feed.name}`);
          for (const item of feedData.items) {
            allItems.push({
              source: feed.name,
              title: item.title,
              content: item.contentSnippet || item.content || '',
              link: item.link,
              pubDate: item.pubDate || item.isoDate || ''
            });
          }
        }
      } catch (e) {
        console.error(`⚠️ Erreur de lecture du flux ${feed.name}: ${e.message}`);
      }
    }

    if (allItems.length === 0) {
      console.warn('⚠️ Aucun article RSS récupéré de toutes les sources.');
      return [];
    }

    // 2️⃣ Sort by newest first
    allItems.sort((a, b) => new Date(b.pubDate) - new Date(a.pubDate));

    // 3️⃣ Load recent history (last 7 days) to filter duplicates
    const recent = db.getDb()
      .prepare('SELECT title, link FROM technews_history WHERE date >= date(\'now\', \'-7 days\')')
      .all();
    const seen = new Set(recent.map(r => `${r.title}@@${r.link}`));

    // 4️⃣ Keep only fresh items
    const fresh = allItems.filter(it => !seen.has(`${it.title}@@${it.link}`));

    // 5️⃣ Insert fresh items into history for future deduplication
    if (fresh.length > 0) {
      const insertStmt = db.getDb().prepare(
        'INSERT OR IGNORE INTO technews_history (date, title, link, source) VALUES (?, ?, ?, ?)'
      );
      const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
      const tx = db.getDb().transaction(() => {
        fresh.forEach(it => insertStmt.run(today, it.title, it.link, it.source));
      });
      tx();
    }

    // 6️⃣ Return up to 30 most recent fresh items
    return fresh.slice(0, 30);
  }
}

module.exports = new RssService();
