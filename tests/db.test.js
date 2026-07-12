const test = require('node:test');
const assert = require('node:assert');
const db = require('../src/db/database');

test('Database Test Suite', async (t) => {
  // Initialisation
  db.initDatabase();

  const dummyDate = '2000-01-01';
  const dummyChatId = '12345678999';

  // Nettoyage initial de sécurité
  const cleanUp = () => {
    const sqlite = db.getDb();
    sqlite.prepare('DELETE FROM coupons WHERE date = ?').run(dummyDate);
    sqlite.prepare('DELETE FROM technews WHERE date = ?').run(dummyDate);
    sqlite.prepare('DELETE FROM subscribers WHERE chat_id = ?').run(dummyChatId);
  };

  cleanUp();

  await t.test('Should save and retrieve a coupon', () => {
    const couponContent = '⚽ Pronostic test de football';
    const matchesJson = JSON.stringify([{ match_id: 1, home: 'A', away: 'B' }]);

    db.saveCoupon(dummyDate, couponContent, matchesJson);
    const retrieved = db.getCoupon(dummyDate);

    assert.ok(retrieved);
    assert.strictEqual(retrieved.date, dummyDate);
    assert.strictEqual(retrieved.contenu, couponContent);
    assert.strictEqual(retrieved.matchs_json, matchesJson);
  });

  await t.test('Should save and retrieve tech news', () => {
    const newsContent = '📰 Tech News test content';

    db.saveTechNews(dummyDate, newsContent);
    const retrieved = db.getTechNews(dummyDate);

    assert.ok(retrieved);
    assert.strictEqual(retrieved.date, dummyDate);
    assert.strictEqual(retrieved.contenu, newsContent);
  });

  await t.test('Should manage subscribers', () => {
    // 1. Ajouter un abonné
    db.addSubscriber(dummyChatId, 'private');
    let subscribers = db.getSubscribers();
    let found = subscribers.find(s => s.chat_id === dummyChatId);
    assert.ok(found);
    assert.strictEqual(found.type, 'private');

    // 2. Ignorer les doublons (INSERT IGNORE)
    db.addSubscriber(dummyChatId, 'group'); // Devrait être ignoré car déjà présent
    subscribers = db.getSubscribers();
    found = subscribers.find(s => s.chat_id === dummyChatId);
    assert.strictEqual(found.type, 'private'); // N'a pas changé

    // 3. Supprimer un abonné
    db.removeSubscriber(dummyChatId);
    subscribers = db.getSubscribers();
    found = subscribers.find(s => s.chat_id === dummyChatId);
    assert.strictEqual(found, undefined);
  });

  // Nettoyage final
  cleanUp();
});
