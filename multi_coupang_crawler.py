import sys
import re
import time
import json
import random
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count, freeze_support

import undetected_chromedriver as uc
import selenium
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException
from fake_useragent import UserAgent

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def get_chrome_major_version() -> int:
    """
    Mac의 실제 Chrome 버전을 읽어서 major version만 반환.
    """
    import subprocess
    try:
        output = subprocess.check_output(
            [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "--version"
            ]
        ).decode("utf-8").strip()

        # 예: "Google Chrome 126.0.6478.183"
        ver = int(output.split()[2].split(".")[0])
        return ver
    except:
        return 120  # fallback


def get_product_code(url: str) -> str:
    try:
        if "products/" in url:
            return url.split("products/")[-1].split("?")[0]
    except:
        pass
    return "unknown"


def get_num_in_str(element: str) -> int:
    try:
        return int(re.sub(r'[^0-9]', '', element))
    except:
        return 0


def get_star_rating(element: str) -> float:
    try:
        rating_percent = float(re.sub(r'[^0-9]', '', element))
        return round((rating_percent / 20), 2)
    except:
        return 0.0


def replace_thumbnail_size(url: str) -> str:
    if not url:
        return ""
    return re.sub(r'/remote/[^/]+/image', '/remote/292x292ex/image', url)


# ---------------------------------------------------------
# Driver Setup (NEW VERSION)
# ---------------------------------------------------------

def setup_driver(proxy_ip=None, proxy_port=None):
    """
    undetected_chromedriver 세션을 매번 새롭게 만듭니다.
    Options 재사용 금지!
    """

    # Chrome version auto-detection
    major_ver = get_chrome_major_version()

    # NEW Options (매번 새로운 객체)
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized")
    # options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Random UA
    options.add_argument(f"--user-agent={UserAgent().random}")

    # Proxy
    if proxy_ip and proxy_port:
        options.add_argument(f"--proxy-server={proxy_ip}:{proxy_port}")

    # Create NEW driver
    driver = uc.Chrome(
        options=options,
        enable_cdp_events=True,
        version_main=142,
        headless=False
    )
    return driver


# ---------------------------------------------------------
# Crawl Single Product
# ---------------------------------------------------------

def crawl_single_product(url, proxy_ip=None, proxy_port=None):
    result = {
        "url": url,
        "status": "failed",
        "data": {},
        "error": None,
    }

    driver = None

    try:
        driver = setup_driver(proxy_ip, proxy_port)
        driver.set_page_load_timeout(30)
        driver.get('https://www.coupang.com/')
        time.sleep(10)
        driver.get(url)

        wait = WebDriverWait(driver, 20)

        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.product-title")))
        except TimeoutException:
            raise Exception("Coupang blocked or page load timeout")

        # 데이터 수집
        data = {}
        data["product_code"] = get_product_code(url)

        try:
            data["title"] = driver.find_element(By.CSS_SELECTOR, "h1.product-title").text
        except:
            data["title"] = ""

        try:
            img = driver.find_element(By.CSS_SELECTOR, "div.product-image img").get_attribute("src")
            data["image_url"] = replace_thumbnail_size(img)
        except:
            data["image_url"] = ""

        try:
            cats = driver.find_elements(By.CSS_SELECTOR, "ul.breadcrumb li")
            data["categories"] = [c.text for c in cats[1:]]
        except:
            data["categories"] = []

        try:
            style = driver.find_element(By.CSS_SELECTOR, "span.rating-star-num").get_attribute("style")
            data["star_rating"] = get_star_rating(style)
        except:
            data["star_rating"] = 0.0

        try:
            rc = driver.find_element(By.CSS_SELECTOR, "span.rating-count-txt").text
            data["review_count"] = get_num_in_str(rc)
        except:
            data["review_count"] = 0

        # Prices
        try:
            sp = driver.find_elements(By.CSS_SELECTOR, "div.price-amount.sales-price-amount")
            data["original_price"] = get_num_in_str(sp[0].text) if sp else 0
        except:
            data["original_price"] = 0

        try:
            fp = driver.find_elements(By.CSS_SELECTOR, "div.price-amount.final-price-amount")
            data["final_price"] = get_num_in_str(fp[0].text) if fp else 0
        except:
            data["final_price"] = 0

        result["status"] = "success"
        result["data"] = data

    except Exception as e:
        result["error"] = str(e)

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

    return result


# ---------------------------------------------------------
# Parallel Runner
# ---------------------------------------------------------

def run_parallel(urls, workers=None, proxy_ip=None, proxy_port=None):
    if workers is None:
        workers = max(1, int(cpu_count() * 0.8))

    print(f"[INFO] Running parallel crawling with {workers} workers...")

    results = []
    start = time.time()

    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_map = {
            pool.submit(crawl_single_product, u, proxy_ip, proxy_port): u for u in urls
        }

        for idx, future in enumerate(as_completed(future_map)):
            url = future_map[future]
            try:
                r = future.result()
                results.append(r)
                icon = "✅" if r["status"] == "success" else "❌"
                print(f"[{idx+1}/{len(urls)}] {icon} {url[-30:]} ...")
            except Exception as e:
                print(f"[{idx+1}] 💥 System Error: {e}")

    elapsed = time.time() - start

    print("\n===============================")
    print("SUMMARY")
    print(f"Total: {len(urls)}")
    print(f"Success: {len([x for x in results if x['status']=='success'])}")
    print(f"Failed: {len([x for x in results if x['status']=='failed'])}")
    print(f"Time: {elapsed:.2f}s")
    print("===============================")

    return results


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

if __name__ == "__main__":
    freeze_support()

    parser = argparse.ArgumentParser()
    parser.add_argument("urls", nargs="*", help="Coupang URLs")
    parser.add_argument("-f", "--file", type=str)
    parser.add_argument("-w", "--workers", type=int)
    parser.add_argument("--proxy-ip")
    parser.add_argument("--proxy-port", type=int)

    args = parser.parse_args()

    urls = []

    if args.urls:
        urls.extend(args.urls)

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            urls.extend([x.strip() for x in f if x.strip()])

    if not urls:
        print("Enter Coupang URLs (comma separated):")
        raw = input("URLs: ").strip()
        if raw:
            urls = [x.strip() for x in raw.split(",")]

    if not urls:
        print("No URLs provided.")
        sys.exit(0)

    # ★ 중요한 안정화 단계: ChromeDriver 패치 미리 만들기 (Race Condition 방지)
    print("[INFO] Pre-initializing uc Chrome...")
    try:
        d = setup_driver(args.proxy_ip, args.proxy_port)
        d.quit()
        print("[INFO] Pre-initialization OK")
    except Exception as e:
        print("[WARN] Pre-init failed:", e)

    results = run_parallel(urls, workers=args.workers, proxy_ip=args.proxy_ip, proxy_port=args.proxy_port)

    print(json.dumps(results, indent=4, ensure_ascii=False))
