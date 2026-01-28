"""Preview generation service for negotiation panels."""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")  # Non-interactive backend

from ..models.session import NegotiationSession, OutcomeSpaceData
from .settings_service import SettingsService


def _get_preview_format() -> str:
    """Get configured image format for previews."""
    performance_settings = SettingsService.load_performance()
    return performance_settings.plot_image_format


def _get_preview_path(session_dir: Path, preview_type: str) -> Path:
    """Get path to preview file with configured format.

    Args:
        session_dir: Directory where preview is saved.
        preview_type: Type of preview (utility2d, timeline, histogram, result).

    Returns:
        Path to preview file.
    """
    fmt = _get_preview_format()
    return session_dir / f"{preview_type}_preview.{fmt}"


def _find_existing_preview(session_dir: Path, preview_type: str) -> Path | None:
    """Find existing preview file with any supported format.

    Args:
        session_dir: Directory where preview is saved.
        preview_type: Type of preview.

    Returns:
        Path to existing preview, or None if not found.
    """
    # Try all supported formats
    for fmt in ["webp", "png", "jpg", "svg"]:
        preview_file = session_dir / f"{preview_type}_preview.{fmt}"
        if preview_file.exists():
            return preview_file
    return None


class NegotiationPreviewService:
    """Service for generating WebP preview images of negotiation panels."""

    @staticmethod
    def generate_all_previews(
        session: NegotiationSession, session_dir: Path
    ) -> dict[str, bool]:
        """Generate all preview images for a negotiation session.

        Args:
            session: The negotiation session to generate previews for.
            session_dir: Directory where previews will be saved.

        Returns:
            Dictionary mapping preview type to success status.
        """
        results = {}

        # Generate 2D utility space preview
        if session.outcome_space_data:
            try:
                NegotiationPreviewService._generate_utility2d_preview(
                    session, session_dir
                )
                results["utility2d"] = True
            except Exception as e:
                print(f"Warning: Failed to generate utility2d preview: {e}")
                results["utility2d"] = False

        # Generate timeline preview
        if session.offers:
            try:
                NegotiationPreviewService._generate_timeline_preview(
                    session, session_dir
                )
                results["timeline"] = True
            except Exception as e:
                print(f"Warning: Failed to generate timeline preview: {e}")
                results["timeline"] = False

        # Generate histogram preview
        if session.offers:
            try:
                NegotiationPreviewService._generate_histogram_preview(
                    session, session_dir
                )
                results["histogram"] = True
            except Exception as e:
                print(f"Warning: Failed to generate histogram preview: {e}")
                results["histogram"] = False

        # Generate result preview (only if completed)
        # DISABLED: Result should show live data, not cached image
        # if session.agreement or session.end_reason:
        #     try:
        #         NegotiationPreviewService._generate_result_preview(session, session_dir)
        #         results["result"] = True
        #     except Exception as e:
        #         print(f"Warning: Failed to generate result preview: {e}")
        #         results["result"] = False

        return results

    @staticmethod
    def _generate_utility2d_preview(session: NegotiationSession, session_dir: Path):
        """Generate 2D utility space preview showing negotiation trace."""
        import matplotlib.pyplot as plt

        plot_file = _get_preview_path(session_dir, "utility2d")
        image_format = _get_preview_format()

        if not session.outcome_space_data:
            return

        data = session.outcome_space_data
        negotiator_names = session.negotiator_names or []

        # Use first two negotiators for axes
        x_idx = 0
        y_idx = min(1, len(negotiator_names) - 1)

        # Extract utilities
        x_utils = [u[x_idx] for u in data.outcome_utilities]
        y_utils = [u[y_idx] for u in data.outcome_utilities]

        # Get names
        x_name = (
            negotiator_names[x_idx] if x_idx < len(negotiator_names) else f"Neg {x_idx}"
        )
        y_name = (
            negotiator_names[y_idx] if y_idx < len(negotiator_names) else f"Neg {y_idx}"
        )

        # Create figure
        fig, ax = plt.subplots(figsize=(6, 6))

        # Add outcome scatter
        ax.scatter(
            x_utils,
            y_utils,
            s=2,
            alpha=0.3,
            color="#6495ED",  # Cornflower blue
            label="Outcomes",
            zorder=1,
        )

        # Add Pareto frontier
        if data.pareto_utilities:
            pareto_x = [u[x_idx] for u in data.pareto_utilities]
            pareto_y = [u[y_idx] for u in data.pareto_utilities]
            ax.scatter(pareto_x, pareto_y, s=4, color="red", label="Pareto", zorder=5)

        # Add negotiation trace (offers made during negotiation)
        # Separate traces by proposer to show different colors per negotiator
        if session.offers and len(session.offers) > 0:
            # Get colors for negotiators
            colors = session.negotiator_infos and [
                info.color for info in session.negotiator_infos
            ]
            if not colors:
                # Fallback to default colors
                colors = [
                    "#4a6fa5",
                    "#22a06b",
                    "#9f6b0a",
                    "#943d73",
                    "#0891b2",
                    "#dc2626",
                    "#7c3aed",
                    "#059669",
                ]

            # Group offers by proposer
            n_negotiators = len(negotiator_names) if negotiator_names else 0
            for neg_idx in range(n_negotiators):
                # Get offers made by this negotiator
                neg_offers = [
                    offer
                    for offer in session.offers
                    if offer.proposer_index == neg_idx
                    and len(offer.utilities) > max(x_idx, y_idx)
                ]

                if neg_offers:
                    offer_x = [offer.utilities[x_idx] for offer in neg_offers]
                    offer_y = [offer.utilities[y_idx] for offer in neg_offers]

                    neg_name = (
                        negotiator_names[neg_idx]
                        if neg_idx < len(negotiator_names)
                        else f"Neg {neg_idx}"
                    )
                    color = colors[neg_idx % len(colors)]

                    ax.plot(
                        offer_x,
                        offer_y,
                        marker="o",
                        markersize=4,
                        linestyle=":",
                        color=color,
                        alpha=0.7,
                        label=f"{neg_name} offers",
                        zorder=7,
                    )

        # Add special points using markers from negmas.plots.util
        # Markers: NASH_MARKER = "triangle-left", KALAI_MARKER = "triangle-down"
        #          KS_MARKER = "triangle-up", WELFARE_MARKER = "triangle-right"
        point_config = [
            ("nash_point", "Nash", "<", "brown", 80),  # triangle-left
            ("kalai_point", "Kalai", "v", "green", 70),  # triangle-down
            ("kalai_smorodinsky_point", "KS", "^", "cyan", 70),  # triangle-up
            ("max_welfare_point", "MaxWelfare", ">", "blue", 80),  # triangle-right
        ]

        for point_attr, label, marker, color, size in point_config:
            point = getattr(data, point_attr, None)
            if point and len(point.utilities) > max(x_idx, y_idx):
                ax.scatter(
                    [point.utilities[x_idx]],
                    [point.utilities[y_idx]],
                    s=size,
                    marker=marker,
                    color=color,
                    alpha=0.6,
                    label=label,
                    zorder=10,
                )

        # Add agreement point if available
        if session.agreement and session.final_utilities:
            ax.scatter(
                [session.final_utilities[x_idx]],
                [session.final_utilities[y_idx]],
                s=200,
                marker="*",
                color="black",
                alpha=0.9,
                label="Agreement",
                zorder=15,
            )

        # Configure plot
        ax.set_xlabel(x_name)
        ax.set_ylabel(y_name)
        ax.set_title("Negotiation Trace")
        ax.grid(True, alpha=0.3, color="lightgray")
        ax.set_facecolor("white")
        fig.patch.set_facecolor("white")
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=True, fontsize=8)

        # Save preview image
        try:
            fig.savefig(plot_file, format=image_format, dpi=100, bbox_inches="tight")
        except Exception as e:
            print(f"Warning: Failed to save utility2d preview to {plot_file}: {e}")
        finally:
            plt.close(fig)

    @staticmethod
    def _generate_timeline_preview(session: NegotiationSession, session_dir: Path):
        """Generate timeline preview using matplotlib."""
        plot_file = _get_preview_path(session_dir, "timeline")
        image_format = _get_preview_format()

        if not session.offers:
            return

        # Extract data
        steps = [offer.step for offer in session.offers]
        n_negotiators = len(session.negotiator_names) if session.negotiator_names else 0

        if n_negotiators == 0:
            return

        # Create figure
        fig, ax = plt.subplots(figsize=(8, 4))

        # Use step-based x-axis for preview
        colors = [
            "#4a6fa5",
            "#22a06b",
            "#9f6b0a",
            "#943d73",
            "#0891b2",
            "#dc2626",
            "#7c3aed",
            "#059669",
        ]

        # SIMPLIFIED VIEW: Each agent's utility for their own offers only
        for i in range(n_negotiators):
            # Filter offers by proposer (only this agent's offers)
            agent_offers = [
                offer for offer in session.offers if offer.proposer_index == i
            ]

            # Sort by step to ensure correct order
            agent_offers.sort(key=lambda x: x.step)

            # Get steps and utilities for this agent's own offers
            agent_steps = [offer.step for offer in agent_offers]
            utilities = [
                offer.utilities[i] if i < len(offer.utilities) else 0
                for offer in agent_offers
            ]

            name = (
                session.negotiator_names[i]
                if i < len(session.negotiator_names)
                else f"Neg {i}"
            )
            color = colors[i % len(colors)]

            # Only plot if agent made at least one offer
            if agent_steps:
                ax.plot(
                    agent_steps,
                    utilities,
                    marker="o",
                    markersize=4,
                    linewidth=2,
                    color=color,
                    label=name,
                )

        # Configure plot
        ax.set_xlabel("Step")
        ax.set_ylabel("Utility")
        ax.set_title("Utility Timeline")
        ax.grid(True, alpha=0.3, color="lightgray")
        ax.set_facecolor("white")
        fig.patch.set_facecolor("white")
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), frameon=True, fontsize=8)

        # Save preview image
        try:
            fig.savefig(plot_file, format=image_format, dpi=100, bbox_inches="tight")
        except Exception as e:
            print(f"Warning: Failed to save timeline preview to {plot_file}: {e}")
        finally:
            plt.close(fig)

    @staticmethod
    def _generate_histogram_preview(session: NegotiationSession, session_dir: Path):
        """Generate histogram preview (per-issue value distribution) using matplotlib."""
        plot_file = _get_preview_path(session_dir, "histogram")
        image_format = _get_preview_format()

        if not session.offers or not session.issue_names:
            return

        n_issues = len(session.issue_names)
        if n_issues == 0:
            return

        # Create grid layout: 2 issues per row for better readability
        n_cols = 2
        n_rows = (n_issues + n_cols - 1) // n_cols  # Ceiling division
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(8, 4 * n_rows))

        # Flatten axes array for easier indexing
        if n_issues == 1:
            axes = [axes]
        elif n_rows == 1:
            # axes is 1D array for single row
            pass
        else:
            # axes is 2D array, flatten it
            axes = axes.flatten()

        # Process offers to count value occurrences per issue
        for i, issue_name in enumerate(session.issue_names):
            ax = axes[i]

            # Collect values for this issue from all offers
            value_counts = {}
            for offer in session.offers:
                if offer.offer_dict and issue_name in offer.offer_dict:
                    value = offer.offer_dict[issue_name]
                    value_str = str(value)  # Convert to string for categorical data
                    value_counts[value_str] = value_counts.get(value_str, 0) + 1

            if not value_counts:
                # No data for this issue
                ax.text(
                    0.5,
                    0.5,
                    "No data",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                )
                ax.set_title(issue_name, fontsize=10)
                ax.set_facecolor("white")
                continue

            # Sort by value for consistent display
            sorted_items = sorted(value_counts.items())
            values = [item[0] for item in sorted_items]
            counts = [item[1] for item in sorted_items]

            # Create bar chart
            x_positions = range(len(values))
            ax.bar(x_positions, counts, color="#4a6fa5", alpha=0.7, edgecolor="black")
            ax.set_xticks(x_positions)
            ax.set_xticklabels(values, rotation=45, ha="right", fontsize=8)
            ax.set_title(issue_name, fontsize=10)
            ax.set_ylabel("Count")
            ax.grid(True, alpha=0.3, color="lightgray", axis="y")
            ax.set_facecolor("white")

        # Hide empty subplots if odd number of issues
        total_subplots = n_rows * n_cols
        for i in range(n_issues, total_subplots):
            axes[i].set_visible(False)

        fig.suptitle("Issue Value Distribution")
        fig.patch.set_facecolor("white")
        plt.tight_layout()

        # Save preview image
        try:
            fig.savefig(plot_file, format=image_format, dpi=100, bbox_inches="tight")
        except Exception as e:
            print(f"Warning: Failed to save histogram preview to {plot_file}: {e}")
        finally:
            plt.close(fig)

    @staticmethod
    def _generate_result_preview(session: NegotiationSession, session_dir: Path):
        """Generate result preview (text-based summary as image) using matplotlib."""
        plot_file = _get_preview_path(session_dir, "result")
        image_format = _get_preview_format()

        # Create a simple text-based figure
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.axis("off")

        # Build result text
        lines = []
        lines.append(f"Status: {session.status.value.upper()}")

        if session.end_reason:
            lines.append(f"End Reason: {session.end_reason}")

        if session.agreement:
            lines.append(f"Agreement: Yes")
            if session.agreement_dict:
                for key, val in session.agreement_dict.items():
                    lines.append(f"  • {key}: {val}")
        else:
            lines.append(f"Agreement: No")

        if session.final_utilities:
            lines.append(f"Final Utilities:")
            for i, util in enumerate(session.final_utilities):
                name = (
                    session.negotiator_names[i]
                    if i < len(session.negotiator_names)
                    else f"Neg {i}"
                )
                lines.append(f"  • {name}: {util:.3f}")

        lines.append(f"Steps: {session.current_step}")

        if session.duration_seconds():
            lines.append(f"Duration: {session.duration_seconds():.2f}s")

        # Add text
        text = "\n".join(lines)
        ax.text(
            0.5,
            0.5,
            text,
            ha="center",
            va="center",
            fontsize=12,
            family="monospace",
            transform=ax.transAxes,
        )

        fig.suptitle("Negotiation Result")
        fig.patch.set_facecolor("white")

        # Save preview image
        try:
            fig.savefig(plot_file, format=image_format, dpi=100, bbox_inches="tight")
        except Exception as e:
            print(f"Warning: Failed to save result preview to {plot_file}: {e}")
        finally:
            plt.close(fig)
