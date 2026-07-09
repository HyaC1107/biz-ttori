const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const pixelmatch = require('pixelmatch');
const { PNG } = require('pngjs');

// 명령줄 인자 파싱
const args = process.argv.slice(2);
const params = {};
for (let i = 0; i < args.length; i += 2) {
  const key = args[i].replace(/^--/, '');
  const val = args[i + 1];
  params[key] = val;
}

const mode = params.mode || 'compare'; // 'before' | 'after' | 'compare'
const url = params.url || 'http://localhost:3000/admin/orderlist/payment-wait';
const selector = params.selector || 'body';
const diffLimit = parseFloat(params.diffLimit || '0.5'); // 허용 오차율 (%)

const diffDir = path.join(process.cwd(), 'visual-diff');
if (!fs.existsSync(diffDir)) {
  fs.mkdirSync(diffDir);
}

const beforeImgPath = path.join(diffDir, 'before.png');
const afterImgPath = path.join(diffDir, 'after.png');
const diffImgPath = path.join(diffDir, 'diff.png');

async function captureScreen(outputPath) {
  console.log(`🌐 브라우저 기동: ${url}`);
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
  });
  const page = await context.newPage();

  try {
    await page.goto(url, { waitUntil: 'networkidle' });
    console.log(`📸 엘리먼트 캡처 중... selector: "${selector}"`);
    const element = await page.$(selector);
    if (!element) {
      throw new Error(`선택자 "${selector}"를 페이지 내에서 찾을 수 없습니다.`);
    }
    await element.screenshot({ path: outputPath });
    console.log(`✅ 저장 완료: ${outputPath}`);
  } catch (err) {
    console.error('❌ 스크린샷 캡처 실패:', err.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
}

function compareImages() {
  console.log('🔍 이미지 대조 분석 시작...');
  if (!fs.existsSync(beforeImgPath) || !fs.existsSync(afterImgPath)) {
    console.error('❌ 대조할 before.png 또는 after.png 파일이 존재하지 않습니다. 먼저 캡처를 실행하세요.');
    process.exit(1);
  }

  const imgBefore = PNG.sync.read(fs.readFileSync(beforeImgPath));
  const imgAfter = PNG.sync.read(fs.readFileSync(afterImgPath));
  const { width, height } = imgBefore;

  if (imgAfter.width !== width || imgAfter.height !== height) {
    console.warn(`⚠️ 경고: Before 이미지(${width}x${height})와 After 이미지(${imgAfter.width}x${imgAfter.height})의 해상도가 달라 대조가 불가합니다. 레이아웃이 유실되었을 확률이 큽니다.`);
    process.exit(1);
  }

  const diff = new PNG({ width, height });
  const mismatchedPixels = pixelmatch(
    imgBefore.data,
    imgAfter.data,
    diff.data,
    width,
    height,
    { threshold: 0.1 }
  );

  fs.writeFileSync(diffImgPath, PNG.sync.write(diff));
  
  const totalPixels = width * height;
  const diffPercent = ((mismatchedPixels / totalPixels) * 100).toFixed(3);

  console.log(`📊 분석 결과:`);
  console.log(`- 전체 픽셀: ${totalPixels} px`);
  console.log(`- 불일치 픽셀: ${mismatchedPixels} px`);
  console.log(`- 변형 오차율: ${diffPercent} % (기준 임계치: ${diffLimit} %)`);
  console.log(`- 결과 이미지: ${diffImgPath}`);

  if (parseFloat(diffPercent) > diffLimit) {
    console.error(`❌ [경고] 허용 임계치(${diffLimit}%)를 초과하는 레이아웃 변형이 감지되었습니다. 롤백을 수행하세요.`);
    process.exit(1);
  } else {
    console.log(`✅ [통과] 레이아웃 정합성이 검증되었습니다. 변경 사항을 반영하셔도 좋습니다.`);
    process.exit(0);
  }
}

async function main() {
  if (mode === 'before') {
    await captureScreen(beforeImgPath);
  } else if (mode === 'after') {
    await captureScreen(afterImgPath);
  } else {
    // compare mode
    compareImages();
  }
}

main();
