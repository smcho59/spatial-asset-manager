# Stage 3: STAC Collection/Item 생성 및 적재

## 목적
COG + 파생 산출물을 STAC Item으로 등록하여 필터 검색이 가능하게 한다.

## 입력
- COG 파일: `<NAS_ROOT>/**/*.tif`
- 썸네일: `<NAS_ROOT>/result/thumb/...`

## 환경 변수
- `NAS_DATA_ROOT`: NAS 루트 경로
- `PUBLIC_BASE_URL`: 공개 URL 베이스 (예: `https://innopam/data`)
- `DERIV_ROOT`: 파생 산출물 루트 (기본값: `<NAS_ROOT>/result`)

## 실행 (Docker Compose)
```
docker compose --profile ingest run --rm ingest --public-base-url https://innopam/data
```

## STAC 속성 규칙
- `year`, `region`, `zone`은 파일명 패턴에서 자동 추출
  - 예: `2023_Asan_B_cog.tif` → `year=2023`, `region=Asan`, `zone=B`

## ID 규칙
- `id`는 파일명(확장자 제외)을 사용

## Assets
- `assets.data`: COG URL
- `assets.thumbnail`: 썸네일 URL (존재 시)

## 체크포인트
- DB에 item 적재 확인:
```
docker exec spatial-asset-manager-db psql -U sam -d spatial_asset_manager \
  -c "SELECT COUNT(*) FROM items;" \
  -c "SELECT id, properties->>'year', properties->>'region', properties->>'zone' FROM items LIMIT 5;"
```

## 산출물(JSON 덤프)
- `docs/stac-collections.json`
- `docs/stac-items.json`
