# Stage 4: STAC API 배포/연결

## 목적
STAC API 엔드포인트를 제공하여 QGIS STAC 플러그인에서 검색/필터가 가능하게 한다.

## 구성
- API 컨테이너: `spatial-asset-manager-api`
- 엔드포인트: `http://<host>:8081/stac`

## 실행
```
docker compose up -d api
```

## 주요 엔드포인트
- `/stac` (Landing)
- `/stac/conformance`
- `/stac/collections`
- `/stac/collections/{collection_id}`
- `/stac/collections/{collection_id}/items`
- `/stac/search` (GET/POST)

## 확인 방법
```
curl.exe http://192.168.0.77:8081/stac
curl.exe http://192.168.0.77:8081/stac/conformance
curl.exe http://192.168.0.77:8081/stac/collections
```

## QGIS 연결
- STAC endpoint: `http://192.168.0.77:8081/stac`
