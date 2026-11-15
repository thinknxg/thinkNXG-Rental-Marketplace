const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const BASE = "http://demo.test:8000";
const pages = [
  ["guest", "home", "/marketplace"], ["guest", "equipment", "/marketplace/equipment"], ["guest", "detail", "/marketplace/equipment/cuplock-standard-3-0-m-galvanised"],
  ["guest", "for-suppliers", "/marketplace/for-suppliers"], ["buyer@demo.thinknxg.com", "wizard", "/marketplace/post-requirement?type=Hire"],
  ["buyer@demo.thinknxg.com", "customer-overview", "/marketplace/account"], ["buyer@demo.thinknxg.com", "customer-compare", "/marketplace/account/tenders/TND-2026-00001/compare"],
  ["buyer@demo.thinknxg.com", "customer-request", "/marketplace/account/requests"],
  ["muscat-formwork@demo.thinknxg.com", "vendor-dashboard", "/marketplace/vendor"], ["muscat-formwork@demo.thinknxg.com", "vendor-tender", "/marketplace/vendor/tenders/TND-2026-00002"],
  ["muscat-formwork@demo.thinknxg.com", "vendor-listings", "/marketplace/vendor/listings"],
  ["Administrator", "operator-dashboard", "/marketplace/operator"], ["Administrator", "operator-tender", "/marketplace/operator/tenders/TND-2026-00001"],
];
(async () => {
  const browser = await chromium.launch({ executablePath: "/usr/bin/google-chrome", args: ["--no-sandbox", "--host-resolver-rules=MAP mp.local 127.0.0.1"] });
  const ctxs = {};
  const errors = [];
  for (const [user, name, path] of pages) {
    for (const [vw, w, hgt] of [["d", 1440, 900], ...(["home", "customer-compare", "vendor-dashboard", "wizard"].includes(name) ? [["m", 390, 844]] : [])]) {
      const key = user + vw;
      if (!ctxs[key]) {
        ctxs[key] = await browser.newContext({ viewport: { width: w, height: hgt } });
        if (user !== "guest") {
          const r = await ctxs[key].request.post(BASE + "/api/method/login", { form: { usr: user, pwd: user === "Administrator" ? "admin" : "Demo@12345" } });
          if (!r.ok()) errors.push("login " + user + " " + r.status());
        }
      }
      const page = await ctxs[key].newPage();
      page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
      page.on("console", (m) => m.type() === "error" && errors.push(`${name} console: ${m.text()}`));
      await page.goto(BASE + path, { waitUntil: "networkidle" }).catch((e) => errors.push(name + " nav " + e.message));
      await page.waitForTimeout(700);
      if (name === "wizard" && vw === "d") { await page.click("text=Cuplock Scaffolding").catch(() => {}); await page.waitForTimeout(300); }
      await page.screenshot({ path: `/home/claude/shots/${name}-${vw}.png`, fullPage: vw === "d" });
      const toast = await page.$$eval(".toast.err,.empty h3", (els) => els.map((e) => e.textContent)).catch(() => []);
      if (toast.length) errors.push(`${name}: UI says ${toast.join(" | ")}`);
      await page.close();
    }
  }
  console.log(errors.length ? errors.join("\n") : "no errors");
  await browser.close();
})();
