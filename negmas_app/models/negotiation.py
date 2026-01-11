"""Negotiation parameters model."""

from dataclasses import dataclass, field


@dataclass
class NegotiationParams:
    """Parameters for running a negotiation."""

    # Basic options
    protocol: str = "SAO"
    negotiators: list[str] = field(
        default_factory=lambda: ["AspirationNegotiator", "NaiveTitForTatNegotiator"]
    )
    extend_negotiators: bool = False
    truncate_ufuns: bool = False
    params: list[str] = field(default_factory=list)
    share_ufuns: bool = False
    share_reserved_values: bool = False

    # Deadline
    steps: int | None = None
    time_limit: float | None = None

    # Scenario
    scenario: str | None = None
    reserved: list[float] = field(default_factory=list)
    fraction: list[float] = field(default_factory=list)
    discount: bool = True
    normalize: bool = True

    # Generated scenario
    issues: int | None = None
    values_min: int = 2
    values_max: int = 50
    sizes: list[int] = field(default_factory=list)
    reserved_values_min: float = 0.0
    reserved_values_max: float = 1.0
    rational: bool = True
    rational_fraction: list[float] = field(default_factory=list)
    reservation_selector: str = "min"
    issue_names: list[str] = field(default_factory=list)
    os_name: str | None = None
    ufun_names: list[str] = field(default_factory=list)
    numeric: bool = False
    linear: bool = True
    pareto_generator: str | None = None

    # Output control
    verbose: bool = False
    verbosity: int = 0
    progress: bool = True
    history: bool = False
    stats: bool = True
    rank_stats: bool = False
    compact_stats: bool = True

    # Plotting
    plot: bool = True
    only2d: bool = False
    plot_show: bool = False
    simple_offers_view: bool = False
    annotations: bool = True
    show_agreement: bool = True
    pareto_dist: bool = True
    nash_dist: bool = True
    kalai_dist: bool = True
    max_welfare_dist: bool = True
    max_rel_welfare_dist: bool = False
    end_reason: bool = True
    show_reserved: bool = True
    total_time: bool = True
    relative_time: bool = True
    show_n_steps: bool = True
    plot_path: str | None = None

    # Saving
    save_path: str | None = None
    save_history: bool = True
    save_stats: bool = True
    save_type: str = "yml"
    save_compact: bool = True

    # Advanced
    fast: bool = False
    extra_paths: list[str] = field(default_factory=list)
    raise_exceptions: bool = False

    def to_cli_args(self) -> list[str]:
        """Convert parameters to CLI arguments for the negotiate command."""
        args = []

        self._add_basic_args(args)
        self._add_deadline_args(args)
        self._add_scenario_args(args)
        self._add_generated_scenario_args(args)
        self._add_output_args(args)
        self._add_plotting_args(args)
        self._add_saving_args(args)
        self._add_advanced_args(args)

        return args

    def _add_basic_args(self, args: list[str]) -> None:
        if self.protocol and self.protocol != "SAO":
            args.extend(["--protocol", self.protocol])

        for neg in self.negotiators:
            if neg:
                args.extend(["--negotiator", neg])

        if self.extend_negotiators:
            args.append("--extend-negotiators")
        if self.truncate_ufuns:
            args.append("--truncate-ufuns")

        for p in self.params:
            if p:
                args.extend(["--params", p])

        args.append("--share-ufuns" if self.share_ufuns else "--no-share-ufuns")
        args.append(
            "--share-reserved-values"
            if self.share_reserved_values
            else "--no-share-reserved-values"
        )

    def _add_deadline_args(self, args: list[str]) -> None:
        if self.steps is not None:
            args.extend(["--steps", str(self.steps)])
        if self.time_limit is not None:
            args.extend(["--time", str(self.time_limit)])

    def _add_scenario_args(self, args: list[str]) -> None:
        if self.scenario:
            args.extend(["--scenario", self.scenario])

        for r in self.reserved:
            args.extend(["--reserved", str(r)])

        for f in self.fraction:
            args.extend(["--fraction", str(f)])

        if not self.discount:
            args.append("--no-discount")
        if not self.normalize:
            args.append("-N")

    def _add_generated_scenario_args(self, args: list[str]) -> None:
        if self.issues is not None:
            args.extend(["--issues", str(self.issues)])

        args.extend(["--values-min", str(self.values_min)])
        args.extend(["--values-max", str(self.values_max)])

        for s in self.sizes:
            args.extend(["--size", str(s)])

        args.extend(["--reserved-values-min", str(self.reserved_values_min)])
        args.extend(["--reserved-values-max", str(self.reserved_values_max)])

        args.append("--rational" if self.rational else "--irrational-ok")

        for rf in self.rational_fraction:
            args.extend(["--rational-fraction", str(rf)])

        if self.reservation_selector != "min":
            args.extend(["--reservation-selector", self.reservation_selector])

        for name in self.issue_names:
            if name:
                args.extend(["--issue-name", name])

        if self.os_name:
            args.extend(["--os-name", self.os_name])

        for name in self.ufun_names:
            if name:
                args.extend(["--ufun-names", name])

        if self.numeric:
            args.append("--numeric")
        if not self.linear:
            args.append("--non-linear")
        if self.pareto_generator:
            args.extend(["--pareto-generator", self.pareto_generator])

    def _add_output_args(self, args: list[str]) -> None:
        if self.verbose:
            args.append("--verbose")
        if self.verbosity > 0:
            args.extend(["--verbosity", str(self.verbosity)])

        args.append("--progress" if self.progress else "--no-progress")
        if self.history:
            args.append("--history")
        if not self.stats:
            args.append("--no-stats")
        if self.rank_stats:
            args.append("--rank-stats")
        args.append("--compact-stats" if self.compact_stats else "--detailed-stats")

    def _add_plotting_args(self, args: list[str]) -> None:
        args.append("--plot" if self.plot else "--no-plot")
        if self.only2d:
            args.append("--only2d")
        args.append("--no-plot-show")  # Always disable, we handle in browser

        if self.simple_offers_view:
            args.append("--simple-offers-view")
        if not self.annotations:
            args.append("--no-annotations")
        if not self.show_agreement:
            args.append("--no-agreement")
        if not self.pareto_dist:
            args.append("--no-pareto-dist")
        if not self.nash_dist:
            args.append("--no-nash-dist")
        if not self.kalai_dist:
            args.append("--no-kalai-dist")
        if not self.max_welfare_dist:
            args.append("--no-max-welfare-dist")
        if self.max_rel_welfare_dist:
            args.append("--max-rel-welfare-dist")
        if not self.end_reason:
            args.append("--no-end-reason")
        if not self.show_reserved:
            args.append("--no-show-reserved")
        if not self.total_time:
            args.append("--no-total-time")
        if not self.relative_time:
            args.append("--no-relative-time")
        if not self.show_n_steps:
            args.append("--no-show-n-steps")
        if self.plot_path:
            args.extend(["--plot-path", self.plot_path])

    def _add_saving_args(self, args: list[str]) -> None:
        if self.save_path:
            args.extend(["--save-path", self.save_path])
            args.append("--save-history" if self.save_history else "--no-save-history")
            args.append("--save-stats" if self.save_stats else "--no-save-stats")
            args.extend(["--save-type", self.save_type])
            args.append("--save-compact" if self.save_compact else "--no-save-compact")

    def _add_advanced_args(self, args: list[str]) -> None:
        if self.fast:
            args.append("--fast")
        for path in self.extra_paths:
            if path:
                args.extend(["--path", path])
        if self.raise_exceptions:
            args.append("--raise-exceptions")
