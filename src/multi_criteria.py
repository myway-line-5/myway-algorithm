
"""
Multi-Criteria Subway Route Search

사용자가 선택한 우선순위에 따라 최적 경로를 탐색한다.

지원 기준:
    distance  : 이동거리 최소
    fare      : 운임 최소
    time      : 소요 시간 최소
    transfers : 환승 횟수 최소

사용 예시:
    result = multi_criteria(
        subway,
        "L2_MAIN_037",
        "L9_MAIN_038",
        priorities=["fare", "time"]
    )
"""

import heapq
import itertools
import math

# --------------------------------------------------
# 1. 우선순위 설정
# --------------------------------------------------

VALID_PRIORITIES = {
    "distance",
    "fare",
    "time",
    "transfers"
}

DEFAULT_PRIORITIES = [
    "distance",
    "fare",
    "time",
    "transfers"
]

def validate_priorities(priorities):
    """
    우선순위 입력값 검사.

    1~4개까지 선택할 수 있으며 중복은 허용하지 않는다.
    """

    if priorities is None:
        return DEFAULT_PRIORITIES.copy()

    if not isinstance(priorities, (list, tuple)):
        raise ValueError("priorities는 리스트 또는 튜플이어야 합니다.")

    if not 1 <= len(priorities) <= 4:
        raise ValueError("우선순위는 1개 이상 4개 이하로 선택해야 합니다.")

    if any(not isinstance(item, str) for item in priorities):
        raise ValueError("우선순위 항목은 문자열이어야 합니다.")

    if len(set(priorities)) != len(priorities):
        raise ValueError("동일한 우선순위를 중복 선택할 수 없습니다.")

    invalid = set(priorities) - VALID_PRIORITIES

    if invalid:
        raise ValueError(
            f"지원하지 않는 우선순위입니다: {sorted(invalid)}"
        )

    return list(priorities)

# --------------------------------------------------
# 2. 운임 계산
# --------------------------------------------------

def calculate_fare(distance_m):
    """
    누적 이동거리를 기준으로 운임을 계산한다.

    현재 프로젝트에서 사용한 거리별 추정 운임:
        10km 이하: 1550원
        10km 초과 ~ 50km: 5km마다 100원 추가
        50km 초과: 8km마다 100원 추가

    주의:
        실제 수도권 운임 전체 규칙을 구현한 것이 아니라
        프로젝트에서 사용하는 거리 기반 추정 방식이다.
    """

    if distance_m < 0:
        raise ValueError("이동거리는 음수일 수 없습니다.")

    if distance_m <= 10000:
        return 1550

    if distance_m <= 50000:
        extra_units = math.ceil((distance_m - 10000) / 5000)
        return 1550 + extra_units * 100

    extra_units = math.ceil((distance_m - 50000) / 8000)

    return 2350 + extra_units * 100

# --------------------------------------------------
# 3. 간선 정보 처리
# --------------------------------------------------

def get_edge_distance(edge):
    """간선의 이동거리를 반환한다."""

    edge_type = str(edge.get("type", "RIDE")).upper()

    # 노선 변경 환승 간선의 거리는 이동거리에서 제외한다.
    if edge_type in {"LINE_CHANGE", "TRANSFER"}:
        return 0.0

    distance = edge.get(
        "distance",
        edge.get("distance_m", 0)
    )

    distance = float(distance or 0)

    if distance < 0:
        raise ValueError("간선 이동거리는 음수일 수 없습니다.")

    return distance

def get_edge_time(edge):
    """간선의 소요 시간을 반환한다."""

    time_value = edge.get(
        "time",
        edge.get("travel_time", 0)
    )

    time_value = float(time_value or 0)

    if time_value < 0:
        raise ValueError("간선 소요 시간은 음수일 수 없습니다.")

    return time_value

def get_transfer_count(edge):
    """간선에서 증가하는 환승 횟수를 반환한다."""

    edge_type = str(edge.get("type", "")).upper()

    if edge_type == "LINE_CHANGE":
        return 1

    transfer_value = edge.get("transfer", 0)

    if isinstance(transfer_value, bool):
        return int(transfer_value)

    if transfer_value is None:
        return 0

    count = int(transfer_value)

    if count < 0:
        raise ValueError("환승 횟수는 음수일 수 없습니다.")

    return count

# --------------------------------------------------
# 4. 경로의 우선순위 비교값 생성
# --------------------------------------------------

def get_priority_key(label, priorities):
    """
    사용자가 지정한 순서대로 비교할 튜플을 생성한다.

    예:
        priorities = ["fare", "time"]

        반환:
            (운임, 소요 시간)
    """

    values = {
        "distance": label["distance"],
        "fare": calculate_fare(label["distance"]),
        "time": label["time"],
        "transfers": label["transfers"]
    }

    return tuple(values[key] for key in priorities)

def get_dominance_key(label, priorities):
    """
    향후 경로 확장 가능성을 고려한 지배 관계 비교값.

    운임을 우선순위에 포함하면 누적 거리가 이후 운임에
    영향을 주므로 distance도 내부적으로 비교한다.

    단, distance가 사용자 우선순위에 포함되지 않았다면
    최종 경로 선택 기준으로 사용하지는 않는다.
    """

    dimensions = []

    if "distance" in priorities or "fare" in priorities:
        dimensions.append(label["distance"])

    if "fare" in priorities:
        dimensions.append(calculate_fare(label["distance"]))

    if "time" in priorities:
        dimensions.append(label["time"])

    if "transfers" in priorities:
        dimensions.append(label["transfers"])

    return tuple(dimensions)

# --------------------------------------------------
# 5. 다중 라벨 지배 관계 검사
# --------------------------------------------------

def dominates(a, b):
    """
    a가 b보다 모든 비교 항목에서 작거나 같고,
    적어도 하나에서 더 작으면 a가 b를 지배한다.

    모든 항목이 같아도 기존 후보를 유지한다.
    """

    if len(a) != len(b):
        return False

    return all(x <= y for x, y in zip(a, b))

# --------------------------------------------------
# 6. 다중 조건 경로 탐색
# --------------------------------------------------

def multi_criteria(
    subway,
    start_node,
    end_node,
    priorities=None
):
    """
    사용자 우선순위에 따른 다중 조건 경로 탐색.

    Parameters
    ----------
    subway:
        .stations와 .graph를 가진 SubwayGraph 객체

    start_node:
        출발역 노드 ID

    end_node:
        도착역 노드 ID

    priorities:
        1~4개의 우선순위 리스트

        예:
            ["distance"]
            ["fare", "time"]
            ["transfers", "fare", "distance"]
            ["distance", "fare", "time", "transfers"]

    Returns
    -------
    dict 또는 None

    성공:
        {
            "total_time": ...,
            "total_distance": ...,
            "total_fare": ...,
            "total_transfers": ...,
            "priority_order": [...],
            "route": [...]
        }

    실패:
        None
    """

    # ----------------------------------------------
    # 입력값 검사
    # ----------------------------------------------

    priorities = validate_priorities(priorities)

    if subway is None:
        raise ValueError("subway 객체가 필요합니다.")

    if not hasattr(subway, "stations") or not hasattr(subway, "graph"):
        raise ValueError("subway에는 stations와 graph가 필요합니다.")

    if start_node not in subway.stations:
        raise ValueError(f"출발역 노드가 존재하지 않습니다: {start_node}")

    if end_node not in subway.stations:
        raise ValueError(f"도착역 노드가 존재하지 않습니다: {end_node}")

    if start_node not in subway.graph:
        raise ValueError(f"출발역 그래프 노드가 존재하지 않습니다: {start_node}")

    if start_node == end_node:
        return {
            "total_time": 0.0,
            "total_distance": 0.0,
            "total_fare": calculate_fare(0),
            "total_transfers": 0,
            "priority_order": priorities,
            "route": []
        }

    # ----------------------------------------------
    # 초기 탐색 상태
    # ----------------------------------------------

    counter = itertools.count()

    labels = {}
    frontiers = {
        node_id: []
        for node_id in subway.graph
    }

    start_label = {
        "node": start_node,
        "distance": 0.0,
        "time": 0.0,
        "transfers": 0,
        "route": [],
        "active": True
    }

    start_id = next(counter)
    labels[start_id] = start_label
    frontiers[start_node].append(start_id)

    queue = []

    heapq.heappush(
        queue,
        (
            get_priority_key(start_label, priorities),
            next(counter),
            start_id
        )
    )

    # ----------------------------------------------
    # 다중 라벨 탐색
    # ----------------------------------------------

    while queue:

        _, _, current_id = heapq.heappop(queue)

        current = labels[current_id]

        # 이미 더 나은 후보에 의해 제거된 상태라면 건너뛴다.
        if not current["active"]:
            continue

        current_node = current["node"]

        if current_node not in subway.graph:
            continue

        for edge in subway.graph[current_node]:

            next_node = edge.get("to")

            if next_node is None:
                raise ValueError(
                    f"간선에 'to' 목적지 정보가 없습니다: {edge}"
                )

            if next_node not in subway.graph:
                raise ValueError(
                    f"그래프에 존재하지 않는 목적지 노드입니다: {next_node}"
                )

            edge_distance = get_edge_distance(edge)
            edge_time = get_edge_time(edge)
            edge_transfers = get_transfer_count(edge)

            # 새로운 경로 후보 생성
            new_route = current["route"] + [
                {
                    **edge,
                    "from": current_node,
                    "to": next_node
                }
            ]

            new_label = {
                "node": next_node,
                "distance": current["distance"] + edge_distance,
                "time": current["time"] + edge_time,
                "transfers": current["transfers"] + edge_transfers,
                "route": new_route,
                "active": True
            }

            new_key = get_dominance_key(
                new_label,
                priorities
            )

            # --------------------------------------
            # 기존 후보와 지배 관계 비교
            # --------------------------------------

            rejected = False

            for existing_id in frontiers[next_node]:

                existing = labels[existing_id]

                if not existing["active"]:
                    continue

                existing_key = get_dominance_key(
                    existing,
                    priorities
                )

                # 기존 후보가 새 후보보다 좋거나 같으면 제외
                if dominates(existing_key, new_key):
                    rejected = True
                    break

            if rejected:
                continue

            # --------------------------------------
            # 새 후보가 지배하는 기존 후보 제거
            # --------------------------------------

            for existing_id in frontiers[next_node]:

                existing = labels[existing_id]

                if not existing["active"]:
                    continue

                existing_key = get_dominance_key(
                    existing,
                    priorities
                )

                if dominates(new_key, existing_key):
                    existing["active"] = False

            # 새 후보 등록
            new_id = next(counter)

            labels[new_id] = new_label
            frontiers[next_node].append(new_id)

            heapq.heappush(
                queue,
                (
                    get_priority_key(new_label, priorities),
                    next(counter),
                    new_id
                )
            )

    # ----------------------------------------------
    # 도착역 후보 중 최적 경로 선택
    # ----------------------------------------------

    candidates = []

    for label_id in frontiers.get(end_node, []):

        label = labels[label_id]

        if not label["active"]:
            continue

        candidates.append(label)

    if not candidates:
        return None

    best = min(
        candidates,
        key=lambda label: get_priority_key(
            label,
            priorities
        )
    )

    # ----------------------------------------------
    # 최종 반환
    # ----------------------------------------------

    return {
        "total_time": best["time"],
        "total_distance": best["distance"],
        "total_fare": calculate_fare(best["distance"]),
        "total_transfers": best["transfers"],
        "priority_order": priorities,
        "route": best["route"]
    }
