const test = require('node:test');
const assert = require('node:assert');
const rssService = require('../src/services/rss');

test('RSS Service Unit Test Suite', async (t) => {
  
  await t.test('Should fetch and aggregate items from all active feeds', async (t) => {
    // Mock parsers parsing method to return mock articles
    t.mock.method(rssService.parser, 'parseURL', async (url) => {
      if (url.includes('techcrunch')) {
        return {
          items: [
            { title: 'TechCrunch Article', contentSnippet: 'TechCrunch desc', link: 'tc-link', pubDate: 'Sun, 12 Jul 2026 05:00:00 GMT' }
          ]
        };
      }
      if (url.includes('theverge')) {
        return {
          items: [
            { title: 'The Verge Article', contentSnippet: 'Verge desc', link: 'verge-link', pubDate: 'Sun, 12 Jul 2026 04:00:00 GMT' }
          ]
        };
      }
      if (url.includes('arstechnica')) {
        return {
          items: [
            { title: 'Ars Technica Article', contentSnippet: 'Ars desc', link: 'ars-link', pubDate: 'Sun, 12 Jul 2026 06:00:00 GMT' }
          ]
        };
      }
      return { items: [] };
    });

    const news = await rssService.fetchTechNews();

    // Verify we aggregated 3 articles (1 from each feed)
    assert.strictEqual(news.length, 3);
    
    // Verify sorting by pubDate descending (newest first: Ars Technica 6h00 -> TechCrunch 5h00 -> The Verge 4h00)
    assert.strictEqual(news[0].source, 'Ars Technica');
    assert.strictEqual(news[0].title, 'Ars Technica Article');
    
    assert.strictEqual(news[1].source, 'TechCrunch');
    assert.strictEqual(news[1].title, 'TechCrunch Article');
    
    assert.strictEqual(news[2].source, 'The Verge');
    assert.strictEqual(news[2].title, 'The Verge Article');
  });

  await t.test('Should handle individual feed failures gracefully', async (t) => {
    t.mock.method(rssService.parser, 'parseURL', async (url) => {
      if (url.includes('techcrunch')) {
        throw new Error('Network timeout');
      }
      if (url.includes('theverge')) {
        return {
          items: [
            { title: 'The Verge Article', contentSnippet: 'Verge desc', link: 'verge-link', pubDate: 'Sun, 12 Jul 2026 04:00:00 GMT' }
          ]
        };
      }
      return { items: [] };
    });

    const news = await rssService.fetchTechNews();

    // Verification: TechCrunch failed but pipeline continued and returned The Verge article
    assert.strictEqual(news.length, 1);
    assert.strictEqual(news[0].source, 'The Verge');
    assert.strictEqual(news[0].title, 'The Verge Article');
  });
});
