
import heapq
import math

def calculate_fare(
    distance_m,
    base_fare=1550,
    base_distance_m=10000,
    middle_limit_m=50000,
    middle_unit_m=5000,
    long_unit_m=8000,
    extra_fare=100
):
    """
    수도권 일반 교통카드 성인 거리비례 운임 추정.

    - 10km 이하: 기본요금
    - 10km 초과~50km: 5km마다 100원 추가
    - 50km 초과: 8km마다 100원 추가
    """

    if distance_m < 0:
        raise ValueError("이동거리는 음수일 수 없습니다.")

    if distance_m <= base_distance_m:
        return base_fare

    if distance_m <= middle_limit_m:
        extra_units = math.ceil(
            (distance_m - base_distance_m) / middle_unit_m
        )
        return base_fare + extra_units * extra_fare

    # 50km까지의 추가 운임
    middle_units = math.ceil(
        (middle_limit_m - base_distance_m) / middle_unit_m
    )

    middle_fare = base_fare + middle_units * extra_fare

    # 50km 초과 구간의 추가 운임
    long_units = math.ceil(
        (distance_m - middle_limit_m) / long_unit_m
    )

    return middle_fare + long_units * extra_fare

def minimum_cost(subway, start_node, end_node):
    """
    총 운임을 최소화하는 경로 탐색 알고리즘.

    우선순위:
    1. 총 운임이 가장 저렴한 경로
    2. 운임이 같으면 소요 시간이 짧은 경로
    3. 시간까지 같으면 환승 횟수가 적은 경로

    운임은 누적 RIDE 거리로 계산한다.
    LINE_CHANGE 간선의 거리는 운임 거리에서 제외한다.

    여러 경로의 (거리, 시간, 환승 횟수)를 관리하여
    동일 운임 구간 안에서 더 빠른 경로도 비교한다.
    """

    if start_node not in subway.stations:
        raise ValueError(f"출발역 노드를 찾을 수 없습니다: {start_node}")

    if end_node not in subway.stations:
        raise ValueError(f"도착역 노드를 찾을 수 없습니다: {end_node}")

    if start_node == end_node:
        return {
            "total_fare": calculate_fare(0),
            "total_distance": 0,
            "total_time": 0,
            "total_transfers": 0,
            "route": []
        }

    # 각 경로 후보의 정보
    # label = 거리, 시간, 환승 횟수, 이전 label, 이전 간선
    labels = [{
        "node": start_node,
        "distance": 0.0,
        "time": 0.0,
        "transfers": 0,
        "previous": None,
        "edge": None,
        "active": True
    }]

    # 노드별로 유지할 경로 후보의 label ID
    labels_by_node = {
        node_id: []
        for node_id in subway.stations
    }
    labels_by_node[start_node].append(0)

    # (누적 거리, 누적 시간, 환승 횟수, label ID)
    queue = [(0.0, 0.0, 0, 0)]

    while queue:
        current_distance, current_time, current_transfers, label_id = (
            heapq.heappop(queue)
        )

        current_label = labels[label_id]

        # 다른 경로에 의해 이미 열등한 후보가 된 경우
        if not current_label["active"]:
            continue

        current_node = current_label["node"]

        for edge in subway.graph[current_node]:
            next_node = edge["to"]
            edge_type = edge["type"]

            edge_time = float(edge["time"])
            edge_transfer = int(edge.get("transfer", 0))

            if edge_time < 0 or edge_transfer < 0:
                raise ValueError("시간과 환승 증가는 음수일 수 없습니다.")

            # 실제 이동 간선의 거리만 운임 계산에 포함
            if edge_type == "RIDE":
                edge_distance = float(edge["distance"])
            else:
                edge_distance = 0.0

            if edge_distance < 0:
                raise ValueError("이동거리는 음수일 수 없습니다.")

            next_distance = current_distance + edge_distance
            next_time = current_time + edge_time
            next_transfers = current_transfers + edge_transfer

            # 기존 후보에 비해 새 후보가 열등한지 검사
            dominated = False

            for old_id in labels_by_node[next_node]:
                old = labels[old_id]

                if not old["active"]:
                    continue

                if (
                    old["distance"] <= next_distance
                    and old["time"] <= next_time
                    and old["transfers"] <= next_transfers
                ):
                    dominated = True
                    break

            if dominated:
                continue

            # 새 후보가 기존 후보보다 우수하면 기존 후보 제거
            for old_id in labels_by_node[next_node]:
                old = labels[old_id]

                if not old["active"]:
                    continue

                if (
                    next_distance <= old["distance"]
                    and next_time <= old["time"]
                    and next_transfers <= old["transfers"]
                ):
                    old["active"] = False

            # 새로운 경로 후보 등록
            new_id = len(labels)

            labels.append({
                "node": next_node,
                "distance": next_distance,
                "time": next_time,
                "transfers": next_transfers,
                "previous": label_id,
                "edge": edge,
                "active": True
            })

            labels_by_node[next_node].append(new_id)

            heapq.heappush(
                queue,
                (
                    next_distance,
                    next_time,
                    next_transfers,
                    new_id
                )
            )

    # 목적지의 모든 유효 후보 중 최적 경로 선택
    destination_candidates = [
        label_id
        for label_id in labels_by_node[end_node]
        if labels[label_id]["active"]
    ]

    if not destination_candidates:
        return None

    best_id = min(
        destination_candidates,
        key=lambda label_id: (
            calculate_fare(labels[label_id]["distance"]),
            labels[label_id]["time"],
            labels[label_id]["transfers"]
        )
    )

    best = labels[best_id]

    # 경로 복원
    route = []
    current_id = best_id

    while labels[current_id]["previous"] is not None:
        current_label = labels[current_id]

        previous_id = current_label["previous"]
        edge = current_label["edge"]

        previous_node = labels[previous_id]["node"]

        route.append({
            "from": previous_node,
            "to": current_label["node"],
            "time": edge["time"],
            "distance": edge["distance"],
            "fare_distance": (
                edge["distance"]
                if edge["type"] == "RIDE"
                else 0
            ),
            "type": edge["type"],
            "transfer": edge.get("transfer", 0)
        })

        current_id = previous_id

    route.reverse()

    return {
        "total_fare": calculate_fare(best["distance"]),
        "total_distance": best["distance"],
        "total_time": best["time"],
        "total_transfers": best["transfers"],
        "route": route
    }