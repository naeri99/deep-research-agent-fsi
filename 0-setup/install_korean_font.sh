#!/bin/bash

echo "한글 폰트 설치 및 matplotlib 설정을 시작합니다..."

# 나눔 폰트 설치
echo "나눔 폰트 설치 중..."
if command -v yum > /dev/null; then
    sudo yum install -y google-noto-sans-cjk-fonts || {
        echo "패키지 관리자로 설치 실패. 직접 폰트를 다운로드합니다..."
        mkdir -p ~/.fonts
        cd ~/.fonts
        curl -O https://github.com/naver/nanumfont/raw/master/NanumGothic.ttf
    }
else
    echo "yum을 찾을 수 없습니다. 직접 폰트를 다운로드합니다..."
    mkdir -p ~/.fonts
    cd ~/.fonts
    curl -O https://github.com/naver/nanumfont/raw/master/NanumGothic.ttf
fi

# 폰트 캐시 갱신
echo "폰트 캐시를 갱신합니다..."
fc-cache -f -v

# 설치된 폰트 확인
echo "설치된 나눔 폰트 목록:"
fc-list | grep -i "nanum\|noto"

# matplotlib 설정
echo "matplotlib 설정 파일 찾는 중..."
MATPLOTLIB_DIR=$(python -c "import matplotlib; print(matplotlib.get_configdir())")
MATPLOTLIB_DATA_DIR=$(python -c "import matplotlib; print(matplotlib.get_data_path())")
MATPLOTLIBRC_PATH="${MATPLOTLIB_DATA_DIR}/matplotlibrc"

echo "matplotlib 설정 파일 경로: ${MATPLOTLIBRC_PATH}"

if [ -f "$MATPLOTLIBRC_PATH" ]; then
    echo "matplotlibrc 파일 백업 및 수정 중..."
    cp "$MATPLOTLIBRC_PATH" "${MATPLOTLIBRC_PATH}.backup"
    
    if grep -q "^#font.family" "$MATPLOTLIBRC_PATH"; then
        sed -i 's/^#font.family.*/font.family: sans-serif/' "$MATPLOTLIBRC_PATH"
    elif grep -q "^font.family" "$MATPLOTLIBRC_PATH"; then
        sed -i 's/^font.family.*/font.family: sans-serif/' "$MATPLOTLIBRC_PATH"
    else
        echo "font.family: sans-serif" >> "$MATPLOTLIBRC_PATH"
    fi
    
    if grep -q "^#font.sans-serif" "$MATPLOTLIBRC_PATH"; then
        sed -i 's/^#font.sans-serif.*/font.sans-serif: NanumGothic, Noto Sans CJK KR, DejaVu Sans, sans-serif/' "$MATPLOTLIBRC_PATH"
    elif grep -q "^font.sans-serif" "$MATPLOTLIBRC_PATH"; then
        sed -i 's/^font.sans-serif.*/font.sans-serif: NanumGothic, Noto Sans CJK KR, DejaVu Sans, sans-serif/' "$MATPLOTLIBRC_PATH"
    else
        echo "font.sans-serif: NanumGothic, Noto Sans CJK KR, DejaVu Sans, sans-serif" >> "$MATPLOTLIBRC_PATH"
    fi
    
    if grep -q "^#axes.unicode_minus" "$MATPLOTLIBRC_PATH"; then
        sed -i 's/^#axes.unicode_minus.*/axes.unicode_minus: False/' "$MATPLOTLIBRC_PATH"
    elif grep -q "^axes.unicode_minus" "$MATPLOTLIBRC_PATH"; then
        sed -i 's/^axes.unicode_minus.*/axes.unicode_minus: False/' "$MATPLOTLIBRC_PATH"
    else
        echo "axes.unicode_minus: False" >> "$MATPLOTLIBRC_PATH"
    fi
else
    echo "새로운 설정 파일을 생성합니다..."
    mkdir -p "${MATPLOTLIB_DIR}"
    cat > "${MATPLOTLIB_DIR}/matplotlibrc" << EOF
font.family: sans-serif
font.sans-serif: NanumGothic, Noto Sans CJK KR, DejaVu Sans, sans-serif
axes.unicode_minus: False
EOF
    echo "새로운 설정 파일이 생성되었습니다: ${MATPLOTLIB_DIR}/matplotlibrc"
fi

# matplotlib 폰트 캐시 삭제
echo "matplotlib 폰트 캐시 삭제 중..."
rm -rf ~/.cache/matplotlib/* 2>/dev/null || echo "캐시 파일이 없거나 삭제할 수 없습니다."

echo "설정이 완료되었습니다."

# 테스트 스크립트 생성
echo "테스트 스크립트 생성 중..."
cat > test_korean_font.py << EOF
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 10, 100)
y = np.sin(x)

plt.figure(figsize=(10, 6))
plt.plot(x, y, label='사인 함수')
plt.plot(x, -y, label='-사인 함수')
plt.title('한글 테스트: 사인 함수 그래프')
plt.xlabel('x축 라벨')
plt.ylabel('y축 라벨')
plt.legend()
plt.grid(True)
plt.savefig('korean_font_test.png')
plt.show()

print("테스트 완료! korean_font_test.png 파일을 확인하세요.")
EOF

echo "테스트 스크립트가 생성되었습니다: test_korean_font.py"
echo "다음 명령어로 테스트할 수 있습니다: python test_korean_font.py"
