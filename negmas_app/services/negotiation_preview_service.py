"""Preview generation service for negotiation panels."""

from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ..models.session import NegotiationSession, OutcomeSpaceData


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
        if session.agreement or session.end_reason:
            try:
                NegotiationPreviewService._generate_result_preview(session, session_dir)
                results["result"] = True
            except Exception as e:
                print(f"Warning: Failed to generate result preview: {e}")
                results["result"] = False

        return results

    @staticmethod
    def _generate_utility2d_preview(session: NegotiationSession, session_dir: Path):
        """Generate 2D utility space preview."""
        plot_file = session_dir / "utility2d_preview.webp"

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

        # Create figure
        fig = go.Figure()

        # Add outcome scatter
        fig.add_trace(
            go.Scatter(
                x=x_utils,
                y=y_utils,
                mode="markers",
                marker=dict(
                    size=3, color="rgba(100, 149, 237, 0.5)", line=dict(width=0)
                ),
                name="Outcomes",
                showlegend=False,
            )
        )

        # Add Pareto frontier
        if data.pareto_utilities:
            pareto_x = [u[x_idx] for u in data.pareto_utilities]
            pareto_y = [u[y_idx] for u in data.pareto_utilities]
            fig.add_trace(
                go.Scatter(
                    x=pareto_x,
                    y=pareto_y,
                    mode="lines+markers",
                    marker=dict(size=4, color="red"),
                    line=dict(color="red", width=2),
                    name="Pareto",
                    showlegend=True,
                )
            )

        # Add special points
        special_points = []
        if data.nash_point:
            special_points.append(("Nash", data.nash_point.utilities, "purple"))
        if data.kalai_point:
            special_points.append(("Kalai", data.kalai_point.utilities, "green"))
        if data.kalai_smorodinsky_point:
            special_points.append(
                ("KS", data.kalai_smorodinsky_point.utilities, "orange")
            )
        if data.max_welfare_point:
            special_points.append(
                ("MaxWelfare", data.max_welfare_point.utilities, "blue")
            )

        for name, utils, color in special_points:
            if len(utils) > max(x_idx, y_idx):
                fig.add_trace(
                    go.Scatter(
                        x=[utils[x_idx]],
                        y=[utils[y_idx]],
                        mode="markers",
                        marker=dict(size=10, color=color, symbol="star"),
                        name=name,
                        showlegend=True,
                    )
                )

        # Add agreement point if available
        if session.agreement and session.final_utilities:
            fig.add_trace(
                go.Scatter(
                    x=[session.final_utilities[x_idx]],
                    y=[session.final_utilities[y_idx]],
                    mode="markers",
                    marker=dict(size=12, color="red", symbol="x", line=dict(width=2)),
                    name="Agreement",
                    showlegend=True,
                )
            )

        # Update layout
        x_name = (
            negotiator_names[x_idx] if x_idx < len(negotiator_names) else f"Neg {x_idx}"
        )
        y_name = (
            negotiator_names[y_idx] if y_idx < len(negotiator_names) else f"Neg {y_idx}"
        )

        fig.update_layout(
            title=f"2D Utility Space",
            xaxis_title=x_name,
            yaxis_title=y_name,
            width=600,
            height=600,
            plot_bgcolor="white",
            showlegend=True,
            legend=dict(x=1.05, y=1, xanchor="left", yanchor="top", font=dict(size=10)),
            margin=dict(l=60, r=100, t=40, b=60),
        )

        fig.update_xaxes(showgrid=True, gridcolor="lightgray")
        fig.update_yaxes(showgrid=True, gridcolor="lightgray")

        # Save as WebP
        try:
            fig.write_image(
                str(plot_file), format="webp", width=600, height=600, scale=1.5
            )
        except Exception as e:
            print(f"Warning: Failed to save utility2d preview to {plot_file}: {e}")

    @staticmethod
    def _generate_timeline_preview(session: NegotiationSession, session_dir: Path):
        """Generate timeline preview."""
        plot_file = session_dir / "timeline_preview.webp"

        if not session.offers:
            return

        # Extract data
        steps = [offer.step for offer in session.offers]
        n_negotiators = len(session.negotiator_names) if session.negotiator_names else 0

        if n_negotiators == 0:
            return

        # Create figure
        fig = go.Figure()

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

        for i in range(n_negotiators):
            utilities = [
                offer.utilities[i] if i < len(offer.utilities) else 0
                for offer in session.offers
            ]
            name = (
                session.negotiator_names[i]
                if i < len(session.negotiator_names)
                else f"Neg {i}"
            )
            color = colors[i % len(colors)]

            fig.add_trace(
                go.Scatter(
                    x=steps,
                    y=utilities,
                    mode="lines+markers",
                    name=name,
                    line=dict(color=color, width=2),
                    marker=dict(size=4, color=color),
                )
            )

        # Update layout
        fig.update_layout(
            title="Utility Timeline",
            xaxis_title="Step",
            yaxis_title="Utility",
            width=800,
            height=400,
            plot_bgcolor="white",
            showlegend=True,
            legend=dict(x=1.05, y=1, xanchor="left", yanchor="top", font=dict(size=10)),
            margin=dict(l=60, r=100, t=40, b=60),
        )

        fig.update_xaxes(showgrid=True, gridcolor="lightgray")
        fig.update_yaxes(showgrid=True, gridcolor="lightgray")

        # Save as WebP
        try:
            fig.write_image(
                str(plot_file), format="webp", width=800, height=400, scale=1.5
            )
        except Exception as e:
            print(f"Warning: Failed to save timeline preview to {plot_file}: {e}")

    @staticmethod
    def _generate_histogram_preview(session: NegotiationSession, session_dir: Path):
        """Generate histogram preview (utility distribution)."""
        plot_file = session_dir / "histogram_preview.webp"

        if not session.offers:
            return

        n_negotiators = len(session.negotiator_names) if session.negotiator_names else 0
        if n_negotiators == 0:
            return

        # Create subplots for each negotiator
        fig = make_subplots(
            rows=1,
            cols=n_negotiators,
            subplot_titles=[
                session.negotiator_names[i]
                if i < len(session.negotiator_names)
                else f"Neg {i}"
                for i in range(n_negotiators)
            ],
        )

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

        for i in range(n_negotiators):
            utilities = [
                offer.utilities[i] if i < len(offer.utilities) else 0
                for offer in session.offers
            ]
            color = colors[i % len(colors)]

            fig.add_trace(
                go.Histogram(
                    x=utilities,
                    name=session.negotiator_names[i]
                    if i < len(session.negotiator_names)
                    else f"Neg {i}",
                    marker_color=color,
                    showlegend=False,
                    nbinsx=20,
                ),
                row=1,
                col=i + 1,
            )

        # Update layout
        fig.update_layout(
            title_text="Utility Distribution",
            width=min(300 * n_negotiators, 1000),
            height=400,
            plot_bgcolor="white",
            showlegend=False,
            margin=dict(l=60, r=20, t=60, b=60),
        )

        fig.update_xaxes(title_text="Utility", showgrid=True, gridcolor="lightgray")
        fig.update_yaxes(title_text="Count", showgrid=True, gridcolor="lightgray")

        # Save as WebP
        try:
            fig.write_image(
                str(plot_file),
                format="webp",
                width=min(300 * n_negotiators, 1000),
                height=400,
                scale=1.5,
            )
        except Exception as e:
            print(f"Warning: Failed to save histogram preview to {plot_file}: {e}")

    @staticmethod
    def _generate_result_preview(session: NegotiationSession, session_dir: Path):
        """Generate result preview (text-based summary as image)."""
        plot_file = session_dir / "result_preview.webp"

        # Create a simple text-based figure
        fig = go.Figure()

        # Build result text
        lines = []
        lines.append(f"<b>Status:</b> {session.status.value.upper()}")

        if session.end_reason:
            lines.append(f"<b>End Reason:</b> {session.end_reason}")

        if session.agreement:
            lines.append(f"<b>Agreement:</b> Yes")
            if session.agreement_dict:
                for key, val in session.agreement_dict.items():
                    lines.append(f"  • {key}: {val}")
        else:
            lines.append(f"<b>Agreement:</b> No")

        if session.final_utilities:
            lines.append(f"<b>Final Utilities:</b>")
            for i, util in enumerate(session.final_utilities):
                name = (
                    session.negotiator_names[i]
                    if i < len(session.negotiator_names)
                    else f"Neg {i}"
                )
                lines.append(f"  • {name}: {util:.3f}")

        lines.append(f"<b>Steps:</b> {session.current_step}")

        if session.duration_seconds():
            lines.append(f"<b>Duration:</b> {session.duration_seconds():.2f}s")

        # Add text annotation
        text = "<br>".join(lines)

        fig.add_annotation(
            x=0.5,
            y=0.5,
            text=text,
            showarrow=False,
            font=dict(size=14, family="monospace"),
            align="left",
            xref="paper",
            yref="paper",
        )

        fig.update_layout(
            title="Negotiation Result",
            width=600,
            height=400,
            plot_bgcolor="white",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            margin=dict(l=40, r=40, t=60, b=40),
        )

        # Save as WebP
        try:
            fig.write_image(
                str(plot_file), format="webp", width=600, height=400, scale=1.5
            )
        except Exception as e:
            print(f"Warning: Failed to save result preview to {plot_file}: {e}")
