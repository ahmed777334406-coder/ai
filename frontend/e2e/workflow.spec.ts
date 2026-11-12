import { test, expect, Page } from '@playwright/test';
import fs from 'node:fs';
const origin=process.env.API_ORIGIN || 'https://smartfind-api-production.up.railway.app';
const base=origin+'/api/v1';
async function register(page:Page,name:string,email:string,password:string) {
  await page.goto('/register');
  await page.getByLabel(/full name/i).fill(name);
  await page.getByLabel(/email/i).fill(email);
  await page.getByLabel(/password/i).fill(password);
  await page.locator('form button.primary-button').click();
  await expect(page).toHaveURL(/\/dashboard/);
}
async function report(page:Page,status:string,title:string) {
  page.on('dialog',dialog=>dialog.accept());
  await page.goto(`/report/${status}`);
  await page.getByLabel('Title',{exact:true}).fill(title);
  await page.getByLabel('Category',{exact:true}).selectOption('Bags');
  await page.getByLabel('Color',{exact:true}).fill('Black');
  await page.getByLabel('Location',{exact:true}).selectOption({label:'University Library · 图书馆'});
  await page.getByLabel('Description',{exact:true}).fill(`${status==='LOST'?'I lost':'I found'} a black backpack near the Beihang library entrance. Fictional demonstration report.`);
  await page.locator('input[type="file"]').setInputFiles('../data/demo/images/backpack.png');
  await page.getByRole('button',{name:'Submit report',exact:true}).click();
  await expect(page).toHaveURL(/\/item\/\d+/,{timeout:45000});
  const id=Number(new URL(page.url()).pathname.split('/').pop());
  await expect(page.locator('.detail-image')).toBeVisible();
  await expect.poll(()=>page.locator('.detail-image').evaluate((img:HTMLImageElement)=>img.complete&&img.naturalWidth>0)).toBeTruthy();
  return id;
}
test('students report, match, claim, and administrator approves recovery',async({browser})=>{
  test.setTimeout(180000);
  const credentialsFile=process.env.SMARTFIND_TEST_CREDENTIALS;
  test.skip(!credentialsFile,'Set SMARTFIND_TEST_CREDENTIALS to a private admin credentials file.');
  const admin=JSON.parse(fs.readFileSync(credentialsFile!,'utf8'));
  const ownerContext=await browser.newContext();const finderContext=await browser.newContext();const adminContext=await browser.newContext();
  const owner=await ownerContext.newPage(), finder=await finderContext.newPage(), reviewer=await adminContext.newPage();
  const site=process.env.BASE_URL || 'http://localhost:3000';
  for (const page of [owner,finder,reviewer]) {
    const goto=page.goto.bind(page); page.goto=((url:string,opts:any)=>goto(url.startsWith('/')?site+url:url,opts)) as any;
  }
  const stamp=Date.now();const password=`Fictional-Private-${stamp}!`;
  await register(owner,'Fictional Owner',`owner-${stamp}@example.edu`,password);
  const lost=await report(owner,'LOST',`Fictional black backpack ${stamp}`);
  await register(finder,'Fictional Finder',`finder-${stamp}@example.edu`,password);
  const found=await report(finder,'FOUND',`Found fictional black backpack ${stamp}`);
  await owner.goto('/matches');
  const card=owner.locator('.match-card').filter({has:owner.getByRole('heading',{name:`Found fictional black backpack ${stamp}`,exact:true})});
  await expect(card).toBeVisible();
  await expect(card).toContainText('Fallback matching');
  await owner.screenshot({path:'../docs/screenshots/matching-results.png',fullPage:true});
  await card.getByRole('link',{name:/review found item/i}).click();
  await owner.getByLabel(/ownership verification details/i).fill('Fictional identifying evidence: blue ribbon sewn inside the main pocket.');
  await owner.getByRole('button',{name:/submit ownership claim/i}).click();
  await expect(owner).toHaveURL(/\/claims/);
  await expect(owner.locator('tbody')).toContainText('PENDING');
  await reviewer.goto('/login');await reviewer.getByLabel(/email/i).fill(admin.email);await reviewer.getByLabel(/password/i).fill(admin.password);
  await reviewer.locator('form button.primary-button').click();await expect(reviewer).toHaveURL(/\/dashboard/);
  await reviewer.goto('/admin/claims');
  const claim=reviewer.locator('.claim-card').filter({hasText:`Listing #${found}`});
  await expect(claim).toBeVisible();
  await reviewer.screenshot({path:'../docs/screenshots/admin-claim-review.png',fullPage:true});
  await claim.getByRole('button',{name:'Approve',exact:true}).click();
  await expect(claim).toContainText('APPROVED');
  await owner.reload();await expect(owner.locator('tbody')).toContainText('APPROVED');
  await owner.goto(`/item/${lost}`);await expect(owner.locator('.detail-top')).toContainText('RECOVERED');
  await finder.goto(`/item/${found}`);await expect(finder.locator('.detail-top')).toContainText('RECOVERED');
  await owner.goto('/notifications');await expect(owner.locator('main')).toContainText('Your recovery claim was approved');
  await finder.goto('/notifications');await expect(finder.locator('main')).toContainText('The item has been recovered');
  await owner.screenshot({path:'../docs/screenshots/recovery-notifications.png',fullPage:true});
  await ownerContext.close();await finderContext.close();await adminContext.close();
});
