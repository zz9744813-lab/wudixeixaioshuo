const fs = require('fs');
const path = require('path');

const pagesDir = path.resolve(__dirname, '../src/pages');

const forbidden = [
  '页面开发中',
  '页面维护中',
  '敬请期待',
  'TODO 页面',
  'TODO: 页面',
  'Coming soon',
  'Under construction',
];

function walk(dir) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(full));
    } else if (/\.(jsx|tsx|js|ts)$/.test(entry.name)) {
      files.push(full);
    }
  }

  return files;
}

let failed = false;

for (const file of walk(pagesDir)) {
  const text = fs.readFileSync(file, 'utf8');
  for (const word of forbidden) {
    if (text.includes(word)) {
      console.error(`[placeholder-page] ${file} contains forbidden text: "${word}"`);
      failed = true;
    }
  }
}

if (failed) {
  console.error('\nPlaceholder page check FAILED. Fix the files above before committing.');
  process.exit(1);
}

console.log('No placeholder pages found.');
