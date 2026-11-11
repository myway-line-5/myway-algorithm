
from graph import SubwayGraph
from dijkstra import dijkstra
from constrained_dijkstra import constrained_dijkstra
from minimum_transfer import minimum_transfer


class RouteManager:

    def __init__(self, subway):
        self.subway = subway

    def find_route(self, request):

        departure = request.get("departure")
        destination = request.get("destination")
        optimization = request.get("optimization", "shortest_time")
        constraints = request.get("constraints") or {}

        # 1. 필수 입력 확인
        if not departure or not destination:
            return {
                "status": "error",
                "message": "출발역과 도착역을 입력해야 합니다."
            }

        # 2. 최적화 기준 확인
        if optimization not in ["shortest_time", "minimum_transfer"]:
            return {
                "status": "error",
                "message": "지원하지 않는 경로 탐색 기준입니다."
            }

        # 3. 제약 조건 확인
        max_time = constraints.get("max_time")
        max_transfers = constraints.get("max_transfers")

        if max_time is not None:
            if not isinstance(max_time, (int, float)) or max_time < 0:
                return {
                    "status": "error",
                    "message": "최대 소요 시간은 0 이상의 숫자여야 합니다."
                }

        if max_transfers is not None:
            if (
                not isinstance(max_transfers, int)
                or isinstance(max_transfers, bool)
                or max_transfers < 0
            ):
                return {
                    "status": "error",
                    "message": "최대 환승 횟수는 0 이상의 정수여야 합니다."
                }

        # 4. 최소 환승 + 추가 제약 조건은 현재 미지원
        if optimization == "minimum_transfer":
            if max_time is not None or max_transfers is not None:
                return {
                    "status": "error",
                    "message": "최소 환승 탐색과 추가 제약 조건의 조합은 아직 지원하지 않습니다."
                }

        # 5. 출발역과 도착역 검색
        start_candidates = self.subway.find_station(departure)
        end_candidates = self.subway.find_station(destination)

        if not start_candidates:
            return {
                "status": "error",
                "message": f"출발역 '{departure}'을 찾을 수 없습니다."
            }

        if not end_candidates:
            return {
                "status": "error",
                "message": f"도착역 '{destination}'을 찾을 수 없습니다."
            }

        if len(start_candidates) > 1:
            return {
                "status": "need_selection",
                "message": "출발역 후보가 여러 개입니다.",
                "candidates": start_candidates
            }

        if len(end_candidates) > 1:
            return {
                "status": "need_selection",
                "message": "도착역 후보가 여러 개입니다.",
                "candidates": end_candidates
            }

        start_node = start_candidates[0]
        end_node = end_candidates[0]

        # 6. 경로 탐색 알고리즘 선택
        if optimization == "shortest_time":

            if max_time is not None or max_transfers is not None:
                result = constrained_dijkstra(
                    self.subway,
                    start_node,
                    end_node,
                    max_time=max_time,
                    max_transfers=max_transfers
                )

                algorithm_name = "조건부 다익스트라"

            else:
                result = dijkstra(
                    self.subway,
                    start_node,
                    end_node
                )

                algorithm_name = "최단 시간 다익스트라"

        else:
            result = minimum_transfer(
                self.subway,
                start_node,
                end_node
            )

            algorithm_name = "최소 환승 다익스트라"

        # 7. 경로 존재 여부 확인
        if result is None:
            return {
                "status": "no_route",
                "message": "조건에 맞는 경로를 찾을 수 없습니다."
            }

        # 8. 결과 반환
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
        "destination": "잠실",
        "optimization": "shortest_time",
        "constraints": {}
    }

    result = manager.find_route(request)

    print(result)
