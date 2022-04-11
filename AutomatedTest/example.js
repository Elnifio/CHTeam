const puppeteer = require("puppeteer");

const username = "TestUser04";
const password = "123456";
const address = "None";
const email = `${username}@email.com`;

(async() => {
    // Launch the browser
    const browser = await puppeteer.launch();

    // Connects to the page
    const page = await browser.newPage();
    await page.goto("http://127.0.0.1:5000/");

    // registers the account
    await page.click("a.btn.btn-sm");
    await page.type("#username", username);
    await page.type("#email", email);
    await page.type("#address", address);
    await page.type("#password1", password);
    await page.type("#password2", password);
    
    // 
    const [response] = await Promise.all([
        page.click("#submit"),
        page.waitForNavigation({waitUntil: "networkidle2"}),
        
      ]);

    console.log(response);
    await page.pdf({path: "page.pdf", format: "A4"});
    await browser.close();
})();