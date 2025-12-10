# DE_Toy_Project: Coupang Crawler Context

## 1. 프로젝트 개요
이 프로젝트는 쿠팡(Coupang)의 상품 페이지에서 주요 정보를 수집하는 하이브리드 크롤링 솔루션입니다.
1. **Python Crawler**: `undetected_chromedriver`를 사용하여 대량의 데이터를 서버/로컬 환경에서 수집 (단일 및 멀티 프로세싱 지원).
2. **Chrome Extension**: 사용자가 브라우저로 상품 페이지를 방문할 때 자동으로 데이터를 추출하여 JSON으로 저장하는 보조 도구.

## 2. 주요 파일 및 역할
| 파일/폴더명 | 역할 | 특징 |
|---|---|---|
| `simple_coupang_crawler.py` | 단일 URL 크롤링 (Python) | 단일 스레드, 대화형 입력 또는 CLI 인자 처리. 디버깅용. |
| `multi_coupang_crawler.py` | 대량 URL 병렬 크롤링 (Python) | `ProcessPoolExecutor` 기반 멀티프로세싱. 파일 입력 지원. **Chrome Option(User-Agent) 설정 최적화 완료.** |
| `CoupangScraperExtension/` | 크롬 확장 프로그램 소스 | `manifest.json` (V3), `content.js` (추출 로직). 브라우저 직접 실행용. |

## 3. 기술 스택 및 라이브러리
- **Python**: Python 3.10+
- **Browser Automation (Python)**: `undetected-chromedriver` (Selenium Wrapper)
- **Browser Extension**: JavaScript (ES6+), Chrome Manifest V3
- **Utilities**: `fake_useragent`, `multiprocessing`, `argparse`

## 4. 크롤링 로직 상세 (Common Logic)
Python 크롤러와 Chrome Extension 모두 동일한 CSS Selector 전략을 사용하여 일관된 데이터를 수집합니다.

| 필드명 | CSS Selector | 데이터 처리 로직 |
|---|---|---|
| **상품명** (`title`) | `h1.product-title` | 텍스트 추출 |
| **이미지** (`image_url`) | `div.product-image img` (src) | 썸네일 리사이징 (`/remote/292x292ex/image` 로 변경) |
| **카테고리** (`categories`) | `ul.breadcrumb li` | 리스트로 추출 ('Home' 제외) |
| **별점** (`star_rating`) | `span.rating-star-num` (style) | `width: N%` 파싱 -> N / 20 계산 (5점 만점 환산) |
| **리뷰 수** (`review_count`) | `span.rating-count-txt` | 숫자만 정규식 추출 (`re.sub(r'[^0-9]', ...)`)|
| **정가** (`original_price`) | `div.price-amount.sales-price-amount` | 숫자만 추출 |
| **판매가** (`final_price`) | `div.price-amount.final-price-amount` | 숫자만 추출 |
| **상품코드** (`product_code`) | URL 파싱 | URL의 `products/` 뒷부분 추출 |

## 5. Python 크롤러 실행 방법

### Simple Crawler
```bash
python simple_coupang_crawler.py "https://www.coupang.com/vp/products/..."
```

### Multi Crawler (권장)
```bash
# 파일 입력 (urls.txt: 한 줄에 URL 하나)
python multi_coupang_crawler.py --file urls.txt --workers 4

# 직접 URL 입력
python multi_coupang_crawler.py "url1" "url2"
```

## 6. Chrome Extension 실행 방법
Python 크롤러가 차단되거나, 브라우징 중 간편하게 데이터를 수집하고 싶을 때 사용합니다.

### 6.1 설치
1. Chrome 주소창에 `chrome://extensions/` 입력.
2. 우측 상단 **'개발자 모드(Developer mode)'** 활성화.
3. **'압축해제된 확장 프로그램을 로드합니다(Load unpacked)'** 클릭.
4. 프로젝트 폴더 내 `CoupangScraperExtension` 디렉토리 선택.

### 6.2 사용
1. 쿠팡 상품 상세 페이지(`.../vp/products/...`) 접속.
2. 페이지 로드 완료 후 약 **2초 뒤** 자동으로 크롤링 수행.
3. `coupang_{상품코드}.json` 파일이 브라우저 다운로드 경로에 저장됨.

## 7. 최근 변경 이력 (History)
- **2025-12-09**: 
  - `multi_coupang_crawler.py`: Chrome Option 내 `user-agent` 인자 오타 수정 (`user-agent` -> `--user-agent`). DNS 오류 및 접속 불가 현상 해결.
  - `CoupangScraperExtension`: JavaScript 기반의 크롬 확장 프로그램 신규 추가 (자동 JSON 추출).

## 8. 주의 사항
- **Headless 모드**: 쿠팡의 강력한 탐지로 인해 Python 크롤러는 Headless 모드 비활성화(GUI 모드) 상태로 동작합니다.
- **Chrome 버전**: `undetected_chromedriver` 사용 시 로컬 Chrome 버전과 `version_main` 파라미터가 일치해야 할 수 있습니다 (현재 142 설정).
- **Extension**: 확장 프로그램은 켜져 있는 동안 접속하는 모든 상품 페이지에서 다운로드를 시도하므로, 사용하지 않을 때는 비활성화하는 것을 권장합니다.