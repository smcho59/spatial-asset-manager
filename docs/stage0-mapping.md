# Stage 0: 인벤토리 및 매핑 규칙

## 소스 경로
- NAS 호스트 경로: `X:\web_images` 또는 `\\192.168.0.62\web\web_images`
- 공개 URL 베이스: `https://innopam/data`

## 파일명 패턴
```
YYYY_<region>_<zone?>_cog.tif
```

규칙:
- `year`: 앞 4자리 연도
- `region`: 영문 문자열 (대소문자 유지)
- `zone`: 선택 항목. 없으면 빈값으로 저장
- `project`: 현재 미사용

## STAC Properties
인덱싱 시 최소로 채울 항목:
- `year` (정수)
- `region` (문자열, 영문)
- `zone` (문자열, 없으면 빈값)

## 예시 매핑
- `X:\web_images\2022_Gamcho_cog.tif`
  - year: `2022`
  - region: `Gamcho`
  - zone: `""`
- `X:\web_images\2022_Geumha_cog.tif`
  - year: `2022`
  - region: `Geumha`
  - zone: `""`
- `X:\web_images\2023_Asan_B_cog.tif`
  - year: `2023`
  - region: `Asan`
  - zone: `B`

## 인벤토리 템플릿 (CSV)
```
nas_path,year,region,zone
X:\web_images\2022_Gamcho_cog.tif,2022,Gamcho,
X:\web_images\2022_Geumha_cog.tif,2022,Geumha,
X:\web_images\2023_Asan_B_cog.tif,2023,Asan,B
```
