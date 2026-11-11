#!/usr/bin/env python3
"""Preprocess Seoul Subway Lines 2 and 5 source CSVs into graph-ready CSVs.

All outputs are UTF-8-SIG CSVs. The program intentionally excludes Line 9.
It preserves source row references and flags reverse directions that are
created under the symmetric-travel-time assumption.
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "processed"
OUT.mkdir(parents=True, exist_ok=True)

ROUTE_FILE = "서울교통공사 역간거리 및 소요시간_240810.csv"
TRANSFER_FILE = "서울교통공사_환승역거리 소요시간 정보_20260831.csv"
FARE_FILE = "서울교통공사_운임표_250628.csv"


def read_csv(filename: str) -> list[dict[str, str]]:
    path = RAW / filename
    with path.open("r", encoding="cp949", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(filename: str, headers: list[str], rows: list[dict]) -> None:
    path = OUT / filename
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def mmss_to_seconds(value: str | None) -> int | None:
    if value is None or not str(value).strip():
        return None
    parts = str(value).strip().split(":")
    if len(parts) == 2:
        minutes, seconds = map(int, parts)
        if not 0 <= seconds < 60:
            raise ValueError(f"Invalid MM:SS value: {value}")
        return minutes * 60 + seconds
    if len(parts) == 3:
        hours, minutes, seconds = map(int, parts)
        if not 0 <= minutes < 60 or not 0 <= seconds < 60:
            raise ValueError(f"Invalid HH:MM:SS value: {value}")
        return hours * 3600 + minutes * 60 + seconds
    raise ValueError(f"Unsupported time format: {value}")


def km_to_m(value: str | None) -> int | None:
    if value is None or not str(value).strip():
        return None
    return round(float(str(value).strip()) * 1000)


def normalize_name(name: str) -> str:
    """Remove a trailing parenthetical station-area alias for matching only."""
    return re.sub(r"\([^)]*\)$", "", name.strip()).strip()


route_all = read_csv(ROUTE_FILE)
transfer_all = read_csv(TRANSFER_FILE)
fare_all = read_csv(FARE_FILE)
route2 = [r for r in route_all if r["호선"].strip() == "2"]
route5 = [r for r in route_all if r["호선"].strip() == "5"]

if len(route2) != 52 or len(route5) != 56:
    raise ValueError(
        f"Unexpected route row counts: line2={len(route2)}, line5={len(route5)}. "
        "Review source version before continuing."
    )

# Explicitly split the source row sequences into their actual route branches.
# Line 2: first 44 rows describe the loop, ending with the repeated City Hall row.
# Remaining 8 rows describe the Seongsu and Sindorim branches (4 each).
line2_loop = route2[:44]
line2_seongsu = route2[44:48]
line2_sinjeong = route2[48:52]
if line2_loop[0]["역명"] != "시청" or line2_loop[-1]["역명"] != "시청":
    raise ValueError("Line 2 loop boundary does not match expected City Hall rows.")
if [r["역명"] for r in line2_seongsu] != ["용답", "신답", "용두", "신설동"]:
    raise ValueError("Line 2 Seongsu-branch rows do not match expected order.")
if [r["역명"] for r in line2_sinjeong] != ["도림천", "양천구청", "신정네거리", "까치산"]:
    raise ValueError("Line 2 Sinjeong-branch rows do not match expected order.")

# Line 5: rows 1-38 lead from Banghwa to Cheonho. Gangdong is the branch node;
# rows after it are split into the Hanam and Macheon branches.
line5_trunk = route5[:38]  # Banghwa ... Cheonho
line5_gangdong = route5[38]
line5_hanam = route5[39:49]  # Gildong ... Hanam Geomdansan
line5_macheon = route5[49:56]  # Dunchon-dong ... Macheon
if line5_trunk[-1]["역명"] != "천호" or line5_gangdong["역명"] != "강동":
    raise ValueError("Line 5 branch boundary does not match expected Cheonho/Gangdong rows.")
if line5_hanam[-1]["역명"] != "하남검단산" or line5_macheon[-1]["역명"] != "마천":
    raise ValueError("Line 5 branch terminal check failed.")

# Build fare station name/code lookup from both origin and destination columns.
fare_name_codes: dict[str, set[str]] = defaultdict(set)
fare_code_names: dict[str, set[str]] = defaultdict(set)
for r in fare_all:
    for name_col, code_col in (("출발역명", "출발역번호"), ("도착역명", "도착역번호")):
        name = r[name_col].strip()
        code = r[code_col].strip()
        fare_name_codes[normalize_name(name)].add(code)
        fare_code_names[code].add(name)


def resolve_fare_code(line: str, station_name: str) -> tuple[str, str]:
    norm = normalize_name(station_name)
    candidates = fare_name_codes.get(norm, set())
    if line == "2":
        valid = {c for c in candidates if c.isdigit() and 200 <= int(c) <= 250}
        # Kkachisan is the Line 2 branch terminal but shares the integrated
        # fare-table station code used by the Line 5 side.
        if station_name == "까치산":
            valid = {"2519"}
    elif line == "5":
        valid = {c for c in candidates if c.isdigit() and 2511 <= int(c) <= 2566}
    else:
        raise ValueError(f"Unsupported line: {line}")
    if len(valid) != 1:
        raise ValueError(
            f"Fare station-code mapping is not unique: line={line}, "
            f"station={station_name}, candidates={sorted(valid)}"
        )
    code = next(iter(valid))
    display_name = sorted(fare_code_names[code])[0]
    return code, display_name


stations: list[dict] = []
station_by_id: dict[str, dict] = {}
node_lookup: dict[tuple[str, str, str], str] = {}
fare_mapping_by_line_name: dict[tuple[str, str], tuple[str, str]] = {}


def add_station(node_id: str, line: str, branch: str, name: str, source_row: str,
                is_junction: bool = False) -> str:
    code, fare_display_name = resolve_fare_code(line, name)
    record = {
        "node_id": node_id,
        "station_name": name,
        "line": line,
        "branch_id": branch,
        "fare_station_code": code,
        "fare_station_display_name": fare_display_name,
        "source_route_row_no": source_row,
        "is_branch_junction": str(is_junction).lower(),
        "source_file": ROUTE_FILE,
    }
    stations.append(record)
    station_by_id[node_id] = record
    node_lookup[(line, branch, name)] = node_id
    fare_mapping_by_line_name[(line, name)] = (code, fare_display_name)
    return node_id


def add_chain_nodes(line: str, branch: str, rows: list[dict], prefix: str,
                    start_index: int = 1) -> list[str]:
    ids = []
    for i, r in enumerate(rows, start=start_index):
        name = r["역명"].strip()
        node_id = f"{prefix}_{i:03d}"
        add_station(node_id, line, branch, name, r["연번"],
                    is_junction=name in {"성수", "신도림", "강동"})
        ids.append(node_id)
    return ids


# Line 2 main loop; the final City Hall row closes the loop and reuses the
# first City Hall node rather than creating a duplicate graph vertex.
line2_main_names = [r["역명"].strip() for r in line2_loop[:-1]]
if len(set(line2_main_names)) != len(line2_main_names):
    raise ValueError("Unexpected duplicate station inside Line 2 main-loop rows.")
line2_main_ids = add_chain_nodes("2", "main_loop", line2_loop[:-1], "L2_MAIN")
for name, node_id in zip(line2_main_names, line2_main_ids):
    node_lookup[("2", "main_loop", name)] = node_id
node_lookup[("2", "main_loop", "시청_종점반복")] = line2_main_ids[0]

# Line 2 Seongsu and Sinjeong branch states have separate junction vertices so
# the supplied same-line branch-walking records can be represented explicitly.
l2_seongsu_origin = add_station("L2_SEONGSU_000", "2", "seongsu_branch", "성수",
                                "branch_origin_from_main", True)
l2_seongsu_ids = [l2_seongsu_origin] + add_chain_nodes(
    "2", "seongsu_branch", line2_seongsu, "L2_SEONGSU", 1
)
l2_sinjeong_origin = add_station("L2_SINJEONG_000", "2", "sinjeong_branch", "신도림",
                                 "branch_origin_from_main", True)
l2_sinjeong_ids = [l2_sinjeong_origin] + add_chain_nodes(
    "2", "sinjeong_branch", line2_sinjeong, "L2_SINJEONG", 1
)

# Line 5 trunk and two separate Gangdong branch states.
line5_main_ids = add_chain_nodes("5", "main_to_gangdong", line5_trunk, "L5_MAIN")
l5_hanam_origin = add_station("L5_HANAM_000", "5", "hanam_branch", "강동",
                              line5_gangdong["연번"], True)
l5_hanam_ids = [l5_hanam_origin] + add_chain_nodes(
    "5", "hanam_branch", line5_hanam, "L5_HANAM", 1
)
l5_macheon_origin = add_station("L5_MACHEON_000", "5", "macheon_branch", "강동",
                                line5_gangdong["연번"], True)
l5_macheon_ids = [l5_macheon_origin] + add_chain_nodes(
    "5", "macheon_branch", line5_macheon, "L5_MACHEON", 1
)

# Main-line lookup is explicit to avoid accidentally selecting a branch state.
for r, node_id in zip(line2_loop[:-1], line2_main_ids):
    node_lookup[("2", "main_loop", r["역명"].strip())] = node_id
for r, node_id in zip(line5_trunk, line5_main_ids):
    node_lookup[("5", "main_to_gangdong", r["역명"].strip())] = node_id
for r, node_id in zip(line2_seongsu, l2_seongsu_ids[1:]):
    node_lookup[("2", "seongsu_branch", r["역명"].strip())] = node_id
for r, node_id in zip(line2_sinjeong, l2_sinjeong_ids[1:]):
    node_lookup[("2", "sinjeong_branch", r["역명"].strip())] = node_id
for r, node_id in zip(line5_hanam, l5_hanam_ids[1:]):
    node_lookup[("5", "hanam_branch", r["역명"].strip())] = node_id
for r, node_id in zip(line5_macheon, l5_macheon_ids[1:]):
    node_lookup[("5", "macheon_branch", r["역명"].strip())] = node_id


segments: list[dict] = []
segment_counter = 0


def add_ride_pair(from_id: str, to_id: str, source_row: dict) -> None:
    global segment_counter
    travel_time = mmss_to_seconds(source_row["소요시간"])
    distance = km_to_m(source_row["역간거리(km)"])
    if travel_time is None or distance is None or travel_time <= 0 or distance <= 0:
        raise ValueError(f"Invalid ride segment source row: {source_row}")
    for a, b, inferred in ((from_id, to_id, False), (to_id, from_id, True)):
        segment_counter += 1
        segments.append({
            "edge_id": f"S{segment_counter:04d}",
            "from_node": a,
            "from_station": station_by_id[a]["station_name"],
            "from_line": station_by_id[a]["line"],
            "from_branch": station_by_id[a]["branch_id"],
            "to_node": b,
            "to_station": station_by_id[b]["station_name"],
            "to_line": station_by_id[b]["line"],
            "to_branch": station_by_id[b]["branch_id"],
            "travel_time_sec": travel_time,
            "distance_m": distance,
            "edge_type": "RIDE",
            "direction_inferred": str(inferred).lower(),
            "source_row_no": source_row["연번"],
            "source_file": ROUTE_FILE,
            "note": "역간 자료의 순서 방향을 원방향으로 사용; 역방향은 동일 시간·거리로 가정" if inferred else "원본 행 순서 기준",
        })


def add_chain_edges(node_ids: list[str], target_rows: list[dict]) -> None:
    if len(node_ids) != len(target_rows) + 1:
        raise ValueError("Chain node and target-row counts do not match.")
    for i, r in enumerate(target_rows):
        add_ride_pair(node_ids[i], node_ids[i + 1], r)


# Line 2 loop: row 0 is origin; rows 1..43 encode each following section,
# and the final repeated City Hall row closes the loop.
line2_loop_ids = line2_main_ids + [line2_main_ids[0]]
add_chain_edges(line2_loop_ids, line2_loop[1:])

# Line 2 branches start from branch-specific copies of Seongsu and Sindorim.
add_chain_edges(l2_seongsu_ids, line2_seongsu)
add_chain_edges(l2_sinjeong_ids, line2_sinjeong)

# Line 5 trunk runs Banghwa -> Cheonho. The Gangdong section is duplicated into
# the Hanam/Macheon branch states, preserving the two branch continuations.
add_chain_edges(line5_main_ids, line5_trunk[1:])
add_ride_pair(line5_main_ids[-1], l5_hanam_origin, line5_gangdong)
add_ride_pair(line5_main_ids[-1], l5_macheon_origin, line5_gangdong)
add_chain_edges(l5_hanam_ids, line5_hanam)
add_chain_edges(l5_macheon_ids, line5_macheon)

# Transfer mapping: station/line pair -> graph node. Branch junctions are
# intentionally explicit to preserve the published same-line connector times.
def get_transfer_node(line: str, station: str) -> str:
    if line == "2":
        if station == "성수": return node_lookup[("2", "main_loop", station)]
        if station == "신도림": return node_lookup[("2", "main_loop", station)]
        if station == "까치산": return node_lookup[("2", "sinjeong_branch", station)]
        return node_lookup[("2", "main_loop", station)]
    if line == "5":
        if station == "강동":
            raise ValueError("Gangdong transfer must be handled as a branch connector.")
        return node_lookup[("5", "main_to_gangdong", station)]
    raise ValueError(f"Transfer references excluded line: {line}")


transfer_rows = []
transfer_counter = 0


def add_transfer(from_id: str, to_id: str, travel_time: int, distance: int,
                 transfer_type: str, counts_as_transfer: bool,
                 inferred: bool, source_row_no: str, note: str) -> None:
    global transfer_counter
    transfer_counter += 1
    transfer_rows.append({
        "edge_id": f"T{transfer_counter:04d}",
        "from_node": from_id,
        "from_station": station_by_id[from_id]["station_name"],
        "from_line": station_by_id[from_id]["line"],
        "from_branch": station_by_id[from_id]["branch_id"],
        "to_node": to_id,
        "to_station": station_by_id[to_id]["station_name"],
        "to_line": station_by_id[to_id]["line"],
        "to_branch": station_by_id[to_id]["branch_id"],
        "travel_time_sec": travel_time,
        "distance_m": distance,
        "transfer_type": transfer_type,
        "counts_as_transfer": str(counts_as_transfer).lower(),
        "transfer_count_increment": 1 if counts_as_transfer else 0,
        "direction_inferred": str(inferred).lower(),
        "source_row_no": source_row_no,
        "source_file": TRANSFER_FILE,
        "note": note,
    })


# First, create the three same-line branch connectors.
branch_specs = [
    ("성수", "2", "main_loop", "seongsu_branch", "L2 branch connector"),
    ("신도림", "2", "main_loop", "sinjeong_branch", "L2 branch connector"),
    ("강동", "5", "hanam_branch", "macheon_branch", "L5 branch connector"),
]
for station, line, from_branch, to_branch, note in branch_specs:
    candidates = [r for r in transfer_all
                  if r["호선"].strip() == line
                  and r["환승역명"].strip() == station
                  and r["환승노선"].strip() == f"{line}호선"]
    if len(candidates) != 1:
        raise ValueError(f"Expected one branch-connector source row for {line} {station}; found {len(candidates)}")
    r = candidates[0]
    a = node_lookup[(line, from_branch, station)]
    b = node_lookup[(line, to_branch, station)]
    t = mmss_to_seconds(r["환승소요시간"])
    d = int(r["환승거리"])
    add_transfer(a, b, t, d, "BRANCH_CHANGE", False, True, r["연번"],
                 note + "; 원본에 지선 측 방향 정보가 없어 main/branch 상태 연결 방향은 설계상 가정")
    add_transfer(b, a, t, d, "BRANCH_CHANGE", False, True, r["연번"],
                 note + "; 원본에 지선 측 방향 정보가 없어 반대 연결 방향도 설계상 가정")

# Create inter-line 2<->5 interchange links from all matching source records.
interline_source = [r for r in transfer_all
                    if r["호선"].strip() in {"2", "5"}
                    and r["환승노선"].strip() in {"2호선", "5호선"}
                    and r["호선"].strip() != r["환승노선"].strip().replace("호선", "")]
for r in interline_source:
    from_line = r["호선"].strip()
    to_line = r["환승노선"].strip().replace("호선", "")
    station = r["환승역명"].strip()
    a = get_transfer_node(from_line, station)
    b = get_transfer_node(to_line, station)
    t = mmss_to_seconds(r["환승소요시간"])
    d = int(r["환승거리"])
    add_transfer(a, b, t, d, "LINE_CHANGE", True, False, r["연번"], "원본 환승 데이터 방향")

# Add reverse direction only where the source file does not contain it.
existing_pairs = {(r["from_node"], r["to_node"]) for r in transfer_rows}
for r in list(transfer_rows):
    if r["transfer_type"] != "LINE_CHANGE":
        continue
    a, b = r["to_node"], r["from_node"]
    if (a, b) not in existing_pairs:
        add_transfer(a, b, int(r["travel_time_sec"]), int(r["distance_m"]),
                     "LINE_CHANGE", True, True, r["source_row_no"],
                     "반대 방향 원본 행이 없어 원본 환승시간·거리를 대칭 적용")
        existing_pairs.add((a, b))

# Remove accidental duplicate directed edges, while preserving direction-specific
# source rows if the source happens to contain distinct values.
seen_transfer = set()
for r in transfer_rows:
    key = (r["from_node"], r["to_node"])
    if key in seen_transfer:
        raise ValueError(f"Duplicate transfer edge: {key}")
    seen_transfer.add(key)

# Build the Line 2+5 fare station mapping. Multiple graph states can share one
# fare station code when they are different platform/branch states of one station.
fare_mapping = []
unique_station_fare_codes = set()
seen_line_station = set()
for s in stations:
    key = (s["line"], s["station_name"])
    if key in seen_line_station:
        continue
    seen_line_station.add(key)
    code, display_name = resolve_fare_code(*key)
    unique_station_fare_codes.add(code)
    fare_mapping.append({
        "line": key[0],
        "station_name": key[1],
        "normalized_station_name": normalize_name(key[1]),
        "fare_station_code": code,
        "fare_station_display_name": display_name,
        "mapping_rule": "line-specific fare code range; Kkachisan Line 2 shares 2519",
        "source_file": FARE_FILE,
    })

# Restrict fare OD table to pairs whose endpoints are both in the selected
# Line 2/5 fare-code set. This is a lookup/reference table, not edge fare.
fare_od = [r for r in fare_all
           if r["출발역번호"].strip() in unique_station_fare_codes
           and r["도착역번호"].strip() in unique_station_fare_codes]
expected_pairs = len(unique_station_fare_codes) ** 2
actual_pairs = {(r["출발역번호"].strip(), r["도착역번호"].strip()) for r in fare_od}
missing_fare_pairs = expected_pairs - len(actual_pairs)

# Quality checks and basic directed graph connectivity.
node_ids = {s["node_id"] for s in stations}
if len(node_ids) != len(stations):
    raise ValueError("Duplicate node_id detected.")
for e in segments + transfer_rows:
    if e["from_node"] not in node_ids or e["to_node"] not in node_ids:
        raise ValueError(f"Edge references unknown node: {e}")
    if int(e["travel_time_sec"]) <= 0 or int(e["distance_m"]) <= 0:
        raise ValueError(f"Non-positive time/distance: {e}")

adj = defaultdict(list)
for e in segments + transfer_rows:
    adj[e["from_node"]].append(e["to_node"])
seen = set()
queue = deque([stations[0]["node_id"]])
while queue:
    u = queue.popleft()
    if u in seen:
        continue
    seen.add(u)
    queue.extend(v for v in adj[u] if v not in seen)

checks = [
    {"check": "line2_source_rows", "value": len(route2), "expected": 52, "status": "PASS" if len(route2)==52 else "FAIL"},
    {"check": "line5_source_rows", "value": len(route5), "expected": 56, "status": "PASS" if len(route5)==56 else "FAIL"},
    {"check": "station_nodes", "value": len(stations), "expected": 110, "status": "PASS" if len(stations)==110 else "REVIEW"},
    {"check": "directed_ride_edges", "value": len(segments), "expected": 214, "status": "PASS" if len(segments)==214 else "REVIEW"},
    {"check": "directed_transfer_edges", "value": len(transfer_rows), "expected": 18, "status": "PASS" if len(transfer_rows)==18 else "REVIEW"},
    {"check": "fare_station_codes", "value": len(unique_station_fare_codes), "expected": 106, "status": "PASS" if len(unique_station_fare_codes)==106 else "REVIEW"},
    {"check": "fare_od_rows", "value": len(fare_od), "expected": expected_pairs, "status": "PASS" if len(fare_od)==expected_pairs else "REVIEW"},
    {"check": "unmapped_fare_od_pairs", "value": missing_fare_pairs, "expected": 0, "status": "PASS" if missing_fare_pairs==0 else "REVIEW"},
    {"check": "reachable_nodes_from_first_node", "value": len(seen), "expected": len(stations), "status": "PASS" if len(seen)==len(stations) else "REVIEW"},
]

write_csv("stations.csv", list(stations[0].keys()), stations)
write_csv("segments.csv", list(segments[0].keys()), segments)
write_csv("transfers.csv", list(transfer_rows[0].keys()), transfer_rows)
write_csv("fare_station_mapping.csv", list(fare_mapping[0].keys()), fare_mapping)
write_csv("fare_od_2_5.csv", list(fare_od[0].keys()), fare_od)
write_csv("quality_checks.csv", ["check", "value", "expected", "status"], checks)

# Unified directed edge file for graph loading.
graph_edges = []
for e in segments:
    graph_edges.append({
        "edge_id": e["edge_id"], "from_node": e["from_node"], "to_node": e["to_node"],
        "travel_time_sec": e["travel_time_sec"], "distance_m": e["distance_m"],
        "edge_type": e["edge_type"], "transfer_count_increment": 0,
        "direction_inferred": e["direction_inferred"],
        "source_row_no": e["source_row_no"], "source_file": e["source_file"],
        "note": e["note"],
    })
for e in transfer_rows:
    graph_edges.append({
        "edge_id": e["edge_id"], "from_node": e["from_node"], "to_node": e["to_node"],
        "travel_time_sec": e["travel_time_sec"], "distance_m": e["distance_m"],
        "edge_type": e["transfer_type"],
        "transfer_count_increment": e["transfer_count_increment"],
        "direction_inferred": e["direction_inferred"],
        "source_row_no": e["source_row_no"], "source_file": e["source_file"],
        "note": e["note"],
    })
write_csv("graph_edges.csv", list(graph_edges[0].keys()), graph_edges)

# Also create a compact source coverage report.
report_lines = [
    "SEOUL SUBWAY LINES 2 & 5 PREPROCESSING REPORT",
    "===============================================",
    f"Source route rows: Line 2={len(route2)}, Line 5={len(route5)}",
    f"Output station nodes: {len(stations)}",
    f"Directed ride edges: {len(segments)}",
    f"Directed transfer/branch edges: {len(transfer_rows)}",
    f"Mapped line-station fare entries: {len(fare_mapping)}",
    f"Unique fare station codes: {len(unique_station_fare_codes)}",
    f"Filtered fare OD rows: {len(fare_od)} (expected {expected_pairs})",
    f"Reachable graph nodes: {len(seen)} / {len(stations)}",
    "",
    "Important assumptions:",
    "1. Line 2 rows are split into the main loop, Seongsu branch and Sinjeong branch.",
    "2. The repeated City Hall row closes the Line 2 loop; it is not a new station node.",
    "3. Line 5 rows are split at Gangdong into Hanam and Macheon branches.",
    "4. Reverse ride edges use the published forward time/distance symmetrically; direction_inferred=true marks these edges.",
    "5. Same-line transfer records at Seongsu, Sindorim and Gangdong are modeled as branch connectors and do not increment line-transfer count.",
    "6. Inter-line 2<->5 transfer rows are directed as published; a missing reciprocal row is added with direction_inferred=true.",
    "7. The fare OD subset is a reference/validation lookup, not a per-edge fare weight. Fare must be computed for the complete trip or verified against OD fare data.",
    "8. Line 9 is completely excluded from all processed graph files.",
    "9. Source datasets have different reference dates; record these dates when reporting results.",
    "",
    "Quality checks:",
]
for c in checks:
    report_lines.append(f"- {c['check']}: {c['value']} (expected {c['expected']}) [{c['status']}]")
(OUT / "preprocessing_report.txt").write_text("\n".join(report_lines), encoding="utf-8")

print("Preprocessing completed")
for c in checks:
    print(f"{c['check']}: {c['value']} / {c['expected']} [{c['status']}]")
