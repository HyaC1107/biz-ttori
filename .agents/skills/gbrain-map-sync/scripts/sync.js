#!/usr/bin/env node

/**
 * .agents/skills/gbrain-map-sync/scripts/sync.js
 * 
 * projects/ 디렉토리를 스캔하여 memory/g-brain-map.md의 프로젝트 노드 테이블을 자동으로 동기화합니다.
 */

const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '../../../..');
const PROJECTS_DIR = path.join(ROOT_DIR, 'projects');
const MAP_FILE = path.join(ROOT_DIR, 'memory', 'g-brain-map.md');

function getProjectDirectories() {
  if (!fs.existsSync(PROJECTS_DIR)) return [];
  
  return fs.readdirSync(PROJECTS_DIR).filter(file => {
    const filePath = path.join(PROJECTS_DIR, file);
    const stat = fs.statSync(filePath);
    // 특정 제외 대상을 뺀 디렉토리만 프로젝트로 인식
    return stat.isDirectory() && file !== 'node_modules' && file !== '.git';
  });
}

function generateTable(projects) {
  let table = `| 프로젝트 | 폴더 | context | api-specs 범위 | 상태 |\n`;
  table += `|:---|:---|:---|:---|:---|\n`;
  
  if (projects.length === 0) {
    table += `| _(없음 — 첫 연동 대기)_ | — | — | — | — |\n`;
  } else {
    projects.forEach(proj => {
      // projects/README.md의 wikilink 룰에 따른 형식: [[프로젝트명/프로젝트명]]
      table += `| [[${proj}/${proj}]] | \`projects/${proj}/\` | \`projects/${proj}/context.md\` | \`projects/${proj}/api-specs.md\` | 🟢 활성 |\n`;
    });
  }
  return table;
}

function main() {
  console.log('🔄 지브레인 맵(g-brain-map) 동기화 중...');
  
  if (!fs.existsSync(MAP_FILE)) {
    console.error(`❌ 지브레인 맵 파일이 존재하지 않습니다: ${MAP_FILE}`);
    process.exit(1);
  }
  
  const projects = getProjectDirectories();
  const tableContent = generateTable(projects);
  
  let mapContent = fs.readFileSync(MAP_FILE, 'utf8');
  
  // 섹션 범위 치환
  const startHeader = '## 📂 프로젝트 노드 (실연동 시 추가)';
  const endHeader = '### 내부 툴';
  
  const startIdx = mapContent.indexOf(startHeader);
  const endIdx = mapContent.indexOf(endHeader);
  
  if (startIdx === -1 || endIdx === -1 || startIdx >= endIdx) {
    console.error('❌ g-brain-map.md의 프로젝트 노드 테이블 영역을 찾을 수 없습니다.');
    process.exit(1);
  }
  
  // 헤더 아래 개행 추가 후 테이블 삽입
  const before = mapContent.substring(0, startIdx + startHeader.length);
  const after = mapContent.substring(endIdx);
  
  const updatedContent = `${before}\n\n> 실제 활성화된 외부 프로젝트 노드 자동 동기화 목록입니다.\n\n${tableContent}\n`;
  
  fs.writeFileSync(MAP_FILE, updatedContent + after, 'utf8');
  console.log(`✅ 동기화 완료: 프로젝트 ${projects.length}개 추가됨 (${projects.join(', ')})`);
}

main();
