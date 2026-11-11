
from graph import SubwayGraph
from dijkstra import dijkstra
from minimum_transfer import minimum_transfer
from constrained_dijkstra import constrained_dijkstra


class RouteManager:

    def __init__(self, subway):
        self.subway = subway

    def find_exact_station(self, station_name):
        """역 이름이 정확히 일치하는 노드 검색"""

        results = []

        for node_id, info in self.subway.stations.items():
            if info["name"] == station_name:
                results.append({
                    "node_id": node_id,
                    "name": info["name"],
                    "line": info["line"],
                    "branch": info["branch"]
                })

        return results

    def search(self, request):
        """구조화된 사용자 요청을 받아 적절한 경로 알고리즘 실행"""

        departure = request.get("departure")
        destination = request.get("destination")

        constraints = request.get("constraints") or {}
        optimization = request.get("optimization", "shortest_time")

        # 1. 필수 입력 확인
        if not isinstance(departure, str) or not departure.strip():
            return {
                "status": "error",
                "message": "출발역을 입력해야 합니다."
            }

        if not isinstance(destination, str) or not destination.strip():
            return {
                "status": "error",
                "message": "도착역을 입력해야 합니다."
            }

        if not isinstance(constraints, dict):
            return {
                "status": "error",
                "message": "constraints는 딕셔너리 형식이어야 합니다."
            }

        # 2. 최적화 목적 확인
        if optimization not in ["shortest_time", "minimum_transfer"]:
            return {
                "status": "error",
                "message": f"지원하지 않는 최적화 방식입니다: {optimization}"
            }

        max_time = constraints.get("max_time")
        max_transfers = constraints.get("max_transfers")

        # 3. 제한 조건 검증
        if max_time is not None:
            if (
                isinstance(max_time, bool)
                or not isinstance(max_time, (int, float))
                or max_time < 0
            ):
                return {
                    "status": "error",
                    "message": "최대 소요 시간은 0 이상의 숫자여야 합니다."
                }

        if max_transfers is not None:
            if (
                isinstance(max_transfers, bool)
                or not isinstance(max_transfers, int)
                or max_transfers < 0
            ):
                return {
                    "status": "error",
                    "message": "최대 환승 횟수는 0 이상의 정수여야 합니다."
                }

        # 4. 역 이름 검색
        start_results = self.find_exact_station(departure)
        end_results = self.find_exact_station(destination)

        if not start_results:
            return {
                "status": "error",
                "message": f"출발역 '{departure}'을 찾을 수 없습니다."
            }

        if not end_results:
            return {
                "status": "error",
                "message": f"도착역 '{destination}'을 찾을 수 없습니다."
            }

        # 5. 동일 역 이름이 여러 노드에 존재하는 경우
        if len(start_results) > 1:
            return {
                "status": "need_selection",
                "station_type": "departure",
                "candidates": start_results,
                "message": "출발역의 노선을 선택해야 합니다."
            }

        if len(end_results) > 1:
            return {
                "status": "need_selection",
                "station_type": "destination",
                "candidates": end_results,
                "message": "도착역의 노선을 선택해야 합니다."
            }

        start_node = start_results[0]["node_id"]
        end_node = end_results[0]["node_id"]

        # 6. 알고리즘 선택
        if optimization == "shortest_time":

            if max_time is not None or max_transfers is not None:
                algorithm_name = "조건부 다익스트라"

                result = constrained_dijkstra(
                    self.subway,
                    start_node,
                    end_node,
                    max_time=max_time,
                    max_transfers=max_transfers
                )

            else:
                algorithm_name = "최단 시간 다익스트라"

                result = dijkstra(
                    self.subway,
                    start_node,
                    end_node
                )

        elif optimization == "minimum_transfer":

            # 현재 최소 환승 알고리즘은 제한 조건을 적용하지 않음
            if max_time is not None or max_transfers is not None:
                return {
                    "status": "error",
                    "message": (
                        "현재 최소 환승 알고리즘은 "
                        "시간·환승 제한과 함께 사용할 수 없습니다."
                    )
                }

            algorithm_name = "최소 환승 다익스트라"

            result = minimum_transfer(
                self.subway,
                start_node,
                end_node
            )

        # 7. 경로가 없는 경우
        if result is None:
            return {
                "status": "no_route",
                "message": "조건을 만족하는 경로가 없습니다."
            }

        # 8. 결과 반환
        # 알고리즘 결과에 환승 횟수가 없으면 경로에서 직접 계산
        total_transfers = result.get("total_transfers")

        if total_transfers is None:
            total_transfers = sum(
                step.get("transfer", 0)
                for step in result["route"]
            )

        return {
            "status": "success",
            "algorithm": algorithm_name,
            "departure": departure,
            "destination": destination,
            "total_time": result["total_time"],
            "total_transfers": total_transfers,
            "route": result["route"]
        }


if __name__ == "__main__":
    subway = SubwayGraph()
    manager = RouteManager(subway)

    request = {
        "departure": "강남",
        "destination": "여의도",
        "constraints": {
            "max_time": 40 * 60,
            "max_transfers": 1
        },
        "optimization": "shortest_time"
    }

    result = manager.search(request)

    print("\n===== 경로 탐색 결과 =====")

    if result["status"] == "success":
        print(f"알고리즘: {result['algorithm']}")
        print(f"출발역: {result['departure']}")
        print(f"도착역: {result['destination']}")
        print(f"총 소요 시간: {result['total_time']}초")
        print(f"총 환승 횟수: {result['total_transfers']}")

        print("\n===== 이동 경로 =====")

        for step in result["route"]:
            print(
                f"{step['from']} → {step['to']} "
                f"({step['time']}초)"
            )
    else:
        print(result["message"])
