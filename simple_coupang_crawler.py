import sys
import re
import time
import random
import json
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from fake_useragent import UserAgent

# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def setup_driver() -> uc.Chrome:
    """
    Sets up the undetected_chromedriver with appropriate options.
    """
    options = uc.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--start-maximized")
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Random User Agent
    random_ua = UserAgent().random
    options.add_argument(f'--user-agent={random_ua}')
    
    # Initialize driver. 
    # Note: explicit driver_executable_path is removed to let uc find it automatically on macOS/Linux.
    # Fix: Explicitly set version_main to 142 to match the installed Chrome version and avoid version mismatch errors.
    driver = uc.Chrome(options=options, enable_cdp_events=True, incognito=True, version_main=142)
    return driver

def get_product_code(url: str) -> str:
    """Extracts product code from the URL."""
    try:
        if "products/" in url:
            return url.split("products/")[-1].split("?")[0]
    except:
        pass
    return "unknown"

def get_num_in_str(element: str) -> int:
    """Extracts numbers from a string."""
    try:
        return int(re.sub(r'[^0-9]', '', element))
    except:
        return 0

def get_star_rating(element: str) -> float: 
    """Calculates star rating from style attribute (e.g., width: 90%)."""
    try:
        rating_percent = float(re.sub(r'[^0-9]', '', element))
        # Coupang rating width is percentage (0-100), usually mapped to 5 stars.
        # If width is 100%, it's 5 stars. 100/20 = 5.
        avg_rating = round((rating_percent / 20), 2) 
        return avg_rating
    except:
        return 0.0

def replace_thumbnail_size(url: str) -> str:
    """Changes image URL to get a larger version."""
    if not url:
        return ""
    return re.sub(r'/remote/[^/]+/image', '/remote/292x292ex/image', url)

# ---------------------------------------------------------
# Core Crawling Logic
# ---------------------------------------------------------

def get_product_info(driver: uc.Chrome, url: str) -> dict:
    """
    Extracts basic product information from the current page.
    """
    product_dict = {}
    product_code = get_product_code(url)
    product_dict['product_code'] = product_code
    product_dict['url'] = url

    try:
        # 1. Product Title
        try:
            title = driver.find_element(By.CSS_SELECTOR, 'h1.product-title').text
            product_dict['title'] = title
        except NoSuchElementException:
            product_dict['title'] = "N/A"
            print("[WARN] Could not find product title.")

        # 2. Product Image
        try:
            image_url = driver.find_element(By.CSS_SELECTOR, 'div.product-image img').get_attribute('src')
            product_dict['image_url'] = replace_thumbnail_size(image_url)
        except NoSuchElementException:
            product_dict['image_url'] = ""

        # 3. Category (Breadcrumbs)
        try:
            categorys = driver.find_elements(By.CSS_SELECTOR, 'ul.breadcrumb li')
            category_list = []
            for i in range(1, len(categorys)): # Skip 'Home' usually
                category_list.append(categorys[i].text) 
            product_dict['categories'] = category_list
        except Exception:
            product_dict['categories'] = []

        # 4. Star Rating
        try:
            el = driver.find_element(By.CSS_SELECTOR, 'span.rating-star-num').get_attribute("style")
            product_dict['star_rating'] = get_star_rating(el)
        except NoSuchElementException:
            product_dict['star_rating'] = 0.0

        # 5. Review Count
        try:
            el = driver.find_element(By.CSS_SELECTOR, 'span.rating-count-txt').text
            product_dict['review_count'] = get_num_in_str(el)
        except NoSuchElementException:
            product_dict['review_count'] = 0

        # 6. Price (Sales vs Final)
        # Sales price (Original price)
        try:
            sales_price_el = driver.find_element(By.CSS_SELECTOR, 'div.price-amount.sales-price-amount')
            product_dict['original_price'] = get_num_in_str(sales_price_el.text)
        except NoSuchElementException:
            product_dict['original_price'] = 0

        # Final price (Sale price)
        try:
            final_price_el = driver.find_element(By.CSS_SELECTOR, 'div.price-amount.final-price-amount')
            product_dict['final_price'] = get_num_in_str(final_price_el.text)
        except NoSuchElementException:
            # Sometimes there is no discount, check if there's a standard price element
            # But usually 'final-price-amount' exists. If not, it might be out of stock or different layout.
            product_dict['final_price'] = 0

    except Exception as e:
        print(f"[ERROR] Failed to extract product info: {e}")

    return product_dict

def run_crawling(url: str):
    print(f"[INFO] Starting crawler for URL: {url}")
    driver = None
    try:
        driver = setup_driver()
        driver.get(url)
        
        # Wait for page load (random sleep to be safe)
        time.sleep(random.uniform(2, 4))
        
        data = get_product_info(driver, url)
        
        print("\n" + "="*50)
        print(" [CRAWLING RESULT] ")
        print("="*50)
        print(json.dumps(data, indent=4, ensure_ascii=False))
        print("="*50 + "\n")

    except Exception as e:
        print(f"[ERROR] An error occurred during crawling: {e}")
    finally:
        if driver:
            print("[INFO] Closing driver...")
            driver.quit()

# ---------------------------------------------------------
# Main Execution
# ---------------------------------------------------------

if __name__ == "__main__":
    # Check if URL is provided via command line args
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        # Default behavior: ask for input
        print("Please enter the Coupang product URL:")
        target_url = input("URL: ").strip()

    if target_url:
        run_crawling(target_url)
    else:
        print("[ERROR] No URL provided.")
