# Subway Route Search

수도권 지하철 2호선, 5호선, 9호선 데이터를 기반으로 최적 경로를 탐색하는 프로젝트입니다.

사용자가 원하는 경로 탐색 기준에 따라 최단 시간, 최소 환승, 조건부 최단 시간 및 다중 기준 경로를 제공합니다.

---

## 1. 프로젝트 구조

```text
SubwayProject/
├── raw/                              # 원본 데이터
│
├── processed/                       # 전처리 결과 데이터
│   ├── stations.csv
│   ├── graph_edges.csv
│   ├── segments.csv
│   ├── transfers.csv
│   ├── line9_segments.csv
│   ├── fare_station_mapping.csv
│   ├── fare_od_2_5.csv
│   ├── quality_checks.csv
│   └── preprocessing_report.txt
│
└── src/                              # 알고리즘 및 전처리 코드
    ├── graph.py
    ├── dijkstra.py
    ├── constrained_dijkstra.py
    ├── minimum_transfer.py
    ├── minimum_cost.py
    ├── multi_criteria.py
    └── preprocess_2_5.py
```

### 1.1 메인 서버에서 사용하는 파일

기존 메인 서버에서 사용하는 기본 경로 탐색 알고리즘은 다음 세 가지입니다.

- `src/dijkstra.py`
- `src/constrained_dijkstra.py`
- `src/minimum_transfer.py`

다중 기준 경로 탐색 기능을 사용하는 경우에는 다음 파일도 추가로 불러옵니다.

- `src/multi_criteria.py`

`minimum_cost.py`는 최소 운임 경로 탐색을 위한 별도 모듈이며, 현재 기본 메인 서버 연동 대상 세 파일에는 포함되지 않습니다.

**중요: 알고리즘 코드의 수정 및 유지보수는 반드시 `src/`에 있는 파일을 기준으로 진행합니다.**

`processed/`는 전처리된 CSV 데이터 저장 디렉터리이며, 메인 서버가 알고리즘 코드를 가져오는 위치가 아닙니다.

`processed/` 안에 `dijkstra.py`, `constrained_dijkstra.py`, `minimum_transfer.py` 등 동일한 이름의 Python 파일이 존재한다면 혼동을 방지하기 위해 삭제하는 것을 권장합니다. 단, CSV 데이터 파일은 유지해야 합니다.

---

## 2. 경로 탐색 알고리즘

### 2.1 최단 시간 경로

- 파일: `src/dijkstra.py`
- 함수: `dijkstra(subway, start_node, end_node)`

출발역부터 도착역까지 소요 시간이 가장 짧은 경로를 탐색합니다.

사용 예시:

```python
from src.dijkstra import dijkstra

result = dijkstra(
    subway,
    "L2_MAIN_037",
    "L9_MAIN_038"
)

if result is not None:
    print(result["total_time"])
    print(result["total_transfers"])
    print(result["route"])
```

### 2.2 조건부 최단 시간 경로

- 파일: `src/constrained_dijkstra.py`
- 함수:

```python
constrained_dijkstra(
    subway,
    start_node,
    end_node,
    max_time=None,
    max_transfers=None
)
```

사용자가 설정한 시간 및 환승 횟수 제한을 만족하는 경로 중 소요 시간이 가장 짧은 경로를 탐색합니다.

| 매개변수 | 설명 |
|---|---|
| `subway` | 지하철 그래프 객체 |
| `start_node` | 출발역 노드 ID |
| `end_node` | 도착역 노드 ID |
| `max_time` | 최대 소요 시간 제한(초) |
| `max_transfers` | 최대 환승 횟수 |

사용 예시:

```python
from src.constrained_dijkstra import constrained_dijkstra

result = constrained_dijkstra(
    subway,
    "L5_MAIN_003",
    "L9_MAIN_038",
    max_time=3900,
    max_transfers=1
)

if result is not None:
    print(result["total_time"])
    print(result["total_transfers"])
    print(result["route"])
```

잘못된 입력값이 전달되면 `ValueError`가 발생합니다.

### 2.3 최소 환승 경로

- 파일: `src/minimum_transfer.py`
- 함수: `minimum_transfer(subway, start_node, end_node)`

환승 횟수가 가장 적은 경로를 탐색합니다.

환승 횟수가 같으면 소요 시간이 짧은 경로를 우선합니다.

사용 예시:

```python
from src.minimum_transfer import minimum_transfer

result = minimum_transfer(
    subway,
    "L2_MAIN_037",
    "L9_MAIN_038"
)

if result is not None:
    print(result["total_time"])
    print(result["total_transfers"])
    print(result["route"])
```

### 2.4 최소 운임 경로

- 파일: `src/minimum_cost.py`
- 함수: `minimum_cost(subway, start_node, end_node)`

누적 이동거리에 따른 운임을 계산하여 운임이 가장 저렴한 경로를 탐색합니다.

운임이 같으면 소요 시간이 짧은 경로를 우선하고, 소요 시간까지 같으면 환승 횟수가 적은 경로를 선택합니다.

사용 예시:

```python
from src.minimum_cost import minimum_cost

result = minimum_cost(
    subway,
    "L2_MAIN_037",
    "L9_MAIN_038"
)

if result is not None:
    print(result["total_time"])
    print(result["total_transfers"])
    print(result["route"])
```

**운임 계산 참고 사항**

현재 운임은 누적 이동거리를 기반으로 계산하는 프로젝트용 추정 방식입니다. 실제 수도권 지하철 운임에는 공식 운임 거리, 환승 할인, 이용자 유형 등 추가 규칙이 적용될 수 있으므로 실제 운임과 완전히 일치한다고 보장하지 않습니다.

### 2.5 다중 기준 경로 탐색

- 파일: `src/multi_criteria.py`
- 함수:

```python
multi_criteria(
    subway,
    start_node,
    end_node,
    priorities=None
)
```

사용자가 선택한 우선순위에 따라 여러 기준을 조합하여 최적 경로를 탐색합니다.

지원 기준은 다음 네 가지입니다.

| 기준 | 입력값 | 비교 방향 |
|---|---|---|
| 이동거리 | `distance` | 짧을수록 우선 |
| 운임 | `fare` | 저렴할수록 우선 |
| 소요 시간 | `time` | 짧을수록 우선 |
| 환승 횟수 | `transfers` | 적을수록 우선 |

#### 우선순위 선택 규칙

- 1개부터 4개까지 선택할 수 있습니다.
- 사용자가 입력한 순서대로 우선순위를 적용합니다.
- 선택하지 않은 기준은 경로 비교에 사용하지 않습니다.
- 동일한 기준을 중복 선택할 수 없습니다.
- 지원하지 않는 기준을 입력하면 `ValueError`가 발생합니다.
- `priorities`를 생략하면 기본 순서인 거리 → 운임 → 시간 → 환승 횟수를 사용합니다.

#### 사용 예시

**기준 1개 선택**

```python
priorities = ["distance"]
```

이동거리가 가장 짧은 경로를 선택합니다.

**기준 2개 선택**

```python
priorities = ["distance", "fare"]
```

이동거리를 우선 비교하고, 이동거리가 같으면 운임을 비교합니다.

**기준 3개 선택**

```python
priorities = ["fare", "time", "transfers"]
```

운임 → 소요 시간 → 환승 횟수 순서로 비교합니다.

**기준 4개 선택**

```python
priorities = [
    "distance",
    "fare",
    "time",
    "transfers"
]
```

네 가지 기준을 모두 비교합니다.

#### 함수 호출 예시

```python
from src.multi_criteria import multi_criteria

result = multi_criteria(
    subway,
    "L2_MAIN_037",
    "L9_MAIN_038",
    priorities=["fare", "time"]
)

if result is not None:
    print("총 이동거리:", result["total_distance"])
    print("총 운임:", result["total_fare"])
    print("총 소요 시간:", result["total_time"])
    print("총 환승 횟수:", result["total_transfers"])
    print("적용 우선순위:", result["priority_order"])
    print("상세 경로:", result["route"])
else:
    print("경로를 찾을 수 없습니다.")
```

#### 다중 기준 탐색 방식

다중 기준 탐색은 각 역에 하나의 경로만 저장하지 않고 여러 경로 후보를 유지하는 다중 라벨 탐색 방식을 사용합니다.

1. 출발역에서 탐색을 시작합니다.
2. 각 경로 후보의 누적 거리, 시간, 환승 횟수를 계산합니다.
3. 누적 이동거리를 기준으로 운임을 계산합니다.
4. 비교 기준에 따라 불필요한 경로 후보를 제거합니다.
5. 도착역에 도달한 후보들을 사용자가 지정한 우선순위 순서대로 비교합니다.
6. 최적 경로를 반환합니다.

운임은 간선별 운임을 단순히 더하지 않고, 전체 누적 이동거리를 기준으로 계산합니다.

---

## 3. 함수 입력 및 반환값

### 3.1 공통 입력값

경로 탐색 함수는 기본적으로 다음 값을 입력받습니다.

| 매개변수 | 설명 |
|---|---|
| `subway` | `.stations`와 `.graph`를 가진 SubwayGraph 객체 |
| `start_node` | 출발역 노드 ID |
| `end_node` | 도착역 노드 ID |

`constrained_dijkstra`는 추가로 시간 및 환승 제한을 입력받습니다.

`multi_criteria`는 추가로 사용자 우선순위 목록을 입력받습니다.

### 3.2 반환값

기존 기본 알고리즘 세 함수는 경로 탐색 성공 시 다음과 같은 딕셔너리를 반환합니다.

```python
{
    "total_time": 2535.0,
    "total_transfers": 2,
    "route": [
        # 경로를 구성하는 간선 정보
    ]
}
```

`multi_criteria`는 다음과 같은 형식으로 반환합니다.

```python
{
    "total_time": 2535.0,
    "total_distance": 28700.0,
    "total_fare": 1950,
    "total_transfers": 2,
    "priority_order": [
        "fare",
        "time"
    ],
    "route": [
        # 경로를 구성하는 간선 정보
    ]
}
```

| 반환 항목 | 설명 |
|---|---|
| `total_time` | 전체 소요 시간(초) |
| `total_distance` | 전체 이동거리(m) |
| `total_fare` | 계산된 운임(원) |
| `total_transfers` | 전체 환승 횟수 |
| `priority_order` | 적용한 우선순위 목록 |
| `route` | 출발역부터 도착역까지의 상세 경로 |

경로를 찾지 못하면 `None`을 반환합니다.

### 3.3 오류 처리

| 함수 | 잘못된 입력 처리 |
|---|---|
| `dijkstra` | 별도 입력값 검사 없음 |
| `constrained_dijkstra` | `ValueError` 발생 |
| `minimum_transfer` | 별도 입력값 검사 없음 |
| `minimum_cost` | 구현된 입력 검사에 따름 |
| `multi_criteria` | `ValueError` 발생 |

호출하는 쪽에서는 경로 탐색 결과가 `None`인지 확인해야 합니다.

---

## 4. 데이터 전처리 및 재생성

원본 데이터가 변경되거나 전처리 결과를 다시 생성해야 하는 경우 프로젝트 최상위 디렉터리에서 다음 명령어를 실행합니다.

```powershell
python src/preprocess_2_5.py
```

전처리 스크립트는 `raw/`의 원본 데이터를 읽어 `processed/`에 결과 파일을 생성합니다.

### 4.1 전처리 결과 파일

| 파일 | 설명 |
|---|---|
| `stations.csv` | 지하철 역 노드 정보 |
| `graph_edges.csv` | 경로 탐색 그래프 간선 정보 |
| `segments.csv` | 역간 이동 구간 정보 |
| `transfers.csv` | 환승 및 연결 정보 |
| `line9_segments.csv` | 9호선 방향별 역간 거리 및 소요 시간 |
| `fare_station_mapping.csv` | 역과 운임 역 코드 매핑 |
| `fare_od_2_5.csv` | 2·5호선 출발역-도착역 운임 데이터 |
| `quality_checks.csv` | 전처리 데이터 품질 검사 결과 |
| `preprocessing_report.txt` | 전처리 실행 및 검증 보고서 |

전처리 실행 후 `processed/`에 결과 파일이 정상적으로 생성되었는지 확인합니다.

### 4.2 데이터 구성 참고 사항

현재 프로젝트는 수도권 지하철 2호선, 5호선, 9호선을 대상으로 합니다.

- 2호선 및 5호선: 역간 거리 및 소요 시간 데이터 기반
- 9호선: 역간 거리 데이터와 열차 운행 시각표를 이용한 방향별 소요 시간 기반
- 환승 정보: 대상 노선 사이의 연결 정보
- 운임 정보: 2·5호선 OD 운임 데이터 및 역 코드 매핑

2·5호선과 9호선의 소요 시간 산출 방식이 서로 다르며, 실시간 열차 도착 정보나 운행 지연, 승강장 이동 시간 등은 별도로 반영되지 않습니다.

---

## 5. 파일 관리 및 협업 규칙

팀원 간 코드 중복 및 실행 오류를 방지하기 위해 다음 규칙을 지킵니다.

1. 기본 경로 탐색 알고리즘은 `src/`의 파일을 기준으로 관리합니다.
2. 다중 기준 경로 탐색 기능은 `src/multi_criteria.py`를 사용합니다.
3. `processed/`에는 전처리 결과 데이터 파일을 저장합니다.
4. `processed/`에 알고리즘 Python 파일의 복사본을 중복 관리하지 않는 것을 권장합니다.
5. 알고리즘을 수정했다면 반드시 `src/`의 파일을 기준으로 테스트합니다.
6. 전처리 스크립트를 실행한 후 결과 CSV 파일이 정상적으로 생성되었는지 확인합니다.
7. GitHub에 변경 사항을 반영할 때 알고리즘 파일이 비어 있거나 누락되지 않았는지 확인합니다.

특히 `src/`와 `processed/`에 같은 이름의 Python 파일을 중복 관리하면 어느 파일이 실제로 실행되는지 혼동할 수 있습니다.

과거 `src/constrained_dijkstra.py` 파일이 비어 있어 메인 서버가 시작되지 않았던 사례가 있으므로, 알고리즘 파일을 수정하거나 병합할 때는 파일 내용과 Git 변경 사항을 함께 확인해야 합니다.

---

## 6. 메인 서버 연동 시 참고 사항

- 출발역과 도착역은 역 이름이 아니라 그래프에서 사용하는 노드 ID를 전달해야 합니다.
- 동일한 역 이름이 여러 노선에 존재할 수 있으므로 노선별 노드 ID를 구분해야 합니다.
- `subway` 객체는 `.stations`와 `.graph` 속성을 가지고 있어야 합니다.
- `constrained_dijkstra`의 `max_time` 단위는 초입니다.
- `multi_criteria`의 우선순위는 `distance`, `fare`, `time`, `transfers` 중 1~4개를 입력합니다.
- `multi_criteria`는 사용자가 입력한 우선순위 순서대로 경로를 비교합니다.
- 경로 탐색 결과가 `None`일 수 있으므로 메인 서버에서 반환값을 확인해야 합니다.
- 다중 기준 경로 탐색을 사용하려면 메인 서버에서 `src/multi_criteria.py`를 별도로 import해야 합니다.

### 메인 서버 호출 예시

```python
from src.dijkstra import dijkstra
from src.constrained_dijkstra import constrained_dijkstra
from src.minimum_transfer import minimum_transfer
from src.multi_criteria import multi_criteria

# 다중 기준 경로 탐색
result = multi_criteria(
    subway,
    start_node,
    end_node,
    priorities=["distance", "fare"]
)
```

---

## 7. 테스트 및 검증

알고리즘을 수정하거나 추가한 경우 다음 항목을 테스트합니다.

| 테스트 항목 | 검증 내용 |
|---|---|
| 최단 시간 | 소요 시간이 가장 짧은 경로 선택 |
| 조건부 최단 시간 | 시간 및 환승 제한 준수 |
| 최소 환승 | 환승 횟수 최소화 |
| 최소 운임 | 운임이 가장 저렴한 경로 선택 |
| 다중 기준 1개 | 단일 기준으로 경로 선택 |
| 다중 기준 2개 | 두 기준의 우선순위 적용 |
| 다중 기준 3개 | 세 기준의 우선순위 적용 |
| 다중 기준 4개 | 네 기준의 우선순위 적용 |
| 우선순위 변경 | 입력 순서에 따른 결과 변경 |
| 잘못된 입력 | 오류 처리 확인 |
| 경로 없음 | `None` 반환 확인 |
| 데이터 검증 | 노드 및 간선 정보의 유효성 확인 |

테스트는 프로젝트 최상위 디렉터리에서 실행합니다.

예시:

```powershell
python -m pytest -q
```

