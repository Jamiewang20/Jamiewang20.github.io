const contents = document.querySelector('.toc');
if (contents) {
  contents.open = window.matchMedia('(min-width: 1200px)').matches;
  const links = [...contents.querySelectorAll('a')];
  const headings = links.map(link => document.getElementById(link.hash.slice(1))).filter(Boolean);
  let scheduled = false;
  function highlight() {
    let current = headings[0];
    for (const heading of headings) {
      if (heading.getBoundingClientRect().top <= 150) current = heading;
      else break;
    }
    for (const link of links) {
      if (current && link.hash === `#${current.id}`) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    }
    scheduled = false;
  }
  window.addEventListener('scroll', () => {
    if (!scheduled) { scheduled = true; window.requestAnimationFrame(highlight); }
  }, { passive: true });
  highlight();
}
