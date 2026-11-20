# Subway Route Search

수도권 지하철 2호선, 5호선, 9호선 데이터를 기반으로 최적 경로를 탐색하는 프로젝트입니다.

## 1. 프로젝트 구조

```text
SubwayProject/
├── raw/                  # 원본 데이터
├── processed/            # 전처리된 데이터
│   ├── stations.csv
│   ├── segments.csv
│   ├── transfers.csv
│   ├── graph_edges.csv
│   ├── line9_segments.csv
│   ├── fare_station_mapping.csv
│   ├── fare_od_2_5.csv
│   ├── quality_checks.csv
│   └── preprocessing_report.txt
│
├── src/
│   ├── graph.py
│   ├── dijkstra.py
│   ├── constrained_dijkstra.py
│   ├── minimum_transfer.py
│   ├── minimum_cost.py
│   └── preprocess_2_5.py
│
└── README.md
```

## 2. 메인 서버 연동 파일

메인 서버에서 경로 탐색을 위해 불러오는 알고리즘 파일은 다음 세 개입니다.

| 파일 | 기능 |
|---|---|
| `src/dijkstra.py` | 최단 시간 경로 탐색 |
| `src/constrained_dijkstra.py` | 시간 및 환승 제한을 적용한 경로 탐색 |
| `src/minimum_transfer.py` | 최소 환승 경로 탐색 |

**주의사항**

- 메인 서버는 `src/` 디렉터리의 알고리즘 파일만 사용합니다.
- `processed/` 디렉터리에 동일한 이름의 Python 파일이 존재하더라도 메인 서버에서 사용하지 않습니다.
- 알고리즘을 수정할 때는 반드시 `src/`의 파일을 수정해야 합니다.
- 동일한 이름의 파일을 여러 위치에서 관리하면 코드 불일치 및 실행 오류가 발생할 수 있으므로 `processed/`에는 전처리 결과 데이터만 보관하는 것을 권장합니다.

## 3. 알고리즘 사용법

### 3.1 공통 입력 데이터

세 알고리즘은 다음과 같은 입력을 사용합니다.

| 입력값 | 설명 |
|---|---|
| `subway` | `.stations`와 `.graph`를 가진 지하철 그래프 객체 |
| `start_node` | 출발역 ID |
| `end_node` | 도착역 ID |

역 이름이 아닌 **역 ID**를 전달해야 합니다.

예시:

```python
start_node = "L2_MAIN_037"  # 2호선 당산
end_node = "L9_MAIN_038"    # 9호선 중앙보훈병원
```

### 3.2 최단 시간 경로

파일: `src/dijkstra.py`

출발역부터 도착역까지 소요 시간이 가장 짧은 경로를 탐색합니다.

```python
from src.dijkstra import dijkstra

result = dijkstra(
    subway,
    start_node,
    end_node
)
```

### 3.3 시간 및 환승 제한 경로

파일: `src/constrained_dijkstra.py`

사용자가 설정한 최대 소요 시간과 최대 환승 횟수를 만족하는 경로 중 소요 시간이 가장 짧은 경로를 탐색합니다.

```python
from src.constrained_dijkstra import constrained_dijkstra

result = constrained_dijkstra(
    subway,
    start_node,
    end_node,
    max_time=2400,
    max_transfers=2
)
```

| 추가 입력값 | 설명 |
|---|---|
| `max_time` | 최대 허용 소요 시간(초) |
| `max_transfers` | 최대 허용 환승 횟수 |

예시에서 `max_time=2400`은 최대 40분을 의미합니다.

### 3.4 최소 환승 경로

파일: `src/minimum_transfer.py`

환승 횟수를 가장 적게 사용하는 경로를 우선 탐색합니다. 환승 횟수가 같으면 소요 시간이 짧은 경로를 선택합니다.

```python
from src.minimum_transfer import minimum_transfer

result = minimum_transfer(
    subway,
    start_node,
    end_node
)
```

## 4. 반환값 및 오류 처리

세 알고리즘의 정상적인 반환값은 다음과 같은 구조입니다.

```python
{
    "total_time": 2535.0,
    "total_transfers": 2,
    "route": [
        # 경로를 구성하는 간선 정보
    ]
}
```

| 반환 항목 | 설명 |
|---|---|
| `total_time` | 총 소요 시간(초) |
| `total_transfers` | 총 환승 횟수 |
| `route` | 출발역부터 도착역까지의 상세 경로 |

조건을 만족하는 경로가 없으면 `None`을 반환합니다.

### 입력값 오류

| 알고리즘 | 입력값 검사 |
|---|---|
| `dijkstra` | 별도 입력값 검사 없음 |
| `constrained_dijkstra` | 잘못된 입력에 대해 `ValueError` 발생 |
| `minimum_transfer` | 별도 입력값 검사 없음 |

메인 서버에서는 경로가 존재하지 않는 경우(`None`)와 입력값 오류(`ValueError`)를 구분하여 처리해야 합니다.

## 5. 데이터 전처리 및 재생성

원본 데이터는 `raw/` 디렉터리에 보관합니다.

전처리 코드는 `src/preprocess_2_5.py`입니다.

프로젝트 루트 디렉터리에서 다음 명령어를 실행합니다.

```bash
python src/preprocess_2_5.py
```

전처리가 완료되면 `processed/` 디렉터리에 다음 결과 파일이 생성됩니다.

| 결과 파일 | 설명 |
|---|---|
| `stations.csv` | 지하철 역 노드 정보 |
| `segments.csv` | 역간 구간 데이터 |
| `transfers.csv` | 환승 및 연결 정보 |
| `graph_edges.csv` | 경로 탐색에 사용하는 그래프 간선 데이터 |
| `line9_segments.csv` | 9호선 방향별 역간 거리 및 소요 시간 |
| `fare_station_mapping.csv` | 운임 데이터와 역 코드 연결 정보 |
| `fare_od_2_5.csv` | 2·5호선 출발역-도착역 운임 데이터 |
| `quality_checks.csv` | 전처리 데이터 검증 결과 |
| `preprocessing_report.txt` | 전처리 및 검증 요약 |

**주의사항**

- 원본 데이터가 `raw/`에 있어야 합니다.
- 전처리 결과를 변경하려면 원본 데이터를 수정한 뒤 전처리 명령을 다시 실행합니다.
- 그래프 생성에 필요한 `stations.csv`, `graph_edges.csv`가 정상적으로 생성되었는지 확인해야 합니다.
- 전처리 결과 파일은 `processed/`에 보관합니다.

## 6. 메인 서버 연동 시 참고사항

메인 서버 담당자는 다음 순서로 연동하면 됩니다.

1. `graph.py`를 통해 지하철 그래프 객체를 생성합니다.
2. 그래프 객체의 `.stations`와 `.graph`를 확인합니다.
3. 출발역과 도착역에 해당하는 역 ID를 전달합니다.
4. 필요한 경로 탐색 함수를 호출합니다.
5. 반환된 `total_time`, `total_transfers`, `route`를 사용하여 결과를 출력합니다.
6. 반환값이 `None`이면 경로가 없는 것으로 처리합니다.

알고리즘 파일은 메인 서버와 독립적으로 관리하며, 인터페이스를 변경할 때는 메인 서버 담당자와 먼저 협의합니다.

## 7. 개발 및 관리 시 주의사항

- 메인 서버에서 사용하는 알고리즘 파일은 `src/`의 세 파일입니다.
- `processed/`에는 전처리 결과 데이터만 보관하는 것을 권장합니다.
- 알고리즘 파일을 수정할 때는 `src/`의 파일을 기준으로 수정합니다.
- 전처리 코드를 실행하기 전에 원본 데이터 파일이 준비되어 있는지 확인합니다.
- 알고리즘 수정 후에는 관련 테스트 코드를 실행하여 경로 탐색 결과를 검증합니다.
