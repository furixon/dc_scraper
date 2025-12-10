import sys
import re
import time
import json
import random
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from fake_useragent import UserAgent

# ---------------------------------------------------------
# 1. Helper Functions (Data Cleaning)
# ---------------------------------------------------------

def get_product_code(url: str) -> str:
    """URL에서 상품 코드를 추출합니다."""
    try:
        if "products/" in url:
            return url.split("products/")[-1].split("?")[0]
    except:
        pass
    return "unknown"

def get_num_in_str(element: str) -> int:
    """문자열에서 숫자만 추출합니다."""
    try:
        return int(re.sub(r'[^0-9]', '', element))
    except:
        return 0

def get_star_rating(element: str) -> float: 
    """style 속성(width: %)에서 별점을 계산합니다."""
    try:
        rating_percent = float(re.sub(r'[^0-9]', '', element))
        # 100% = 5점 -> 20으로 나눔
        avg_rating = round((rating_percent / 20), 2) 
        return avg_rating
    except:
        return 0.0

def replace_thumbnail_size(url: str) -> str:
    """썸네일 이미지 URL을 더 큰 사이즈로 변경합니다."""
    if not url:
        return ""
    return re.sub(r'/remote/[^/]+/image', '/remote/292x292ex/image', url)

# ---------------------------------------------------------
# 2. Driver Setup (Optimized)
# ---------------------------------------------------------

def setup_optimized_driver(proxy_ip: str = None, proxy_port: int = None) -> uc.Chrome:
    """
    Sets up the undetected_chromedriver.
    NOTE: Coupang heavily detects headless browsers. 
    Using standard GUI mode (similar to simple_coupang_crawler.py) for stability.
    """
    options = uc.ChromeOptions()
    # options.add_argument("--headless=new")  # 최신 헤드리스 모드 사용
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Add proxy if provided
    if proxy_ip and proxy_port:
        options.add_argument(f'--proxy-server={proxy_ip}:{proxy_port}')
    
    # Random User Agent
    random_ua = UserAgent().random
    options.add_argument(f'--user-agent={random_ua}')
    
    # macOS 환경 및 버전 호환성 고려 (simple_coupang_crawler.py 참고)
    driver = None
    for attempt in range(3):
        try:
            driver = uc.Chrome(
                options=options, 
                enable_cdp_events=True, 
                incognito=True, 
                version_main=142  # 설치된 Chrome 버전에 맞춰 설정
            )
            break
        except FileNotFoundError:
            # 멀티프로세싱 시 파일 경합으로 발생 가능
            time.sleep(random.uniform(1, 2))
        except Exception as e:
            if attempt == 2:
                raise e
            time.sleep(random.uniform(1, 2))
            
    return driver

# ---------------------------------------------------------
# 3. Core Crawling Logic (Single Process)
# ---------------------------------------------------------

def crawl_single_product(url: str, proxy_ip: str = None, proxy_port: int = None) -> dict:
    """
    단일 URL에 대해 독립적인 드라이버를 띄우고 정보를 수집합니다.
    프로세스별로 실행됩니다.
    """
    result = {
        "url": url,
        "status": "failed",
        "data": {},
        "error": None
    }
    
    driver = None
    try:
        driver = setup_optimized_driver(proxy_ip, proxy_port)
        
        # 페이지 로드 타임아웃 설정
        driver.set_page_load_timeout(30)
        driver.get(url)
        
        # 스마트 대기: 상품 제목이 뜰 때까지 최대 20초 대기
        wait = WebDriverWait(driver, 20)
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.product-title')))
        except TimeoutException:
            # 제목이 안 뜨면 로딩 실패로 간주
            raise Exception("Page load timeout or bot detection")

        # 데이터 추출을 위한 Dictionary
        product_dict = {}
        product_dict['product_code'] = get_product_code(url)

        # 1. Title
        try:
            title = driver.find_element(By.CSS_SELECTOR, 'h1.product-title').text
            product_dict['title'] = title
        except:
            product_dict['title'] = "N/A"

        # 2. Image
        try:
            # 이미지가 로딩되지 않았어도 src 속성은 있을 수 있음
            image_url = driver.find_element(By.CSS_SELECTOR, 'div.product-image img').get_attribute('src')
            product_dict['image_url'] = replace_thumbnail_size(image_url)
        except:
            product_dict['image_url'] = ""

        # 3. Categories
        try:
            categorys = driver.find_elements(By.CSS_SELECTOR, 'ul.breadcrumb li')
            category_list = [c.text for c in categorys[1:]] # 첫 번째는 보통 홈이므로 제외
            product_dict['categories'] = category_list
        except:
            product_dict['categories'] = []

        # 4. Rating
        try:
            el = driver.find_element(By.CSS_SELECTOR, 'span.rating-star-num').get_attribute("style")
            product_dict['star_rating'] = get_star_rating(el)
        except:
            product_dict['star_rating'] = 0.0

        # 5. Review Count
        try:
            el = driver.find_element(By.CSS_SELECTOR, 'span.rating-count-txt').text
            product_dict['review_count'] = get_num_in_str(el)
        except:
            product_dict['review_count'] = 0

        # 6. Prices
        try:
            # 정가
            sales_price_el = driver.find_elements(By.CSS_SELECTOR, 'div.price-amount.sales-price-amount')
            product_dict['original_price'] = get_num_in_str(sales_price_el[0].text) if sales_price_el else 0
            
            # 판매가
            final_price_el = driver.find_elements(By.CSS_SELECTOR, 'div.price-amount.final-price-amount')
            product_dict['final_price'] = get_num_in_str(final_price_el[0].text) if final_price_el else 0
        except:
            product_dict['original_price'] = 0
            product_dict['final_price'] = 0

        result["status"] = "success"
        result["data"] = product_dict

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
# 4. Parallel Execution Controller
# ---------------------------------------------------------

def run_parallel_crawling(urls: list, max_workers: int = None, proxy_ip: str = None, proxy_port: int = None):
    """
    주어진 URL 리스트를 병렬로 처리합니다.
    """
    if max_workers is None:
        # CPU 코어의 80% 정도만 사용 (너무 많이 띄우면 메모리 부족/차단 위험)
        max_workers = max(1, int(cpu_count() * 0.8))
    
    print(f"[INFO] Starting parallel crawling with {max_workers} workers for {len(urls)} URLs...")
    
    results = []
    start_time = time.time()

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Future 객체 생성
        future_to_url = {executor.submit(crawl_single_product, url, proxy_ip, proxy_port): url for url in urls}
        
        # 완료되는 순서대로 결과 처리
        for i, future in enumerate(as_completed(future_to_url)):
            url = future_to_url[future]
            try:
                res = future.result()
                results.append(res)
                
                # 진행 상황 출력
                status_icon = "✅" if res['status'] == "success" else "❌"
                print(f"[{i+1}/{len(urls)}] {status_icon} Processed: {url[-30:]}...")
                
            except Exception as exc:
                print(f"[{i+1}/{len(urls)}] 💥 System Error for {url}: {exc}")

    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*60)
    print(f" [CRAWLING SUMMARY]")
    print(f" - Total URLs: {len(urls)}")
    print(f" - Success: {len([r for r in results if r['status'] == 'success'])}")
    print(f" - Failed: {len([r for r in results if r['status'] == 'failed'])}")
    print(f" - Total Time: {duration:.2f} seconds")
    print("="*60 + "\n")
    
    return results

# ---------------------------------------------------------
# 5. Main Entry Point
# ---------------------------------------------------------

if __name__ == "__main__":
    # Windows 환경에서 multiprocessing 사용 시 필수
    from multiprocessing import freeze_support
    freeze_support()

    parser = argparse.ArgumentParser(description="Multi-Process Coupang Crawler")
    parser.add_argument("urls", nargs="*", help="List of Coupang product URLs separated by space")
    parser.add_argument("--file", "-f", help="File path containing URLs (one per line)", type=str)
    parser.add_argument("--workers", "-w", help="Number of parallel workers", type=int, default=None)
    parser.add_argument("--proxy-ip", help="Proxy server IP address", type=str, default=None)
    parser.add_argument("--proxy-port", help="Proxy server port", type=int, default=None)
    
    args = parser.parse_args()
    
    target_urls = []
    
    # 1. 커맨드라인 인자로 URL이 들어온 경우
    if args.urls:
        target_urls.extend(args.urls)
        
    # 2. 파일로 주어진 경우
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                file_urls = [line.strip() for line in f if line.strip()]
                target_urls.extend(file_urls)
        except Exception as e:
            print(f"[ERROR] Failed to read file: {e}")

    # 3. 아무것도 없으면 입력 받기
    if not target_urls:
        print("Enter Coupang product URLs (comma separated):")
        raw_input = input("URLs: ").strip()
        if raw_input:
            target_urls = [u.strip() for u in raw_input.split(',')]

    if target_urls:
        # [중요] 병렬 실행 전 메인 프로세스에서 드라이버를 한 번 초기화하여 
        # 바이너리 패치 및 다운로드 경쟁 상태(Race Condition)를 방지합니다.
        print("[INFO] Pre-initializing chromedriver to prevent race conditions...")
        try:
            dummy_driver = setup_optimized_driver(args.proxy_ip, args.proxy_port)
            dummy_driver.quit()
            print("[INFO] Driver initialized successfully.")
        except Exception as e:
            print(f"[WARN] Driver pre-initialization failed (will retry in workers): {e}")

        # 실행
        final_results = run_parallel_crawling(target_urls, max_workers=args.workers, proxy_ip=args.proxy_ip, proxy_port=args.proxy_port)
        
        # 결과 JSON 출력
        print(json.dumps(final_results, indent=4, ensure_ascii=False))
    else:
        print("[ERROR] No URLs provided.")
