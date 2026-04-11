const { chromium } = require('playwright');

async function testPages() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const results = [];
  const errors = [];

  // Listen for console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(`Console Error: ${msg.text()}`);
    }
  });

  page.on('pageerror', err => {
    errors.push(`Page Error: ${err.message}`);
  });

  const pages = [
    { url: 'http://localhost:5175/', name: 'Home' },
    { url: 'http://localhost:5175/search', name: 'Search' },
    { url: 'http://localhost:5175/genres', name: 'Genres' },
    { url: 'http://localhost:5175/subscription', name: 'Subscription' },
    { url: 'http://localhost:5175/settings', name: 'Settings' },
  ];

  for (const p of pages) {
    console.log(`\n=== Testing ${p.name} ===`);
    errors.length = 0;

    try {
      await page.goto(p.url, { waitUntil: 'networkidle', timeout: 30000 });
      await page.waitForTimeout(2000);

      const title = await page.title();
      const bodyText = await page.locator('body').textContent();
      const hasContent = bodyText && bodyText.length > 50;

      console.log(`  Title: ${title}`);
      console.log(`  Has Content: ${hasContent}`);
      console.log(`  Errors: ${errors.length > 0 ? errors.join(', ') : 'None'}`);

      // Try to interact with the page
      if (p.name === 'Search') {
        // Try typing in search box
        const searchInput = page.locator('input[placeholder*="番号"]');
        if (await searchInput.count() > 0) {
          await searchInput.fill('STAR-696');
          console.log('  ✓ Search input works');

          // Click search button
          const searchBtn = page.locator('button:has-text("搜索")');
          if (await searchBtn.count() > 0) {
            await searchBtn.click();
            await page.waitForTimeout(3000);
            console.log('  ✓ Search button clicked');
          }
        } else {
          console.log('  ✗ Search input not found');
        }
      }

      if (p.name === 'Genres') {
        // Wait for genres to load
        await page.waitForTimeout(3000);
        const genreCards = page.locator('.genre-card');
        const count = await genreCards.count();
        console.log(`  Genre cards: ${count}`);
        if (count > 0) {
          await genreCards.first().click();
          await page.waitForTimeout(2000);
          console.log('  ✓ Clicked first genre');
        }
      }

      results.push({ page: p.name, status: 'OK', errors: [...errors] });

    } catch (e) {
      console.log(`  ✗ Error: ${e.message}`);
      results.push({ page: p.name, status: 'FAIL', errors: [e.message] });
    }
  }

  console.log('\n\n=== SUMMARY ===');
  for (const r of results) {
    console.log(`${r.status === 'OK' ? '✓' : '✗'} ${r.page}: ${r.status} ${r.errors.length > 0 ? `(${r.errors.length} errors)` : ''}`);
  }

  await browser.close();
}

testPages().catch(console.error);
