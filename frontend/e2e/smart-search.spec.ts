import { test, expect } from '@playwright/test';
test('real database search and assistant fallback on mobile',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('/smart-search');
  await page.getByLabel('Describe your item').fill('黑色耳机');
  await page.getByRole('button',{name:'Search reports',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('bilingual_rule_hash_fallback');
  await expect(page.locator('.item-grid')).toContainText('earbuds');
  await page.getByLabel('Search mode').selectOption('assistant');
  await page.getByRole('button',{name:'Search reports',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('database_grounded_fallback');
  await expect(page.getByRole('heading',{name:'Generated summary'})).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy();
  await page.reload();
  await page.getByRole('button',{name:'中文',exact:true}).click();
  await expect(page.locator('h1')).toHaveText('AI 智能搜索');
  await page.reload();await expect(page.locator('h1')).toHaveText('AI 智能搜索');
});
test('saved report survives failed image upload and retries without duplicate',async({page})=>{
  let creates=0, uploads=0;
  await page.route('**/api/v1/listings',async route=>{
    if(route.request().method()==='POST')creates++;
    await route.continue();
  });
  await page.route('**/api/v1/listings/*/images',async route=>{
    uploads++;if(uploads===1)return route.abort('failed');await route.continue();
  });
  await page.goto('/report/LOST');
  await page.getByLabel('Item title',{exact:true}).fill(`Retry wallet ${Date.now()}`);
  await page.getByLabel('Description',{exact:true}).fill('Fictional green wallet with a purple ribbon.');
  await page.locator('input[type=file]').setInputFiles('../data/demo/images/backpack.png');
  page.on('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'Submit report',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Your report is saved');
  await page.getByRole('button',{name:'Retry photo upload',exact:true}).click();
  await expect(page).toHaveURL(/\/item\/\d+/);
  expect(creates).toBe(1);expect(uploads).toBe(2);
});
