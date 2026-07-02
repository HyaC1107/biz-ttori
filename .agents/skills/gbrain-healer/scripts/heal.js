#!/usr/bin/env node

/**
 * .agents/skills/gbrain-healer/scripts/heal.js
 * 
 * 지브레인(G-Brain) 깨진 위키링크 자동 치환 및 복원 스크립트.
 * 작동 원리:
 *   1. 모든 .md 노트를 탐색해 실재 파일(Basename) 목록을 추출합니다.
 *   2. 각 노트 내부의 [[위키링크]]를 파싱하여 존재하지 않는 노트(깨진 링크)를 색출합니다.
 *   3. 깨진 링크의 이름과 현존하는 파일명 간의 유사도(Levenshtein Distance)를 측정합니다.
 *   4. 가장 유력한 매칭 후보(임계값 기준)를 찾아 자동으로 교정하거나 리포트합니다.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '../../../..');
const MAX_LEVENSHTEIN_DISTANCE = 4; // 자동 치환을 적용할 최대 편집 거리

// Levenshtein 편집 거리 알고리즘
function getLevenshteinDistance(a, b) {
  const tmp = [];
  let i, j;
  for (i = 0; i <= a.length; i++) tmp.push([i]);
  for (j = 0; j <= b.length; j++) tmp[0][j] = j;
  for (i = 1; i <= a.length; i++) {
    for (j = 1; j <= b.length; j++) {
      tmp[i][j] = Math.min(
        tmp[i - 1][j] + 1,
        tmp[i][j - 1] + 1,
        tmp[i - 1][j - 1] + (a[i - 1].toLowerCase() === b[j - 1].toLowerCase() ? 0 : 1)
      );
    }
  }
  return tmp[a.length][b.length];
}

// 재귀적으로 마크다운 파일 찾기
function getMarkdownFiles(dir, fileList = []) {
  const files = fs.readdirSync(dir);
  files.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    
    // 특정 폴더 제외 (node_modules, .git, .obsidian)
    if (stat.isDirectory()) {
      if (file !== 'node_modules' && file !== '.git' && file !== '.obsidian' && file !== '.claude' && file !== '_templates') {
        getMarkdownFiles(filePath, fileList);
      }
    } else if (file.endsWith('.md')) {
      fileList.push(filePath);
    }
  });
  return fileList;
}

function main() {
  console.log('🔍 지브레인(G-Brain) 깨진 링크 복원 시작...');
  
  const allNotes = getMarkdownFiles(ROOT_DIR);
  const basenamesMap = new Map(); // Lowercase basename -> Original File Name (without .md)
  const exactBasenames = new Set(); // Original Basenames with .md
  
  allNotes.forEach(filePath => {
    const base = path.basename(filePath);
    const nameWithoutExt = path.basename(filePath, '.md');
    basenamesMap.set(nameWithoutExt.toLowerCase(), nameWithoutExt);
    exactBasenames.add(base);
  });

  let totalLinks = 0;
  let brokenLinksCount = 0;
  let fixedLinksCount = 0;
  
  const results = [];

  allNotes.forEach(filePath => {
    let content = fs.readFileSync(filePath, 'utf8');
    const relativePath = path.relative(ROOT_DIR, filePath);
    
    // 주석 영역 및 펜스 코드블록 임시 마스킹
    let maskedContent = content
      .replace(/```[\s\S]*?```/g, m => ' '.repeat(m.length)) // Code block
      .replace(/`[^`]+`/g, m => ' '.repeat(m.length));       // Inline code

    // [[링크]] 추출 정규식
    const linkRegex = /\[\[([^\]]+)\]\]/g;
    let match;
    let hasChanges = false;

    // 수정을 위해 링크 매치 수집
    const fileMatches = [];
    while ((match = linkRegex.exec(maskedContent)) !== null) {
      const fullMatch = match[0];
      const rawTarget = match[1];
      
      // 별칭(|), 헤딩(#) 분리
      const isMedia = /\.(png|jpg|jpeg|gif|pdf)$/i.test(target);
      if (!target || target.startsWith('{') || target.startsWith('}') || target === '.' || target === '..' || isMedia) continue; // 스킵
      
      totalLinks++;
      const targetBase = path.basename(target);
      const targetWithExt = targetBase.endsWith('.md') ? targetBase : `${targetBase}.md`;

      if (!exactBasenames.has(targetWithExt)) {
        brokenLinksCount++;
        fileMatches.push({
          fullMatch,
          rawTarget,
          targetClean: targetBase,
          startIndex: match.index,
          length: fullMatch.length
        });
      }
    }

    if (fileMatches.length > 0) {
      // 뒤에서부터 치환하여 인덱스 밀림 방지
      fileMatches.sort((a, b) => b.startIndex - a.startIndex);
      
      const hasHangul = str => /[ㄱ-ㅎ|ㅏ-ㅣ|가-힣]/.test(str);

      fileMatches.forEach(item => {
        const targetLower = item.targetClean.toLowerCase();
        const targetHasHangul = hasHangul(targetLower);
        let bestMatch = null;
        let minDistance = Infinity;

        // 현존하는 모든 노트 목록과 유사도 비교
        for (const [key, val] of basenamesMap.entries()) {
          // 한글 포함 여부가 다르면 서로 비교하지 않음 (오탐 방지)
          if (targetHasHangul !== hasHangul(key)) continue;

          const dist = getLevenshteinDistance(targetLower, key);
          if (dist < minDistance) {
            minDistance = dist;
            bestMatch = val;
          }
        }

        // 단어 길이에 따른 동적 임계값 적용 (오탐 극소화)
        let allowedDistance = 1;
        if (item.targetClean.length > 5) {
          allowedDistance = 3;
        } else if (item.targetClean.length > 3) {
          allowedDistance = 2;
        }

        // 특정 임계값 내에 가장 유사한 노트가 있는 경우 자동 치환
        if (minDistance <= allowedDistance && bestMatch) {
          // 원래 별칭이나 헤딩이 있었으면 유지
          let suffix = '';
          if (item.rawTarget.includes('|')) {
            suffix = '|' + item.rawTarget.split('|').slice(1).join('|');
          } else if (item.rawTarget.includes('#')) {
            suffix = '#' + item.rawTarget.split('#').slice(1).join('#');
          }

          const resolvedLink = `[[${bestMatch}${suffix}]]`;
          
          // 실제 content에서 치환
          content = content.substring(0, item.startIndex) + resolvedLink + content.substring(item.startIndex + item.length);
          hasChanges = true;
          fixedLinksCount++;
          
          console.log(`✅ [자동 교정] ${relativePath}: \`${item.fullMatch}\` ➡️ \`${resolvedLink}\` (유사도: ${minDistance})`);
        } else {
          // 자동 치환이 불가능한 모호한 링크는 리포트 대상
          results.push({
            file: relativePath,
            link: item.fullMatch,
            clean: item.targetClean,
            rawTarget: item.rawTarget
          });
        }
      });

      if (hasChanges) {
        fs.writeFileSync(filePath, content, 'utf8');
      }
    }
  });

  console.log('\n--- 📊 치료 결과 리포트 ---');
  console.log(`전체 링크 점검: ${totalLinks}개`);
  console.log(`발견된 깨진 링크: ${brokenLinksCount}개`);
  console.log(`자동 교정 완료: ${fixedLinksCount}개`);
  console.log(`미해결 링크 (수동 검토 필요): ${results.length}개`);
  
  if (results.length > 0) {
    console.log('\n⚠️  아래 링크는 자동 복원이 어렵습니다. LLM의 지능적 판단이나 수동 수정이 필요합니다:');
    results.forEach((item, idx) => {
      console.log(`  [${idx + 1}] 파일: ${item.file} | 깨진 링크: \`${item.link}\``);
    });
    process.exit(1); // 미해결 링크 존재 시 1 반환 (젬또리 LLM이 이어서 풀 수 있도록 힌트 제공)
  } else {
    console.log('🎉 모든 [[링크]] 정상 복원 완료!');
    process.exit(0);
  }
}

main();
