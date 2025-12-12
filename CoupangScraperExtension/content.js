// Helper Functions (Python 로직 이식)

// 1. 숫자 추출
function getNumInStr(str) {
    if (!str) return 0;
    const num = str.replace(/[^0-9]/g, '');
    return parseInt(num, 10) || 0;
}

// 2. 썸네일 리사이징
function replaceThumbnailSize(url) {
    if (!url) return "";
    // 파이썬 로직: re.sub(r'/remote/[^/]+/image', '/remote/292x292ex/image', url)
    return url.replace(/\/remote\/[^/]+\/image/, '/remote/292x292ex/image');
}

// 3. 별점 계산
function getStarRating(styleStr) {
    if (!styleStr) return 0.0;
    try {
        const ratingPercent = parseFloat(styleStr.replace(/[^0-9.]/g, ''));
        // 100% = 5점 -> 20으로 나눔
        return Math.round((ratingPercent / 20) * 100) / 100;
    } catch (e) {
        return 0.0;
    }
}

// 4. 상품 코드 추출 (URL 기반)
function getProductCode() {
    const url = window.location.href;
    try {
        if (url.includes('products/')) {
            return url.split('products/')[1].split('?')[0];
        }
    } catch (e) { }
    return "unknown";
}

// 메인 크롤링 함수
function scrapeProduct() {
    console.log("[Coupang Scraper] 데이터 추출 시작...");

    const productData = {
        url: window.location.href,
        crawled_at: new Date().toISOString(),
        product_code: getProductCode(),
        title: "N/A",
        image_url: "",
        categories: [],
        star_rating: 0.0,
        review_count: 0,
        original_price: 0,
        final_price: 0
    };

    try {
        // 1. Title
        const titleEl = document.querySelector('h1.product-title');
        if (titleEl) productData.title = titleEl.innerText.trim();

        // 2. Image
        const imgEl = document.querySelector('div.product-image img');
        if (imgEl) productData.image_url = replaceThumbnailSize(imgEl.src);

        // 3. Categories
        const breadcrumbs = document.querySelectorAll('ul.breadcrumb li');
        if (breadcrumbs.length > 0) {
            // 첫 번째(Home) 제외하고 텍스트 추출
            productData.categories = Array.from(breadcrumbs)
                .slice(1)
                .map(el => el.innerText.trim());
        }

        // 4. Rating
        const ratingEl = document.querySelector('span.rating-star-num');
        if (ratingEl) {
            productData.star_rating = getStarRating(ratingEl.getAttribute('style'));
        }

        // 5. Review Count
        const reviewEl = document.querySelector('span.rating-count-txt');
        if (reviewEl) {
            productData.review_count = getNumInStr(reviewEl.innerText);
        }

        // 6. Prices
        const originalPriceEl = document.querySelector('div.price-amount.sales-price-amount');
        if (originalPriceEl) {
            productData.original_price = getNumInStr(originalPriceEl.innerText);
        }

        const finalPriceEl = document.querySelector('div.price-amount.final-price-amount');
        if (finalPriceEl) {
            productData.final_price = getNumInStr(finalPriceEl.innerText);
        }

        console.log("[Coupang Scraper] 추출 완료:", productData);
        return productData;

    } catch (e) {
        console.error("[Coupang Scraper] 에러 발생:", e);
        return null;
    }
}

// JSON 파일 다운로드 트리거
function downloadJSON(data, filename) {
    const jsonStr = JSON.stringify(data, null, 4);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    setTimeout(() => {
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }, 0);
}

// 실행 로직: 폴링(Polling) 방식으로 데이터 로드 대기
let attempts = 0;
const maxAttempts = 15; // 최대 15초 대기

const intervalId = setInterval(() => {
    attempts++;
    console.log(`[Coupang Scraper] 데이터 추출 시도 ${attempts}/${maxAttempts}...`);
    
    const data = scrapeProduct();
    
    // 성공 조건: 제목이 N/A가 아니고, 가격 정보(판매가 또는 정가)가 존재할 때
    const isValidData = data && data.title !== "N/A" && (data.final_price !== 0 || data.original_price !== 0);

    if (isValidData) {
        clearInterval(intervalId);
        const filename = `coupang_${data.product_code}.json`;
        downloadJSON(data, filename);
        console.log(`[Coupang Scraper] ${filename} 다운로드 완료`);
    } else {
        if (attempts >= maxAttempts) {
            clearInterval(intervalId);
            console.log("[Coupang Scraper] 최대 시도 횟수 초과. 유효한 상품 정보를 찾지 못했습니다.");
        }
    }
}, 1000); // 1초 간격으로 확인
