
import csv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EDGE_FILE = BASE_DIR / "processed" / "graph_edges.csv"

distances = []

with open(EDGE_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    print("컬럼:", reader.fieldnames)

    for row in reader:
        distance = float(row["distance_m"])
        distances.append(distance)

print("\n===== 그래프 거리 데이터 분석 =====")
print("연결 개수:", len(distances))
print("최소 거리:", min(distances), "m")
print("최대 거리:", max(distances), "m")
print("평균 거리:", sum(distances) / len(distances), "m")

print("\n===== 거리 샘플 =====")
for distance in distances[:20]:
    print(distance, "m")
