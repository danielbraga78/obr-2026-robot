import unittest

from competition.behavior_manager import BehaviorManager
from competition.config import load_config
from competition.navigation.navigator import Navigator
from competition.world_model import WorldModel

REPO_ROOT = "/home/leosouza/Desktop/robot-OBR/2026/teste"


class CompetitionArchitectureTests(unittest.TestCase):
    def test_world_model_defaults(self) -> None:
        world = WorldModel()
        self.assertFalse(world.line_visible)
        self.assertFalse(world.obstacle_detected)
        self.assertFalse(world.camera_connected)

    def test_behavior_manager_starts_with_follow_line(self) -> None:
        manager = BehaviorManager()
        behavior = manager.current_behavior
        self.assertEqual(behavior.name, "FOLLOW_LINE")

    def test_navigator_emits_move_command(self) -> None:
        navigator = Navigator()
        cmd = navigator.build_command("follow", 0.2, -0.1)
        self.assertEqual(cmd, "MOVE,20,0,0")

    def test_config_loader_reads_yaml(self) -> None:
        config = load_config(f"{REPO_ROOT}/competition/config/default.yaml")
        self.assertIn("competition", config)
        self.assertEqual(config["competition"]["mission"], "rescue")


if __name__ == "__main__":
    unittest.main()
