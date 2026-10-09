// Renders one PNG card per label: node render.js
const path = require('path');
const { chromium } = require('playwright');

const cards = [
  ['tp', 'ТП'],
  ['zayavki', 'ЗАЯВКИ'],
  ['fony', 'ФОНЫ'],
  ['sms-bot', 'СМС БОТ'],
  ['all-dep', 'ALL DEP'],
];

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 1280 } });
  await page.goto('file://' + path.join(__dirname, 'template.html'));
  for (const [slug, label] of cards) {
    await page.evaluate((t) => { document.getElementById('label').textContent = t; }, label);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(__dirname, 'out', `${slug}.png`) });
    console.log('rendered', slug);
  }
  await browser.close();
})();
