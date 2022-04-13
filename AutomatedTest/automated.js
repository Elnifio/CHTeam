const fs = require("fs");
const puppeteer = require("puppeteer");

const basePath = "./cookies/";

const UPVOTE_P = 1;
const MIN_PRICE = 10;
const MAX_PRICE = 100;

const MIN_QUANTITY = 1;
const MAX_QUANTITY = 10;
const SELL_P = 0.05;
const BUY_P = 0.2;

async function initialize() {
    let browser = await puppeteer.launch();
    return browser;
}

function shuffle(arr) {
    let i = 0;

    while (i < arr.length) {
        let choice = Math.floor(Math.random() * (arr.length - i)) + i;
        let temp = arr[i];
        arr[i] = arr[choice];
        arr[choice] = temp;
        i += 1
    }
}

async function register(name, password, address, browser) {
    console.log(`Registering user ${name}`);
    const email = `${name}@email.com`;

    const page = await browser.newPage();
    await page.goto("http://127.0.0.1:5000/");

    // registers the account
    await page.click("a.btn.btn-sm");
    await page.type("#username", name);
    await page.type("#email", email);
    await page.type("#address", address);
    await page.type("#password1", password);
    await page.type("#password2", password);
    
    await Promise.all([
        page.click("#submit"),
        page.waitForNavigation({waitUntil: "networkidle2"}),
        
      ]);

    const cookies = await page.cookies();
    const info = {
        email: email,
        password: password,
        cookie: cookies
    }
    fs.writeFileSync(`${basePath}${name}.json`, JSON.stringify(info), {encoding: "utf-8"});
    console.log(`Register complete`);
    return browser;
}

async function login(name, browser) {
    console.log(`Loggin in user ${name}`);
    if (!fs.existsSync(`${basePath}${name}.json`)) {
        console.warn(`User ${name} does not exist. Run Register first`);
        return;
    }

    if (browser == undefined) {
        console.warn("Browser undefined");
        return;
    }

    const info = JSON.parse(fs.readFileSync(`${basePath}${name}.json`, {encoding: "utf-8"}));

    const page = await browser.newPage();
    await page.setCookie(...info.cookie);

    console.log(`Login complete for user ${name}`);
    return {page, browser, info};
}

async function findItems(name, browser) {
    console.log("Finding item for user " + name);

    const bundle = await login(name, browser);
    if (bundle == undefined) {
        return;
    }
    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    await page.goto("http://127.0.0.1:5000/market");

    const choices = await page.$("#category");
    const options = await choices.$$("option");

    const choice = await (await options[Math.floor(Math.random() * (options.length - 1)) + 1].getProperty("value")).jsonValue();

    await page.select("#category", choice);

    console.log("Submitting the query");
    await Promise.all([
        page.click("#submit"),
        page.waitForNavigation({waitUntil: "networkidle2"}),
    ]);

    console.log("Choosing items to buy");
    const links = await page.$$("tr a.btn-info");

    for (let link of links) {
        if (Math.random() < BUY_P) {
            let href = await (await link.getProperty("href")).jsonValue();
            if (info.items == undefined) {
                info.items = [];
            }

            if (info.items.includes(href)) {
                continue;
            } else {
                info.items.push(href);
            }
        }
    }

    console.log("Choosing items to sell");
    const sellItems = await page.$$("tr a.btn-success");
    for (let sell of sellItems) {
        if (Math.random() < SELL_P) {
            let href = await (await sell.getProperty("href")).jsonValue();
            if (info.sells == undefined) {
                info.sells = [];
            }
    
            if (info.sells.includes(href)) {
                continue;
            } else {
                info.sells.push(href);
            }
        }
    }

    fs.writeFileSync(`${basePath}${name}.json`, JSON.stringify(info), {encoding: 'utf-8'});
    console.log("FindItem Complete");
    return browser;
}

async function addToCart(name, browser) {
    console.log("Entering addToCart");

    const bundle = await login(name, browser);
    if (bundle == undefined) {
        console.warn("Bundle not exist, run register first");
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.items == undefined) {
        console.warn("Items undefined, run findItems first");
        return;
    }

    console.log(`Visiting ${info.items.length} items`);

    for (let url of info.items) {
        await page.goto(url);

        let choices = await page.$$("body > div:nth-child(5) > table > tbody > tr");
        if (choices.length == 0) {
            console.warn(`No available inventory for item ${url}`);
            continue;
        }
        shuffle(choices);

        let tables = await choices[0].$$("td h5.mt-4");

        let quantityRemaining = parseInt(await (await tables[2].getProperty("innerHTML")).jsonValue());

        if (quantityRemaining <= 0) {
            continue;
        }

        await Promise.all([
            page.click("td div a.btn-info"),
            page.waitForNavigation({waitUntil: "networkidle2"}),
        ]);

        await page.type("#quantity", `${Math.floor(Math.random() * (quantityRemaining)) + 1}`);
        
        await Promise.all([
            page.click("#submit"),
            page.waitForNavigation({waitUntil: "networkidle2"}),
        ]);
    }

    console.log("Exiting addToCart");
    return browser;
}

async function addFund(name, bundle=undefined, browser) {

    console.log(`Adding fund for ${name}`);

    if (bundle == undefined) {
        bundle = await login(name, browser);
    }

    if (bundle == undefined) {
        console.warn("Bundle not exist, run register first");
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    await page.goto("http://127.0.0.1:5000/edit_info");
    await page.type("#balance_change", "100");
    await page.type("#password1", info.password);
    await page.type("#password2", info.password);

    await Promise.all([
        page.click("#submit"),
        page.waitForNavigation({waitUntil: "networkidle2"}),
    ]);

    console.log(`Added $1000 for ${name}`);
}

async function checkout(name, browser) {
    console.log(`Checking out for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        console.warn("Bundle not exist, run register first");
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    await page.goto("http://127.0.0.1:5000/cart");

    let items = await page.$$("body > div > table:nth-child(2) > tbody > tr");
    if (items.length == 0) {
        console.warn("No items in cart, run addToCart first");
        return;
    }

    let fund = (await page.$$("ul.navbar-nav li.nav-item a.nav-link"))[3];
    fund = await (await fund.getProperty("innerText")).jsonValue();
    fund = parseFloat(fund.trim().replace("$", ""));
    
    let money = (await page.$("body > div > div:nth-child(3) > div:nth-child(1) > p"));
    money = await (await money.getProperty("innerText")).jsonValue();
    money = parseFloat(money.trim().replace("$", ""));
    
    while (fund <= money) {
        await addFund(name, {page: await browser.newPage(), browser: browser, info: info});
        fund += 1000;
    }

    await Promise.all([
        page.goto("http://127.0.0.1:5000/checkout"),
        page.waitForNavigation({waitUntil: "networkidle2"}),
    ]);

    await page.pdf({path: "checked-out.pdf", format: "A4"});

    console.log(`Checkout complete`);
    return browser;
}

async function makeOrderURLs(name, browser) {
    console.log("Calling makeOrderURLs");
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        console.warn("Bundle not exist, run register first");
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    await page.goto("http://127.0.0.1:5000/buy_history");

    let boughts = await page.$$("body > div > table > tbody > tr");

    if (boughts.length == 0) {
        console.warn("No items bought; run checkout first");
        return;
    }

    let orders = await page.$$("body > div.container > table > tbody > tr > td:nth-child(7) > div > a");

    let itemURL = [];
    let sellerURL = [];

    console.log(`Clicking ${orders.length} buttons`);
    for (let button of orders) {
        let p = await browser.newPage();
        let url = await (await button.getProperty("href")).jsonValue();
        await p.goto(url);
        let items = await p.$$("body > div.container > table > tbody > tr > td:nth-child(1) > a");
        for (let item of items) {
            let url = await(await item.getProperty("href")).jsonValue();
            if (!itemURL.includes(url)) {
                itemURL.push(url);
            }
        }

        let sellers = await p.$$("body > div.container > table > tbody > tr > td:nth-child(6) > div > a");

        for (let seller of sellers) {
            let url = await(await seller.getProperty("href")).jsonValue();
            if (!sellerURL.includes(url)) {
                sellerURL.push(url);
            }
        }
    }

    info.urls = {item: itemURL, seller: sellerURL};
    fs.writeFileSync(`${basePath}${name}.json`, JSON.stringify(info), {encoding: "utf-8"});
    console.log("makeOrderURLs complete");
    return browser;
}

async function makeComment(name, browser) {
    console.log(`Making comment for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        console.warn("Bundle not exist, run register first");
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.urls == undefined) {
        console.warn("Orders not exist");
        return;
    }

    console.log(`Creating comments for items`);
    for (let item of info.urls.item) {
        await page.goto(item);
        let isReviewed = await page.$("#user-review-title");
        isReviewed = await (await isReviewed.getProperty("innerText")).jsonValue();
        if (isReviewed != "Edit Review") {
            continue;
        }

        let rating = Math.floor(Math.random() * 6);
        if (rating != 0) {
            await page.click(`#user-rating-${rating}`);
        }

        await page.type("#user-review-editor", `${info.email} bought and reviewed on this item.`);

        await Promise.all([
            page.click("#user-review-publish-icon"),
            page.waitForNavigation({waitUntil: "networkidle2"}),
        ]);
    }

    console.log(`Creating comments for sellers`);
    for (let item of info.urls.seller) {
        await page.goto(item);
        let isReviewed = await page.$("#user-review-title");
        isReviewed = await (await isReviewed.getProperty("innerText")).jsonValue();
        if (isReviewed != "Edit Review") {
            continue;
        }

        let rating = Math.floor(Math.random() * 6);
        if (rating != 0) {
            await page.click(`#user-rating-${rating}`);
        }

        await page.type("#user-review-editor", `${info.email} bought something from this seller.`);
        
        await Promise.all([
            page.click("#user-review-publish-icon"),
            page.waitForNavigation({waitUntil: "networkidle2"}),
        ]);
    }

    console.log(`Make comment complete for ${name}`);
    return browser;
}

async function clickUpvote(name, browser) {
    console.log(`Clicking Upvote for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        console.warn("Bundle not exist, run register first");
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.urls == undefined) {
        console.warn("Lacking info urls, run checkout first");
        return;
    }

    console.log("Clicking upvote for items");
    for (let item of info.urls.item) {
        await page.goto(item);
        let upvoteButtons = await page.$$("i.fa-thumbs-o-up");
        for (let button of upvoteButtons) {
            if (Math.random() < UPVOTE_P) {
                let identifier = await (await button.getProperty("id")).jsonValue();
                await page.click(`#${identifier}`);
            }
        }
    }

    console.log(`Clicking upvote for sellers`);
    for (let item of info.urls.seller) {
        await page.goto(item);
        let upvoteButtons = await page.$$("i.fa-thumbs-o-up");
        for (let button of upvoteButtons) {
            if (Math.random() < UPVOTE_P) {
                let identifier = await (await button.getProperty("id")).jsonValue();
                await page.click(`#${identifier}`);
            }
        }
    }

    return browser;
}

async function makeSell(name, browser) {d
    console.log(`Making sell for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        console.warn("Bundle not exist, run register first");
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.sells == undefined) {
        console.warn(`Sells property undefined, run findItems first`);
        return;
    }

    for (let url of info.sells) {
        await page.goto(url);

        let price = Math.floor(Math.random() * (MAX_PRICE - MIN_PRICE)) + MIN_PRICE;

        await page.type("#price", `${price}`);

        let amt = Math.floor(Math.random() * (MAX_QUANTITY - MIN_QUANTITY)) + MIN_QUANTITY;

        await page.type("#quantity", `${amt}`);

        await Promise.all([
            page.click("#submit"),
            page.waitForNavigation({waitUntil: "networkidle2"})
        ]);
    }

    console.log("Make Sell success");

    return browser;
}

// const name = "name05"

// initialize().
// // then(x => register(name, "123456", "Address for name06", x)).
// // then(x => findItems(name, x)).
// then(x => clickUpvote(name, x)).
// then((x) => x.close()).then(x => {console.log("Finished")});

let i = 0;


