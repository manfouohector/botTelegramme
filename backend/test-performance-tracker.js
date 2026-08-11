const { evaluateOutcome } = require('./src/services/performanceTracker');

console.log('🧪 TEST PERFORMANCE TRACKER LOGIC');
console.log('===================================');

const tests = [
  { outcome: '1X2_1', home: 2, away: 1, expected: true },
  { outcome: '1X2_1', home: 1, away: 1, expected: false },
  { outcome: '1X2_X', home: 0, away: 0, expected: true },
  { outcome: '1X2_2', home: 0, away: 3, expected: true },
  { outcome: 'BTTS_YES', home: 1, away: 1, expected: true },
  { outcome: 'BTTS_YES', home: 2, away: 0, expected: false },
  { outcome: 'OVER_2_5', home: 2, away: 1, expected: true },
  { outcome: 'OVER_2_5', home: 1, away: 1, expected: false },
  { outcome: 'DOUBLE_CHANCE_1X', home: 1, away: 1, expected: true },
  { outcome: 'DRAW_NO_BET_1', home: 2, away: 0, expected: true },
];

let passed = 0;
tests.forEach((t, i) => {
  const result = evaluateOutcome(t.outcome, t.home, t.away);
  const ok = result === t.expected;
  if (ok) passed++;
  console.log(`Test ${i + 1} [${t.outcome} pour ${t.home}-${t.away}]: ${ok ? '✅ PASS' : '❌ FAIL'}`);
});

console.log(`\nResultat: ${passed}/${tests.length} tests reussis.`);
if (passed === tests.length) {
  console.log('SUCCESS: Le module Performance Tracker est valide.');
} else {
  console.error('ERROR: Des tests ont echoue.');
  process.exit(1);
}
