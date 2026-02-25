"""
Lazada Googlebot Lightweight Crawler v2026
=========================================
Strategy: Mimic Googlebot to access SEO-rendered content and __INIT_DATA__.
Features: Lightweight, no Playwright required.
"""

import requests
import re
import json
import logging
import random
import time
from typing import List, Dict, Optional
from urllib.parse import urlparse, urljoin

try:
    from data_engine.feature_engine import FeatureExtractor
    HAS_FEATURE_EXTRACTOR = True
except ImportError:
    HAS_FEATURE_EXTRACTOR = False

# --- Logger Setup ---
logger = logging.getLogger("lazada.googlebot")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _ch = logging.StreamHandler()
    _ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_ch)

LAZADA_BASE = "https://www.lazada.vn"

class LazadaCrawler:
    def __init__(self, limit: int = 50):
        self.limit = limit
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9"
        })

    def _normalize_url(self, raw_url: str) -> str:
        try:
            parsed = urlparse(raw_url)
            return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        except:
            return raw_url

    def _extract_json_data(self, html: str) -> Optional[Dict]:
        """Extract JSON SEO data from Lazada HTML."""
        # Try window.__INIT_DATA__
        match = re.search(r'window\.__INIT_DATA__\s*=\s*(\{.*?\});', html)
        if match:
            try:
                return json.loads(match.group(1))
            except: pass
            
        # Try script type="application/ld+json"
        matches = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        for m in matches:
            try:
                data = json.loads(m.strip())
                if isinstance(data, dict) and (data.get('@type') == 'ItemList' or 'itemListElement' in data):
                    return data
            except: pass
            
        return None

    def _parse_items(self, html: str) -> List[Dict]:
        """Extract product list from JSON or DOM."""
        data = self._extract_json_data(html)
        items = []

        if data:
            list_elements = data.get('itemListElement', [])
            for i in list_elements:
                p = i.get('item', i)
                if not p: continue
                
                name = p.get('name')
                url = p.get('url')
                image = p.get('image')
                price_val = 0
                if 'offers' in p:
                    price_val = float(p['offers'].get('price', 0))
                
                if name and url:
                    items.append({
                        "name": name,
                        "url": url if url.startswith('http') else urljoin(LAZADA_BASE, url),
                        "image": image,
                        "price": price_val / 1000 if price_val >= 1000 else price_val,
                        "itemid": re.search(r'i(\d+)\.html', url).group(1) if re.search(r'i(\d+)\.html', url) else str(random.randint(1,999999))
                    })

        if not items:
            tags = re.findall(r'href="(//www\.lazada\.vn/products/.*?\.html)".*?title="(.*?)"', html)
            for link, title in tags:
                url = "https:" + link
                items.append({
                    "name": title,
                    "url": url,
                    "price": 0,
                    "itemid": re.search(r'i(\d+)\.html', url).group(1) if re.search(r'i(\d+)\.html', url) else str(random.randint(1,999999))
                })

        return items

    def crawl(self, shop_url: str) -> List[Dict]:
        target_url = self._normalize_url(shop_url)
        logger.info(f"🚀 [Lazada] Googlebot Strategy: {target_url}")

        results = []
        page_num = 1
        
        while len(results) < self.limit:
            delim = "&" if "?" in target_url else "?"
            p_url = f"{target_url}{delim}page={page_num}"
            logger.info(f"📄 Page {page_num}...")
            
            try:
                resp = self.session.get(p_url, timeout=15)
                if resp.status_code != 200: break
                
                page_items = self._parse_items(resp.text)
                if not page_items: break
                
                new_added = 0
                existing_ids = {r['itemid'] for r in results}
                for item in page_items:
                    if item['itemid'] not in existing_ids:
                        ai = {}
                        if HAS_FEATURE_EXTRACTOR:
                            try:
                                ai = FeatureExtractor.extract(item['name']) or {}
                            except: pass
                        
                        full_record = {
                            **item,
                            "category": ai.get("category", "Other"),
                            "ai_category": ai.get("category",""),
                            "item_type":   ai.get("item_type",""),
                            "style":       ai.get("style",""),
                            "color":       ai.get("color",""),
                            "season":      ai.get("season",""),
                            "source":      "lazada"
                        }
                        results.append(full_record)
                        new_added += 1
                
                if new_added == 0: break
                logger.info(f"📊 Added {new_added} items.")
                
                page_num += 1
                time.sleep(random.uniform(1, 2))
                if page_num > 5: break
            except Exception as e:
                logger.error(f"Error: {e}")
                break

        return results[:self.limit]

def crawl_lazada_shop_url(shop_url: str, limit: int = 50) -> List[Dict]:
    crawler = LazadaCrawler(limit=limit)
    try:
        return crawler.crawl(shop_url)
    except Exception as e:
        logger.error(f"Error in crawl_lazada_shop_url: {e}")
        return []

if __name__ == "__main__":
    test_url = "https://www.lazada.vn/women-fashion-concept-store/"
    c = LazadaCrawler(limit=5)
    print(json.dumps(c.crawl(test_url), indent=2, ensure_ascii=False))
