// Renders the deposit card backgrounds for the bot and prints where the live values go:
// node render-deposit-bg.js <out dir>
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const SCALE = 1.5;
const out = process.argv[2] || path.join(__dirname, 'out', 'deposit');

(async () => {
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: SCALE });
  const layout = { scale: SCALE };
  for (const theme of ['emerald', 'gold']) {
    const q = theme === 'gold' ? '?bg=1&gold=1' : '?bg=1';
    await page.goto('file://' + path.join(__dirname, 'deposit-card.html') + q);
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(out, `${theme}.jpg`), type: 'jpeg', quality: 92 });
    console.log('rendered', theme);
  }
  Object.assign(layout, await page.evaluate(() => {
    const box = (el) => { const r = el.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height, right: r.right, bottom: r.bottom }; };
    const amount = document.querySelector('.amount');
    return {
      worker: box(document.getElementById('worker')),
      panel: box(document.querySelector('.panel')),
      when: box(document.getElementById('when')),
      amount: box(amount),
      amount_max_w: document.querySelector('.rc').getBoundingClientRect().right - 72 - amount.getBoundingClientRect().left,
      rows: [...document.querySelectorAll('dd')].map(box),
    };
  }));
  fs.writeFileSync(path.join(out, 'layout.json'), JSON.stringify(layout, null, 1));
  await browser.close();
})();
