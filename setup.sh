#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}==================================================${NC}"
echo -e "${GREEN}       Biz-Ttori 환경 초기화 스크립트 실행         ${NC}"
echo -e "${GREEN}==================================================${NC}"

# 1. 디렉토리 구조 검증 및 생성
echo -e "\n${YELLOW}[1/4] 필수 디렉토리 확인 및 생성...${NC}"
mkdir -p keys daily agents memory _templates tools projects specs

# 2. keys/.env.example 파일 생성
echo -e "\n${YELLOW}[2/4] 환경변수 템플릿 파일 생성...${NC}"
cat <<EOT > keys/.env.example
# ==========================================
# Biz-Ttori API Keys & Environment Variables
# ==========================================

# 1. Slack Integration (보고용)
# Phase 1 단방향 알림 — Incoming Webhook URL만 있으면 됨 (봇 토큰 불필요)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
# Phase 2 양방향(슬래시커맨드/멘션)용 — 봇 앱 생성 후 발급
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
SLACK_CHANNEL_ID=C0123456789

# 2. DB Connection (풀스택 로컬/배포 검증용)
DATABASE_URL="postgresql://user:password@localhost:5432/biz_db?schema=public"

# 3. OpenAI & Gemini API Keys (챗또리 및 젬또리 예비용)
OPENAI_API_KEY=sk-proj-your-openai-api-key
GEMINI_API_KEY=AIzaSy-your-gemini-api-key
EOT

if [ ! -f keys/.env ]; then
    cp keys/.env.example keys/.env
    echo -e "${GREEN}  -> keys/.env 파일을 생성했습니다. 실제 API 키들을 여기에 입력하세요.${NC}"
else
    echo -e "${YELLOW}  -> keys/.env 파일이 이미 존재합니다. 덮어쓰지 않았습니다.${NC}"
fi

# 3. 환경 진단
echo -e "\n${YELLOW}[3/4] 시스템 환경 및 도구 진단...${NC}"

check_cmd() {
    if command -v "$1" &> /dev/null; then
        echo -e "${GREEN}  ✔ $1: $(eval "$2" 2>&1 | head -n 1)${NC}"
    else
        echo -e "${RED}  ✖ $1가 설치되어 있지 않습니다. ($3)${NC}"
    fi
}

check_cmd "node" "node -v" "Node.js v22 권장"
check_cmd "npm" "npm -v" "NPM 패키지 매니저"
check_cmd "python3" "python3 --version" "Python 3.12+"
check_cmd "uv" "uv --version" "astral uv 패키지 매니저"
check_cmd "git" "git --version" "Git 버전 관리"
check_cmd "claude" "claude --version" "npm i -g @anthropic-ai/claude-code"
check_cmd "agy" "agy --version" "pip install antigravity-cli 또는 uv tool install"
check_cmd "codex" "codex --version" "npm install -g @openai/codex"

# 4. 마무리 안내
echo -e "\n${YELLOW}[4/4] 초기화 완료!${NC}"
echo -e "${GREEN}설치가 정상적으로 완료되었습니다.${NC}"
echo -e "다음 단계를 진행해 주세요:"
echo -e " 1. ${YELLOW}keys/.env${NC} 파일을 열어 필요한 API 키와 Slack 토큰을 설정하세요."
echo -e " 2. Obsidian에서 ${YELLOW}/Users/linkcampus02/biz-ttori${NC} 폴더를 새 볼트로 연결하세요."
echo -e " 3. 터미널에서 ${GREEN}claude${NC}를 입력하여 협업 세션을 시작하세요."
echo -e "${GREEN}==================================================${NC}"
