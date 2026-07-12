const test = require('node:test');
const assert = require('node:assert');
const db = require('../src/db/database');

// Import commands
const startCmd = require('../src/commands/start');
const aideCmd = require('../src/commands/aide');
const couponCmd = require('../src/commands/coupon');
const matchsCmd = require('../src/commands/matchs');
const technewsCmd = require('../src/commands/technews');

function getLocalDateString() {
  const d = new Date();
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

test('Bot Commands Test Suite', async (t) => {
  db.initDatabase();

  const todayStr = getLocalDateString();
  const testChatId = '88888888';

  // Helper to create mocked ctx
  const createMockCtx = (chatId, chatType = 'private') => {
    const replies = [];
    return {
      chat: { id: chatId, type: chatType },
      replies,
      async reply(text, options) {
        replies.push({ text, options });
        return { message_id: 1 };
      },
      async replyWithMarkdown(text, options) {
        replies.push({ text, options, markdown: true });
        return { message_id: 1 };
      }
    };
  };

  // Clean test user and content
  const cleanDb = () => {
    const sqlite = db.getDb();
    sqlite.prepare('DELETE FROM subscribers WHERE chat_id = ?').run(testChatId);
    sqlite.prepare('DELETE FROM coupons WHERE date = ?').run(todayStr);
    sqlite.prepare('DELETE FROM technews WHERE date = ?').run(todayStr);
  };

  cleanDb();

  await t.test('/start command should register subscriber and send welcome message', async () => {
    const ctx = createMockCtx(testChatId);
    await startCmd(ctx);

    // Verify reply
    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes('Bienvenue'));

    // Verify user is registered in db
    const subs = db.getSubscribers();
    const found = subs.find(s => s.chat_id === testChatId);
    assert.ok(found);
    assert.strictEqual(found.type, 'private');
  });

  await t.test('/aide command should display command list', async () => {
    const ctx = createMockCtx(testChatId);
    await aideCmd(ctx);

    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes('Liste des commandes'));
  });

  await t.test('/coupon command - when not generated yet', async () => {
    const ctx = createMockCtx(testChatId);
    await couponCmd(ctx);

    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes("Le coupon du jour n'est pas encore prêt"));
  });

  await t.test('/coupon command - when generated', async () => {
    // Save dummy coupon in database
    db.saveCoupon(todayStr, '⚽ PAYS-BAS - FRANCE : Victoire France', JSON.stringify([]));

    const ctx = createMockCtx(testChatId);
    await couponCmd(ctx);

    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes('PAYS-BAS'));
  });

  await t.test('/matchs command - when not generated', async () => {
    // Delete today's coupon
    const sqlite = db.getDb();
    sqlite.prepare('DELETE FROM coupons WHERE date = ?').run(todayStr);

    const ctx = createMockCtx(testChatId);
    await matchsCmd(ctx);

    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes("Aucun match n'a été analysé"));
  });

  await t.test('/matchs command - when generated', async () => {
    const matchesList = [
      {
        match_id: 1,
        home_team: 'Belgique',
        away_team: 'Italie',
        competition: 'Euro 2024',
        confidence_score: 75,
        bet_type: 'Victoire Belgique',
        reasoning_brief: 'À domicile.'
      }
    ];

    db.saveCoupon(todayStr, 'Dummy Coupon text', JSON.stringify(matchesList));

    const ctx = createMockCtx(testChatId);
    await matchsCmd(ctx);

    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes('Matchs analysés aujourd\'hui'));
    assert.ok(ctx.replies[0].text.includes('Belgique vs Italie'));
  });

  await t.test('/technews command - when not generated yet', async () => {
    const ctx = createMockCtx(testChatId);
    await technewsCmd(ctx);

    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes("L'actualité tech d'aujourd'hui n'est pas encore prête"));
  });

  await t.test('/technews command - when generated', async () => {
    db.saveTechNews(todayStr, '📰 Tech News : Apple sort son nouveau casque');

    const ctx = createMockCtx(testChatId);
    await technewsCmd(ctx);

    assert.strictEqual(ctx.replies.length, 1);
    assert.ok(ctx.replies[0].text.includes('Apple sort son nouveau casque'));
  });

  cleanDb();
});
