
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


# 1. 역 코드별 그래프 노드 수집
code_to_nodes = defaultdict(list)

with open(STATION_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        code = normalize_code(row["fare_station_code"])
        node = row["node_id"]

        if code and code.lower() != "none":
            code_to_nodes[code].append(node)


# 2. 거리 기준 그래프 생성
graph = defaultdict(list)

with open(EDGE_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        start = row["from_node"]
        end = row["to_node"]
        distance = float(row["distance_m"])

        graph[start].append((end, distance))


# 3. 여러 출발 노드에서 거리 최단 경로 계산
def dijkstra_distance(start_nodes):
    distances = {}
    queue = []

    for node in start_nodes:
        distances[node] = 0
        heapq.heappush(queue, (0, node))

    while queue:
        current_distance, current = heapq.heappop(queue)

        if current_distance > distances[current]:
            continue

        for next_node, edge_distance in graph[current]:
            new_distance = current_distance + edge_distance

            if new_distance < distances.get(next_node, float("inf")):
                distances[next_node] = new_distance
                heapq.heappush(queue, (new_distance, next_node))

    return distances


# 4. OD 데이터와 비교
comparisons = []
unreachable = 0
missing_mapping = 0

with open(FARE_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        start_code = normalize_code(row["출발역번호"])
        end_code = normalize_code(row["도착역번호"])

        if start_code not in code_to_nodes or end_code not in code_to_nodes:
            missing_mapping += 1
            continue

        start_nodes = code_to_nodes[start_code]
        end_nodes = set(code_to_nodes[end_code])

        distances = dijkstra_distance(start_nodes)

        graph_distance = min(
            (distances[node] for node in end_nodes if node in distances),
            default=None
        )

        if graph_distance is None:
            unreachable += 1
            continue

        od_distance = float(row["총거리"]) * 1000
        difference = abs(graph_distance - od_distance)

        comparisons.append({
            "start": row["출발역명"],
            "end": row["도착역명"],
            "graph_km": graph_distance / 1000,
            "od_km": od_distance / 1000,
            "difference_m": difference
        })


# 5. 결과 출력
print("===== 그래프 거리와 OD 거리 비교 =====")
print("비교 가능한 데이터:", len(comparisons))
print("역 코드 매핑 누락:", missing_mapping)
print("그래프 연결 경로 없음:", unreachable)

if comparisons:
    differences = [item["difference_m"] for item in comparisons]

    print("\n===== 거리 차이 분석 =====")
    print("평균 차이:", round(sum(differences) / len(differences), 2), "m")
    print("최대 차이:", round(max(differences), 2), "m")

    print("차이 50m 이하:", sum(d <= 50 for d in differences))
    print("차이 100m 이하:", sum(d <= 100 for d in differences))
    print("차이 100m 초과:", sum(d > 100 for d in differences))

    print("\n===== 거리 차이가 큰 사례 10개 =====")

    comparisons.sort(
        key=lambda item: item["difference_m"],
        reverse=True
    )

    for item in comparisons[:10]:
        print(
            f"{item['start']} → {item['end']} | "
            f"그래프: {item['graph_km']:.2f}km | "
            f"OD: {item['od_km']:.2f}km | "
            f"차이: {item['difference_m']:.0f}m"
        )
