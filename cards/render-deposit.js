// Renders a deposit card: node render-deposit.js amount=647 worker=lastsignal num=1284 ...
// Keys: amount worker num when method payout share today count goal out
const path = require('path');
const { chromium } = require('playwright');

const args = Object.fromEntries(process.argv.slice(2).map((a) => a.split(/=(.*)/s).slice(0, 2)));
const out = args.out || path.join(__dirname, 'out', `deposit-${args.num || 'card'}.png`);
delete args.out;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(__dirname, 'deposit.html') + '?' + new URLSearchParams(args));
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: out });
  console.log('rendered', out);
  await browser.close();
})();
