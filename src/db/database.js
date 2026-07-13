const path = require('path');
const fs = require('fs');
const { DatabaseSync } = require('node:sqlite');

const DB_DIR = path.join(__dirname, '..', '..', 'data');
const DB_PATH = path.join(DB_DIR, 'bot.db');

let db = null;

function initDatabase() {
  if (!fs.existsSync(DB_DIR)) {
    fs.mkdirSync(DB_DIR, { recursive: true });
  }

  try {
    db = new DatabaseSync(DB_PATH);
    
    // Create tables
    db.exec(`
      CREATE TABLE IF NOT EXISTS coupons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        contenu TEXT NOT NULL,
        matchs_json TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS technews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        contenu TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );

      CREATE TABLE IF NOT EXISTS technews_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        title TEXT NOT NULL,
        link TEXT NOT NULL,
        source TEXT,
        UNIQUE(title, link)
      );
    `);

    console.log('Base de données SQLite natif (node:sqlite) initialisée avec succès.');
  } catch (error) {
    console.error('Erreur lors de l\'initialisation de la base de données:', error.message);
    throw error;
  }
}

function getDb() {
  if (!db) {
    initDatabase();
  }
  return db;
}

// operations sur les coupons
function saveCoupon(date, contenu, matchsJson = null) {
  const connection = getDb();
  const stmt = connection.prepare(`
    INSERT OR REPLACE INTO coupons (date, contenu, matchs_json)
    VALUES (?, ?, ?)
  `);
  return stmt.run(date, contenu, matchsJson);
}

function getCoupon(date) {
  const connection = getDb();
  const stmt = connection.prepare(`
    SELECT * FROM coupons WHERE date = ?
  `);
  return stmt.get(date);
}

// operations sur les technews
function saveTechNews(date, contenu) {
  const connection = getDb();
  const stmt = connection.prepare(`
    INSERT OR REPLACE INTO technews (date, contenu)
    VALUES (?, ?)
  `);
  return stmt.run(date, contenu);
}

function getTechNews(date) {
  const connection = getDb();
  const stmt = connection.prepare(`
    SELECT * FROM technews WHERE date = ?
  `);
  return stmt.get(date);
}

// operations sur les subscribers
function addSubscriber(chatId, type = 'private') {
  const connection = getDb();
  const stmt = connection.prepare(`
    INSERT OR IGNORE INTO subscribers (chat_id, type)
    VALUES (?, ?)
  `);
  return stmt.run(String(chatId), type);
}

function getSubscribers() {
  const connection = getDb();
  const stmt = connection.prepare(`
    SELECT chat_id, type FROM subscribers
  `);
  return stmt.all();
}

function removeSubscriber(chatId) {
  const connection = getDb();
  const stmt = connection.prepare(`
    DELETE FROM subscribers WHERE chat_id = ?
  `);
  return stmt.run(String(chatId));
}

module.exports = {
  initDatabase,
  saveCoupon,
  getCoupon,
  saveTechNews,
  getTechNews,
  addSubscriber,
  getSubscribers,
  removeSubscriber,
  getDb
};
