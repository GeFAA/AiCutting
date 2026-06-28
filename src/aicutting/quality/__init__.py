"""Edit self-critic: scores the finished cut so the director can grade its own work."""

from aicutting.quality.critic import DimensionScore, EditQuality, score_edit

__all__ = ["DimensionScore", "EditQuality", "score_edit"]
