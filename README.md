# 매장경영노트 · 수익화 파이프라인 대시보드

블로그 · 클립 · 브랜드커넥트 · 쇼핑커넥트/크리에이터샵 · 인스타 · 스레드 · 유튜브 쇼츠 · 모두의 숲 과일 위탁의
진행 상황과 수익, 다음 액션을 한 화면에 모은 정적 웹 앱입니다. 폰에서는 PWA로 설치해 앱처럼 쓸 수 있습니다.

- 라이브: https://kims1112.github.io/storenote-dashboard/
- 데이터: [`data.json`](./data.json) — **이 파일만 고치면 웹과 폰 앱에 그대로 반영됩니다.**

## 구조

```
dashboard/
├─ index.html              화면 껍데기 (데이터 없음)
├─ styles.css              디자인 시스템 · 반응형
├─ app.js                  렌더링 · 라우팅(#/채널id) · 새로고침
├─ data.json               ← 유일한 데이터 소스 (수정 지점)
├─ manifest.webmanifest    PWA 설치 정보
├─ sw.js                   서비스 워커 (data.json은 네트워크 우선, samples/는 캐시 제외)
├─ samples/v6/             v6 상세페이지 샘플 (860px 뷰포트 · GIF 3종 실제 재생)
├─ samples/template/       표준 자동화 템플릿 설명 + 실제 파일 4개 뷰어
├─ icon-*.png              앱 아이콘
├─ preview_desktop.png     검수용 미리보기 (1440×900)
└─ preview_mobile.png      검수용 미리보기 (390×844)
```

## 데이터 갱신 방법

1. `data.json`의 `meta.updated_at`, `meta.updated_label`, `meta.data_version`을 갱신합니다.
2. `kpis`, `alerts`, `timeline`, `channels[]`의 수치·문구를 실제 확인된 값으로 바꿉니다.
   - `channels[].progress`는 0~100 정수, `progress_basis`에 그 근거를 한 줄로 적습니다.
   - `status`는 `operating` · `preparing` · `waiting` 중 하나입니다.
   - `next[].owner`는 `파인` 또는 `보현님`.
3. push하면 GitHub Pages가 1~2분 안에 새로 배포합니다.

### 판매 연동 · 방문자/수익 · 제철 족보 블록 (2026-11-19 추가)

| 블록 | 쓰는 곳 | 규칙 |
|---|---|---|
| `sync` | 판매 패널 상단 칩 | `last_synced_label`(마지막 동기화 시각), `schedule`, `sources`(조회한 화면과 시각) |
| `sales` | 통합·과일 채널의 **판매계정 연동 · 판매 알림** 패널 | `new_orders_total`, `alert.level`(`idle`/`live`), `alert.badge`, `accounts[]`(주문·매출·상품상태) |
| `blog_stats` | **블로그 방문자 추이 · 예상수익 추이** 차트 | `labels`(14일), `visitors.values`, `views.values`, `revenue.sources[]`(애드포스트·쇼핑커넥트 일별, 집계 전 날은 `null`) |
| `updates` | **최신 진행 현황** 목록 | `time`, `channel`, `state`(`done`/`waiting`/`scheduled`), `title`, `detail` |
| `fruit_calendar` | **1년 제철 과일 족보 · 시기별 소싱 추천** (통합·과일 채널) | `months[]`(1~12월: `items`·`supply`·`peak`·`todo`·`prep`·`watch`), `rule`, `supplier_note`, `basis`. 강조 월은 화면을 연 날짜로 자동 계산 |

- 신규 주문이 1건 이상이면 `sales.new_orders_total`을 올리고 `alert.level`을 `live`로 바꿉니다. 배너가 붉은 알림 배지(펄스)로 바뀌고 채널별 '신규 주문 N건' 배지가 표시됩니다. 0건이면 `idle`로 두고 "신규 주문 0건 · 대기중"으로 표시합니다.
- 차트는 외부 라이브러리 없이 `app.js`가 SVG로 그립니다(폭 700 기준 viewBox, 좁은 화면은 글자·점을 키워 축소 대응). 값이 없으면 `0` 또는 `null`로 두고 **숫자를 지어내지 않습니다.**
- 정기 갱신은 예약 작업 `📊-대시보드-실데이터-동기화-및-판매알림`(매일 10:40·14:40·18:40·22:40)이 이 블록들을 직접 고쳐 push합니다.

채널의 `links[].url`에 `./samples/v6/`처럼 사이트 안 페이지를 넣으면 대시보드에서 새 탭으로 열립니다.
`url`이 비어 있으면 '작업 폴더 파일' 비활성 칩으로 표시됩니다.

```bash
cd dashboard
python3 - <<'PY'   # 수치 수정 후
import json; d=json.load(open('data.json'))
d['meta']['data_version'] += 1
json.dump(d, open('data.json','w'), ensure_ascii=False, indent=2)
PY
git add -A && git commit -m "data: 수익화 현황 갱신" && git push
```

## 로컬에서 보기

```bash
cd dashboard && python3 -m http.server 8000
# http://localhost:8000
```

`index.html`을 파일로 바로 열면 브라우저 보안 규칙 때문에 `data.json`을 읽지 못합니다. 로컬 서버나 배포 주소를 쓰세요.

## 배포

GitHub Pages (`main` 브랜치 루트). 저장소를 새로 만들 때는 아래와 같습니다.

```bash
gh repo create KIMS1112/storenote-dashboard --public --source=. --remote=origin --push
gh api -X POST repos/KIMS1112/storenote-dashboard/pages -f 'source[branch]=main' -f 'source[path]=/'
```

## 개인정보

이 저장소는 공개입니다. 공개 채널 주소·진행 상태·확인된 수치만 담고,
전화번호·이메일·비밀번호·계정 식별자·개인 주소는 넣지 않습니다.
