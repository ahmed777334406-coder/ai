import { test, expect } from '@playwright/test';
test('homepage, language switching and mobile layout',async({page})=>{
  const errors:string[]=[]; page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.getByRole('link',{name:'Sign in',exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:'中文',exact:true}).click();
  await expect(page.getByRole('button',{name:'English',exact:true})).toBeVisible();
  await page.getByRole('button',{name:'English',exact:true}).click();
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  expect(errors).toEqual([]);
});
test('anonymous dashboard and report form need no login',async({page})=>{
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('.alert.error')).toHaveCount(0);
  await page.goto('/report/LOST');
  await expect(page.getByLabel('Item title',{exact:true})).toBeVisible();
  const cookies=await page.context().cookies();
  expect(cookies.find(c=>c.name==='smartfind_visitor')?.httpOnly).toBe(true);
  expect(await page.evaluate(()=>localStorage.getItem('smartfind_token'))).toBeNull();
  await page.goto('/register'); await expect(page).toHaveURL(/\/dashboard/);
});
test('administrator sign in rejects invalid credentials',async({page})=>{
  await page.goto('/admin/login');
  await page.getByLabel(/email/i).fill(`missing-${Date.now()}@example.edu`);
  await page.getByLabel(/password/i).fill('Incorrect-Test-Password!');
  await page.locator('form button.primary-button').click();
  await expect(page.locator('.alert.error')).toHaveText('Incorrect email or password');
  expect(await page.evaluate(()=>localStorage.getItem('smartfind_token'))).toBeNull();
});
