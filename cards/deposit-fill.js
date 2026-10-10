// Shared data binding for deposit-*.html variants. Any id that is missing in a variant is skipped.
// Query keys: amount worker num when method payout share today count goal top (name:sum,name:sum,...)
(() => {
  const fmt = (n) => {
    const [i, f] = Number(n).toFixed(2).split('.');
    return i.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + (f === '00' ? '' : '.' + f);
  };
  const $ = (id) => document.getElementById(id);
  const set = (id, v) => { if (v != null && $(id)) $(id).textContent = v; };
  const icons = { USDT: '₮', BTC: '₿', ETH: 'Ξ', TON: '◆', CARD: '▭' };

  window.fill = (d) => {
    if (d.amount != null) {
      set('amount', fmt(d.amount));
      const big = Number(d.amount) >= 1000;
      $('card').classList.toggle('gold', big);
      set('badge', big ? 'КРУПНЫЙ ДЕПОЗИТ' : 'НОВЫЙ ДЕПОЗИТ');
    }
    if (d.worker != null) { set('worker', d.worker); set('initials', d.worker.slice(0, 2).toUpperCase()); }
    if (d.num != null) set('num', '#' + d.num);
    set('when', d.when);
    if (d.method != null) {
      set('method', d.method);
      const m = d.method.split(' ')[0];
      set('mico', icons[m.toUpperCase()] || m[0]);
    }
    if (d.payout != null) set('payout', '$' + fmt(d.payout));
    if (d.share != null) set('share', d.share + '%');
    if (d.today != null) set('today', '$' + fmt(d.today));
    set('count', d.count);
    if (d.goal != null) set('goal', '$' + fmt(d.goal));
    if (d.today != null && d.goal != null && $('progress'))
      $('progress').style.width = Math.min(100, d.today / d.goal * 100) + '%';

    if (d.top != null && $('top')) {
      const rows = d.top.split(',').map((r) => r.split(':'));
      const max = Math.max(...rows.map(([, s]) => Number(s)));
      $('top').innerHTML = '';
      rows.forEach(([name, sum], i) => {
        const li = document.createElement('li');
        if (name === d.worker) li.className = 'me';
        li.innerHTML = '<span class="pos"></span><span class="n"></span><span class="s"></span><i><b></b></i>';
        li.querySelector('.pos').textContent = i + 1;
        li.querySelector('.n').textContent = name;
        li.querySelector('.s').textContent = '$' + fmt(sum);
        li.querySelector('b').style.width = (Number(sum) / max * 100) + '%';
        $('top').append(li);
      });
    }
  };
  window.fill(Object.fromEntries(new URLSearchParams(location.search)));
})();
