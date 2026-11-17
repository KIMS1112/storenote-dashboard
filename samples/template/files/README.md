# 상세페이지 자동화 템플릿 (v6 표준)

상품 데이터 **JSON 하나 + 사진 몇 장**만 넣으면, 스마트스토어 상세페이지를 통째로 찍어냅니다.
밝은 상업용 톤 · 큰 모바일 타이포 · GIF 3종 · 숫자/배송 인포그래픽 · 1720px/860px 분할이 한 번에 나옵니다.

```bash
# 예시(제주감귤) 그대로 실행
python3 generate_detail_page.py --data product.example.json --out ./out/제주감귤
```

결과는 `./out/제주감귤/` 에 생깁니다.

---

## 1. 준비물

| 항목 | 내용 |
|---|---|
| Python | 3.9+ |
| 패키지 | `weasyprint`, `pymupdf`, `pillow`, `fonttools`, `numpy` |
| 폰트 | `fonts/` 폴더의 TTF 9종 (G마켓 산스 · 주아 · 마포금빛나루 · Pretendard) — 저장소에 포함 |
| 사진 | 상품 실사컷 6~10장 (아래 5번) |

```bash
pip install weasyprint pymupdf pillow fonttools numpy
```

---

## 2. 폴더 구조

```
templates/상세페이지_자동화/
├─ generate_detail_page.py   ← 실행 파일 (HTML 생성 · 폰트 서브셋 · PNG 렌더 · 분할)
├─ gif_renderer.py           ← GIF 3종 렌더 (Pillow로 프레임 직접 그림)
├─ product.example.json      ← 데이터 예시 (제주감귤). 이걸 복사해서 쓰세요
├─ README.md
├─ fonts/                    ← 무료 상업용 TTF 9종
└─ assets/
   ├─ emoji/                 ← 트위모지 SVG (CC-BY 4.0)
   └─ example/               ← 예시 사진 9장
```

---

## 3. 사용법 (3단계)

### ① JSON 복사 후 값 바꾸기

```bash
cp product.example.json product.사과.json
```

### ② 사진 넣기

`assets/사과/` 폴더를 만들고 아래 이름으로 저장한 뒤, JSON `images` 값을 그 이름으로 바꿉니다.

| 키 | 쓰이는 곳 | 권장 |
|---|---|---|
| `hero` | 히어로 대표컷 | 3:4 세로, 2000px 이상 |
| `peel` | POINT 01 큰 사진 + GIF 02 1컷 | 4:3 가로 |
| `segments` | POINT 01 작은 사진 + GIF 02 2컷 | 4:3 가로 |
| `juice` | GIF 02 3컷 | 4:3 가로 |
| `harvest` | (선택) 수확 컷 | 4:3 |
| `sorting` | (선택) 선별 컷 | 4:3 |
| `box` | POINT 03 큰 사진 | 3:4 세로 |
| `boxtop` | POINT 03 작은 사진 | 1:1 |
| `size` | 크기 안내 기준컷 | 4:3 가로 |

### ③ 실행

```bash
python3 generate_detail_page.py --data product.사과.json --out ./out/사과
```

| 옵션 | 설명 |
|---|---|
| `--scale 2` | PNG 배율. 기본 2 = 1720px 폭. 1로 두면 860px |
| `--no-gif` | GIF 없이 빠르게 미리보기 |

---

## 4. JSON 구조

`product.example.json`이 곧 스키마입니다. 자주 고치는 값만 정리하면:

| 키 | 의미 |
|---|---|
| `meta.brand` / `meta.product` | 브랜드명 · 상품명 |
| `meta.file_prefix` | 파일명 접두어 (`상세페이지_v6`. 버전 바꿀 때 여기만) |
| `meta.product_slug` | HTML 파일명에 붙는 상품명 |
| `topbar` | 최상단 띠 문구 |
| `hero` | 대표컷·한 줄 약속·손글씨·가격 3칸 |
| `trust` | 신뢰바 4개 (아이콘 이름 + 제목 + 설명) |
| `specs` | "숫자로 보는 한 상자" 카드 4개 + 각주 |
| `statement` | 왜 이 상품인가 · 비교표 · 맞음/안 맞음 |
| `points[]` | POINT 01~03 (제목·본문·CHECK·사진·스티커) |
| `shipping` | 4단계 타임라인 + 상자 단면도 |
| `size` | 큰 지름 숫자·구성 카드·100g당 가격 바·스펙표 |
| `options` | 2.5kg/4.5kg 카드 |
| `storage` | 보관 4단계 + 온도 카드 |
| `faq[]` | Q/A (A에는 `<b>` 사용 가능) |
| `cs` | 배송·교환/환불 4칸 |
| `closing` | 마지막 CTA + 가격 배지 |
| `footer` | 사업자 정보 |
| `gif` | GIF 3종 문구·숫자·컷 (`enabled:false`면 GIF 없이) |

### 아이콘 이름

`truck` `box` `clock` `shield` `leaf` `sugar` `ruler` `weight` `calendar` `peel` `aroma` `cold` `sun` `newspaper` `check` `x` `arrow_down` `thermo` `hand` `droplet` `star` `pin` `gift` `info`

---

## 5. 사진 준비 규칙

- **실제 상품 사진**을 쓰세요. AI 생성컷은 시안 확인용이며, 스마트스토어 상품성 심사·표시광고법에서 문제가 될 수 있습니다.
- 같은 촬영·같은 조명으로 통일하세요. 밝은 자연광 + 크림/화이트 배경이 이 템플릿의 톤입니다.
- 사진 안에 **글자·로고·워터마크를 넣지 마세요.** 글자는 HTML이 그립니다.
- 2000px 이상 원본을 쓰면 1720px 출력에서도 선명합니다.

---

## 6. 산출물

```
out/사과/
├─ 상세페이지_v6_상단.png / _중단.png / _하단.png   (1720px)
├─ 상세페이지_v6_전체.png                            (확인용 860px 1장)
├─ 860/상세페이지_v6_상단_860.png …                  (스마트스토어 업로드용)
├─ 상세페이지_v6_사과.html                           (GIF가 움직이는 원본)
├─ gif_01_benefit.gif / gif_02_peel_juice.gif / gif_03_check.gif
├─ v6_제작노트.md
├─ assets/ · fonts/                                  (HTML이 참조)
└─ work/source.html · page.pdf                       (중간 산출물)
```

업로드는 `860/` 폴더의 3장을 순서대로 올리면 됩니다(각 5,000px 이하 권장).

---

## 7. 디자인 규칙 (바꾸지 마세요)

| 요소 | 값 | 이유 |
|---|---|---|
| 폭 | 860px | 스마트스토어·G마켓·옥션 권장 폭 |
| 본문 | 24~25px | 모바일에서 줌 없이 읽히는 최소선(2026 가이드: 24pt↑) |
| 섹션 제목 | 52~54px | 스크롤 중 섹션 구분 |
| 히어로 제목 | 84px | 첫 3초 후킹 |
| 핵심 숫자 | 47~88px | 숫자가 먼저 눈에 들어오게 |
| 한 줄 글자 수 | 15자 이내 | 모바일 가독 |
| 색 | 화이트 / 크림 / 오렌지 | 다크 섹션 금지 |
| 신뢰 요소 | 3곳 이상 | 상단 신뢰바 · 중단 선별 · 하단 보상 |

---

## 8. 자주 나는 문제

| 증상 | 원인 / 해결 |
|---|---|
| 한글이 어절 중간에서 끊김 | `generate_detail_page.py`의 `keepall()`이 음절 사이에 WORD JOINER를 넣어 처리합니다. 직접 HTML을 고칠 때는 이 함수를 거치세요. |
| 페이지가 잘림 | `@page size`가 40000px입니다. 상품이 아주 길면 `build_css()`의 값을 키우고 `render_pngs`의 페이지 수 경고를 확인하세요. |
| GIF가 안 생김 | `assets/`에 `peel`/`segments`/`juice` 사진이 있는지 확인. 없으면 GIF 02만 건너뜁니다. |
| 글자가 네모(□)로 | 폰트 서브셋 문자셋에 없는 글자입니다. JSON에 새 글자를 넣으면 자동으로 다시 서브셋됩니다. |
| 파일이 너무 큼 | `--scale 1`로 미리보기 후 최종만 `--scale 2`. GIF 02는 5MB 안팎입니다. |

---

## 9. 라이선스

- **G마켓 산스** — 무료 배포(자유 사용·수정·재배포)
- **주아(Jua)** — SIL OFL
- **마포금빛나루** — 서울시 무료 배포
- **Pretendard** — SIL OFL
- **트위모지 SVG** — CC-BY 4.0 (출처 표기: Twitter Twemoji)

모두 상업적 사용이 가능하지만, 재배포 시 각 라이선스 고지를 유지하세요.
