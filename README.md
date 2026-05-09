# 🩺 건강 관리 대시보드

노션 페이지 데이터를 자동으로 읽어 GitHub Pages에 시각화 대시보드를 띄우는 프로젝트입니다.

## 동작 구조

```
노션 페이지 수정
    ↓ (매일 자정 or 수동 실행)
GitHub Actions → fetch_notion.py 실행
    ↓
노션 API에서 테이블 데이터 읽기
    ↓
data.json 업데이트 & push
    ↓
GitHub Pages index.html이 data.json 읽어 차트 렌더링
    ↓
노션 /embed 블록에서 실시간 표시
```

---

## 셋업 방법 (5단계)

### 1. 노션 API 토큰 발급

1. https://www.notion.so/my-integrations 접속
2. **New integration** 클릭
3. 이름 입력 (예: `health-dashboard`) → Submit
4. **Internal Integration Token** 복사 (나중에 사용)

### 2. 노션 페이지에 Integration 연결

1. 건강 관리 대시보드 노션 페이지 열기
2. 우측 상단 `...` → **Connect to** → 방금 만든 Integration 선택

### 3. GitHub 리포지토리 생성 & 파일 업로드

1. GitHub에서 새 **Public** 리포지토리 생성 (예: `health-dashboard`)
2. 이 폴더의 파일 전체를 업로드:
   - `index.html`
   - `fetch_notion.py`
   - `data.json`
   - `.github/workflows/update.yml`

### 4. GitHub Secrets 설정

리포지토리 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 값 |
|------------|-----|
| `NOTION_TOKEN` | 1단계에서 복사한 토큰 |
| `NOTION_PAGE_ID` | 노션 페이지 URL의 마지막 32자리 (예: `35bcebc2591981399191e361c3567d25`) |

### 5. GitHub Pages 활성화

리포지토리 → **Settings** → **Pages**  
→ Source: **Deploy from a branch**  
→ Branch: `main` / `/ (root)` → **Save**

---

## 첫 실행 (수동)

리포지토리 → **Actions** 탭 → **Sync Notion Data** → **Run workflow**

완료 후 `https://{GitHub유저명}.github.io/{리포이름}/` 접속해서 확인!

---

## 노션에 임베드

1. 노션 페이지에서 `/embed` 입력
2. GitHub Pages URL 붙여넣기
3. **Embed link** 클릭

---

## 자동 업데이트 주기

현재 설정: **매일 자정 UTC (한국시간 오전 9시)**

변경하려면 `.github/workflows/update.yml`의 cron 값 수정:
```yaml
- cron: '0 15 * * *'  # 한국시간 자정 (UTC 15:00)
```

---

## 노션 페이지 수정 시 주의

`fetch_notion.py`는 아래 규칙으로 테이블을 파싱합니다:

- **콜레스테롤 표**: 헤딩에 "콜레스테롤" 또는 "혈관" 포함 → 행이 항목(HDL/LDL/총/중성), 열이 기간
- **간 혹 표**: 헤딩에 "간 혹" 포함 → 행이 항목(크기), 열이 기간
- **유방 혹 표**: 헤딩에 "유방" 포함 → 행이 항목(크기/판정/비고), 열이 기간
- **검진 일정 표**: 헤딩에 "검진" 또는 "일정" 포함

테이블 구조(행=항목, 열=기간)를 유지하면 자동으로 파싱됩니다.
