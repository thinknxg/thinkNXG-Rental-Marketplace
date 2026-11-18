// Renders every asset in manifest.json to PNG (2x) and, where requested, PDF. Usage: node render.js [nameFilter]
const { chromium } = require("/opt/node22/lib/node_modules/playwright");
const fs = require("fs"), path = require("path");
const ROOT = path.resolve(__dirname, "..");
const man = JSON.parse(fs.readFileSync(path.join(__dirname, "manifest.json")));
const filter = process.argv[2];
(async () => {
  const b = await chromium.launch({ executablePath: "/usr/bin/google-chrome", args: ["--no-sandbox", "--allow-file-access-from-files"] });
  for (const a of man) {
    if (filter && !a.name.includes(filter)) continue;
    const ctx = await b.newContext({ viewport: { width: a.w, height: a.h }, deviceScaleFactor: a.scale || 2 });
    const p = await ctx.newPage();
    await p.goto("file://" + path.join(ROOT, "source-files/html", a.html));
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(250);
    const dir = path.join(ROOT, a.dir); fs.mkdirSync(dir, { recursive: true });
    if (a.kinds.includes("png")) await p.screenshot({ path: path.join(dir, a.name + ".png"), clip: { x: 0, y: 0, width: a.w, height: a.h } });
    if (a.kinds.includes("pdf")) await p.pdf({ path: path.join(dir, a.name + ".pdf"), preferCSSPageSize: true, printBackground: true });
    await ctx.close();
    console.log("ok", a.dir + "/" + a.name);
  }
  await b.close();
})();
