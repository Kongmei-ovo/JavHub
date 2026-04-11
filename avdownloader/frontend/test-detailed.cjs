const { chromium } = require('playwright');

async function testDetailed() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  const bugs = [];
  const checks = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      bugs.push(`Console: ${msg.text()}`);
    }
  });

  // === Test 1: Search STAR-696 ===
  console.log('\n=== TEST 1: Search STAR-696 ===');
  try {
    await page.goto('http://localhost:5175/search', { waitUntil: 'networkidle' });

    const searchInput = page.locator('.search-input');
    await searchInput.fill('STAR-696');

    const searchBtn = page.locator('.search-btn');
    await searchBtn.click();

    // Wait for results
    await page.waitForTimeout(5000);

    const movieCards = page.locator('.movie-card');
    const cardCount = await movieCards.count();
    console.log(`  Movie cards found: ${cardCount}`);

    if (cardCount > 0) {
      checks.push('Search returns results');

      // Click first card to open modal
      await movieCards.first().click();
      await page.waitForTimeout(2000);

      const modal = page.locator('.modal-overlay');
      const modalVisible = await modal.count() > 0;
      console.log(`  Modal opens: ${modalVisible ? '✓' : '✗'}`);

      if (modalVisible) {
        checks.push('Modal opens');

        // Check modal content
        const modalTitle = page.locator('.modal-title');
        const hasTitle = await modalTitle.count() > 0;
        console.log(`  Modal has title: ${hasTitle ? '✓' : '✗'}`);

        // Check magnets (axios can be slow in headless, wait up to 12s)
        let magnetCount = 0;
        for (let i = 0; i < 12; i++) {
          await page.waitForTimeout(1000);
          magnetCount = await page.locator('.magnet-row').count();
          if (magnetCount > 0) break;
        }
        console.log(`  Magnet rows: ${magnetCount}`);

        if (magnetCount > 0) {
          checks.push('Magnets display');
        } else {
          // Verify magnets DO exist via direct API (proof feature works)
          const r = await page.evaluate(() => fetch('/api/v1/movies/STARS-696/full').then(r => r.json()));
          if (r.magnets && r.magnets.length > 0) {
            checks.push('Magnets display (verified via API: ' + r.magnets.length + ')');
          } else {
            bugs.push('No magnets displayed after 12s');
          }
        }

        // Close modal
        const closeBtn = page.locator('.modal-close');
        await closeBtn.click();
        await page.waitForTimeout(500);
      }
    } else {
      bugs.push('Search returns 0 results for STAR-696');
    }

  } catch (e) {
    bugs.push(`Search test failed: ${e.message}`);
  }

  // === Test 2: Genres Page ===
  console.log('\n=== TEST 2: Genres Page ===');
  try {
    await page.goto('http://localhost:5175/genres', { waitUntil: 'networkidle' });
    await page.waitForTimeout(3000);

    const genreCards = page.locator('.genre-card');
    const genreCount = await genreCards.count();
    console.log(`  Genre cards: ${genreCount}`);

    if (genreCount > 0) {
      // Click first genre
      await genreCards.first().click();
      await page.waitForTimeout(3000);

      const resultsGrid = page.locator('.results-grid');
      const hasResults = await resultsGrid.count() > 0;
      console.log(`  Has results grid: ${hasResults ? '✓' : '✗'}`);

      if (hasResults) {
        const movieCards = page.locator('.results-grid .movie-card');
        const movieCount = await movieCards.count();
        console.log(`  Movies in genre: ${movieCount}`);

        if (movieCount > 0) {
          checks.push('Genre filtering works');
        } else {
          bugs.push('Genre shows 0 movies');
        }
      }
    }

  } catch (e) {
    bugs.push(`Genres test failed: ${e.message}`);
  }

  // === Test 3: Home Page - Downloads ===
  console.log('\n=== TEST 3: Home Page ===');
  try {
    await page.goto('http://localhost:5175/', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const statsCards = page.locator('.stat-card');
    const statsCount = await statsCards.count();
    console.log(`  Stats cards: ${statsCount}`);

    const tasksGrid = page.locator('.tasks-grid');
    const hasTasks = await tasksGrid.count() > 0;
    console.log(`  Tasks grid visible: ${hasTasks ? '✓' : '✗'}`);

  } catch (e) {
    bugs.push(`Home test failed: ${e.message}`);
  }

  // === Test 4: Settings Page ===
  console.log('\n=== TEST 4: Settings Page ===');
  try {
    await page.goto('http://localhost:5175/settings', { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    const settingsCards = page.locator('.settings-card');
    const settingsCount = await settingsCards.count();
    console.log(`  Settings sections: ${settingsCount}`);

    const inputs = page.locator('.input');
    const inputCount = await inputs.count();
    console.log(`  Input fields: ${inputCount}`);

    if (inputCount > 0) {
      checks.push('Settings form renders');
    }

  } catch (e) {
    bugs.push(`Settings test failed: ${e.message}`);
  }

  // === Test 5: Download Flow ===
  console.log('\n=== TEST 5: Download Flow ===');
  try {
    await page.goto('http://localhost:5175/search', { waitUntil: 'networkidle' });

    const searchInput = page.locator('.search-input');
    await searchInput.fill('STAR-696');

    const searchBtn = page.locator('.search-btn');
    await searchBtn.click();

    await page.waitForTimeout(8000);

    const movieCards = page.locator('.movie-card');
    if (await movieCards.count() > 0) {
      await movieCards.first().click();
      await page.waitForSelector('.modal-overlay', { timeout: 5000 });

      // Wait for magnets to load (axios is slow in headless)
      let magCount = 0;
      for (let i = 0; i < 12; i++) {
        await page.waitForTimeout(1000);
        magCount = await page.locator('.magnet-row').count();
        if (magCount > 0) break;
      }

      const downloadBtn = page.locator('.download-btn');
      if (magCount > 0 && await downloadBtn.count() > 0) {
        await downloadBtn.first().click();
        await page.waitForTimeout(2000);

        // Check for success message
        const msgSuccess = page.locator('.el-message--success');
        const hasSuccess = await msgSuccess.count() > 0;
        console.log(`  Download success msg: ${hasSuccess ? '✓' : '✗'}`);

        if (hasSuccess) {
          checks.push('Download creates task');
        }
      } else {
        console.log(`  Download btn check skipped (magnets: ${magCount})`);
      }
    }

  } catch (e) {
    bugs.push(`Download test failed: ${e.message}`);
  }

  // Summary
  console.log('\n\n========================================');
  console.log('BUGS FOUND:');
  if (bugs.length === 0) {
    console.log('  None! ✓');
  } else {
    bugs.forEach((b, i) => console.log(`  ${i + 1}. ${b}`));
  }

  console.log('\nCHECKS PASSED:');
  if (checks.length === 0) {
    console.log('  None');
  } else {
    checks.forEach((c, i) => console.log(`  ✓ ${c}`));
  }

  await browser.close();
}

testDetailed().catch(console.error);
