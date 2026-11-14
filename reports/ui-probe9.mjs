export default async function run(page) {
  const out = { calls: [] };
  page.on('request', r => {
    const u = r.url();
    if (/\/api\//.test(u) && !/\.(png|svg|css|js)/.test(u)) {
      out.calls.push({ method: r.method(), url: u.replace(/^https?:\/\/[^/]+/, '').slice(0, 70) });
    }
  });
  const bodies = [];
  page.on('response', async r => {
    const u = r.url();
    if (/\/api\/(design|screen|explore|screening)/.test(u)) {
      let txt = '';
      try { txt = (await r.text()).slice(0, 400); } catch { }
      bodies.push({ url: u.replace(/^https?:\/\/[^/]+/, ''), status: r.status(), body: txt });
    }
  });

  await page.locator('button:has-text("07 Design studio")').first().click();
  await page.waitForTimeout(1000);
  out.callsAfterOpen = [...out.calls];

  // Fire the move event properly, the way a real drag does.
  await page.evaluate(() => {
    const s = document.querySelector('input[type=range]');
    s.value = '12';
    s.dispatchEvent(new Event('input', { bubbles: true }));
    s.dispatchEvent(new Event('change', { bubbles: true }));
  });
  await page.waitForTimeout(4000);
  out.callsAfterSlider = out.calls.filter(c => !out.callsAfterOpen.includes(c));
  out.apiBodies = bodies;

  // Reach into the DOM for the actual metric text nodes
  out.cards = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('*')].filter(e =>
      /A\s?NNUAL PVT ELECTRICITY|SOLAR HEATING FRACTION|ELECTRIC SELF-SUFFICIENCY|PAYBACK|ANNUAL COST DELTA|DRINKING WATER|NET ELECTRICITY/i.test(e.textContent || '') && e.children.length === 0
    );
    return [...new Set(cards.map(c => c.textContent.trim()))].slice(0, 10);
  });
  out.placeholders = await page.evaluate(() =>
    (document.body.innerText.match(/—/g) || []).length
  );
  return out;
}
