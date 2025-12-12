import undetected_chromedriver as uc
import time
import argparse
import os

def scrape_url(driver, url, download_dir, wait_time=15):
    """
    Navigates to the URL and waits for the extension to download data.
    """
    print(f"\n[Scraping] Navigating to: {url}")
    try:
        driver.get(url)
        print(f"[Wait] Waiting {wait_time} seconds for extension data extraction...")
        time.sleep(wait_time)
        print(f"[Done] Check {download_dir} for results.\n")
    except Exception as e:
        print(f"[Error] Failed to scrape {url}: {e}")

def automated_extension_crawler(initial_url: str, download_dir: str, install_mode: bool):
    """
    Main crawler loop.
    """
    # 1. Profile Setup
    profile_dir = os.path.join(os.getcwd(), "chrome_profile")
    if not os.path.exists(profile_dir):
        os.makedirs(profile_dir)

    options = uc.ChromeOptions()
    
    # 2. Extension Setup
    extension_path = os.path.abspath("CoupangScraperExtension")
    if os.path.exists(extension_path):
        options.add_argument(f"--load-extension={extension_path}")
    else:
        print(f"Warning: Extension folder not found at {extension_path}")

    # 3. Download Dir Setup
    abs_download_dir = os.path.abspath(download_dir)
    prefs = {
        "download.default_directory": abs_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": False
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-session-crashed-bubble")

    print("Initializing browser...")
    driver = None
    try:
        driver = uc.Chrome(options=options, user_data_dir=profile_dir)
        
        # --- Install Mode Logic ---
        if install_mode:
            print("Navigating to chrome://extensions for installation...")
            driver.get("chrome://extensions")
            print("\n" + "="*60)
            print(" [ 확장 프로그램 설치 가이드 ]")
            print(" 1. 우측 상단 '개발자 모드' 활성화")
            print(" 2. '압축해제된 확장 프로그램 로드' 클릭")
            print(f" 3. 선택할 폴더: {extension_path}")
            print("="*60 + "\n")
            input(">>> 설치가 완료되면 엔터(Enter)를 눌러 계속하세요...")

        # --- Initial Scrape ---
        if initial_url:
            scrape_url(driver, initial_url, abs_download_dir)

        # --- Continuous Loop (Server-like) ---
        print("="*60)
        print(" [ Interactive Mode ]")
        print(" 다음 URL을 입력하세요. (종료하려면 'q' 또는 'exit' 입력)")
        print("="*60)

        while True:
            try:
                user_input = input("URL >>> ").strip()
                if user_input.lower() in ['q', 'exit', 'quit']:
                    print("Exiting...")
                    break
                
                if not user_input:
                    continue
                
                if not user_input.startswith("http"):
                    print("Error: Invalid URL (must start with http/https)")
                    continue

                scrape_url(driver, user_input, abs_download_dir)
            
            except KeyboardInterrupt:
                print("\nInterrupted by user. Exiting...")
                break

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            print("Closing browser...")
            driver.quit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Chrome with extensions to scrape Coupang (Interactive Mode)."
    )
    # URL is now optional
    parser.add_argument(
        "url",
        nargs='?', 
        type=str,
        help="Initial Coupang Product URL (Optional)"
    )
    parser.add_argument(
        "--out",
        type=str,
        default="./downloads",
        help="Directory to save downloaded JSON files (default: ./downloads)"
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Launch in installation mode (pauses at chrome://extensions)"
    )

    args = parser.parse_args()
    
    if not os.path.exists(args.out):
        os.makedirs(args.out)
        
    automated_extension_crawler(args.url, args.out, args.install)
