
import csv
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
FARE_FILE = BASE_DIR / "processed" / "fare_od_2_5.csv"

fare_groups = defaultdict(list)

with open(FARE_FILE, "r", encoding="utf-8-sig", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        distance = float(row["총거리"])
        fare = int(row["운임"])

        fare_groups[fare].append(distance)

print("===== 거리별 운임 분석 =====")

for fare in sorted(fare_groups):
    distances = fare_groups[fare]

    print(f"\n운임: {fare:,}원")
    print(f"최소 거리: {min(distances)} km")
    print(f"최대 거리: {max(distances)} km")
    print(f"데이터 개수: {len(distances)}")

print("\n===== 운임별 거리 경계 분석 =====")

sorted_fares = sorted(fare_groups)

for i in range(len(sorted_fares) - 1):
    lower_fare = sorted_fares[i]
    upper_fare = sorted_fares[i + 1]

    lower_max = max(fare_groups[lower_fare])
    upper_min = min(fare_groups[upper_fare])

    print(
        f"{lower_fare:,}원 최대거리: {lower_max}km"
        f" / {upper_fare:,}원 최소거리: {upper_min}km"
    )
