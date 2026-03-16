"""
Shopee Googlebot Ultimate Crawler v2026
=======================================
Strategy: Mimic Googlebot to access SEO-rendered content and __NEXT_DATA__.
Features: Correct Price (VND*100k), Correct Links, Leaf Category Only, AI Integration.
"""

import requests
import re
import json
import logging
import random
import time
import unicodedata
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

try:
    from data_engine.feature_engine import FeatureExtractor
    HAS_FEATURE_EXTRACTOR = True
except ImportError:
    HAS_FEATURE_EXTRACTOR = False

# --- Logger Setup ---
logger = logging.getLogger("shopee.ultimate")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _ch = logging.StreamHandler()
    _ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_ch)

class ShopeeCrawler:
    def __init__(self, limit: int = 50):
        # Giới hạn tối đa 30 sản phẩm mỗi lần crawl
        self.limit = min(limit, 30)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
        })
        self.current_shopid = ""

    def _normalize_shop_url(self, raw_url: str) -> str:
        """🥇 Clean and normalize shop URL, extracting shop name."""
        try:
            parsed = urlparse(raw_url)
            path_parts = [p for p in parsed.path.strip('/').split('/') if p]
            if not path_parts: return raw_url
            
            # If it's a product link or have query params, just get the first part as shop name
            shop_name = path_parts[0]
            return f"https://shopee.vn/{shop_name}"
        except:
            return raw_url

    def _get_shop_id(self, html: str) -> Optional[str]:
        """🧩 Extract shopid from HTML (NEXT_DATA or regex)."""
        patterns = [
            r'shopid["\']?:\s*(\d+)',
            r'shop_id["\']?:\s*(\d+)',
            r'-i\.(\d+)\.',
            r'product/(\d+)/'
        ]
        for p in patterns:
            m = re.search(p, html, re.IGNORECASE)
            if m: return m.group(1)
        return None

    def _generate_slug(self, text: str) -> str:
        """Helper to create URL slug."""
        s = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
        s = re.sub(r'[^a-zA-Z0-9\s-]', '', s).lower()
        s = re.sub(r'[\s-]+', '-', s).strip('-')
        return s

    def _price(self, price_val) -> float:
        """
        Chuẩn hóa giá về đơn vị VND đầy đủ như trên Shopee.
        - 69.999 đ trên Shopee  → 69999
        - Nếu Shopee trả nội bộ 6.999.900 (x100) → chia 100 → 69999
        """
        if not price_val:
            return 0.0
        try:
            # Bước 1: chuyển về số thuần (bỏ ký tự .,₫,...)
            if isinstance(price_val, str):
                cleaned = re.sub(r"[^\d]+", "", price_val)
                num = float(cleaned) if cleaned else 0.0
            else:
                num = float(price_val)

            # Bước 2: nếu số quá lớn nhưng chia 100 ra < 1.000.000 → coi là dạng nội bộ x100
            # Ví dụ: 6_999_900 → 69_999; 4_900_000 → 49_000
            if num >= 1_000_000:
                candidate = num / 100.0
                if candidate <= 1_000_000:
                    return candidate

            # Còn lại: coi như đã là VND thật
            return num
        except Exception:
            return 0.0

    def _extract_product_links(self, html: str) -> List[str]:
        """🥉 Extract product links using regex."""
        links = []
        # Pattern 1: SEO links (-i.SHOPID.ITEMID)
        matches_seo = re.findall(r'href="(/[^"]+?-i\.(\d+)\.(\d+))', html)
        for link, sid, iid in matches_seo:
            links.append(f"https://shopee.vn/product/{sid}/{iid}")
        # Pattern 2: Standard links (/product/SHOPID/ITEMID)
        matches_std = re.findall(r'href="(/product/(\d+)/(\d+))', html)
        for link, sid, iid in matches_std:
            links.append(f"https://shopee.vn/product/{sid}/{iid}")
        return list(set(links))

    def _parse_product_detail(self, html: str, url: str) -> Optional[List[Dict]]:
        """🧬 Ultimate Parser: NEXT_DATA + LD+JSON Fallback."""
        # --- Case 1: __NEXT_DATA__ ---
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
                pinfo = data.get("props", {}).get("pageProps", {}).get("productInfo") or \
                        data.get("props", {}).get("pageProps", {}).get("item")
                if pinfo:
                    # Build variant-aware items
                    items = self._build_items_from_json(pinfo, url)
                    return items
            except: pass

        # --- Case 2: application/ld+json ---
        ld_matches = re.findall(r'<script [^>]*type="application/ld\+json"[^>]*>(.*?)</script>', html, re.DOTALL)
        ld_prod, ld_bc = None, None
        for txt in ld_matches:
            try:
                d = json.loads(txt)
                items = d if isinstance(d, list) else [d]
                for it in items:
                    if it.get("@type") == "Product": ld_prod = it
                    if it.get("@type") == "BreadcrumbList": ld_bc = it
            except: pass

        if ld_prod:
            name = ld_prod.get("name", "")
            sid, iid = self.current_shopid, ld_prod.get("productID", "")
            
            # Try extract IDs from current URL if possible
            m1 = re.search(r"-i\.(\d+)\.(\d+)", url)
            m2 = re.search(r"product/(\d+)/(\d+)", url)
            if m1: sid, iid = m1.groups()
            elif m2: sid, iid = m2.groups()

            # Price
            offers = ld_prod.get("offers", {})
            p_raw = offers.get("price", 0) if isinstance(offers, dict) else (offers[0].get("price", 0) if offers else 0)
            price_vnd = self._price(p_raw)

            # Category (Leaf Only)
            cat_leaf = "Other"
            if ld_bc:
                parts = [e.get("item", {}).get("name", "") for e in ld_bc.get("itemListElement", []) if e.get("position", 0) > 1]
                parts = [p for p in parts if p and p != name]
                if parts: cat_leaf = parts[-1]

            return [self._finalize_item(name, sid, iid, price_vnd, cat_leaf, ld_prod.get("image", ""), url)]

        return None

    def _build_item_from_json(self, item: Dict, url: str) -> Dict:
        """Helper for NEXT_DATA item."""
        name = item.get("name", "")
        iid = str(item.get("itemid", ""))
        sid = str(item.get("shopid", "")) or self.current_shopid
        
        # Price: Models or item price
        models = item.get("models", [])
        p_raw = models[0].get("price", 0) if models else item.get("price", 0)
        price_vnd = self._price(p_raw)
        
        # Category: Last in list
        cats = item.get("categories", [])
        cat_leaf = cats[-1].get("display_name", "Other") if cats else "Other"
        
        return self._finalize_item(name, sid, iid, price_vnd, cat_leaf, item.get("image", ""), url)

    def _finalize_item(self, name, shopid, itemid, price, cat_leaf, img_hash, url, variant_color: Optional[str] = None) -> Dict:
        """✨ Finalize Record: Correct Links + AI Classification."""
        sid = shopid or self.current_shopid
        slug = self._generate_slug(name)
        
        # FIX: Link chuẩn mở 100% – luôn dùng dạng /product/SHOPID/ITEMID
        # Dạng này là canonical của Shopee và luôn redirect đúng trang chi tiết.
        if sid and itemid:
            product_url = f"https://shopee.vn/product/{sid}/{itemid}"
        else:
            product_url = url

        # Image
        if img_hash and not str(img_hash).startswith("http"):
            image_url = f"https://cf.shopee.vn/file/{img_hash}"
        else:
            image_url = img_hash

        # AI: Map Shopee Leaf -> AI Category
        ai = {}
        if HAS_FEATURE_EXTRACTOR:
            try: ai = FeatureExtractor.extract(name, cat_leaf) or {}
            except: pass

        # If variant color provided, prefer that as color hint for normalization
        color_hint = variant_color or ai.get("color", "")

        # Create stable numeric variant_id when variant_color provided to avoid DB collision
        variant_id = None
        if variant_color:
            try:
                import zlib
                variant_id = int(zlib.adler32(f"{itemid}|{variant_color}".encode('utf-8')) & 0x7FFFFFFF)
            except Exception:
                variant_id = None

        return {
            "itemid": itemid,
            "variant_id": variant_id,
            "shopid": sid,
            "name": name,
            "price": price,
            "image": image_url,
            # URL chuẩn Shopee – dùng đồng nhất ở backend & frontend
            "url": product_url,
            "product_url": product_url,
            "shopee_link": product_url,
            "category": cat_leaf,
            "ai_category": ai.get("category", ""),
            "item_type": ai.get("item_type", ""),
            "style": ai.get("style", ""),
            "color": color_hint,
            "variant_color": variant_color or "",
            "season": ai.get("season", "")
        }

    def _build_items_from_json(self, item: Dict, url: str) -> List[Dict]:
        """
        Build items with color variants. Prefer color-tier images over the main image.
        """
        name = item.get("name", "")
        iid = str(item.get("itemid", ""))
        sid = str(item.get("shopid", "")) or self.current_shopid
        cats = item.get("categories", [])
        cat_leaf = cats[-1].get("display_name", "Other") if cats else "Other"
        models = item.get("models", []) or []
        tiers = item.get("tier_variations", []) or []
        all_images = item.get("images") or []

        def _resolve_img(val):
            # Shopee either returns hash or index into item.images
            if isinstance(val, str) and val:
                return val
            try:
                idx = int(val)
                if 0 <= idx < len(all_images):
                    return all_images[idx]
            except Exception:
                pass
            # fallback to main image hash
            return item.get("image", "")

        # Identify color tier index
        color_idx = None
        for idx, tv in enumerate(tiers):
            label = (tv.get("name") or "").lower()
            if any(k in label for k in ["màu", "mau", "color", "colour", "颜色", "顏色"]):
                color_idx = idx
                break
        if color_idx is None and tiers:
            # fallback: pick a tier that has images per option
            for idx, tv in enumerate(tiers):
                imgs = tv.get("images") or []
                opts = tv.get("options") or []
                if imgs and len(imgs) == len(opts):
                    color_idx = idx
                    break

        # Map color options to their image hashes
        color_options = []
        if color_idx is not None:
            tv = tiers[color_idx]
            opts = tv.get("options") or []
            imgs = tv.get("images") or []
            for i, opt in enumerate(opts):
                raw_img = imgs[i] if i < len(imgs) else item.get("image", "")
                img_hash = _resolve_img(raw_img)
                color_options.append({"index": i, "name": opt, "img": img_hash})

        results: List[Dict] = []
        if color_options:
            # Build one item per color option, choose price from models that match this color index
            for opt in color_options:
                price_for_opt = None
                for m in models:
                    tindex = m.get("tier_index") or m.get("tier_indexs") or m.get("tier_parent_index") or []
                    if isinstance(tindex, list):
                        if len(tindex) >= (color_idx + 1) and tindex[color_idx] == opt["index"]:
                            price_for_opt = self._price(m.get("price", 0))
                            break
                price_vnd = price_for_opt if price_for_opt is not None else self._price(item.get("price", 0))
                rec = self._finalize_item(name, sid, iid, price_vnd, cat_leaf, opt["img"], url, variant_color=opt["name"])
                rec["images_all"] = item.get("images") or []
                results.append(rec)
        else:
            # No color tier → single item using main image
            # Fallback: if models have names that look like colors, emit one item per model
            emitted = False
            if models:
                for m in models:
                    mname = str(m.get("name") or m.get("model_name") or "").strip()
                    if mname:
                        price_vnd = self._price(m.get("price", 0) or item.get("price", 0))
                        img_hash = item.get("image", "")
                        # Try model-specific image field if exists
                        mh = m.get("image") or m.get("img") or None
                        if mh:
                            img_hash = _resolve_img(mh)
                        rec = self._finalize_item(name, sid, iid, price_vnd, cat_leaf, img_hash, url, variant_color=mname)
                        rec["images_all"] = item.get("images") or []
                        results.append(rec)
                        emitted = True
            if not emitted:
                p_raw = models[0].get("price", 0) if models else item.get("price", 0)
                price_vnd = self._price(p_raw)
                rec = self._finalize_item(name, sid, iid, price_vnd, cat_leaf, item.get("image", ""), url)
                rec["images_all"] = item.get("images") or []
                results.append(rec)

        return results

    def crawl(self, shop_url: str) -> List[Dict]:
        """Crawl Pipeline."""
        target_url = self._normalize_shop_url(shop_url)
        logger.info(f"🚀 Processing Shop: {target_url}")

        try:
            resp = self.session.get(target_url, timeout=15)
            if resp.status_code != 200:
                logger.error(f"Failed to access shop: {resp.status_code}")
                return []
            self.current_shopid = self._get_shop_id(resp.text) or ""
        except Exception as e:
            logger.error(f"Error: {e}")
            return []

        # Find initial product
        query_params = parse_qs(urlparse(shop_url).query)
        initial_item_id = query_params.get("itemId", [None])[0]
        
        product_links = []
        if initial_item_id and self.current_shopid:
            product_links.append(f"https://shopee.vn/product/{self.current_shopid}/{initial_item_id}")

        # Additional links from page
        links = self._extract_product_links(resp.text)
        for l in links:
            if l not in product_links: product_links.append(l)

        # Pagination (simple)
        for page in range(2, 4):
            if len(product_links) >= self.limit: break
            try:
                p_resp = self.session.get(f"{target_url}?page={page}", timeout=15)
                new_links = self._extract_product_links(p_resp.text)
                if not new_links: break
                for nl in new_links:
                    if nl not in product_links: product_links.append(nl)
                time.sleep(1)
            except: break

        results = []
        sliced_links = product_links[: self.limit]
        for idx, url in enumerate(sliced_links):
            logger.info(f"📦 [{idx+1}/{len(sliced_links)}] Parsing: {url}")
            try:
                p_resp = self.session.get(url, timeout=15)
                if p_resp.status_code == 200:
                    items = self._parse_product_detail(p_resp.text, url)
                    if not items:
                        time.sleep(random.uniform(1, 2))
                        continue

                    # Bỏ sản phẩm có giá 0 hoặc thiếu giá
                    # Filter out any with invalid price
                    valid_items = []
                    for it in items if isinstance(items, list) else [items]:
                        price_val = float(it.get("price") or 0)
                        if price_val > 0:
                            valid_items.append(it)
                    if not valid_items:
                        time.sleep(random.uniform(1, 2))
                        continue

                    # Phân loại tuyệt đối: chỉ giữ sản phẩm có ai_category hợp lệ
                    # Phân loại tuyệt đối: giữ items có ai_category hợp lệ
                    filtered = []
                    for it in valid_items:
                        ai_cat = (it.get("ai_category") or "").strip()
                        if not HAS_FEATURE_EXTRACTOR or (ai_cat and ai_cat.lower() != "other"):
                            filtered.append(it)
                    if not filtered:
                        time.sleep(random.uniform(1, 2))
                        continue

                    # Merge while respecting overall limit
                    for it in filtered:
                        results.append(it)
                        if len(results) >= self.limit:
                            break
                time.sleep(random.uniform(1, 2))
            except:
                pass

            # Đảm bảo không bao giờ vượt quá self.limit
            if len(results) >= self.limit:
                break

        logger.info(f"✅ Success: {len(results)} items crawled.")
        return results

def crawl_shop_url(shop_url: str, limit: int = 50) -> List[Dict]:
    crawler = ShopeeCrawler(limit=limit)
    return crawler.crawl(shop_url)

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://shopee.vn/vierlin"
    data = crawl_shop_url(url, limit=5)
    print(json.dumps(data, indent=2, ensure_ascii=True))
