
import heapq


def dijkstra(subway, start_node, end_node):
    """최단 시간을 기준으로 경로를 탐색하는 다익스트라 알고리즘"""

    distances = {
        node_id: float("inf")
        for node_id in subway.stations
    }

    previous = {}

    distances[start_node] = 0
    queue = [(0, start_node)]

    while queue:
        current_time, current_node = heapq.heappop(queue)

        if current_time > distances[current_node]:
            continue

        if current_node == end_node:
            break

        for edge in subway.graph[current_node]:
            next_node = edge["to"]
            next_time = current_time + edge["time"]

            if next_time < distances[next_node]:
                distances[next_node] = next_time

                previous[next_node] = (current_node, edge)

                heapq.heappush(
                    queue,
                    (next_time, next_node)
                )

    if distances[end_node] == float("inf"):
        return None

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

    total_transfers = sum(
        step["transfer"]
        for step in route
    )

    return {
        "total_time": distances[end_node],
        "total_transfers": total_transfers,
        "route": route
    }
