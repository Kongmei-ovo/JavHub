const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('Console Error:', msg.text());
    }
  });
  
  await page.goto('http://localhost:5175/genres', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5000);
  
  const genreCards = page.locator('.genre-card');
  const genreCount = await genreCards.count();
  console.log(`Genre cards: ${genreCount}`);
  
  if (genreCount > 0) {
    // Get the first genre name
    const firstGenreName = await genreCards.first().locator('.genre-name').textContent();
    console.log(`First genre: ${firstGenreName}`);
    
    // Click first genre
    await genreCards.first().click();
    await page.waitForTimeout(5000);
    
    // Check results grid
    const resultsGrid = page.locator('.results-grid');
    const hasResults = await resultsGrid.count() > 0;
    console.log(`Has results grid: ${hasResults ? '✓' : '✗'}`);
    
    // Check genre movies
    const genreMovies = page.locator('.results-grid .movie-card');
    const movieCount = await genreMovies.count();
    console.log(`Movies in genre: ${movieCount}`);
    
    // Check if genre results section is showing
    const genreResults = page.locator('.genre-results');
    const hasGenreResults = await genreResults.count() > 0;
    console.log(`Has genre-results section: ${hasGenreResults ? '✓' : '✗'}`);
    
    // Check if selected genre state
    const selectedGenre = await page.locator('.results-header h2').textContent().catch(() => 'none');
    console.log(`Selected genre header: ${selectedGenre}`);
  }
  
  await browser.close();
})();
