/**
 * korean-history-quiz dev 서버(http://localhost:5175)에서 실제 화면 4장 캡쳐.
 *  1) 홈(모드 선택)
 *  2) 실전 모의고사 문제 풀이(타이머)
 *  3) 답 선택 후 정답/해설
 *  4) 결과 화면
 * 콘텐츠 영역만 clip해서 assets-store/screenshots-real/ 에 저장.
 */
import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import puppeteer from "puppeteer";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "..", "assets-store", "screenshots-real");
mkdirSync(OUT, { recursive: true });

const URL = process.env.URL || "http://localhost:5175/";
const VIEWPORT = { width: 480, height: 1040, deviceScaleFactor: 2 };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function shot(page, name) {
  const path = resolve(OUT, name);
  const metrics = await page.evaluate(() => {
    const root = document.querySelector(".screen, .screen-practice") || document.body;
    const rootRect = root.getBoundingClientRect();
    const selectors = [
      ".hero", ".section", ".mode-grid", ".mode-card",
      ".primary-btn", ".round-picker", ".tabs", ".feedback-mode-toggle",
      ".practice-header", ".meta-row", ".question-grid", ".question-card",
      ".choices", ".choice", ".feedback", ".practice-body",
      ".result-card", ".result-score", ".result-actions", ".qg-result-btn",
    ];
    let maxBottom = rootRect.top;
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach((el) => {
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) return;
        const st = getComputedStyle(el);
        if (st.visibility === "hidden" || st.display === "none") return;
        if (r.bottom > maxBottom) maxBottom = r.bottom;
      });
    }
    return { x: rootRect.left, y: rootRect.top, width: rootRect.width, bottom: maxBottom };
  });
  const pad = 24;
  const clip = {
    x: Math.max(0, Math.floor(metrics.x)),
    y: Math.max(0, Math.floor(metrics.y)),
    width: Math.ceil(metrics.width),
    height: Math.max(200, Math.ceil(metrics.bottom - metrics.y + pad)),
  };
  await page.screenshot({ path, type: "png", clip, captureBeyondViewport: true });
  console.log(`saved: ${path} clip=${clip.width}x${clip.height}`);
}

async function clickByText(page, selector, text) {
  const h = await page.evaluateHandle(
    (sel, txt) => Array.from(document.querySelectorAll(sel)).find((e) => e.textContent && e.textContent.includes(txt)) || null,
    selector, text,
  );
  const el = h.asElement();
  if (!el) throw new Error(`not found: ${selector} ~ ${text}`);
  await el.click();
}

async function main() {
  const browser = await puppeteer.launch({
    headless: "new",
    defaultViewport: VIEWPORT,
    args: ["--no-sandbox", "--lang=ko-KR", "--font-render-hinting=medium"],
  });
  try {
    const page = await browser.newPage();
    await page.setExtraHTTPHeaders({ "Accept-Language": "ko-KR,ko;q=0.9" });
    await page.goto(URL, { waitUntil: "domcontentloaded" });
    await page.evaluate(() => localStorage.clear());
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForSelector(".mode-card", { timeout: 10000, visible: true });
    await sleep(400);

    // 1) 홈
    await shot(page, "01_home.png");

    // 2) 실전 모의고사(타이머) 진입
    await clickByText(page, ".mode-card", "실전 모의고사");
    await page.waitForSelector(".question-card .choice", { timeout: 8000, visible: true });
    // 자료 이미지가 있으면 로드 대기 (없는 문항도 있음)
    await sleep(700);
    await shot(page, "02_question.png");

    // 3) 답 선택 → 정답/해설 (immediate 모드 기본)
    const choices = await page.$$(".choice");
    if (choices.length) await choices[0].click();
    try {
      await page.waitForSelector(".feedback, .choice-correct", { timeout: 4000, visible: true });
    } catch {}
    await sleep(500);
    await shot(page, "03_answer.png");

    // 4) 결과 화면: 빠른 모드(10문제)로 전부 풀어서 결과 도달
    // 홈으로 복귀
    await page.evaluate(() => {
      const back = document.querySelector(".practice-header .icon-btn");
      if (back) back.click();
    });
    await page.waitForSelector(".mode-card", { timeout: 8000, visible: true });
    await sleep(300);
    // 자동 다음 문제(autoAdvance) OFF — 수동 점프와 충돌 방지
    await page.evaluate(() => {
      const sw = document.querySelector(".switch-input");
      if (sw && sw.checked) sw.click();
    });
    await sleep(200);
    // 빠른 모드 시작
    await clickByText(page, ".mode-card", "빠른 모드");
    await page.waitForSelector(".question-card .choice", { timeout: 8000, visible: true });
    await sleep(300);
    // 10문제 순차 풀이: grid 셀로 점프 → 첫 보기 선택
    const cellCount = await page.evaluate(() => document.querySelectorAll(".question-grid-cells button").length);
    for (let i = 0; i < cellCount; i++) {
      await page.evaluate((idx) => {
        const cells = document.querySelectorAll(".question-grid-cells button");
        if (cells[idx]) cells[idx].click();
      }, i);
      await sleep(150);
      await page.evaluate(() => {
        const c = document.querySelector(".question-card .choice:not([disabled])");
        if (c) c.click();
      });
      await sleep(150);
    }
    // 결과 보기
    await sleep(300);
    await page.evaluate(() => {
      const b = document.querySelector(".qg-result-btn")
        || Array.from(document.querySelectorAll("button")).find((x) => /결과/.test(x.textContent || ""));
      if (b) { b.scrollIntoView({ block: "center" }); b.click(); }
    });
    await page.waitForSelector(".result-card", { timeout: 6000, visible: true });
    await sleep(500);
    await shot(page, "04_result.png");
  } finally {
    await browser.close();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
