import re
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from pymongo.errors import DuplicateKeyError
from app.db.mongo import get_gold_collection
from app.core.logger import gold_logger as logger

class GoldScraper:
    SOURCE = "LogamMulia"
    BUY_URL = "https://www.logammulia.com/id/harga-emas-hari-ini"
    SELL_URL = "https://www.logammulia.com/id/sell/gold"
    REQUEST_TIMEOUT = 15.0
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7',
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }

    # Konstanta untuk parsing
    BUY_ROW_TEXT = "1 gr"
    SELL_LABEL_PATTERN = re.compile(r'Harga Buyback', re.I)

    def __init__(self):
        self.collection = get_gold_collection()

    def scrape(self) -> bool:
        """Main entry point. Returns True if scraping and saving succeeded."""
        logger.info("Starting gold price scraping from source: %s", self.SOURCE)
        try:
            buy_html, sell_html = self._fetch_pages()
            buy_price = self._parse_buy_price(buy_html)
            sell_price = self._parse_sell_price(sell_html)
            self._validate_price(buy_price, "buy")
            self._validate_price(sell_price, "sell")

            document = self._build_document(buy_price, sell_price)
            inserted = self._save_to_db(document)
            
            if not inserted:
                return False
            
            buy_price_fmt = f"{buy_price:,}".replace(",", ".")
            sell_price_fmt = f"{sell_price:,}".replace(",", ".")
            scraped_at_fmt = document["scraped_at"].strftime("%Y-%m-%d %H:%M:%S")

            success_msg = f"✅ GOLD SCRAPER SUCCESS | {self.SOURCE} | Date: {document['market_date']} | Buy: Rp {buy_price_fmt} | Sell: Rp {sell_price_fmt} | Scraped: {scraped_at_fmt} WIB"
            logger.info(success_msg)
            
            return True
        except Exception as e:
            logger.exception("Error during gold scraping: %s", e)
            return False

    def _fetch_pages(self) -> tuple[str, str]:
        with httpx.Client(timeout=self.REQUEST_TIMEOUT, headers=self.HEADERS) as client:
            buy_resp = client.get(self.BUY_URL)
            buy_resp.raise_for_status()
            sell_resp = client.get(self.SELL_URL)
            sell_resp.raise_for_status()
        return buy_resp.text, sell_resp.text

    def _parse_buy_price(self, html: str) -> int:
        soup = BeautifulSoup(html, 'html.parser')
        # Cari baris yang mengandung "1 gr"
        td = soup.find('td', string=lambda s: s and self.BUY_ROW_TEXT in s)
        if not td:
            raise ValueError("Could not find '1 gr' row for buy price.")
        row = td.parent
        cols = row.find_all('td')
        if len(cols) < 2:
            raise ValueError("Unexpected table structure for buy prices.")
        price_text = cols[1].text.strip()
        return self._clean_price(price_text)

    def _parse_sell_price(self, html: str) -> int:
        soup = BeautifulSoup(html, 'html.parser')
        label = soup.find(string=self.SELL_LABEL_PATTERN)
        if not label:
            raise ValueError("Could not find 'Harga Buyback' label.")
        container = label.find_parent(class_='ci-child') or label.parent
        value_elem = container.find(class_='value') or container.find(string=re.compile(r'Rp', re.I))
        if not value_elem:
            raise ValueError("Could not find buyback price value.")
        price_text = value_elem.text.strip()
        return self._clean_price(price_text)

    @staticmethod
    def _clean_price(text: str) -> int:
        # Ambil hanya digit (mengabaikan Rp, titik, koma, spasi)
        digits = re.sub(r'[^0-9]', '', text)
        if not digits:
            raise ValueError(f"Could not extract numeric price from: {text}")
        return int(digits)

    @staticmethod
    def _validate_price(price: int, name: str) -> None:
        if price <= 0:
            raise ValueError(f"Invalid {name} price: {price}")

    def _build_document(self, buy_price: int, sell_price: int) -> dict:
        jakarta_now = datetime.now(ZoneInfo("Asia/Jakarta"))
        return {
            "source": self.SOURCE,
            "market_date": jakarta_now.strftime("%Y-%m-%d"),
            "buy_price": buy_price,
            "sell_price": sell_price,
            "currency": "IDR",
            "scraped_at": jakarta_now,
        }

    def _save_to_db(self, document: dict) -> bool:
        try:
            # Coba simpan data ke MongoDB
            result = self.collection.insert_one(document)
            logger.info("Inserted new gold price doc: %s", result.inserted_id)
            return True
        except DuplicateKeyError:
            # Jika data sudah ada, cetak pesan error
            msg = f"Gold price for {document['source']} ({document['market_date']}) already exists. Skip insertion."
            logger.info(msg)
            return False