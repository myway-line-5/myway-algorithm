
import heapq


def constrained_dijkstra(
    subway,
    start_node,
    end_node,
    max_time=None,
    max_transfers=None
):
    # 상태: (현재 역, 지금까지의 환승 횟수)
    start_state = (start_node, 0)

    # 각 상태까지의 최소 소요 시간
    distances = {start_state: 0}

    # 경로 복원을 위한 이전 상태
    previous = {}

    # (누적 시간, 현재 역, 환승 횟수)
    queue = [(0, start_node, 0)]

    final_state = None

    while queue:
        current_time, current_node, transfers = (
            heapq.heappop(queue)
        )

        current_state = (current_node, transfers)

        if current_time > distances[current_state]:
            continue

        # 시간 제한을 넘으면 탐색하지 않음
        if max_time is not None and current_time > max_time:
            continue

        # 목적지 도착
        if current_node == end_node:
            final_state = current_state
            break

        for edge in subway.graph[current_node]:
            next_node = edge["to"]

            next_time = current_time + edge["time"]

            next_transfers = (
                transfers + edge["transfer"]
            )

            # 시간 제한 검사
            if max_time is not None and next_time > max_time:
                continue

            if max_transfers is not None and next_transfers > max_transfers:
                continue
            next_state = (next_node, next_transfers)

            # 더 짧은 경로인지 확인
            if next_time < distances.get(
                next_state, float("inf")
            ):
                distances[next_state] = next_time

                previous[next_state] = (
                    current_state,
                    edge
                )

                heapq.heappush(
                    queue,
                    (
                        next_time,
                        next_node,
                        next_transfers
                    )
                )

    # 조건을 만족하는 경로가 없는 경우
    if final_state is None:
        return None

    # 경로 복원
    route = []
    current_state = final_state

    while current_state != start_state:
        previous_state, edge = previous[current_state]

        route.append({
            "from": previous_state[0],
            "to": current_state[0],
            "time": edge["time"],
            "distance": edge["distance"],
            "type": edge["type"],
            "transfer": edge["transfer"]
        })

        current_state = previous_state

    route.reverse()

    return {
        "total_time": distances[final_state],
        "total_transfers": final_state[1],
        "route": route
    }
