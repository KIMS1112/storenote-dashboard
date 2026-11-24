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
├─ app.js                  렌더링 · 라우팅(#/채널id · #/radar · #/board) · 새로고침
├─ generator.html          과일 상세·마진 원클릭 생성기 (100% 브라우저, 서버 전송 없음)
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
| `fruitAutomation` | 과일 채널의 **과일 자동발주 · 순수익** 패널 | `engine`(엔진 버전·조회 기간·카탈로그 SKU 수·`sources[]` 연동 상태), `kpi`(이번 달 주문·매출·도매원가·수수료·광고비·순수익·마진율), `suppliers[]`(도매처별 집계), `skuMatch[]`, `simulation[]`(품목×채널 예상 마진), `monthly[]`, `recentOrders[]`, `adSpend`, `pending[]`, `notes[]`. **`work/fruit_automation/sync_orders.py --sync-dashboard` 가 생성합니다 — 손으로 고치지 않습니다.** |
| `radar` | **수익화 레이더** (`#/radar`, 통합 화면 요약) | `items[]`: `type`(`brand`/`cpa`/`clip`/`fruit`/`support`)·`title`·`org`·`deadline`(YYYY-MM-DD, 없으면 상시)·`window`·`reward`·`reward_value`·`state`(`decide`/`running`/`open`/`soon`)·`status`·`owner`·`action`·`note`·`link`·`priority`. D-day는 저장하지 않고 **화면을 연 날짜로 자동 계산** |
| `board` | **진행 작업 보드** (`#/board`) | `columns[]`(`doing`/`waiting`/`done`)와 `tasks[]`: `status`·`title`·`owner`·`channel`(채널 id)·`due`·`due_label`·`detail`·`progress`(0~100, 선택)·`scheduled`(예약 작업 이름) |

### 과일 자동발주 · 순수익 엔진 (`work/fruit_automation/sync_orders.py`)

과일 채널의 `fruitAutomation` 블록은 이 엔진이 만듭니다. 데이터 소스는 셋입니다.

| 소스 | 내용 | 막히면 |
|---|---|---|
| 쿠팡 Open API | 발주서(v5 `ordersheets`) — 상품명·수량·결제가·배송비·취소수량 | `403` 호출 IP 미허용이면 연동 상태에 그대로 표시 |
| 네이버 커머스 API | 변경 주문 → `/v1/pay-order/seller/product-orders/query` 상세(옵션명·결제금액) | 동일 (`GW.IP_NOT_ALLOWED`) |
| `orders_manual.json` | 판매센터 화면에서 직접 확인해 적은 주문 | 항상 동작 |

- 매칭·계산: `wholesale_catalog.json` 의 SKU(키워드·`notMatch`) → 업체별 공급가 중 최저가 → 수수료(쿠팡 11.66%·스마트스토어 5.63%, 상품금액 기준) − 공급가(택배 포함) − 배분 광고비(`ad_spend.json`) = 순수익·마진율.
- **확인되지 않은 값은 0으로 채우지 않습니다.** 광고비 `amount` 가 `null` 이면 「집행액 미확인」으로 표시하고, 매칭 실패 주문은 순수익을 `null`(—)로 둡니다.
- `simulation[]` 은 카탈로그 공급가 × **실제 판매 옵션가**로 계산한 예상치이며 실적이 아닙니다. 화면에도 「예상」으로 표시합니다.
- API가 모두 막힌 회차에는 과일 채널의 `오늘 신규 주문` 지표를 덮어쓰지 않습니다(화면 실측값 보존).

```bash
cd work/fruit_automation
python3 test_sync_orders.py -v          # 모의 주문 27개 테스트
python3 sync_orders.py                  # 최근 7일 조회 → latest_sync.json
python3 sync_orders.py --sync-dashboard # dashboard/data.json 의 fruitAutomation 갱신
python3 sync_orders.py --no-fetch --sync-dashboard   # API 없이 장부·카탈로그만으로 갱신
```

`sync_orders.py` 가 `data.json` 을 쓸 때는 `meta.updated_label`·`data_version` 도 함께 올립니다. `.env`(API 키)는 이 폴더에만 있고 저장소로 복사하지 않습니다.

- 신규 주문이 1건 이상이면 `sales.new_orders_total`을 올리고 `alert.level`을 `live`로 바꿉니다. 배너가 붉은 알림 배지(펄스)로 바뀌고 채널별 '신규 주문 N건' 배지가 표시됩니다. 0건이면 `idle`로 두고 "신규 주문 0건 · 대기중"으로 표시합니다.
- 차트는 외부 라이브러리 없이 `app.js`가 SVG로 그립니다(폭 700 기준 viewBox, 좁은 화면은 글자·점을 키워 축소 대응). 값이 없으면 `0` 또는 `null`로 두고 **숫자를 지어내지 않습니다.**
- 정기 갱신은 예약 작업 `📊-대시보드-실데이터-동기화-및-판매알림`(매일 10:40·14:40·18:40·22:40)이 이 블록들을 직접 고쳐 push합니다.
- `radar`·`board`는 동기화 작업이 손대지 않는 별도 블록입니다. 마감이 지난 기회도 지우지 말고 두면 D-day가 `마감`으로 바뀌며 흐리게 표시됩니다.
- 화면에 새 섹션을 넣을 때는 `app.js`에서 `d.radar`·`d.board`가 없는 경우를 먼저 처리해, 블록이 빠진 `data.json`으로도 대시보드 전체가 깨지지 않게 합니다.

### 과일 상세·마진 원클릭 생성기 (`generator.html`)

상품명·옵션별 공급가/판매가·실사 사진을 넣으면 ① 쿠팡(11.66%+CS 2%)·스마트스토어(4.95%+CS 2%)·마케팅링크(2.95%+CS 2%) 건당 마진·마진율·손익분기 ROAS 표, ② 1000×1000 대표이미지, ③ v7 가을 톤 상세 섹션 2장(헤드라인·옵션가 / 규격·배송·보관)을 브라우저에서 만들고 PNG로 저장합니다.

- 모든 계산·합성은 클라이언트에서만 돕니다(사진 업로드 포함, 서버 전송 0). 입력값은 같은 브라우저의 `localStorage`(`storenote-generator-v1`)에만 남습니다.
- 마진 = 판매가 − 공급가 − 수수료(플랫폼+CS) − 배송·포장 원가. 부가세·반품·쿠폰 비용은 미포함입니다.
- 수수료율은 화면의 '수수료율 설정'에서 고칠 수 있고, 바꾸면 표 전체가 다시 계산됩니다.
- 이미지 문구는 입력한 값(상품명·배지·배송·보관·안내)만 사용합니다. 없는 문구를 지어내지 않습니다.

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
