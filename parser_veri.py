from datetime import datetime
import json
import re
import time
from dataclasses import asdict, dataclass
from typing import List, Optional
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import pytz

def convert_event_date(event_date_str: str) -> str:
    try:
        date_obj = datetime.strptime(event_date_str, "%I:%M %p ET (%m/%d/%Y)")
    except ValueError:
        date_obj = datetime.strptime(event_date_str, "%I:%M %p ET")
        date_obj = date_obj.replace(year=datetime.now().year)

    date_obj_utc = date_obj.astimezone(pytz.utc)
    return date_obj_utc.isoformat()

@dataclass
class Item:
    sport_league: str = ''
    event_date_utc: str = ''
    team1: str = ''
    team2: str = ''
    pitcher: str = ''
    period: str = ''
    line_type: str = ''
    price: str = ''
    side: str = ''
    team: str = ''
    spread: float = 0.0

def extract_data() -> List[Item]:
    chrome_options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get("https://veri.bet/odds-picks?filter=upcoming")

    data = []
    time.sleep(30)
    rows = driver.find_elements(By.CLASS_NAME, 'col-lg')

    for row in rows:
        try:
            team1, team2 = [t.text.strip() for t in row.find_elements(By.CSS_SELECTOR, "td a.text-muted span.text-muted")]
            sport_league = row.find_element(By.CSS_SELECTOR, "td span.text-muted a").text.strip()
            event_date_text = row.find_element(By.CSS_SELECTOR, "td span.badge.badge-light").text.strip()
            event_date = convert_event_date(event_date_text)

            moneylines = [m.text.strip() for m in row.find_elements(By.CSS_SELECTOR, "td:nth-child(2) span.text-muted, td:nth-child(6) span.text-muted")]
            spreads = [s.text.strip() for s in row.find_elements(By.CSS_SELECTOR, "td:nth-child(3) span.text-muted, td:nth-child(7) span.text-muted")]
            over_unders = [ou.text.strip() for ou in row.find_elements(By.CSS_SELECTOR, "td:nth-child(4) span.text-muted, td:nth-child(8) span.text-muted")]

            try:
                draw_odds = row.find_element(By.XPATH, ".//td[contains(span/text(), 'DRAW')]/span[@class='text-muted']").text.strip()
            except:
                draw_odds = None

            data.extend(_create_items(sport_league, event_date, team1, team2, moneylines, spreads, over_unders, draw_odds))
        except:
            continue

    driver.quit()
    return data

def _create_items(sport_league: str, event_date: str, team1: str, team2: str, moneylines: List[str], spreads: List[str], over_unders: List[str], draw_odds: Optional[str]) -> List[Item]:
    items = []

    items.append(Item(
        sport_league=sport_league,
        event_date_utc=event_date,
        team1=team1,
        team2=team2,
        period="FULL GAME",
        line_type="moneyline",
        price=moneylines[1],
        side=team1,
        team=team1,
        spread=0
    ))

    items.append(Item(
        sport_league=sport_league,
        event_date_utc=event_date,
        team1=team1,
        team2=team2,
        period="FULL GAME",
        line_type="moneyline",
        price=moneylines[2],
        side=team2,
        team=team2,
        spread=0
    ))

    if spreads[1] != 'N/A':
        spread_text1, spread_price1 = spreads[1].split('(')
        spread_value1 = float(re.search(r'[-+]?\d*\.?\d+', spread_text1).group())
        items.append(Item(
            sport_league=sport_league,
            event_date_utc=event_date,
            team1=team1,
            team2=team2,
            period="FULL GAME",
            line_type="spread",
            price=spread_price1.strip(')'),
            side=team1,
            team=team1,
            spread=spread_value1
        ))

    if spreads[2] != 'N/A':
        spread_text2, spread_price2 = spreads[2].split('(')
        spread_value2 = float(re.search(r'[-+]?\d*\.?\d+', spread_text2).group())
        items.append(Item(
            sport_league=sport_league,
            event_date_utc=event_date,
            team1=team1,
            team2=team2,
            period="FULL GAME",
            line_type="spread",
            price=spread_price2.strip(')'),
            side=team2,
            team=team2,
            spread=spread_value2
        ))

    if over_unders[1] != 'N/A':
        over_text1, over_price1 = over_unders[1].split('(')
        over_value1 = float(re.search(r'[-+]?\d*\.?\d+', over_text1).group())
        items.append(Item(
            sport_league=sport_league,
            event_date_utc=event_date,
            team1=team1,
            team2=team2,
            period="FULL GAME",
            line_type="over/under",
            price=over_price1.strip(')'),
            side="over",
            team="total",
            spread=over_value1
        ))

    if over_unders[2] != 'N/A':
        over_text2, over_price2 = over_unders[2].split('(')
        over_value2 = float(re.search(r'[-+]?\d*\.?\d+', over_text2).group())
        items.append(Item(
            sport_league=sport_league,
            event_date_utc=event_date,
            team1=team1,
            team2=team2,
            period="FULL GAME",
            line_type="over/under",
            price=over_price2.strip(')'),
            side="under",
            team="total",
            spread=over_value2
        ))

    if draw_odds:
        items.append(Item(
            sport_league=sport_league,
            event_date_utc=event_date,
            team1=team1,
            team2=team2,
            period="FULL GAME",
            line_type="moneyline",
            price=draw_odds.split('\n')[1],
            side="draw",
            team="draw",
            spread=0
        ))

    return items

if __name__ == "__main__":
    data = extract_data()
    if data:
        data_dicts = [asdict(item) for item in data]
        json_data = json.dumps(data_dicts, indent=4)
        with open("output.json", "w") as f:
            f.write(json_data)
    else:
        print("No data found.")