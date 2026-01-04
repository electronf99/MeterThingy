import sys

from typing import Dict, Any, Optional
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

class Dashboard:
    def __init__(self, refresh_per_second: int = 10):
        self.console = Console()
        self.live: Optional[Live] = None
        self.refresh_per_second = refresh_per_second
        self.state: Dict[str, Any] = {"title": "Dashboard", "status": "Idle", "rows": []}

    def start(self):
        if self.live is None:
            self.live = Live(self._render(), console=self.console,
                             refresh_per_second=self.refresh_per_second, screen=True)
            self.live.start()

    def stop(self):
        if self.live is not None:
            self.live.stop()
            self.live = None

    def update(self, data: Dict[str, Any], status):
        data["status"] = status["duration"]
        data["rows"] = [
            ("Duration", "", status["duration"]),
            ("Packet Time", "[yellow]~ Warn[/yellow]", "00:12"),
            ("package", "[red]✗ Failed[/red]", "00:08"),
        ]
        self.state.update(data)
        if self.live is not None:
            self.live.update(self._render())  # updates once; no loop

    def _render(self):
        header = Panel(f"[bold cyan]{self.state['title']}[/bold cyan]", border_style="cyan")
        table = Table()
        table.add_column("Name", style="bold")
        table.add_column("Status", justify="center")
        table.add_column("Value", justify="right")
        for name, status_markup, value in self.state["rows"]:
            table.add_row(name, status_markup, value)
        footer = Panel(f"[bold green]Status:[/bold green] {self.state['status']}", border_style="green")
        return Group(header, table, footer)  # <-- return Group, not list



