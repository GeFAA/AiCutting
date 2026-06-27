from types import TracebackType

from rich.console import Console, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from aicutting.core.progress import PHASE_LABELS, PipelinePhase, ProgressEvent


class RunReporter:
    """A live, detailed terminal view of a cut run, driven by ProgressEvents.

    The state tracking (`handle`) is pure and unit-tested; the rich `Live` wiring is a thin shell
    so the user sees each real stage (rating, edit design, assembly, render) and its detail.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._order: list[PipelinePhase] = []
        self._detail: dict[PipelinePhase, str] = {}
        self._fraction: dict[PipelinePhase, tuple[int, int]] = {}
        self._active: PipelinePhase | None = None
        self._done = False
        self._live: Live | None = None

    def handle(self, event: ProgressEvent) -> None:
        phase = event.phase
        if event.message:
            self._detail[phase] = event.message
        if event.step is not None and event.total:
            self._fraction[phase] = (event.step, event.total)
        if phase is PipelinePhase.DONE:
            self._active = None
            self._done = True
            return
        if phase not in self._order:
            self._order.append(phase)
        self._active = phase

    def render(self) -> RenderableType:
        table = Table.grid(padding=(0, 1))
        table.add_column(width=2)
        table.add_column()
        for phase in self._order:
            active = phase is self._active and not self._done
            icon: RenderableType = (
                Spinner("dots", style="cyan") if active else Text("✓", style="green")
            )
            text = Text(PHASE_LABELS.get(phase, phase.value), style="bold" if active else "white")
            detail = self._detail.get(phase, "")
            fraction = self._fraction.get(phase)
            suffix = f"  [{fraction[0]}/{fraction[1]}]" if fraction else ""
            if detail or suffix:
                text.append(f"  —  {detail}{suffix}".rstrip(), style="dim")
            table.add_row(icon, text)
        title = "AI Drone Director · done" if self._done else "AI Drone Director"
        return Panel(table, title=title, border_style="green" if self._done else "cyan")

    def __enter__(self) -> "RunReporter":
        self._live = Live(self.render(), console=self.console, refresh_per_second=12)
        self._live.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._live is not None:
            self._live.update(self.render())
            self._live.__exit__(exc_type, exc, tb)
            self._live = None

    def __call__(self, event: ProgressEvent) -> None:
        self.handle(event)
        if self._live is not None:
            self._live.update(self.render())
