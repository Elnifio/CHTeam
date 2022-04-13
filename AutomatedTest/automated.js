const fs = require("fs");
const puppeteer = require("puppeteer");

const basePath = "./cookies/";

const UPVOTE_P = 0.5; // Controls the probability that a user will upvote a comment
const MIN_PRICE = 10; // controls the minimum price that the user sets when selling an item
const MAX_PRICE = 100; // controls the maximum price that the user sets when selling an item

const MIN_QUANTITY = 1; // controls the min quantity that the user sets when selling an item
const MAX_QUANTITY = 10; // controls the max quantity that the user sets when selling an item

const SELL_P = 0.05; // the probability that the user will sell an item when scrolling through searching list
const BUY_P = 0.2; // the probability that the user will buy an item when scrolling through searching list

const MAX_ORDERS_PLACED = 30; // each user will fake at most this amount of orders

const N_USER = 2;
const USER_PREFIX = "usr";

let logConfig = {indent: 0};
function log(msg) {
    let out = `[${(new Date()).toUTCString()}]`;
    for (let i = 0; i < logConfig.indent; i++) {
        out += " |  ";
    }
    out += msg;

    console.log(out);
}


// Initialize the browser
async function initialize() {
    logConfig.indent += 1;
    if (!fs.existsSync(basePath)) {
        fs.mkdirSync(basePath);
    }
    let browser = await puppeteer.launch();

    logConfig.indent -= 1;
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


// Tests for Register page
async function register(name, password, address, browser) {
    log(`Registering user ${name}`);
    logConfig.indent += 1;
    if (fs.existsSync(`${basePath}${name}.json`)) {
        log("User " + name + " already exists, loading from cookie buffer");

        logConfig.indent -= 1;
        return browser;
    }

    const email = `${name}@email.com`;

    const page = await browser.newPage();
    await page.goto("http://127.0.0.1:5000/register");

    // registers the account
    // await page.click("a.btn.btn-sm");
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
    };

    fs.writeFileSync(`${basePath}${name}.json`, JSON.stringify(info), {encoding: "utf-8"});
    log(`Register complete`);

    logConfig.indent -= 1;
    return browser;
}

// Directly sets the cookie, bypassing the login page
async function login(name, browser) {
    logConfig.indent += 1;
    log(`Loggin in user ${name}`);
    if (!fs.existsSync(`${basePath}${name}.json`)) {
        log(`User ${name} does not exist. Run Register first`);

        logConfig.indent -= 1;
        return;
    }

    if (browser == undefined) {
        log("Browser undefined");
        logConfig.indent -= 1;
        return;
    }

    const info = JSON.parse(fs.readFileSync(`${basePath}${name}.json`, {encoding: "utf-8"}));

    const page = await browser.newPage();
    await page.setCookie(...info.cookie);

    log(`Login complete for user ${name}`);
    logConfig.indent -= 1;
    return {page, browser, info};
}

// Tests the search functionality
async function findItems(name, browser) {
    log("Finding item for user " + name);
    logConfig.indent += 1;

    const bundle = await login(name, browser);
    if (bundle == undefined) {
        logConfig.indent -= 1;
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

    log("Submitting the query");
    await Promise.all([
        page.click("#submit"),
        page.waitForNavigation({waitUntil: "networkidle2"}),
    ]);

    log("Choosing items to buy");
    const links = await page.$$("tr a.btn-info");

    info.items = [];

    for (let link of links) {
        if (Math.random() < BUY_P) {
            let href = await (await link.getProperty("href")).jsonValue();

            if (info.items.includes(href)) {
                continue;
            } else {
                info.items.push(href);
            }
        }
    }

    info.sells = [];
    log("Choosing items to sell");
    const sellItems = await page.$$("tr a.btn-success");
    for (let sell of sellItems) {
        if (Math.random() < SELL_P) {
            let href = await (await sell.getProperty("href")).jsonValue();
    
            if (info.sells.includes(href)) {
                continue;
            } else {
                info.sells.push(href);
            }
        }
    }

    fs.writeFileSync(`${basePath}${name}.json`, JSON.stringify(info), {encoding: 'utf-8'});

    log("FindItem Complete");
    logConfig.indent -= 1;
    return browser;
}

// Tests Cart functionality
async function addToCart(name, browser) {
    log("Entering addToCart");
    logConfig.indent += 1;

    const bundle = await login(name, browser);
    if (bundle == undefined) {
        log("Bundle not exist, run register first");
        logConfig.indent -= 1;
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.items == undefined) {
        log("Items undefined, run findItems first");
        logConfig.indent -= 1;
        return;
    }

    log(`Visiting ${info.items.length} items`);

    for (let url of info.items) {
        await page.goto(url);

        let choices = await page.$$("body > div:nth-child(5) > table > tbody > tr");
        if (choices.length == 0) {
            log(`No available inventory for item ${url}`);
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

    log("Exiting addToCart");
    logConfig.indent -= 1;
    return browser;
}

// Tests add fund & User edit page
async function addFund(name, bundle=undefined, browser) {
    logConfig.indent += 1;
    log(`Adding fund for ${name}`);

    if (bundle == undefined) {
        bundle = await login(name, browser);
    }

    if (bundle == undefined) {
        log("Bundle not exist, run register first");
        logConfig.indent -= 1;
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

    log(`Added $1000 for ${name}`);
    logConfig.indent -= 1;
}

// Tests place order checkout functionality
async function checkout(name, browser) {
    logConfig.indent += 1;
    log(`Checking out for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        log("Bundle not exist, run register first");
        logConfig.indent -= 1;
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    await page.goto("http://127.0.0.1:5000/cart");

    let items = await page.$$("body > div > table:nth-child(2) > tbody > tr");
    if (items.length == 0) {
        log("No items in cart, run addToCart first");
        logConfig.indent -= 1;
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

    log(`Checkout complete`);
    logConfig.indent -= 1;
    return browser;
}

// Tests Review functionality
async function makeOrderURLs(name, browser) {
    logConfig.indent += 1;

    log("Calling makeOrderURLs");
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        log("Bundle not exist, run register first");
        logConfig.indent -= 1;
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    await page.goto("http://127.0.0.1:5000/buy_history");

    let boughts = await page.$$("body > div > table > tbody > tr");

    if (boughts.length == 0) {
        log("No items bought; run checkout first");
        logConfig.indent -= 1;
        return;
    }

    let orders = await page.$$("body > div.container > table > tbody > tr > td:nth-child(7) > div > a");

    let itemURL = [];
    let sellerURL = [];

    log(`Clicking ${orders.length} buttons`);
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
    log("makeOrderURLs complete");

    logConfig.indent -= 1;
    return browser;
}

async function makeComment(name, browser) {
    logConfig.indent += 1;

    log(`Making comment for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        log("Bundle not exist, run register first");
        logConfig.indent -= 1;
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.urls == undefined) {
        log("Orders not exist");
        logConfig.indent -= 1;
        return;
    }

    log(`Creating comments for items`);
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

        await page.click("#user-review-publish-icon");
    }

    log(`Creating comments for sellers`);
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
        
        await page.click("#user-review-publish-icon");
    }

    log(`Make comment complete for ${name}`);
    logConfig.indent -= 1;
    return browser;
}

// Test upvote functionality
async function clickUpvote(name, browser) {
    logConfig.indent += 1;
    log(`Clicking Upvote for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        log("Bundle not exist, run register first");
        logConfig.indent -= 1;
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.urls == undefined) {
        log("Lacking info urls, run checkout first");
        logConfig.indent -= 1;
        return;
    }

    log("Clicking upvote for items");
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

    log(`Clicking upvote for sellers`);
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

    logConfig.indent -= 1;
    return browser;
}

// Test sell item functionality
async function makeSell(name, browser) {
    logConfig.indent += 1;
    log(`Making sell for ${name}`);
    const bundle = await login(name, browser);
    if (bundle == undefined) {
        log("Bundle not exist, run register first");
        logConfig.indent -= 1;
        return;
    }

    const page = bundle.page;
    browser = bundle.browser;
    const info = bundle.info;

    if (info.sells == undefined) {
        log(`Sells property undefined, run findItems first`);
        logConfig.indent -= 1;
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

    log("Make Sell success");

    logConfig.indent -= 1;
    return browser;
}

async function run()  {
    log(`Started Simulating for ${N_USER} users`);
    let browser = await initialize();
    for (let i = 0; i < N_USER; i++) {
        const name = `${USER_PREFIX}${i}`;
        await register(name, "123456", `Address for User ${i}`, browser);
    }

    for (let i = 0; i < N_USER; i++) {
        const name = `${USER_PREFIX}${i}`;

        let n_orders = Math.floor(Math.random() * MAX_ORDERS_PLACED) + 1;
        for (let o = 0; o < n_orders; o++) {
            await findItems(name, browser)
            .then((x) => addToCart(name, x))
            .then(x => checkout(name, x))
            .then(x => makeOrderURLs(name, x))
            .then(x => makeComment(name, x))
            .then(x => makeSell(name, x))
        }
    }

    for (let i = N_USER-1; i >= 0; i--) {
        const name = `${USER_PREFIX}${i}`;
        await clickUpvote(name, browser);
    }

    await browser.close();
    log("Finished Simulating");
}

run();
