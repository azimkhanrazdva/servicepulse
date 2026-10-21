/* Inspect presentation nodes, never translate API identifiers or user-owned data. */
const fs = require('node:fs');
const path = require('node:path');
const ts = require('../frontend/node_modules/typescript');
const allowed = /\b(?:ServicePulse|HTTP|HTTPS|API|URL|SSE|SMTP|Mailpit|PostgreSQL|UTC|UP|DOWN|UNKNOWN|PAUSED|OPEN|CLOSED|ACTIVE|UPCOMING|ENDED|ID|slug|v\d+)\b/g;
const leftovers = [];
let checked = 0;
for (const file of fs.readdirSync('frontend/src').filter(n => n.endsWith('.tsx') && !n.includes('.test.'))) {
  const source = ts.createSourceFile(file, fs.readFileSync(path.join('frontend/src', file), 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  function visit(n) {
    let value;
    if (ts.isJsxText(n)) value = n.text;
    else if (ts.isJsxAttribute(n) && ['aria-label', 'placeholder', 'title'].includes(n.name.getText(source)) && n.initializer && ts.isStringLiteral(n.initializer)) value = n.initializer.text;
    if (value !== undefined) {
      checked++;
      const remainder = value.replace(/https?:\/\/\S+/g, '').replace(allowed, '');
      if (/[A-Za-z]/.test(remainder)) leftovers.push({file, text: value.trim()});
    }
    ts.forEachChild(n, visit);
  }
  visit(source);
}
for (const name of ['index.html', 'public.html']) {
  if (!fs.readFileSync('frontend/' + name, 'utf8').includes('lang="ru"')) throw Error(name + ': expected Russian language');
}
const report = {checked_at: new Date().toISOString(), checked_nodes: checked, untranslated_presentation_nodes: leftovers, scope: 'JSX static text and accessibility labels; protocol names allowlisted, arbitrary user data retained. Dynamic branches covered by component/browser tests.', status: leftovers.length ? 'FAIL' : 'PASS'};
fs.writeFileSync('artifacts/ru-ui-audit.json', JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
if (leftovers.length) process.exitCode = 1;
