import streamlit as st
import pandas as pd
import re, time, subprocess
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# --- ensure Playwright chromium is installed ---
try:
    subprocess.run(["playwright", "install", "chromium"], check=True)
except Exception as e:
    st.write("Installing Chromium failed:", e)

# --- Config ---
HEADLESS = True
MAX_PAGES = 5
STEP_PAUSE = 0.5
WAIT_AFTER_FILTER = 1.0
TYPE_DELAY = 30
NAME_MATCH_CASE_INSENSITIVE = True

HERO_SLUGS = [
    "adam-warlock","black-panther","black-widow","blade","captain-america","cloak-and-dagger",
    "doctor-strange","emma-frost","groot","hawkeye","hela","hulk","human-torch","invisible-woman",
    "iron-fist","iron-man","jeff-the-land-shark","loki","luna-snow","magik","magneto","mantis",
    "mister-fantastic","moon-knight","namor","peni-parker","phoenix","psylocke","rocket-raccoon",
    "scarlet-witch","spider-man","squirrel-girl","star-lord","storm","the-punisher","the-thing",
    "thor","ultron","venom","winter-soldier","wolverine"
]

def norm(s): return re.sub(r"\s+"," ",(s or "").strip())

def contains(cell, target):
    if NAME_MATCH_CASE_INSENSITIVE: return target.lower() in cell.lower()
    return target in cell

def parse_table(tbl, site, hero, player):
    headers = [norm(x.inner_text()) for x in tbl.locator("thead th").all()]
    rows = []
    for r in tbl.locator("tbody tr").all():
        cells = [norm(x.inner_text()) for x in r.locator("td").all()]
        if not cells: continue
        if any(contains(c,player) for c in cells):
            rows.append({
                "site": site,
                "hero": hero,
                "row": " | ".join(cells)
            })
    return rows

def scrape_site(page, site, hero, player):
    if site=="RivalsMeta":
        url=f"https://rivalsmeta.com/characters/{hero}/leaderboard"
    else:
        url=f"https://rivalstracker.com/heroes/{hero}"
    page.goto(url,timeout=30000)
    time.sleep(0.5)
    hits=[]
    for _ in range(MAX_PAGES):
        for tbl in page.locator("table").all():
            hits.extend(parse_table(tbl,site,hero,player))
        try:
            nxt=page.locator("button:has-text('Next'), a:has-text('Next')").first
            if nxt.count()==0: break
            nxt.click(); time.sleep(STEP_PAUSE)
        except: break
    return hits

def run_scraper(player):
    rows=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=HEADLESS)
        page=browser.new_page()
        for hero in HERO_SLUGS:
            for site in ["RivalsTracker","RivalsMeta"]:
                try:
                    rows.extend(scrape_site(page,site,hero,player))
                except: pass
        browser.close()
    return pd.DataFrame(rows)

# --- Streamlit UI ---
st.title("🏆 Marvel Rivals Leaderboard Scraper")

name=st.text_input("Enter your in-game name:")
if st.button("Search"):
    if not name.strip():
        st.warning("Please enter a name first")
    else:
        st.info(f"Scanning Top-500 for {name} … this will take a few minutes")
        df=run_scraper(name.strip())
        if df.empty:
            st.error("No results found")
        else:
            st.success(f"Found {len(df)} entries")
            st.dataframe(df)
            st.download_button("Download CSV",df.to_csv(index=False).encode("utf-8"),
                               file_name=f"{name}_results.csv")
