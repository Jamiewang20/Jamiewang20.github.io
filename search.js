(() => {
  const input = document.querySelector('#search');
  if (!input) return;
  const cards = [...document.querySelectorAll('.article-card')];
  const empty = document.querySelector('#empty');
  const english = document.documentElement.lang === 'en';
  const status = document.createElement('p');
  status.className = 'sub';
  status.setAttribute('role', 'status');
  status.hidden = true;
  input.closest('.search-row').after(status);
  let index = null;
  let pending = null;
  function filter() {
    const terms = input.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    let count = 0;
    for (const card of cards) {
      const text = index?.[card.dataset.slug] ?? card.dataset.search;
      card.hidden = !terms.every(term => text.includes(term));
      count += Number(!card.hidden);
    }
    empty.hidden = count > 0 || (terms.length > 0 && !index && Boolean(pending));
    status.hidden = !terms.length;
    status.textContent = index || !terms.length
      ? (english ? `${count} articles found` : `找到 ${count} 篇文章`)
      : (pending ? (english ? 'Loading full-text search…' : '正在加载全文搜索…')
        : (english ? 'Full-text search is unavailable. Searching titles, summaries and series.' : '全文搜索暂时无法加载，已搜索标题、摘要和系列。'));
  }
  input.addEventListener('input', () => {
    if (input.value.trim() && !index && !pending) {
      pending = fetch('/search-index.json').then(response => {
        if (!response.ok) throw new Error('Search index unavailable');
        return response.json();
      }).then(result => { index = result; }).catch(() => {}).finally(() => {
        pending = null;
        filter();
      });
    }
    filter();
  });
})();
