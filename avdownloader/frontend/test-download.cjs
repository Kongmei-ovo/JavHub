const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  await page.goto('http://localhost:5175/search', { waitUntil: 'networkidle' });
  
  const searchInput = page.locator('.search-input');
  await searchInput.fill('STAR-696');
  
  const searchBtn = page.locator('.search-btn');
  await searchBtn.click();
  
  await page.waitForTimeout(5000);
  
  const movieCards = page.locator('.movie-card');
  const cardCount = await movieCards.count();
  console.log(`Movie cards: ${cardCount}`);
  
  await movieCards.first().click();
  await page.waitForTimeout(3000);
  
  // Check modal state
  const modalVisible = await page.locator('.modal-overlay').count() > 0;
  console.log(`Modal visible: ${modalVisible}`);
  
  // Check magnets
  const magnetRows = page.locator('.magnet-row');
  const magnetCount = await magnetRows.count();
  console.log(`Magnet rows: ${magnetCount}`);
  
  // Check download buttons specifically
  const downloadBtns = page.locator('.download-btn');
  const downloadBtnCount = await downloadBtns.count();
  console.log(`Download buttons: ${downloadBtnCount}`);
  
  // Try to find any button with "下载" text
  const downloadText = page.locator('button:has-text("下载")');
  const downloadTextCount = await downloadText.count();
  console.log(`Buttons with "下载": ${downloadTextCount}`);
  
  // Print HTML of first magnet row
  if (magnetCount > 0) {
    const html = await magnetRows.first().innerHTML();
    console.log('First magnet row HTML:', html.substring(0, 500));
  }
  
  await browser.close();
})();
