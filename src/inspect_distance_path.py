
import csv
import heapq
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent

STATION_FILE = BASE_DIR / "processed" / "stations.csv"
EDGE_FILE = BASE_DIR / "processed" / "graph_edges.csv"
FARE_FILE = BASE_DIR / "processed" / "fare_od_2_5.csv"


def normalize_code(value):
    return str(value).strip().replace(".0", "")


# 역 코드별 노드 및 역 정보
code_to_nodes = defaultdict(list)
station_info = {}

with open(STATION_FILE, encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        node = row["node_id"]
        code = normalize_code(row["fare_station_code"])

        station_info[node] = row

        if code and code.lower() != "none":
            code_to_nodes[code].append(node)


# 그래프 생성
graph = defaultdict(list)

with open(EDGE_FILE, encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        graph[row["from_node"]].append({
            "to": row["to_node"],
            "distance": float(row["distance_m"]),
            "type": row["edge_type"]
        })


# OD 데이터에서 비교할 출발역과 도착역 찾기
target_start = "종합운동장"
target_end = "오금"

fare_row = None

with open(FARE_FILE, encoding="utf-8-sig", newline="") as f:
    for row in csv.DictReader(f):
        if (row["출발역명"] == target_start
                and row["도착역명"] == target_end):
            fare_row = row
            break

if fare_row is None:
    raise ValueError("해당 OD 데이터를 찾을 수 없습니다.")

start_code = normalize_code(fare_row["출발역번호"])
end_code = normalize_code(fare_row["도착역번호"])

start_nodes = code_to_nodes[start_code]
end_nodes = set(code_to_nodes[end_code])


# 거리 기준 다익스트라 + 경로 복원
distances = {}
previous = {}
queue = []

for node in start_nodes:
    distances[node] = 0
    heapq.heappush(queue, (0, node))

while queue:
    current_distance, current = heapq.heappop(queue)

    if current_distance > distances[current]:
        continue

    for edge in graph[current]:
        next_node = edge["to"]
        new_distance = current_distance + edge["distance"]

        if new_distance < distances.get(next_node, float("inf")):
            distances[next_node] = new_distance
            previous[next_node] = (current, edge)
            heapq.heappush(queue, (new_distance, next_node))


reachable = [
    (distances[node], node)
    for node in end_nodes
    if node in distances
]

if not reachable:
    raise ValueError("그래프에서 경로를 찾지 못했습니다.")

total_distance, end_node = min(reachable)

# 경로 복원
path = []
current = end_node

while current in previous:
    prev_node, edge = previous[current]
    path.append((prev_node, current, edge))
    current = prev_node

path.reverse()

print("===== 경로 비교 =====")
print("출발역:", target_start)
print("도착역:", target_end)
print("OD 데이터 거리:", fare_row["총거리"], "km")
print("그래프 누적 거리:", round(total_distance / 1000, 3), "km")

print("\n===== 그래프에서 선택한 경로 =====")

for start, end, edge in path:
    start_info = station_info[start]
    end_info = station_info[end]

    print(
        f"{start_info['station_name']}({start_info['line']})"
        f" → {end_info['station_name']}({end_info['line']})"
        f" | {edge['distance']}m"
        f" | {edge['type']}"
    )

print("\n===== 경로 검증 완료 =====")
