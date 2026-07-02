#!/usr/bin/env node

/**
 * .agents/skills/inbox-cleaner/scripts/clean.js
 * 
 * memory/inbox.md 내용을 오늘 날짜의 daily 로그로 아카이빙하고 inbox를 깨끗이 비웁니다.
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '../../../../');
const INBOX_FILE = path.join(ROOT_DIR, 'memory', 'inbox.md');
const DAILY_DIR = path.join(ROOT_DIR, 'daily');
const TEMPLATE_FILE = path.join(ROOT_DIR, '_templates', 'daily-template.md');

// 오늘 날짜 구하기 (YYMMDD 형식)
function getTodayFilename() {
  const date = new Date();
  const yy = String(date.getFullYear()).slice(-2);
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yy}${mm}${dd}.md`;
}

// 오늘 날짜 구하기 (YYYY-MM-DD 형식)
function getTodayString() {
  const date = new Date();
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
}

// 어제/내일 파일 링크 포맷 생성용 날짜 구하기 (YYMMDD 형식)
function getRelativeDateFilename(offset) {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  const yy = String(date.getFullYear()).slice(-2);
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${yy}${mm}${dd}`;
}

function initializeDailyFile(filePath, dateStr, filenameWithoutExt) {
  const yesterday = getRelativeDateFilename(-1);
  const tomorrow = getRelativeDateFilename(1);
  
  let templateContent = '';
  if (fs.existsSync(TEMPLATE_FILE)) {
    // 템플릿 파일이 있으면 이를 읽어서 날짜 변수 치환
    templateContent = fs.readFileSync(TEMPLATE_FILE, 'utf8')
      .replace(/YYMMDD-1/g, yesterday)
      .replace(/YYMMDD\+1/g, tomorrow)
      .replace(/YYMMDD/g, filenameWithoutExt)
      .replace(/YYYY-MM-DD/g, dateStr);
  } else {
    // 템플릿이 없는 경우 기본 포맷 생성
    templateContent = `---
date: ${dateStr}
projects: []
tags: [daily]
---

[[Daily]] | [[${yesterday}]] ←

# 작업일지 — ${dateStr}

## 오늘 한 일

### [[projects/README\|projects]] — 
- 

---

## 기술 검토 / 의사결정

---

## 내일 할 일
- [ ] 

---

## Slack 보고 요약
> 
`;
  }
  
  fs.writeFileSync(filePath, templateContent, 'utf8');
}

function main() {
  console.log('🧹 우체통(inbox.md) 아카이빙 및 클리어 시작...');

  if (!fs.existsSync(INBOX_FILE)) {
    console.log('ℹ️ inbox.md 파일이 존재하지 않아 작업을 종료합니다.');
    process.exit(0);
  }

  const inboxContent = fs.readFileSync(INBOX_FILE, 'utf8').trim();
  
  // 전달 사항이 없거나 초기 비어있는 상태인 경우 아카이빙 스킵
  if (!inboxContent || inboxContent.includes('전달 사항이 없습니다') || inboxContent.length < 50) {
    console.log('ℹ️ 아카이빙할 신규 전달 사항이 없어 클리어만 유지합니다.');
    process.exit(0);
  }

  const todayFilename = getTodayFilename();
  const dailyFilePath = path.join(DAILY_DIR, todayFilename);
  const dateStr = getTodayString();
  const filenameWithoutExt = path.basename(todayFilename, '.md');

  // daily 디렉토리가 없으면 생성
  if (!fs.existsSync(DAILY_DIR)) {
    fs.mkdirSync(DAILY_DIR, { recursive: true });
  }

  // 오늘 날짜 일지 파일이 없으면 새로 생성
  if (!fs.existsSync(dailyFilePath)) {
    console.log(`📝 오늘 일지 파일 생성 중: ${todayFilename}`);
    initializeDailyFile(dailyFilePath, dateStr, filenameWithoutExt);
  }

  let dailyContent = fs.readFileSync(dailyFilePath, 'utf8');
  
  // 일지에 아카이브 밀어넣기
  const archiveHeader = '\n\n## 📬 Inbox Archive (from 젬또리)';
  const archivedReport = `${archiveHeader}\n\n\`\`\`markdown\n${inboxContent}\n\`\`\`\n`;

  // 이미 해당 아카이브가 존재하는지 검사 (중복 방지)
  if (dailyContent.includes(archiveHeader)) {
    console.log('ℹ️ 오늘 일지에 이미 보관된 내용이 있어 추가 아카이빙을 건너뜁니다.');
  } else {
    // 파일 맨 끝에 덧붙임
    fs.writeFileSync(dailyFilePath, dailyContent + archivedReport, 'utf8');
    console.log(`✅ 오늘 일지(${todayFilename}) 하단에 아카이빙 완료.`);
  }

  // inbox.md 초기화 (비우기)
  const emptyTemplate = `# 📬 젬또리 Fact-Check 전달 사항 (from Antigravity)
* **갱신 일시:** ${new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}
* **상태:** 전달 사항이 없습니다. 클또리(Claude Code)와의 다음 팩트체크 세션을 대기 중입니다.
`;
  fs.writeFileSync(INBOX_FILE, emptyTemplate, 'utf8');
  console.log('🧹 inbox.md 우체통 청소 완료!');
}

main();
