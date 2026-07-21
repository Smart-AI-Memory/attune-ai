"""Trajectory Comparator for Attune AI Ghost Simulator.

Synthesizes comparative metrics, test pass ratios, and diff summaries
across completed ghost trajectories.
"""

from typing import Any


class TrajectoryComparator:
    """Generates comparative matrices across executed ghost trajectories."""

    def compare(self, trajectory_results: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """Compares results across trajectories and highlights the winner.

        Args:
            trajectory_results: Output map from MultiTrajectoryRunner.

        Returns:
            Comparative analysis dictionary with metric breakdown and
            recommended trajectory (None when no trajectory succeeded).
        """
        best_trajectory: str | None = None
        best_score = float("-inf")
        matrix: list[dict[str, Any]] = []

        for traj_id, data in trajectory_results.items():
            success = data.get("success", False)
            tests_passed = data.get("tests_passed", 0)
            tests_total = data.get("tests_total", 0)
            duration = data.get("duration_seconds", 0.0)

            pass_rate = (tests_passed / tests_total) if tests_total > 0 else 0.0
            score = (pass_rate * 100.0) - (duration * 0.1) if success else float("-inf")

            if success and score > best_score:
                best_score = score
                best_trajectory = traj_id

            matrix.append(
                {
                    "trajectory_id": traj_id,
                    "success": success,
                    "pass_rate": round(pass_rate * 100, 1),
                    "duration_seconds": duration,
                    "files_modified": data.get("files_modified", []),
                }
            )

        return {
            "recommended_trajectory": best_trajectory,
            "comparison_matrix": matrix,
        }
