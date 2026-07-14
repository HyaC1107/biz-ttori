#!/usr/bin/env node

/**
 * .agents/scripts/auto-logger.js
 * 
 * Antigravity 에이전트 세션 종료 시(Stop 훅) 자동으로 
 * 오늘 날짜의 작업일지를 생성/갱신해 주는 스크립트.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '../..');
const DAILY_DIR = path.join(ROOT_DIR, 'daily');
const TEMPLATE_PATH = path.join(ROOT_DIR, '_templates/daily-template.md');

// 날짜 포맷 함수
function getFormattedDates() {
  const now = new Date();
  
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const todayStr = `${yyyy}-${mm}-${dd}`;
  
  const yymmdd = todayStr.replace(/-/g, '').substring(2);
  
  // 어제 날짜 계산
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const yesterdayYymmdd = `${yesterday.getFullYear()}`.substring(2) + 
                          String(yesterday.getMonth() + 1).padStart(2, '0') + 
                          String(yesterday.getDate()).padStart(2, '0');
                          
  // 내일 날짜 계산
  const tomorrow = new Date(now);
  tomorrow.setDate(now.getDate() + 1);
  const tomorrowYymmdd = `${tomorrow.getFullYear()}`.substring(2) + 
                         String(tomorrow.getMonth() + 1).padStart(2, '0') + 
                         String(tomorrow.getDate()).padStart(2, '0');

  return { todayStr, yymmdd, yesterdayYymmdd, tomorrowYymmdd };
}

// 깃 변경 사항 목록 수집 (projects 하위만 필터링)
function getGitChanges() {
  try {
    // staged 및 unstaged 파일명/상태 목록 수집
    const statusOutput = execSync('git status --porcelain', { cwd: ROOT_DIR, encoding: 'utf8' });
    if (!statusOutput.trim()) return [];

    const changes = [];
    const lines = statusOutput.split('\n');
    
    lines.forEach(line => {
      if (!line.trim()) return;
      
      const status = line.substring(0, 2).trim();
      const filePath = line.substring(3).trim();
      
      // projects/ 하위 소스 파일만 필터링 (daily/, .agents/ 등 제외)
      if (filePath.startsWith('projects/') && !filePath.includes('projects/README.md')) {
        changes.push({ status, path: filePath });
      }
    });

    return changes;
  } catch (err) {
    console.error('⚠️  Git 변경 사항 조회 실패:', err.message);
    return [];
  }
}

// 작업일지 생성 및 갱신 메인
function main() {
  console.log('📝 [Auto-Logger] 작업일지 자동 갱신 시작...');
  
  const { todayStr, yymmdd, yesterdayYymmdd, tomorrowYymmdd } = getFormattedDates();
  
  // daily/ 폴더가 없으면 생성
  if (!fs.existsSync(DAILY_DIR)) {
    fs.mkdirSync(DAILY_DIR, { recursive: true });
  }

  const logFilePath = path.join(DAILY_DIR, `${yymmdd}.md`);
  let content = '';
  let isNewFile = false;

  // 어제/내일 일지 파일 존재 여부 확인하여 위키링크 조건부 설정 (깨진 링크 예방)
  const yesterdayLink = fs.existsSync(path.join(DAILY_DIR, `${yesterdayYymmdd}.md`)) 
    ? `[[${yesterdayYymmdd}]]` 
    : yesterdayYymmdd;
    
  const tomorrowLink = fs.existsSync(path.join(DAILY_DIR, `${tomorrowYymmdd}.md`)) 
    ? `[[${tomorrowYymmdd}]]` 
    : tomorrowYymmdd;

  // 1. 일지 파일 로드 또는 신규 생성
  if (!fs.existsSync(logFilePath)) {
    isNewFile = true;
    console.log(`🆕 오늘 일지가 존재하지 않아 새로 생성합니다: daily/${yymmdd}.md`);
    
    if (fs.existsSync(TEMPLATE_PATH)) {
      let template = fs.readFileSync(TEMPLATE_PATH, 'utf8');
      
      // 템플릿 치환
      template = template.replace(/YYYY-MM-DD/g, todayStr);
      template = template.replace(/\[\[YYMMDD-1\]\]/g, yesterdayLink);
      template = template.replace(/\[\[YYMMDD\+1\]\]/g, tomorrowLink);
      
      content = template;
    } else {
      // 템플릿 파일이 없을 경우 기본 폴백 구조 생성
      content = `---\ndate: ${todayStr}\nprojects:\ntags: [daily]\n---\n\n[[Daily]] | ${yesterdayLink} ← → ${tomorrowLink}\n\n# 작업일지 — ${todayStr}\n\n## 오늘 한 일\n\n`;
    }
  } else {
    content = fs.readFileSync(logFilePath, 'utf8');
  }

  // 2. Git 변경 사항에 기반한 기록 내용 구성
  const gitChanges = getGitChanges();
  if (gitChanges.length === 0) {
    console.log('✅ 감지된 비즈니스 프로젝트(projects/) 변경 사항이 없어 일지를 추가 갱신하지 않습니다.');
    if (isNewFile) {
      fs.writeFileSync(logFilePath, content, 'utf8');
    }
    return;
  }

  // 프로젝트별로 변경 파일 그룹화
  const projectGroups = {};
  gitChanges.forEach(change => {
    // projects/<프로젝트명>/... 경로 추출
    const parts = change.path.split('/');
    if (parts.length >= 2) {
      const projectName = parts[1];
      if (!projectGroups[projectName]) {
        projectGroups[projectName] = [];
      }
      projectGroups[projectName].push(change);
    }
  });

  // 오늘 한 일 섹션에 작성할 마크다운 빌드
  let updates = '';
  for (const [project, files] of Object.entries(projectGroups)) {
    // 이미 일지 파일에 해당 프로젝트 명의 헤더가 있는지 검사 (중복 기재 방지)
    const headerPattern = new RegExp(`### projects/${project}`, 'i');
    if (headerPattern.test(content)) {
      console.log(`ℹ️  이미 daily/${yymmdd}.md에 'projects/${project}' 관련 기록이 있어 추가하지 않습니다.`);
      continue;
    }

    updates += `### projects/${project} — 소스 코드 자동 기록\n`;
    files.forEach(file => {
      const statusMap = { 'M': '수정', 'A': '추가', 'D': '삭제', 'R': '이름 변경' };
      const statusText = statusMap[file.status] || '변경';
      // 위키링크 깨짐 방지를 위해 대괄호 없이 절대 경로 및 상태 표기
      updates += `- [${statusText}] \`${file.path}\`\n`;
    });
    updates += '\n';
  }

  // 3. 파일 내용에 추가 기록 이식
  if (updates) {
    const todayWorkSection = '## 오늘 한 일';
    const index = content.indexOf(todayWorkSection);
    
    if (index !== -1) {
      const insertPos = index + todayWorkSection.length + 1;
      content = content.substring(0, insertPos) + '\n' + updates + content.substring(insertPos);
      
      // 메타데이터의 projects 리스트 채워주기
      const foundProjects = Object.keys(projectGroups);
      const projectsMetaPattern = /projects:\s*\[?([^\]\n]*)\]?/;
      const match = content.match(projectsMetaPattern);
      if (match) {
        let existingProjects = match[1].trim();
        let projectList = existingProjects 
          ? existingProjects.split(',').map(p => p.replace(/['"\s]/g, '')) 
          : [];
          
        foundProjects.forEach(p => {
          if (!projectList.includes(p)) {
            projectList.push(p);
          }
        });
        
        const newProjectsMeta = `projects: [${projectList.join(', ')}]`;
        content = content.replace(projectsMetaPattern, newProjectsMeta);
      }
      
      fs.writeFileSync(logFilePath, content, 'utf8');
      console.log(`🎉 daily/${yymmdd}.md에 작업 내용 갱신 완료!`);
    } else {
      console.error('❌ 일지 파일에 "## 오늘 한 일" 섹션이 존재하지 않아 본문 업데이트를 건너뜁니다.');
    }
  } else {
    if (isNewFile) {
      fs.writeFileSync(logFilePath, content, 'utf8');
    }
  }
}

main();
