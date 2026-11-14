import { test, expect, Page } from '@playwright/test';
import fs from 'node:fs';
test.beforeEach(async ({page})=>{
  await page.route('**/*', route=>{
    const url=new URL(route.request().url());
    if (url.hostname.endsWith('.railway.app') || url.hostname.endsWith('.vercel.app')) return route.abort();
    return route.continue();
  });
});
async function startVisitor(page:Page) {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard/);
  await expect(page.locator('h1')).toBeVisible();
}
async function report(page:Page,status:string,title:string) {
  page.on('dialog',dialog=>dialog.accept());
  await page.goto(`/report/${status}`);
  if (status === 'LOST') {
    await page.setViewportSize({width:390,height:844});
    expect(await page.evaluate(()=>document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.screenshot({path:'../docs/screenshots/final-report-mobile.png',fullPage:true});
  }
  await page.getByLabel('Item title',{exact:true}).fill(title);
  await page.getByLabel(/^Category/).selectOption('Bags');
  await page.getByLabel('Color',{exact:true}).fill('Black');
  await page.getByLabel(/^Campus zone/).selectOption({label:'Main Library · 主图书馆'});
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
  const stamp=Date.now();
  await startVisitor(owner);
  const lost=await report(owner,'LOST',`Fictional black backpack ${stamp}`);
  await startVisitor(finder);
  const found=await report(finder,'FOUND',`Found fictional black backpack ${stamp}`);
  await owner.goto('/matches');
  const card=owner.locator('.match-card').filter({has:owner.getByRole('heading',{name:`Found fictional black backpack ${stamp}`,exact:true})});
  await expect(card).toBeVisible();
  await expect(card).toContainText('Fallback matching');
  await owner.screenshot({path:'../docs/screenshots/final-matching-results.png',fullPage:true});
  await card.getByRole('link',{name:/review found item/i}).click();
  await owner.getByLabel(/ownership verification details/i).fill('Fictional identifying evidence: blue ribbon sewn inside the main pocket.');
  await owner.getByRole('button',{name:/submit ownership claim/i}).click();
  await expect(owner).toHaveURL(/\/claims/);
  await expect(owner.locator('tbody')).toContainText('PENDING');
  await reviewer.goto('/admin/login');await reviewer.getByLabel(/email/i).fill(admin.email);await reviewer.getByLabel(/password/i).fill(admin.password);
  await reviewer.locator('form button.primary-button').click();await expect(reviewer).toHaveURL(/\/admin\/?$/);
  await reviewer.goto('/admin/claims');
  const claim=reviewer.locator('.claim-card').filter({hasText:`Listing #${found}`});
  await expect(claim).toBeVisible();
  await claim.getByRole('button',{name:'Request more evidence',exact:true}).click();
  await expect(claim).toContainText('NEEDS EVIDENCE');
  await owner.reload();await expect(owner.locator('tbody')).toContainText('NEEDS EVIDENCE');
  await owner.locator('input[type="file"]').setInputFiles('../data/demo/images/backpack.png');
  await expect(owner.locator('.alert.success')).toContainText('Evidence uploaded');
  await reviewer.reload();await expect(claim).toContainText('Received (private)');
  const downloadEvent=reviewer.waitForEvent('download');
  await claim.getByRole('button',{name:'Download private evidence'}).click();
  const download=await downloadEvent;expect(await download.failure()).toBeNull();
  await reviewer.screenshot({path:'../docs/screenshots/final-admin-claim-review.png',fullPage:true});
  await claim.getByRole('button',{name:'Approve',exact:true}).click();
  await expect(claim).toContainText('APPROVED');
  await owner.reload();await expect(owner.locator('tbody')).toContainText('APPROVED');
  await owner.goto(`/item/${lost}`);await expect(owner.locator('.detail-top')).toContainText('RECOVERED');
  await finder.goto(`/item/${found}`);await expect(finder.locator('.detail-top')).toContainText('RECOVERED');
  await owner.goto('/notifications');await expect(owner.locator('main')).toContainText('Your recovery claim was approved');
  await finder.goto('/notifications');await expect(finder.locator('main')).toContainText('The item has been recovered');
  await owner.screenshot({path:'../docs/screenshots/final-recovery-notifications.png',fullPage:true});
  await ownerContext.close();await finderContext.close();await adminContext.close();
});
