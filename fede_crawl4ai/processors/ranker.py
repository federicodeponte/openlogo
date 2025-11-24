"""Logo ranking logic for prioritizing logo results."""

import logging
from typing import List
from ..models import LogoResult

logger = logging.getLogger(__name__)


class LogoRanker:
    """Rank and filter logo results based on confidence and heuristics."""

    def __init__(self, confidence_threshold: float = 0.8):
        """
        Initialize logo ranker.

        Args:
            confidence_threshold: Minimum confidence score to keep logos (default: 0.8)
        """
        self._threshold = confidence_threshold

    def filter_by_confidence(self, logos: List[LogoResult]) -> List[LogoResult]:
        """
        Filter logos below confidence threshold.

        Args:
            logos: List of logo results to filter

        Returns:
            List of logos meeting confidence threshold
        """
        filtered = [logo for logo in logos if logo.confidence >= self._threshold]
        logger.info(
            f"Filtered {len(logos)} logos → {len(filtered)} above threshold {self._threshold}"
        )
        return filtered

    def rank(self, logos: List[LogoResult]) -> List[LogoResult]:
        """
        Rank logos by score, with header logos boosted.

        Ranking heuristics:
        - Base score: confidence from AI analysis
        - Header boost: +0.2 for logos found in header/nav
        - Sort: Highest score first

        Args:
            logos: List of logo results to rank

        Returns:
            Sorted list of logos (highest ranked first)
        """
        if not logos:
            return []

        def calculate_score(logo: LogoResult) -> float:
            """Calculate ranking score for a logo."""
            score = logo.confidence

            # Boost header logos (they're more likely to be main company logo)
            if logo.is_header:
                score += 0.2

            # Cap at 1.0
            return min(score, 1.0)

        # Calculate and assign rank scores
        for logo in logos:
            logo.rank_score = calculate_score(logo)

        # Sort by rank score descending
        ranked = sorted(logos, key=lambda x: x.rank_score, reverse=True)

        logger.info(f"Ranked {len(ranked)} logos (top score: {ranked[0].rank_score:.2f})")
        return ranked

    def get_top_logos(self, logos: List[LogoResult], n: int = 5) -> List[LogoResult]:
        """
        Get top N ranked logos.

        Args:
            logos: List of logo results
            n: Number of top results to return (default: 5)

        Returns:
            Top N logos by rank score
        """
        ranked = self.rank(logos)
        return ranked[:n]

    def filter_and_rank(self, logos: List[LogoResult]) -> List[LogoResult]:
        """
        Convenience method to filter then rank logos.

        Args:
            logos: List of logo results

        Returns:
            Filtered and ranked logos
        """
        filtered = self.filter_by_confidence(logos)
        return self.rank(filtered)
