// Renders a deposit card: node render-deposit.js amount=647 worker=lastsignal num=1284 ...
// Keys: amount worker num when method payout share today count goal top out
// tpl=b|c|d picks deposit-<tpl>.html (default: deposit.html)
const path = require('path');
const { chromium } = require('playwright');

const args = Object.fromEntries(process.argv.slice(2).map((a) => a.split(/=(.*)/s).slice(0, 2)));
const tpl = args.tpl ? `deposit-${args.tpl}.html` : 'deposit.html';
const out = args.out || path.join(__dirname, 'out', `deposit${args.tpl ? '-' + args.tpl : ''}-${args.num || 'card'}.png`);
delete args.out; delete args.tpl;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(__dirname, tpl) + '?' + new URLSearchParams(args));
  await page.evaluate(() => document.fonts.ready);
  const size = await page.evaluate(() => ({ width: document.body.offsetWidth, height: document.body.offsetHeight }));
  await page.setViewportSize(size);
  await page.screenshot({ path: out });
  console.log('rendered', out);
  await browser.close();
})();
