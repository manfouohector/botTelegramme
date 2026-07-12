const Parser = require('rss-parser');

const DEFAULT_FEEDS = [
  // ── Sources internationales ──────────────────────────────────────────────
  { name: 'TechCrunch', url: 'https://techcrunch.com/feed/' },
  { name: 'The Verge', url: 'https://www.theverge.com/rss/index.xml' },
  { name: 'Ars Technica', url: 'https://feeds.arstechnica.com/arstechnica/index' },
  // ── Sources locales Cameroun / Afrique tech ──────────────────────────────
  { name: 'CamerounInfo (Tech)', url: 'https://www.camerouninfo.net/index.php?option=com_content&view=category&id=51&format=feed&type=rss' },
  { name: 'Cameroon-Info.Net', url: 'https://www.cameroon-info.net/rss/categorie/61/informatique.xml' },
  { name: '237online', url: 'https://www.237online.com/category/tech-et-innovation/feed/' },
  { name: 'TechAfrica', url: 'https://techafrique.com/feed/' },
  { name: 'Afrik21 (Numérique)', url: 'https://www.afrik21.africa/category/nouvelles-technologies/feed/' }
];

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
   * Fetches and compiles recent articles from RSS feeds
   * @param {Array} feeds Optional custom list of feeds
   */
  async fetchTechNews(feeds = DEFAULT_FEEDS) {
    console.log('Début de la récupération des flux RSS tech...');
    const allItems = [];

    for (const feed of feeds) {
      try {
        console.log(`Lecture du flux RSS: ${feed.name} (${feed.url})...`);
        const feedData = await this.parser.parseURL(feed.url);
        
        if (feedData && feedData.items) {
          console.log(`${feedData.items.length} articles récupérés de ${feed.name}`);
          
          for (const item of feedData.items) {
            allItems.push({
              source: feed.name,
              title: item.title,
              // Use contentSnippet as brief description, fallback to content
              content: item.contentSnippet || item.content || '',
              link: item.link,
              pubDate: item.pubDate || item.isoDate || ''
            });
          }
        }
      } catch (error) {
        // Log individual feed failures, but don't stop the whole process
        console.error(`Erreur lors de la lecture du flux RSS ${feed.name}:`, error.message);
      }
    }

    if (allItems.length === 0) {
      console.warn('Aucun article RSS récupéré de toutes les sources.');
      return [];
    }

    // Sort items by date descending (newest first)
    allItems.sort((a, b) => {
      const dateA = new Date(a.pubDate);
      const dateB = new Date(b.pubDate);
      // Handle invalid dates
      if (isNaN(dateA)) return 1;
      if (isNaN(dateB)) return -1;
      return dateB - dateA;
    });

    // Return the top 30 latest articles across all sources (inc. Cameroonian feeds)
    return allItems.slice(0, 30);
  }
}

module.exports = new RssService();
