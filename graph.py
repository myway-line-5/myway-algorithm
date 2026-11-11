
from pathlib import Path
import pandas as pd
from collections import defaultdict


class SubwayGraph:
    def __init__(self):
        self.project_dir = Path(__file__).resolve().parent.parent
        self.data_dir = self.project_dir / "processed"

        self.stations = {}
        self.graph = defaultdict(list)

        self.load_data()

    def read_csv(self, filename):
        file_path = self.data_dir / filename

        for encoding in ["utf-8-sig", "cp949", "euc-kr"]:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue

        raise ValueError(f"CSV 인코딩 오류: {filename}")

    def load_data(self):
        # 역 정보 불러오기
        station_df = self.read_csv("stations.csv")

        for _, row in station_df.iterrows():
            node_id = row["node_id"]

            self.stations[node_id] = {
                "name": row["station_name"],
                "line": row["line"],
                "branch": row["branch_id"]
            }

        # 전체 연결 정보 불러오기
        edge_df = self.read_csv("graph_edges.csv")

        for _, row in edge_df.iterrows():
            from_node = row["from_node"]
            to_node = row["to_node"]

            # 존재하지 않는 역을 연결하는 데이터 방지
            if from_node not in self.stations:
                raise ValueError(f"출발 노드가 존재하지 않습니다: {from_node}")

            if to_node not in self.stations:
                raise ValueError(f"도착 노드가 존재하지 않습니다: {to_node}")

            travel_time = float(row["travel_time_sec"])
            distance = float(row["distance_m"])

            if travel_time < 0 or distance < 0:
                raise ValueError(f"음수 이동 비용 발견: {row['edge_id']}")

            transfer_increment = int(
                row["transfer_count_increment"]
            ) if pd.notna(row["transfer_count_increment"]) else 0

            if transfer_increment < 0:
                raise ValueError(
                    f"음수 환승 증가량 발견: {row['edge_id']}"
                )

            edge = {
                "to": to_node,
                "time": travel_time,
                "distance": distance,
                "type": row["edge_type"],
                "transfer": transfer_increment,
                "edge_id": row["edge_id"]
            }

            self.graph[from_node].append(edge)

        print("그래프 생성 완료")
        print(f"역 개수: {len(self.stations)}")
        print(f"연결 개수: {sum(len(v) for v in self.graph.values())}")

    # 역 이름으로 검색
    def find_station(self, station_name):
        results = []

        for node_id, info in self.stations.items():
            if station_name in info["name"]:
                results.append({
                    "node_id": node_id,
                    "name": info["name"],
                    "line": info["line"],
                    "branch": info["branch"]
                })

        return results
