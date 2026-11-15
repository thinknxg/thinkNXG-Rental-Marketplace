const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const BASE = "http://demo.test:8000";
const log = (...a) => console.log(...a);
(async () => {
  const browser = await chromium.launch({ executablePath: "/usr/bin/google-chrome", args: ["--no-sandbox"] });
  const errs = [];
  async function as(user, pwd) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const r = await ctx.request.post(BASE + "/api/method/login", { form: { usr: user, pwd } });
    const p = await ctx.newPage();
    p.on("pageerror", (e) => errs.push(user + ": " + e.message));
    p.on("dialog", (d) => d.accept());
    return p;
  }
  const toast = async (p) => { await p.waitForSelector(".toast", { timeout: 8000 }).catch(() => {}); return (await p.$$eval(".toast", (t) => t.map((x) => x.className + ": " + x.textContent))).join(" | "); };
  const modalFill = async (p, vals) => { for (const [n, v] of Object.entries(vals)) { const el = await p.$(`.modal [name="${n}"]`); const tag = await el.evaluate((e) => e.tagName); if (tag === "SELECT") await el.selectOption(v); else await el.fill(String(v)); } };
  const modalOk = async (p) => { await p.click(".modal footer button:last-child"); };

  // 1. supplier submits an offer through the portal
  let v = await as("muscat-formwork@demo.thinknxg.com", "Demo@12345");
  await v.goto(BASE + "/marketplace/vendor/tenders/TND-2026-00002", { waitUntil: "networkidle" });
  const sel = v.locator(".item-row select").nth(1);
  const opts = await sel.locator("option").allTextContents(); log("listing options:", opts.join(" / "));
  await sel.selectOption({ index: 1 });
  await v.waitForTimeout(300);
  await v.locator(".item-row input[type=number]").nth(1).fill("2.8");
  await v.fill('input[name=transport_charges]', "150"); await v.fill('input[name=mobilization_charges]', "200"); await v.fill('input[name=payment_terms]', "Monthly in arrears");
  await v.check('input[name=availability_confirmed]');
  await v.click("text=Save draft & calculate"); log("save:", await toast(v));
  await v.waitForTimeout(800);
  log("totals:", (await v.$$eval(".kpi b", (b) => b.map((x) => x.textContent))).join(" | "));
  await v.click("text=Submit offer"); log("submit:", await toast(v));
  await v.waitForTimeout(1500);
  log("offer status:", await v.$eval(".card h3 + span, .card .row.between span", (e) => e.textContent).catch(() => "?"));
  await v.screenshot({ path: "/home/claude/shots/e2e-offer-submitted.png", fullPage: true });

  // 2. customer: wizard
  let c = await as("buyer@demo.thinknxg.com", "Demo@12345");
  await c.goto(BASE + "/marketplace/post-requirement", { waitUntil: "networkidle" });
  await c.click(".choice:has-text('Hire')");
  await c.click(".choice:has-text('Ringlock Scaffolding')");
  await c.locator(".item-row input").nth(0).fill("Ringlock standard 2.5 m"); await c.locator(".item-row input").nth(1).fill("400");
  await c.click("text=Continue →");
  const d = (n) => new Date(Date.now() + n * 864e5).toISOString().slice(0, 10);
  await c.fill("input[name=required_from]", d(10)); await c.fill("input[name=required_to]", d(40));
  await c.click("text=Continue →");
  await c.fill("input[name=project_name]", "Qurum Villas"); await c.fill("textarea[name=site_address]", "Way 2731, Qurum"); await c.fill("input[name=city]", "Muscat");
  await c.click("text=Continue →"); await c.fill("input[name=budget_max]", "900");
  await c.click("text=Continue →"); await c.click("text=Continue →");
  await c.screenshot({ path: "/home/claude/shots/e2e-wizard-review.png", fullPage: true });
  await c.click("text=Submit requirement");
  await c.waitForSelector("text=Requirement submitted", { timeout: 15000 }).catch(() => {});
  log("wizard result:", (await c.textContent("#wizard")).replace(/\s+/g, " ").slice(0, 220));
  await c.screenshot({ path: "/home/claude/shots/e2e-wizard-done.png" });

  // 3. customer accepts Gulf's offer
  await c.goto(BASE + "/marketplace/account/tenders/TND-2026-00001/compare", { waitUntil: "networkidle" });
  await c.locator(".offer").first().locator("text=Accept this offer").click();
  await c.click(".modal footer button:has-text('Accept & book')");
  await c.waitForURL(/bookings\//, { timeout: 15000 }).catch(() => {});
  await c.waitForTimeout(1200);
  log("booking url:", c.url());
  await c.click("text=Continue to payment").catch(async () => await c.click("text=Pay now"));
  await c.waitForURL(/payments\//, { timeout: 10000 }).catch(() => {});
  await c.waitForTimeout(800);
  await c.fill("input[name=ref]", "BM-TRF-77881"); await c.click("text=Submit reference"); log("reference:", await toast(c));
  const bookingName = c.url().includes("payments") ? null : null;

  // 4. finance confirms
  let o = await as("Administrator", "admin");
  await o.goto(BASE + "/marketplace/operator/payments?status=Pending", { waitUntil: "networkidle" });
  await o.locator("[data-pc]").first().click(); await modalFill(o, { reference: "BANKMUSCAT-77881" }); await modalOk(o); log("confirm:", await toast(o));
  await o.goto(BASE + "/marketplace/operator", { waitUntil: "networkidle" }); await o.waitForTimeout(600);
  await o.screenshot({ path: "/home/claude/shots/e2e-operator.png", fullPage: true });

  // 5. supplier dispatches
  let g = await as("gulf-scaffold@demo.thinknxg.com", "Demo@12345");
  await g.goto(BASE + "/marketplace/vendor/bookings", { waitUntil: "networkidle" });
  await g.locator("table.t tbody tr").first().click(); await g.waitForTimeout(1000);
  log("vendor booking status:", await g.$eval(".badge", (e) => e.textContent).catch(() => "?"));
  await g.click("#bar-actions >> text=Mark dispatched"); await modalFill(g, { vehicle_details: "Truck MCT-4421", driver_contact: "+968 9555 1212" }); await modalOk(g);
  log("dispatch:", await toast(g)); await g.waitForTimeout(1200);
  await g.screenshot({ path: "/home/claude/shots/e2e-vendor-booking.png", fullPage: true });
  console.log("PAGE ERRORS:", errs.length ? errs.join("\n") : "none");
  await browser.close();
})();
