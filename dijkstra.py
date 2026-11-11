
import heapq


def dijkstra(subway, start_node, end_node):
    # 각 역까지의 최소 이동 시간
    distances = {
        node_id: float("inf")
        for node_id in subway.stations
    }

    # 이전 역과 이동 정보를 저장
    previous = {}

    distances[start_node] = 0

    # (현재까지 걸린 시간, 현재 역)
    queue = [(0, start_node)]

    while queue:
        current_time, current_node = heapq.heappop(queue)

        # 이미 더 짧은 경로를 찾았다면 건너뛰기
        if current_time > distances[current_node]:
            continue

        # 목적지에 도착하면 탐색 종료
        if current_node == end_node:
            break

        # 현재 역과 연결된 역 탐색
        for edge in subway.graph[current_node]:
            next_node = edge["to"]
            travel_time = edge["time"]

            new_time = current_time + travel_time

            # 더 짧은 경로를 발견한 경우
            if new_time < distances[next_node]:
                distances[next_node] = new_time

                previous[next_node] = (
                    current_node,
                    edge
                )

                heapq.heappush(
                    queue,
                    (new_time, next_node)
                )

    # 도착할 수 없는 경우
    if distances[end_node] == float("inf"):
        return None

    # 경로 역추적
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
        "total_time": distances[end_node],
        "route": route
    }
