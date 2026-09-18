# -*- coding: utf-8 -*-
"""
calharness.cli

Typer + Rich powered CLI for calibration map inspection, decoding, and diffing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from calharness.a2l_catalog import A2LCatalog
from calharness.decoder import MapDecoder

app = typer.Typer(help="CalHarness: Open-source calibration toolkit for Bosch EDC16 ECUs.")
console = Console()


@app.command()
def info(
    bin_path: Path = typer.Argument(..., help="Path to ECU binary (2MB full or 512KB cal read)"),
):
    """Inspect binary identity and checksum."""
    if not bin_path.exists():
        console.print(f"[red]Error:[/red] File {bin_path} not found.")
        raise typer.Exit(code=1)

    decoder = MapDecoder(bin_path)
    ident = decoder.get_identity()

    table = Table(title=f"Firmware Identity: {bin_path.name}", show_header=True, header_style="bold cyan")
    table.add_column("Property", style="bold")
    table.add_column("Value", style="green")

    table.add_row("VAG Part Number", ident.vag_part_number or "N/A")
    table.add_row("VAG SW Version", ident.vag_sw_version or "N/A")
    table.add_row("Bosch SW Number", ident.bosch_sw_number or "N/A")
    table.add_row("Calibration ID", ident.calibration_id or "N/A")
    table.add_row("Project Code", ident.project_code or "N/A")
    table.add_row("File Size", f"{ident.file_size:,} bytes")
    table.add_row("SHA-256", ident.sha256)

    console.print(table)


@app.command()
def view(
    bin_path: Path = typer.Argument(..., help="Path to ECU binary"),
    map_name: str = typer.Argument(..., help="A2L symbol name (e.g. PCR_pBDesBas_MAP)"),
):
    """Decode and display a calibration map as a formatted table."""
    decoder = MapDecoder(bin_path)
    try:
        m = decoder.decode(map_name)
    except KeyError:
        console.print(f"[red]Error:[/red] Map '{map_name}' not found in A2L catalog.")
        raise typer.Exit(code=1)

    console.print(Panel.fit(m.summary(), title=f"Map: {map_name}", border_style="cyan"))

    arr = m.numpy_physical()
    if m.y_axis is not None and arr.ndim == 2:
        table = Table(title=f"{m.name} Matrix ({m.unit})", show_header=True, header_style="bold yellow")
        table.add_column(f"{m.x_axis.name} [{m.x_axis.unit}]", style="cyan", justify="right")
        for y_val in m.y_axis.physical_values:
            table.add_column(f"{y_val:.1f} {m.y_axis.unit}".strip(), justify="right")

        for i, x_val in enumerate(m.x_axis.physical_values):
            row = [f"{x_val:.1f}"] + [f"{v:.2f}" for v in arr[i]]
            table.add_row(*row)
        console.print(table)
    else:
        table = Table(title=f"{m.name} Curve ({m.unit})", show_header=True, header_style="bold yellow")
        table.add_column(f"{m.x_axis.name} [{m.x_axis.unit}]", style="cyan", justify="right")
        table.add_column(f"Value [{m.unit}]", justify="right", style="green")

        for x_val, val in zip(m.x_axis.physical_values, arr):
            table.add_row(f"{x_val:.1f}", f"{val:.2f}")
        console.print(table)


@app.command()
def diff(
    stock_bin: Path = typer.Argument(..., help="Path to reference / stock ECU binary"),
    mod_bin: Path = typer.Argument(..., help="Path to modified / tuned ECU binary"),
    map_name: str = typer.Argument(..., help="A2L symbol name (e.g. PCR_pBDesBas_MAP)"),
):
    """Calculate and display the physical delta between two binaries for a specific map."""
    dec_stock = MapDecoder(stock_bin)
    dec_mod = MapDecoder(mod_bin)

    m_stock = dec_stock.decode(map_name)
    m_mod = dec_mod.decode(map_name)

    arr_stock = m_stock.numpy_physical()
    arr_mod = m_mod.numpy_physical()
    delta = arr_mod - arr_stock

    has_diff = not np.allclose(delta, 0.0)
    status_style = "bold green" if not has_diff else "bold magenta"
    status_text = "IDENTICAL (0 delta)" if not has_diff else f"MODIFIED (Delta: [{delta.min():.2f} .. {delta.max():.2f} {m_stock.unit}])"

    console.print(Panel.fit(f"{map_name} | {status_text}", title="Map Delta Analysis", border_style="magenta"))

    if not has_diff:
        return

    if m_stock.y_axis is not None and delta.ndim == 2:
        table = Table(title=f"Delta Table (Mod - Stock) in [{m_stock.unit}]", show_header=True, header_style="bold yellow")
        table.add_column(f"{m_stock.x_axis.name} [{m_stock.x_axis.unit}]", style="cyan", justify="right")
        for y_val in m_stock.y_axis.physical_values:
            table.add_column(f"{y_val:.1f} {m_stock.y_axis.unit}".strip(), justify="right")

        for i, x_val in enumerate(m_stock.x_axis.physical_values):
            row = [f"{x_val:.1f}"]
            for v in delta[i]:
                if abs(v) > 1e-4:
                    style = "bold green" if v > 0 else "bold red"
                    row.append(f"[{style}]{v:+.2f}[/{style}]")
                else:
                    row.append("0.00")
            table.add_row(*row)
        console.print(table)


@app.command()
def audit(
    stock_bin: Path = typer.Argument(..., help="Path to reference / stock ECU binary"),
    mod_bin: Path = typer.Argument(..., help="Path to modified / tuned ECU binary"),
    json_out: Optional[Path] = typer.Option(None, "--output-json", "-o", help="Optional path to write JSON audit report"),
):
    """
    Run complete Semantic Diff Engine and Safety Validator audit.
    Classifies all modified bytes, correlates them to A2L symbols,
    and validates invariants against code/identity/unmapped changes and physical limits.
    """
    if not stock_bin.exists():
        console.print(f"[red]Error:[/red] Stock binary {stock_bin} not found.")
        raise typer.Exit(code=1)
    if not mod_bin.exists():
        console.print(f"[red]Error:[/red] Mod binary {mod_bin} not found.")
        raise typer.Exit(code=1)

    from calharness.diff_engine import SemanticDiffEngine
    from calharness.safety_validator import SafetyValidator, SafetyLevel

    console.print("[cyan]Running Semantic Diff Engine and A2L byte classification...[/cyan]")
    engine = SemanticDiffEngine()
    diff_report = engine.compare(stock_bin, mod_bin)

    console.print("[cyan]Running Safety Invariant Validator...[/cyan]")
    validator = SafetyValidator()
    audit_report = validator.validate(diff_report)

    # 1. Diff Summary Panel
    console.print(Panel.fit(diff_report.summary(), title="Semantic Diff Overview", border_style="cyan"))

    # 2. Changed Maps Table
    if diff_report.maps_changed:
        table = Table(title="Affected Calibration Maps", show_header=True, header_style="bold yellow")
        table.add_column("Map Symbol", style="bold")
        table.add_column("Address", style="dim")
        table.add_column("Shape", justify="center")
        table.add_column("Cells Changed", justify="right", style="cyan")
        table.add_column("Old Range", justify="right")
        table.add_column("New Range", justify="right")
        table.add_column("Max Delta", justify="right", style="bold magenta")
        table.add_column("Unit", style="dim")

        for m in diff_report.maps_changed:
            table.add_row(
                m.name,
                m.hex_address,
                f"{m.shape[0]}x{m.shape[1]}" if len(m.shape) == 2 else f"{m.shape[0]}",
                f"{m.changed_cells_count}/{m.total_cells}",
                f"{m.min_old:.1f}..{m.max_old:.1f}",
                f"{m.min_new:.1f}..{m.max_new:.1f}",
                f"{m.max_delta:+.2f}",
                m.unit,
            )
        console.print(table)

    # 3. Safety Verdict Panel
    if audit_report.overall_verdict == SafetyLevel.PASS:
        verdict_color = "green"
    elif audit_report.overall_verdict == SafetyLevel.WARNING:
        verdict_color = "yellow"
    elif audit_report.overall_verdict == SafetyLevel.UNVERIFIED:
        verdict_color = "blue"
    elif audit_report.overall_verdict == SafetyLevel.NEEDS_EVIDENCE:
        verdict_color = "magenta"
    else:
        verdict_color = "red"

    console.print(Panel.fit(audit_report.summary(), title="Safety Audit Verdict", border_style=verdict_color))

    # 4. JSON output if requested
    if json_out:
        import json
        full_dict = {
            "diff": diff_report.model_dump(mode="json"),
            "audit": audit_report.model_dump(mode="json"),
        }
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(full_dict, f, indent=2)
        console.print(f"[green]Saved machine-readable JSON report to {json_out}[/green]")

    if audit_report.hard_fails_count > 0:
        raise typer.Exit(code=2)


@app.command("checksum-verify")
def checksum_verify(
    bin_path: Path = typer.Argument(..., help="Path to ECU binary (2MB full or 512KB cal read)"),
):
    """
    Perform read-only verification of EDC16 dual-block additive checksums.
    Strictly verify-only: checks Segment 1 and Segment 2 against candidate invariant 0xD01FE500.
    """
    if not bin_path.exists():
        console.print(f"[red]Error:[/red] Binary {bin_path} not found.")
        raise typer.Exit(code=1)

    from calharness.checksum import ChecksumInspector
    inspector = ChecksumInspector()
    try:
        report = inspector.inspect(bin_path)
    except ValueError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(code=1)

    color = "green" if report.is_corroborated else "red"
    console.print(Panel.fit(report.summary(), title=f"EDC16 Checksum Inspection: {bin_path.name}", border_style=color))
    if not report.is_corroborated:
        raise typer.Exit(code=1)


@app.command("log-analyze")
def log_analyze(
    log_path: Path = typer.Argument(..., help="Path to telemetry log file (VCDS or Android CSV)"),
    json_out: Optional[Path] = typer.Option(None, "--output-json", "-o", help="Optional path to write JSON analysis report"),
):
    """
    Analyze vehicle telemetry log for WOT pulls, boost dynamics, N75 governor, and fueling limiters.
    Supports VCDS WOT exports, VCDS Advanced Measuring Blocks (011/003/008), and Android OBD logs.
    """
    if not log_path.exists():
        console.print(f"[red]Error:[/red] Log file {log_path} not found.")
        raise typer.Exit(code=1)

    from calharness.log_analyzer import LogAnalyzer
    analyzer = LogAnalyzer()
    try:
        report = analyzer.analyze_file(log_path)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Failed to analyze log: {exc}")
        raise typer.Exit(code=1)

    console.print(Panel.fit(report.summary(), title=f"Telemetry Analysis: {log_path.name}", border_style="cyan"))

    if report.wot_segments:
        table = Table(title="Detected Acceleration Pulls", show_header=True, header_style="bold yellow")
        table.add_column("Pull #", justify="center", style="bold")
        table.add_column("Type", justify="center")
        table.add_column("Duration", justify="right")
        table.add_column("RPM Span", justify="center")
        table.add_column("Target Boost", justify="right")
        table.add_column("Actual Boost", justify="right")
        table.add_column("Overshoot", justify="right", style="bold magenta")
        table.add_column("Spool", justify="right", style="cyan")
        table.add_column("N75 Range", justify="center")
        table.add_column("Bottleneck", style="bold green")

        for s in report.wot_segments:
            bottleneck_str = "-"
            if s.active_bottleneck.value != "UNKNOWN":
                if s.active_bottleneck.value == "SMOKE_LIMITER":
                    bottleneck_str = f"SMOKE ({s.limiter_metrics.smoke_limiter_pct:.0f}%)"
                elif s.active_bottleneck.value == "TORQUE_LIMITER":
                    bottleneck_str = f"TORQUE ({s.limiter_metrics.torque_limiter_pct:.0f}%)"
                else:
                    bottleneck_str = f"DRIVER ({s.limiter_metrics.driver_wish_pct:.0f}%)"

            table.add_row(
                str(s.segment_id),
                s.pull_kind.value,
                f"{s.duration_s:.1f}s",
                f"{s.start_rpm:.0f}..{s.end_rpm:.0f}",
                f"{s.max_specified_boost_mbar:.0f} mbar" if s.max_specified_boost_mbar > 0 else "N/A",
                f"{s.max_actual_boost_mbar:.0f} mbar",
                f"+{s.overshoot_mbar:.0f} ({s.overshoot_pct:+.1f}%)" if s.overshoot_mbar > 0 else "0",
                f"{s.spool_time_s:.2f}s" if s.spool_time_s is not None else "N/A",
                f"{s.n75_min_duty_pct:.0f}..{s.n75_max_duty_pct:.0f}%" if s.n75_min_duty_pct is not None else "N/A",
                bottleneck_str,
            )
        console.print(table)

    if json_out:
        import json
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2)
        console.print(f"[green]Saved JSON report to {json_out}[/green]")


@app.command("correlate")
def correlate(
    bin_path: Path = typer.Argument(..., help="Path to reference ECU binary"),
    log_path: Path = typer.Argument(..., help="Path to telemetry log file (CSV)"),
    map_name: str = typer.Argument(..., help="Target A2L map name (e.g. PCR_pBDesBas_MAP, FlMng_qPresSmoke_MAP)"),
    mode: str = typer.Option("STRICT", "--mode", "-m", help="Correlation mode: STRICT, EXPERIMENTAL, or COVERAGE_ONLY"),
    json_out: Optional[Path] = typer.Option(None, "--output-json", "-o", help="Optional path to write JSON exposure report"),
):
    """
    Evidence-First Map Exposure Correlator.
    Maps real telemetry samples onto exact A2L calibration meshes to establish spatial exposure
    without assuming causality or issuing ungrounded tuning advice.
    """
    if not bin_path.exists():
        console.print(f"[red]Error:[/red] Binary file {bin_path} not found.")
        raise typer.Exit(code=1)
    if not log_path.exists():
        console.print(f"[red]Error:[/red] Log file {log_path} not found.")
        raise typer.Exit(code=1)

    from calharness.correlator import CorrelatorMode, MapCorrelator, TorqueToFuelConverter
    from calharness.log_analyzer import LogAnalyzer

    mode_upper = mode.upper()
    if mode_upper not in ("STRICT", "EXPERIMENTAL", "COVERAGE_ONLY"):
        console.print(f"[red]Error:[/red] Invalid mode '{mode}'. Choose from STRICT, EXPERIMENTAL, COVERAGE_ONLY.")
        raise typer.Exit(code=1)
    corr_mode = CorrelatorMode(mode_upper)

    decoder = MapDecoder(bin_path)
    torque_conv = None
    try:
        torque_conv = TorqueToFuelConverter(decoder)
    except Exception:
        pass

    analyzer = LogAnalyzer()
    points, fmt, meta = analyzer.parse_log(log_path)
    if not points:
        console.print(f"[red]Error:[/red] No telemetry samples extracted from {log_path.name}")
        raise typer.Exit(code=1)

    correlator = MapCorrelator(decoder=decoder, torque_converter=torque_conv, mode=corr_mode)
    try:
        report = correlator.correlate_points(map_name, points, mode=corr_mode)
    except KeyError:
        console.print(f"[red]Error:[/red] Map '{map_name}' not found in A2L catalog.")
        raise typer.Exit(code=1)
    except Exception as exc:
        console.print(f"[red]Error:[/red] Correlation failed: {exc}")
        raise typer.Exit(code=1)

    summary_lines = [
        f"Map: [bold cyan]{report.map_name}[/bold cyan] (Shape: {report.map_shape})",
        f"Mode: [bold magenta]{report.mode.value}[/bold magenta]",
        f"Total Samples Evaluated: {report.total_points_evaluated}",
        f"Mapped Samples: [green]{report.mapped_points_count}[/green]",
        f"Dropped Samples: [yellow]{report.dropped_points_count}[/yellow]",
    ]
    for k, v in report.axis_coverage_summary.items():
        summary_lines.append(f"  • {k}: {v}")

    console.print(Panel.fit("\n".join(summary_lines), title="Map Exposure Summary", border_style="cyan"))

    if report.drop_reasons:
        table = Table(title="Drop Reasons / Unresolved Axes", show_header=True, header_style="bold red")
        table.add_column("Reason / Semantic Mismatch", style="dim")
        table.add_column("Samples Count", justify="right", style="bold")
        for reason, count in report.drop_reasons.items():
            table.add_row(reason, str(count))
        console.print(table)

    if report.exposure_observations:
        obs_text = "\n\n".join(f"• {obs}" for obs in report.exposure_observations)
        console.print(Panel(obs_text, title="Epistemic Exposure Observations", border_style="green"))

    if json_out:
        import json
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(mode="json"), f, indent=2)
        console.print(f"[green]Saved JSON exposure report to {json_out}[/green]")


if __name__ == "__main__":
    app()

