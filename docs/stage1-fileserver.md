# Stage 1: Static File Server (Nginx) Output

## 목적
NAS에 있는 COG를 HTTP URL로 제공하여 QGIS/브라우저에서 직접 접근 가능하게 한다.

## 산출물
- 파일 서버 컨테이너: `spatial-asset-manager-files`
- COG 접근 URL (현재): `http://192.168.0.77:8080/data/<filename>.tif`
- COG 접근 URL (목표): `https://innopam/data/<filename>.tif` (리버스 프록시 적용 시)

## 구성 위치
- Compose 서비스: `docker-compose.yml` (service: `files`)
- Nginx 설정: `nginx/nginx.conf`

## 검증 체크리스트
- 컨테이너 내 파일 확인:
  - `docker exec spatial-asset-manager-files ls -la /data`
- HTTP Range 지원 확인:
  - `curl.exe -I -r 0-1 http://192.168.0.77:8080/data/2023_Asan_B_cog.tif`
  - 기대값: `206 Partial Content`, `Accept-Ranges: bytes`
- 브라우저 접근 가능:
  - `http://192.168.0.77:8080/data/2023_Asan_B_cog.tif`

## 메모
- SMB 볼륨으로 NAS를 마운트한다.
- QGIS에서 버벅임이 있으면 SMB 옵션 튜닝이 필요할 수 있다.
