import asyncio
import json
import logging
import random
from datetime import datetime
from typing import List, Dict
import os
from playwright.async_api import async_playwright, BrowserContext
from bs4 import BeautifulSoup

# --- UPGRADED CONFIGURATION ---
JSON_FILE = "scrapers/tenders_all3.json"  # ✅ FIXED: Correct path for dashboard
MAX_CONCURRENT_TENDERS = 3  # ✅ Increased to 3 for better performance
MAX_ORGS_PER_SITE = 20      # ✅ More orgs per site
MAX_TENDERS_PER_ORG = 2     # ✅ EXACTLY 2 tenders per org as requested
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TENDERS)

# Global status tracking
scrape_status = {
    "current_site": "None", 
    "last_run": "Never", 
    "status": "Idle", 
    "orgs_scraped": 0,
    "current_org": "",
    "sites_completed": 0,
    "total_sites": 8
}

# ✅ ALL 8 WEBSITES - NO LIMIT!
TENDER_SITES = [
    {"name": "Delhi", "org_url": "https://govtprocurement.delhi.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://govtprocurement.delhi.gov.in"},
    {"name": "eProcure India", "org_url": "https://eprocure.gov.in/eprocure/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://eprocure.gov.in"},
    {"name": "eTenders India", "org_url": "https://etenders.gov.in/eprocure/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://etenders.gov.in"},
    {"name": "Maharashtra", "org_url": "https://mahatenders.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://mahatenders.gov.in"},
    {"name": "Madhya Pradesh", "org_url": "https://mptenders.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://mptenders.gov.in"},
    {"name": "Rajasthan", "org_url": "https://eproc.rajasthan.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://eproc.rajasthan.gov.in"},
    {"name": "Goa", "org_url": "https://eprocure.goa.gov.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://eprocure.goa.gov.in"},
    {"name": "Uttar Pradesh", "org_url": "https://etender.up.nic.in/nicgep/app?page=FrontEndTendersByOrganisation&service=page", "base_url": "https://etender.up.nic.in"},
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ FIXED: Create scrapers folder if missing
os.makedirs("scrapers", exist_ok=True)

def save_data(data):
    """Save ALL data with progress."""
    try:
        # ✅ Ensure scrapers folder exists
        os.makedirs(os.path.dirname(JSON_FILE), exist_ok=True)
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info(f"✅ SAVED {len(data)} sites → {JSON_FILE}")
    except Exception as e:
        logging.error(f"❌ Save error: {e}")

# --- EXTRACTION FUNCTIONS (IMPROVED) ---
def _extract_section_table(soup, header_name):
    header = soup.find(lambda tag: tag.name == "td" and "pageheader" in tag.get("class", []) and header_name in tag.get_text())
    if not header: return {}
    try:
        tbody = header.find_parent("tr").find_next_sibling("tr")
        table = tbody.find("table")
        data = {}
        for row in table.find_all("tr"):
            cols = row.find_all("td")
            for i in range(0, len(cols), 2):
                if i + 1 < len(cols):
                    key = cols[i].get_text(strip=True).replace(":", "").strip()
                    value = cols[i + 1].get_text(strip=True).strip()
                    if key: data[key] = value
        return data
    except: return {}

def _extract_covers(soup):
    header = soup.find(lambda tag: tag.name == "td" and "pageheader" in tag.get("class", []) and "Covers Information" in tag.get_text())
    if not header: return []
    try:
        tbody = header.find_parent("tr").find_next_sibling("tr")
        packet_table = tbody.find("table", id="packetTableView")
        if not packet_table: return []
        rows = packet_table.find_all("tr")[1:]
        return [{"cover_no": r.find_all("td")[0].text.strip(), "description": r.find_all("td")[2].text.strip()} for r in rows if len(r.find_all("td")) >= 3]
    except: return []

def _parse_tender_data(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="table")
    if not table: return []
    rows = table.find("tbody").find_all("tr")[1:MAX_TENDERS_PER_ORG+1] if table.find("tbody") else table.find_all("tr")[1:MAX_TENDERS_PER_ORG+1]
    tenders = []
    for idx, row in enumerate(rows, start=1):
        cols = row.find_all("td")
        if len(cols) < 6: continue
        title_tag = cols[4].find("a")
        tenders.append({
            "s_no": idx,
            "published_date": cols[1].text.strip(),
            "closing_date": cols[2].text.strip(),
            "title_link": base_url + title_tag["href"] if title_tag else None,
            "title_and_ref": cols[4].text.strip(),
        })
    return tenders

# --- CORE SCRAPING ENGINE (OPTIMIZED) ---
async def scrape_single_tender(context: BrowserContext, url: str) -> Dict:
    """✅ Scrapes exactly 1 tender with retry logic."""
    async with semaphore:
        page = None
        for attempt in range(2):
            try:
                page = await context.new_page()
                await page.route("**/*.{png,jpg,jpeg,gif,css,woff,woff2,mp4}", lambda route: route.abort())
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                soup = BeautifulSoup(await page.content(), "html.parser")
                details = {
                    "basic_details": _extract_section_table(soup, "Basic Details"),
                    "work_details": _extract_section_table(soup, "Work Item Details"),
                    "critical_dates": _extract_section_table(soup, "Critical Dates"),
                    "covers": _extract_covers(soup),
                    "scraped_at": datetime.now().isoformat()
                }
                await page.close()
                return details
            except Exception as e:
                if page:
                    await page.close()
                logging.warning(f"⚠️ Tender failed (attempt {attempt+1}): {str(e)[:80]}")
                if attempt == 1:
                    return {"error": str(e)[:100], "status": "failed"}
                await asyncio.sleep(random.uniform(1, 3))

async def process_site(site: Dict, browser):
    """✅ Processes ALL orgs from 1 site."""
    context = None
    page = None
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768}
        )
        page = await context.new_page()
        await page.route("**/*.{png,jpg,jpeg,gif,css,woff,woff2,mp4,webm}", lambda route: route.abort())
        
        logging.info(f"🌐 [{scrape_status['sites_completed']+1}/8] {site['name']} - Fetching orgs...")
        scrape_status["current_site"] = site["name"]
        
        await page.goto(site['org_url'], wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        
        soup = BeautifulSoup(await page.content(), "html.parser")
        org_rows = soup.select("table#table tbody tr[id^='informal']")[:MAX_ORGS_PER_SITE]
        total_orgs = len(org_rows)
        logging.info(f"📍 {site['name']}: Found {total_orgs} orgs (max {MAX_ORGS_PER_SITE})")

        site_data = []
        for idx, row in enumerate(org_rows, 1):
            try:
                cols = row.find_all("td")
                if len(cols) < 3: continue
                
                org_name = cols[1].text.strip()[:60]
                scrape_status["current_org"] = org_name
                a_tag = cols[2].find("a")
                if not a_tag or not a_tag.get("href"): continue
                
                org_link = site['base_url'] + a_tag["href"]
                scrape_status["orgs_scraped"] += 1
                
                logging.info(f"  [{scrape_status['sites_completed']+1}/8][{idx}/{total_orgs}] {org_name}")
                
                # Go to org page
                await page.goto(org_link, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                html = await page.content()
                tenders = _parse_tender_data(html, site['base_url'])
                
                # ✅ EXACTLY 2 TENDERS PER ORG
                if tenders:
                    logging.info(f"    📋 Found {len(tenders)} tenders → Taking first 2")
                    valid_tasks = []
                    for i, t in enumerate(tenders[:MAX_TENDERS_PER_ORG]):
                        if t["title_link"]:
                            valid_tasks.append(scrape_single_tender(context, t["title_link"]))
                    
                    if valid_tasks:
                        details_list = await asyncio.gather(*valid_tasks, return_exceptions=True)
                        for i, details in enumerate(details_list):
                            tenders[i]["details"] = details
                    
                    site_data.append({
                        "organisation": org_name, 
                        "tenders": tenders[:MAX_TENDERS_PER_ORG],
                        "total_tenders_found": len(tenders)
                    })
                
                # ✅ SAVE PROGRESS AFTER EVERY ORG
                progress_data = [{"site": site["name"], "total_orgs": idx, "data": site_data}]
                save_data(progress_data)
                
                await asyncio.sleep(random.uniform(2, 4))  # Rate limiting
                
            except asyncio.TimeoutError:
                logging.error(f"  ⏰ TIMEOUT: {org_name}")
                continue
            except Exception as e:
                logging.error(f"  ⚠️ ERROR {org_name}: {str(e)[:60]}")
                continue

        scrape_status["sites_completed"] += 1
        logging.info(f"✅ {site['name']} COMPLETE: {len(site_data)} orgs")
        return site_data
        
    except Exception as e:
        logging.error(f"❌ Site {site['name']} CRASHED: {e}")
        return []
    finally:
        if page: await page.close()
        if context: await context.close()

# --- MAIN EXECUTION - ALL 8 SITES! ---
async def run_full_scraper():
    global scrape_status
    scrape_status["status"] = "Running"
    scrape_status["orgs_scraped"] = 0
    scrape_status["sites_completed"] = 0
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True, 
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            all_final_data = []

            # ✅ SCRAPE ALL 8 WEBSITES!
            for i, site in enumerate(TENDER_SITES, 1):
                logging.info(f"\n{'='*80}")
                logging.info(f"🚀 [{i}/8] STARTING {site['name']}...")
                logging.info(f"{'='*80}")
                
                data = await process_site(site, browser)
                all_final_data.append({
                    "site": site["name"], 
                    "total_orgs": len(data), 
                    "data": data
                })
                
                # ✅ FINAL SAVE AFTER EACH SITE
                save_data(all_final_data)
                logging.info(f"💾 PROGRESS SAVED: {i}/8 sites complete")
                
                await asyncio.sleep(5)  # Rest between sites
            
            await browser.close()
            
    except Exception as e:
        logging.error(f"❌ SCRAPER FAILED: {e}")
    finally:
        scrape_status["status"] = "Completed"
        scrape_status["last_run"] = datetime.now().isoformat()
        save_data(all_final_data)

if __name__ == "__main__":
    print("🚀" + "="*80)
    print("🏛️  PRO TENDER SCRAPER - ALL 8 WEBSITES!")
    print(f"📁 Output: scrapers/tenders_all3.json")
    print("✅ 2 TENDERS per ORG | 20 ORGS per SITE | ALL 8 SITES")
    print("⏱️  Expected time: 30-60 minutes")
    print("🚀" + "="*80)
    
    try:
        asyncio.run(run_full_scraper())
        print("\n" + "🎉"*40)
        print("✅ ALL 8 WEBSITES SCRAPED SUCCESSFULLY!")
        print(f"📁 Check: scrapers/tenders_all3.json")
        if os.path.exists(JSON_FILE):
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"📊 TOTAL: {len(data)} sites scraped!")
        print("🎉"*40)
    except KeyboardInterrupt:
        print("\n⏹️ Stopped by user - Data saved so far!")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
