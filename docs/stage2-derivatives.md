# Stage 2: Thumbnails / Previews / Footprints

## 목적
QGIS 검색 결과에서 빠르게 고르기 위한 썸네일을 생성한다.

## 산출물 경로
- 썸네일: `<NAS_ROOT>/result/thumb/<relative>.jpg`

## 스크립트
- `scripts/derive/generate_derivatives.py`
- 입력: NAS 내 COG 파일(`*.tif`)
- 출력: 썸네일

## 실행
현재는 수동 실행이 가능하지만, 운영 단계에서 자동화(Stage 6)로 전환한다.

## 썸네일 크기 통일(권장)
QGIS 결과 목록에서 빠르게 비교하려면 256px로 통일한다.
```
docker compose --profile derive run --rm derive --overwrite --thumb-size 256
```

## 체크포인트
- 썸네일 URL 접근:
  - `http://192.168.0.77:8080/data/result/thumb/2023_Asan_B_cog.jpg`
