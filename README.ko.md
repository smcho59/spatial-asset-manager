# Spatial Asset Manager

Synology NAS에 저장된 정사영상(GeoTIFF)과 벡터 데이터(SHP, GeoJSON)를 STAC 호환 메타데이터로 카탈로그화하고, FastAPI/PostGIS 및 React + Mapbox GL JS 프런트엔드로 검색/미리보기하는 Web GIS 플랫폼입니다.

## 목표
- STAC Collection/Item을 통해 래스터/벡터 자산의 메타데이터와 계보를 중앙화합니다.
- PostgreSQL/PostGIS 기반의 빠른 공간/시간 검색을 제공하고 REST/타일 엔드포인트를 노출합니다.
- 다중 레이어 미리보기, 스타일링, 다운로드 링크를 제공하는 지도 기반 UI를 제공합니다.
- NAS 마운트를 읽어 카탈로그를 업데이트하는 수집/검증 작업을 자동화합니다.

## 기술 스택
- Backend: Python (FastAPI, Pydantic, SQLAlchemy/Alembic), STAC 모델/API, 수집/타일링용 백그라운드 워커
- Database: PostgreSQL + PostGIS (공간 인덱싱/검색/지오메트리 연산)
- Frontend: React, Mapbox GL JS (인터랙티브 지도, 클라이언트 쿼리, 미리보기)
- 데이터 표준: STAC core spec (Collections, Items, Assets)
- 운영: Docker Compose, 데이터 수집/검증/유지보수 스크립트

## 로드맵 (Stage 0-6)
Stage 4까지 구현 완료, Stage 5~6은 계획 단계입니다.

- Stage 0 (완료): 인벤토리 + 매핑 규칙, 샘플 커버리지 확인 (`docs/stage0-mapping.md`)
- Stage 1 (완료): 정적 파일 서버, HTTP range 테스트, COG URL 검증 (`docs/stage1-fileserver.md`)
- Stage 2 (완료): 썸네일 생성, 브라우저/QGIS에서 URL 확인 (`docs/stage2-derivatives.md`)
- Stage 3 (완료): STAC 적재, DB에서 속성/에셋 검증 (`docs/stage3-stac.md`)
- Stage 4 (완료): STAC API 엔드포인트, 컬렉션/검색 검증 (`docs/stage4-stac-api.md`)
- Stage 5 (계획): QGIS UX 가이드 및 스타일
- Stage 6 (계획): 운영 자동화(ingest 파이프라인)

## 리포지토리 구조
```
/                     # Project root
|- backend/           # FastAPI 서비스 및 지원 코드
|  |- app/
|  |  |- api/         # REST/STAC API 라우트
|  |  |- core/        # 설정, 의존성, 보안
|  |  |- db/          # 세션 관리, 마이그레이션 설정
|  |  |- models/      # ORM 모델 (STAC, assets, users, jobs)
|  |  |- schemas/     # Pydantic 스키마
|  |  |- services/    # 도메인 로직 (카탈로그, 검색, 인증)
|  |  |- stac/        # STAC 헬퍼/검증기/변환기
|  |  |- workers/     # 수집/타일링/검증 백그라운드 작업
|  |  |- tests/       # 백엔드 테스트
|  |- alembic/        # 마이그레이션 스크립트
|  |- pyproject.toml  # 백엔드 의존성/툴 설정
|  |- .env.example    # 백엔드 환경변수 예시 (DB, NAS 마운트 등)
|- frontend/          # React + Mapbox GL JS 클라이언트
|  |- src/
|  |  |- components/  # UI 컴포넌트
|  |  |- pages/       # 페이지 (카탈로그, 상세, 관리자)
|  |  |- map/         # 지도 설정/스타일/레이어
|  |  |- services/    # API 클라이언트
|  |  |- hooks/       # 공통 훅
|  |  |- styles/      # 스타일
|  |  |- tests/       # 프런트 테스트
|  |- public/         # 정적 자원
|  |- package.json    # 프런트 의존성/스크립트
|  |- .env.example    # 프런트 환경변수 예시
|- scripts/           # 운영 스크립트
|  |- ingest/         # NAS 데이터 STAC 적재
|  |- maintenance/    # 검증/정리/백업/헬스체크
|  |- dev/            # 개발 유틸
|- docker-compose.yml # 로컬 오케스트레이션
|- docs/              # 아키텍처/계약/표준 문서
```

## 참고
- NAS는 읽기 전용 마운트를 권장하며, 컨테이너에 노출되는 경로와 호스트 경로는 다릅니다.
- STAC 스키마 변경 시 `backend/app/models`, `backend/app/schemas`, `frontend/src/types`(추가 시) 를 함께 맞춰주세요.

## Quick Start (Docker + Sample Data)
PostGIS 저장/수집 흐름을 빠르게 확인하는 방법입니다.

### 1) `.env` 설정
컨테이너에서는 항상 `/data/nas`로 NAS를 보게 됩니다. 호스트의 실제 경로를 `.env`에 설정하세요.

유효한 호스트 경로 예시:
- Synology DSM 로컬 경로: `/volume1/data` 또는 `/volume1/projects/gis`
- CIFS/NFS로 마운트한 Linux 경로: `/mnt/nas/data` 또는 `/data/nas`

경로 선택 기준:
- NAS에서 직접 Docker를 실행한다면 DSM 경로(`/volume1/<shared-folder>`)를 사용
- 다른 서버에서 실행한다면 마운트 포인트(`/mnt/nas/...`)를 사용

Synology (NAS에서 Docker 실행) 예시:
```
export NAS_DATA_ROOT=/volume1/data
docker compose --profile ingest run --rm ingest
```

외부 서버(NAS 마운트) 예시:
```
export NAS_DATA_ROOT=/mnt/nas/data
docker compose --profile ingest run --rm ingest
```

```
POSTGRES_USER=sam
POSTGRES_PASSWORD=sam_password
POSTGRES_DB=spatial_asset_manager
DB_PORT=5433
NAS_DATA_ROOT=/volume1/data
TZ=Asia/Seoul
```

### 2) Sample data (included)
리포지토리에 `sample-data` 폴더가 포함되어 있어 빠른 테스트에 사용할 수 있습니다.

### 2) PostGIS 시작
```
docker compose up -d
```

### 3) ingest 이미지 빌드
```
docker compose --profile ingest build
```

### 4) 샘플 ingest 실행
샘플 실행 시 `NAS_DATA_ROOT`를 임시로 `sample-data` 폴더로 변경합니다.
```
NAS_DATA_ROOT=$(pwd)/sample-data docker compose --profile ingest run --rm ingest
```

실제 NAS 수집은 `.env`의 `NAS_DATA_ROOT`를 그대로 사용하면 됩니다.

`items.nas_path`를 기준으로 중복을 막으므로 재실행으로 증분 확인이 가능합니다.

### 5) psql로 확인 (선택)
```
docker exec spatial-asset-manager-db psql -U sam -d spatial_asset_manager \
  -c "SELECT COUNT(*) FROM items;" \
  -c "SELECT id, nas_path, assets->'data'->>'href' AS href FROM items LIMIT 5;"
```

## QGIS: PostGIS 연결
QGIS에서 공간 데이터를 시각적으로 확인하는 방법입니다.

1) `Layer` -> `Data Source Manager` -> `PostgreSQL` -> `New`
2) Connection 설정:
   - Host: `192.168.10.203` (QGIS에서 접근 가능한 호스트 IP)
   - Port: `5433`
   - Database: `spatial_asset_manager`
   - User: `sam`
   - Password: `sam_password`
3) `Test Connection` -> `OK`
4) Browser 패널에서 연결을 열고 `public` -> `items` -> `geom` 추가 (EPSG:4326)
5) 레이어 우클릭 -> `Zoom to Layer`

## TODO
- FastAPI 기반 STAC API 엔드포인트 확장 (Collections/Items/Search)
- 수집 작업 오케스트레이션(큐/워커, 재시도, 모니터링)
- 프리뷰 파이프라인 (COG 타일, 벡터 타일, 썸네일 생성)
- React + Mapbox GL JS 카탈로그 UI 구축
- 관리자/읽기 전용 권한 분리
- 데이터 검증/QC (스키마/CRS/누락 검사)
- 로깅/메트릭/작업 감사 로그
- 백업/복구 및 데이터 라이프사이클 정책
