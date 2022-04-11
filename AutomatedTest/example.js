const puppeteer = require("puppeteer");

(async() => {
    const browser = await puppeteer.launch();
    console.log(await browser.version());
    const page = await browser.newPage();
    await page.goto("https://127.0.0.1:5000");
    await page.pdf({path: "page.pdf", format: "A4"});
    await browser.close();
})();