#!/bin/bash

# UV 환경 설정 및 Jupyter 커널 등록 스크립트

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 기본값 설정
ENV_NAME="myenv"
PYTHON_VERSION="python3.12"

print_info "환경 설정을 시작합니다..."
print_info "환경 이름: $ENV_NAME"
print_info "Python 버전: $PYTHON_VERSION"

# 1. UV 설치 확인 및 자동 설치
if ! command -v uv &> /dev/null; then
    print_warning "UV가 설치되어 있지 않습니다."
    print_info "UV 설치 중..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    fi
    
    if command -v uv &> /dev/null; then
        print_success "UV가 성공적으로 설치되었습니다!"
        uv --version
    else
        print_error "UV 설치에 실패했습니다."
        exit 1
    fi
else
    print_success "UV가 이미 설치되어 있습니다."
    uv --version
fi

# 2. Python 버전 설정
print_info "Python $PYTHON_VERSION 설정 중..."
uv python pin $PYTHON_VERSION
print_success "Python $PYTHON_VERSION이 설정되었습니다."

# 3. 프로젝트 초기화
print_info "프로젝트 초기화 중..."
if [ ! -f "pyproject.toml" ]; then
    uv init --name "$ENV_NAME"
    print_success "프로젝트가 '$ENV_NAME'으로 초기화되었습니다."
else
    print_warning "이미 pyproject.toml이 존재합니다. 기존 프로젝트를 사용합니다."
fi

# 4. 필수 패키지 추가
print_info "Jupyter 관련 필수 패키지 추가 중..."
uv add ipykernel jupyter

# 5. 의존성 동기화
if [ -f "pyproject.toml" ]; then
    print_info "pyproject.toml 발견. 의존성 동기화 중..."
    uv sync
    print_success "pyproject.toml 기반으로 의존성이 설치되었습니다."
fi

# 6. 한글 폰트 설치
if [ -f "$SCRIPT_DIR/install_korean_font.sh" ]; then
    print_info "한글 폰트 설치 중..."
    bash "$SCRIPT_DIR/install_korean_font.sh"
else
    print_warning "install_korean_font.sh를 찾을 수 없습니다. 건너뜁니다."
fi

# 7. 시스템 패키지 설치
print_info "시스템 패키지 설치 중..."
sudo yum install -y poppler-utils || print_warning "poppler-utils 설치 실패 (선택사항)"

# 8. Jupyter 커널 등록
print_info "Jupyter 커널 등록 중..."
DISPLAY_NAME="$ENV_NAME (UV)"

if uv run jupyter kernelspec list 2>/dev/null | grep -q "$ENV_NAME"; then
    print_warning "기존 '$ENV_NAME' 커널을 제거합니다..."
    uv run jupyter kernelspec remove -f "$ENV_NAME" || true
fi

uv run python -m ipykernel install --user --name "$ENV_NAME" --display-name "$DISPLAY_NAME" || {
    print_error "Jupyter 커널 등록에 실패했습니다."
    exit 1
}
print_success "Jupyter 커널이 '$DISPLAY_NAME'로 등록되었습니다."

# 9. 설치 확인
print_info "설치 확인 중..."
echo ""
echo "=== 설치된 Python 버전 ==="
uv run python --version

echo ""
echo "=== 등록된 Jupyter 커널 ==="
uv run jupyter kernelspec list

# 10. 루트 디렉토리에 환경 파일 연결
print_info "루트 디렉토리에 UV 환경 파일 연결 중..."
cd ..

for file in pyproject.toml .venv uv.lock; do
    if [ -e "$file" ] && [ ! -L "$file" ]; then
        print_warning "기존 $file 파일을 ${file}.backup으로 백업합니다."
        mv "$file" "${file}.backup"
    elif [ -L "$file" ]; then
        rm -f "$file"
    fi
done

SOURCE_DIR="$(pwd)/0-setup"

ln -sf "$SOURCE_DIR/pyproject.toml" .
ln -sf "$SOURCE_DIR/.venv" .
[ -f "$SOURCE_DIR/uv.lock" ] && ln -sf "$SOURCE_DIR/uv.lock" .

print_success "루트 디렉토리에 UV 환경 파일이 연결되었습니다!"

echo ""
print_success "환경 설정이 완료되었습니다!"
echo ""
echo "=== 사용 방법 ==="
echo "1. Jupyter Lab 실행: uv run jupyter lab"
echo "2. 패키지 추가: uv add <패키지명>"
echo "3. 스크립트 실행: uv run python main.py"
echo ""
print_info "이제 루트 디렉토리에서 'uv run python main.py' 실행이 가능합니다!"
