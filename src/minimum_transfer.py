
import heapq


def minimum_transfer(subway, start_node, end_node):
    """
    환승 횟수를 최소화하는 경로 탐색 알고리즘.

    1순위: 환승 횟수가 적은 경로
    2순위: 환승 횟수가 같다면 소요 시간이 짧은 경로
    """

    # 각 노드까지의 최적 비용: (환승 횟수, 소요 시간)
    distances = {
        node_id: (float("inf"), float("inf"))
        for node_id in subway.stations
    }

    distances[start_node] = (0, 0)

    previous = {}

    # (환승 횟수, 소요 시간, 현재 노드)
    queue = [(0, 0, start_node)]

    while queue:
        current_transfers, current_time, current_node = (
            heapq.heappop(queue)
        )

        current_cost = (current_transfers, current_time)

        # 이미 더 좋은 경로가 발견된 경우
        if current_cost > distances[current_node]:
            continue

        # 목적지에 도착한 경우
        if current_node == end_node:
            break

        # 연결된 역 탐색
        for edge in subway.graph[current_node]:

            next_node = edge["to"]

            next_transfers = (
                current_transfers + edge["transfer"]
            )

            next_time = current_time + edge["time"]

            next_cost = (next_transfers, next_time)

            # 환승 횟수를 우선 최소화하고,
            # 환승 횟수가 같으면 소요 시간을 비교
            if next_cost < distances[next_node]:

                distances[next_node] = next_cost

                previous[next_node] = (current_node, edge)

                heapq.heappush(
                    queue,
                    (
                        next_transfers,
                        next_time,
                        next_node
                    )
                )

    # 목적지까지 도달할 수 없는 경우
    if distances[end_node][0] == float("inf"):
        return None

    # 경로 복원
    route = []
    current_node = end_node

    while current_node != start_node:

        previous_node, edge = previous[current_node]

        route.append({
            "from": previous_node,
            "to": current_node,
            "time": edge["time"],
            "distance": edge["distance"],
            "type": edge["type"],
            "transfer": edge["transfer"]
        })

        current_node = previous_node

    route.reverse()

    return {
        "total_transfers": distances[end_node][0],
        "total_time": distances[end_node][1],
        "route": route
    }
