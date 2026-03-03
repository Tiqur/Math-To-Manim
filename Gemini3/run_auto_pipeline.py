#!/usr/bin/env python3
import sys
import os
import json
import argparse
import subprocess
import re
import ast
import time
import glob
import tempfile
import shutil
import hashlib
import threading
from PIL import Image
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn, TaskProgressColumn, MofNCompleteColumn
from rich.status import Status
from rich.live import Live

# ---------------------------------------------------------------------------
# PATH FIX: Guarantee we execute inside Gemini3/ and can import src.*
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from src.pipeline import Gemini3Pipeline, run_agent_sync
from src.core import logger
from google import genai

load_dotenv()
console = Console()

# ---------------------------------------------------------------------------
# Verbose mode flag — set to True via --verbose CLI flag in main()
# ---------------------------------------------------------------------------
VERBOSE: bool = False

def vprint(*args, **kwargs):
    """Print only when VERBOSE mode is on."""
    if VERBOSE:
        console.print(*args, **kwargs)

# Timing tracker for ETA estimation across fix-loop attempts
_attempt_times: list[float] = []


# ---------------------------------------------------------------------------
# Per-model API usage & cost tracking
# ---------------------------------------------------------------------------

class ModelStats:
    """
    Thread-safe tracker for API call counts, estimated token usage, and cost.

    Token estimation: ~4 chars per token (rough but consistent).
    Pricing table: USD per 1 million tokens (input, output).
    Unknown models fall back to flash pricing.
    """

    # (input $/1M tok, output $/1M tok)  — mid-2025 public Gemini pricing
    _PRICING: dict[str, tuple[float, float]] = {
        "flash-8b":       (0.0375,  0.15),
        "flash":          (0.075,   0.30),
        "flash-thinking": (0.15,    0.60),
        "pro":            (1.25,   10.00),
        "ultra":          (5.00,   15.00),
    }

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # model_key -> {calls, in_chars, out_chars}
        self._data: dict[str, dict] = {}

    # ── public API ──────────────────────────────────────────────────────────

    def record(self, model: str, prompt: object, response_text: str, label: str = "") -> None:
        """Record one API call.  prompt may be any object — str() is used for sizing."""
        in_chars  = len(str(prompt))
        out_chars = len(response_text)
        key = label or model
        with self._lock:
            if key not in self._data:
                self._data[key] = {"model": model, "calls": 0, "in_chars": 0, "out_chars": 0}
            d = self._data[key]
            d["calls"]    += 1
            d["in_chars"] += in_chars
            d["out_chars"] += out_chars

    def total_cost(self) -> float:
        with self._lock:
            return sum(self._cost_for(d) for d in self._data.values())

    def render_table(self) -> Table:
        """Return a Rich Table with per-model stats + totals row."""
        t = Table(
            title="[bold cyan]API Usage[/bold cyan]",
            show_footer=True, expand=False,
            border_style="dim", header_style="bold",
        )
        t.add_column("Model / Role",  footer="[bold]TOTAL[/bold]")
        t.add_column("Calls",         footer="", justify="right")
        t.add_column("~In (K tok)",   footer="", justify="right")
        t.add_column("~Out (K tok)",  footer="", justify="right")
        t.add_column("~Cost (USD)",   footer="", justify="right")

        total_calls = total_in = total_out = total_cost = 0.0

        with self._lock:
            items = list(self._data.items())

        for key, d in items:
            in_k  = d["in_chars"]  / 4 / 1_000
            out_k = d["out_chars"] / 4 / 1_000
            cost  = self._cost_for(d)
            total_calls += d["calls"]
            total_in    += in_k
            total_out   += out_k
            total_cost  += cost
            t.add_row(
                f"[cyan]{key}[/cyan]",
                str(d["calls"]),
                f"{in_k:,.1f}",
                f"{out_k:,.1f}",
                f"[green]${cost:.4f}[/green]",
            )

        # footer-style totals row
        t.add_row(
            "[bold]ALL[/bold]",
            f"[bold]{int(total_calls)}[/bold]",
            f"[bold]{total_in:,.1f}[/bold]",
            f"[bold]{total_out:,.1f}[/bold]",
            f"[bold green]${total_cost:.4f}[/bold green]",
            end_section=True,
        )
        return t

    # ── private ─────────────────────────────────────────────────────────────

    def _tier(self, model: str) -> str:
        m = model.lower()
        for key in ("flash-8b", "flash-thinking", "flash", "ultra", "pro"):
            if key in m:
                return key
        return "flash"   # safe fallback

    def _cost_for(self, d: dict) -> float:
        ip, op = self._PRICING[self._tier(d["model"])]
        in_tok  = d["in_chars"]  / 4
        out_tok = d["out_chars"] / 4
        return (in_tok * ip + out_tok * op) / 1_000_000


# Singleton used throughout the script
stats = ModelStats()


# ---------------------------------------------------------------------------
# Animation-count helper (for X / N progress in Manim render)
# ---------------------------------------------------------------------------

def count_play_calls(code: str) -> int:
    """Count self.play( calls in generated Manim code as an estimate of total animations."""
    return max(1, len(re.findall(r'self\.play\s*\(', code)))


MANIM_CHEAT_SHEET = """
CRITICAL OPENGL AND MANIM RULES:
1. OPENGL CAMERA: When using `--renderer=opengl`, the camera is an `OpenGLCamera`. IT DOES NOT HAVE A `.frame` ATTRIBUTE.
   - WRONG: `self.play(self.camera.frame.animate.shift(DOWN))`
   - CORRECT: `self.play(self.camera.animate.shift(DOWN))`
2. Geometry Errors: Do not invent arguments for `Polyline`. Use standard `Line(start, end)` or `Polygon(*points)`.
3. Deprecated Syntax: `ShowCreation` is dead. Use `Create()`.
4. LaTeX Errors: All MathTex strings must be raw strings, e.g., MathTex(r"\\frac{a}{b}").
5. OpenGL Opacity: Do NOT use `.set_stroke_opacity()`. Use `.set_stroke(opacity=...)` or `.set_opacity(...)`.
6. Flash Animation: Flash() requires a POINT (np.ndarray), NOT a mobject.
   - WRONG: `Flash(some_line)`, `Flash(some_arc)`, `Flash(some_vgroup)`
   - CORRECT: `Flash(some_line.get_center())`, `Flash(some_arc.get_center())`
7. VMobject.next_to() CRASH: Calling `.next_to()` on a VMobject that has no points raises NotImplementedError.
   Use `.move_to(some_point + RIGHT * offset)` instead.
8. OPENGL BROADCAST ERROR:
   a) Create()/Write() on Arc, Angle, RightAngle, CurvedArrow, or any Arc-based shape
   b) mobject.animate.become(AnyMathTex_or_Tex(...)) — ALWAYS causes this in OpenGL
   c) Transform(A, B) where A and B have different point counts
   d) ReplacementTransform between shapes of different complexity
   FIX: Replace all of the above with FadeOut(old)/FadeIn(new).
9. GrowFromEdge CRASH: Use FadeIn() instead.
10. SCOPE: When fixing, ONLY change the lines in the traceback.
11. ZERO-DURATION WAIT: self.wait(tracker.get_remaining_duration()) CRASHES when remaining == 0.
    ALWAYS wrap it: self.wait(max(0.01, tracker.get_remaining_duration()))
    This applies to EVERY voiceover block — no exceptions.
"""

# ---------------------------------------------------------------------------
# Clickable file:// link helper (Rich markup, OSC 8 hyperlinks)
# ---------------------------------------------------------------------------

def file_link(path: str, label: str | None = None) -> str:
    """
    Return Rich markup for a clickable file:// hyperlink.
    Works in terminals with OSC 8 support (kitty, modern gnome-terminal, etc).
    Falls back to plain text in others.
    """
    abs_path = os.path.abspath(path)
    uri = "file://" + abs_path
    display = label or abs_path
    return f"[link={uri}]{display}[/link]"


# ---------------------------------------------------------------------------
# Rate Limit Safe API Wrapper
# ---------------------------------------------------------------------------
def safe_generate_content(client, model, contents, max_retries=6, _label: str = ""):
    """Wrapper around client.models.generate_content with retry + stats tracking."""
    prompt_snapshot = str(contents)   # snapshot before any mutation
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model, contents=contents)
            stats.record(model, prompt_snapshot, response.text, label=_label or model)
            return response
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "quota" in error_str.lower() or "exhausted" in error_str.lower():
                wait_time = 5 * (2 ** attempt)
                console.print(
                    f"[yellow]⚠ Rate limited (429). Sleeping {wait_time}s "
                    f"(retry {attempt + 1}/{max_retries})…[/yellow]"
                )
                time.sleep(wait_time)
            else:
                raise
    console.print("[red]Max rate-limit retries reached. Forcing final attempt…[/red]")
    response = client.models.generate_content(model=model, contents=contents)
    stats.record(model, prompt_snapshot, response.text, label=_label or model)
    return response


# ---------------------------------------------------------------------------
# Integrated Pipeline
# ---------------------------------------------------------------------------
class IntegratedPipeline(Gemini3Pipeline):
    swarm_model: str = "gemini-3-flash-preview"  # overridden by main()

    def run_and_capture(self, user_prompt: str, audio_instructions: str = "") -> tuple[str, str]:
        PIPELINE_STAGES = [
            ("ConceptAnalyzer",      "Analyzing user prompt…"),
            ("PrerequisiteExplorer", "Building knowledge tree…"),
            ("MathematicalEnricher", "Enriching with LaTeX…"),
            ("VisualDesigner",       "Designing storyboard…"),
            ("NarrativeComposer",    "Composing script…"),
            ("SyncOrchestrator",     "Aligning sync manifest…"),
            ("CodeGenerator",        "Generating Manim code…"),
        ]

        def _agent(agent_obj, prompt: str, label: str):
            """Run agent, track call in stats, return str result."""
            result = run_agent_sync(agent_obj, prompt)
            stats.record(self.swarm_model, prompt, str(result), label=label)
            return result

        if VERBOSE:
            logger.console.rule("[bold red]Integrated Pipeline Start[/bold red]")
        else:
            console.print("[bold blue]⚙  Running generation swarm (7 agents)…[/bold blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=not VERBOSE,
        ) as progress:
            task = progress.add_task("Starting…", total=len(PIPELINE_STAGES))

            # --- Agent 1: ConceptAnalyzer ---
            progress.update(task, description="[cyan]ConceptAnalyzer[/cyan] — Analyzing prompt…")
            if VERBOSE:
                logger.log_agent_start("ConceptAnalyzer", "Analyzing user prompt…")
            analysis_result = _agent(self.concept_analyzer, user_prompt, "ConceptAnalyzer")
            if VERBOSE:
                logger.log_agent_completion("ConceptAnalyzer", str(analysis_result))
            progress.advance(task)

            # --- Agent 2: PrerequisiteExplorer ---
            progress.update(task, description="[cyan]PrerequisiteExplorer[/cyan] — Building knowledge tree…")
            if VERBOSE:
                logger.log_agent_start("PrerequisiteExplorer", "Building knowledge tree…")
            tree_result = _agent(
                self.prerequisite_explorer,
                f"Build a prerequisite tree for this concept analysis: {analysis_result}",
                "PrerequisiteExplorer",
            )
            if VERBOSE:
                logger.log_agent_completion("PrerequisiteExplorer", str(tree_result))
            progress.advance(task)

            # --- Agent 3: MathematicalEnricher ---
            progress.update(task, description="[cyan]MathematicalEnricher[/cyan] — Enriching with LaTeX…")
            if VERBOSE:
                logger.log_agent_start("MathematicalEnricher", "Enriching tree with LaTeX…")
            enriched_tree = _agent(
                self.math_enricher,
                f"Enrich this knowledge tree with physics/math details: {tree_result}",
                "MathematicalEnricher",
            )
            if VERBOSE:
                logger.log_agent_completion("MathematicalEnricher", str(enriched_tree))
            progress.advance(task)

            # --- Agent 4: VisualDesigner ---
            progress.update(task, description="[cyan]VisualDesigner[/cyan] — Designing storyboard…")
            if VERBOSE:
                logger.log_agent_start("VisualDesigner", "Designing visual storyboard…")
            storyboard = _agent(
                self.visual_designer,
                f"Create a visual storyboard for this enriched tree: {enriched_tree}",
                "VisualDesigner",
            )
            if VERBOSE:
                logger.log_agent_completion("VisualDesigner", str(storyboard))
            progress.advance(task)

            # --- Agent 5: NarrativeComposer ---
            progress.update(task, description="[cyan]NarrativeComposer[/cyan] — Composing script…")
            if VERBOSE:
                logger.log_agent_start("NarrativeComposer", "Composing verbose script…")
            verbose_prompt = _agent(
                self.narrative_composer,
                f"Write a verbose animation script based on this storyboard: {storyboard}",
                "NarrativeComposer",
            )
            if VERBOSE:
                logger.log_agent_completion("NarrativeComposer", str(verbose_prompt))
            progress.advance(task)

            # --- Agent 6: SyncOrchestrator ---
            progress.update(task, description="[cyan]SyncOrchestrator[/cyan] — Aligning sync manifest…")
            if VERBOSE:
                logger.log_agent_start("SyncOrchestrator", "Aligning narration with visual actions…")
            sync_manifest = _agent(
                self.sync_orchestrator,
                f"Orchestrate this script and storyboard into a sync manifest: {verbose_prompt} {storyboard}",
                "SyncOrchestrator",
            )
            if VERBOSE:
                logger.log_agent_completion("SyncOrchestrator", str(sync_manifest))
            else:
                # Show a tiny summary even in non-verbose mode
                blocks = len(re.findall(r"Block \d+", str(sync_manifest))) or 1
                console.print(f"[cyan]  → Sync Manifest generated ({blocks} visual-narrative blocks)[/cyan]")
            progress.advance(task)

            # --- Agent 7: CodeGenerator ---
            progress.update(task, description="[cyan]CodeGenerator[/cyan] — Generating Manim code…")
            if VERBOSE:
                logger.log_agent_start("CodeGenerator", "Generating Manim code…")
            full_code_prompt = f"""
        Generate the complete Manim code based on this detailed sync manifest:
        {sync_manifest}

        {MANIM_CHEAT_SHEET}

        {audio_instructions}
        """
            if audio_instructions and VERBOSE:
                console.print("[cyan]  CodeGenerator: audio instructions injected directly.[/cyan]")
            code_result = _agent(self.code_generator, full_code_prompt, "CodeGenerator")
            if VERBOSE:
                logger.log_agent_completion("CodeGenerator", str(code_result))
            progress.advance(task)

        if VERBOSE:
            logger.console.rule("[bold red]Pipeline End[/bold red]")

        console.print("[bold green]✓  Generation swarm complete.[/bold green]")
        console.print(stats.render_table())
        return str(code_result), str(verbose_prompt)


# ---------------------------------------------------------------------------
# Syntax helpers
# ---------------------------------------------------------------------------

def _extract_scene_class(file_path: str) -> str | None:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = ""
                    if isinstance(base, ast.Name):
                        base_name = base.id
                    elif isinstance(base, ast.Attribute):
                        base_name = base.attr
                    if "Scene" in base_name:
                        return node.name
    except Exception:
        pass
    return None


def check_syntax(code_string):
    try:
        ast.parse(code_string)
        return True, ""
    except SyntaxError as e:
        return False, f"SyntaxError at line {e.lineno}: {e.msg}\n{e.text}"


def file_hash(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def get_latest_video(output_log: list[str] | None = None) -> str | None:
    if output_log:
        for line in reversed(output_log):
            m = re.search(r"File ready at\s+(.+\.(?:mp4|mov|webm))", line)
            if m:
                path = m.group(1).strip()
                if os.path.exists(path):
                    vprint(f"[dim]Video (from log): {file_link(path, os.path.basename(path))}[/dim]")
                    return path
                abs_path = os.path.abspath(path)
                if os.path.exists(abs_path):
                    vprint(f"[dim]Video (from log, resolved): {file_link(abs_path, os.path.basename(abs_path))}[/dim]")
                    return abs_path

    media_roots = []
    for candidate in ["media", "../media"]:
        p = os.path.abspath(candidate)
        if os.path.isdir(p):
            media_roots.append(p)

    if not media_roots:
        vprint("[yellow]get_latest_video: no media/ dir found[/yellow]")
        return None

    SKIP_DIRS = {"partial_movie_files", "review_frames", "voiceovers", "images", "texts", "Tex"}
    video_files: list[str] = []
    for media_root in media_roots:
        for dirpath, dirnames, files in os.walk(media_root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in files:
                if fname.endswith((".mp4", ".mov", ".webm")):
                    video_files.append(os.path.join(dirpath, fname))

    if not video_files:
        vprint("[yellow]get_latest_video: no video files found in media/ tree.[/yellow]")
        return None

    latest = max(video_files, key=os.path.getmtime)
    vprint(f"[dim]Video (filesystem scan): {file_link(latest, os.path.basename(latest))}[/dim]")
    return latest


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def extract_error_line(error_output: str, scene_file: str = "output_scene.py") -> int | None:
    scene_basename = os.path.basename(scene_file)
    for pat in [rf'File ".*?{re.escape(scene_basename)}.*?", line (\d+)']:
        matches = re.findall(pat, error_output)
        if matches:
            return int(matches[-1])
    for line in reversed(error_output.strip().splitlines()):
        m = re.match(r'\s*File "(.*?)", line (\d+)', line)
        if m:
            path, lineno = m.group(1), m.group(2)
            if "site-packages" not in path and ".venv" not in path:
                return int(lineno)
    matches = re.findall(r'File ".*?", line (\d+)', error_output)
    return int(matches[-1]) if matches else None


def extract_surgical_context(file_path, error_line, context_lines=12):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        start = max(0, error_line - context_lines - 1)
        end = min(len(all_lines), error_line + context_lines)
        snippet = ""
        for i, line in enumerate(all_lines[start:end], start=start + 1):
            marker = ">>>" if i == error_line else "   "
            snippet += f"{marker} {i:4d} | {line}"
        return snippet
    except Exception:
        return "(could not extract context)"


def extract_traceback_summary(error_output):
    lines = error_output.strip().splitlines()
    last_file_idx = 0
    for i, l in enumerate(lines):
        if l.strip().startswith("File "):
            last_file_idx = i
    return "\n".join(lines[max(0, last_file_idx - 3):])


# ---------------------------------------------------------------------------
# Video / audio info
# ---------------------------------------------------------------------------

def get_video_duration(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
            capture_output=True, text=True,
        )
        return float(json.loads(result.stdout)["format"]["duration"])
    except Exception:
        return None


def parse_animation_log(output_log):
    animations = []
    seen = set()
    for line in output_log:
        m = re.match(r"\s*Animation (\d+): ([^:]+):", line)
        if m:
            idx, desc = int(m.group(1)), m.group(2).strip()
            if idx not in seen:
                seen.add(idx)
                animations.append((idx, desc))
    return sorted(animations, key=lambda x: x[0])


def build_anim_map_from_log(frame_timestamps, animations, duration):
    if not animations or not duration:
        return {}
    total_anims = animations[-1][0] + 1
    result = {}
    for fp, ts in frame_timestamps.items():
        frac = ts / duration
        est_idx = round(frac * (total_anims - 1))
        est_idx = max(0, min(est_idx, total_anims - 1))
        closest = min(animations, key=lambda a: abs(a[0] - est_idx))
        result[fp] = (closest[0], closest[1])
    return result


# ---------------------------------------------------------------------------
# Partial movie frame extraction
# ---------------------------------------------------------------------------

def find_partial_movie_list(media_dir: str) -> str | None:
    """Search recursively for the most recently modified partial_movie_file_list.txt."""
    candidates = []
    for dirpath, dirnames, files in os.walk(media_dir):
        for fname in files:
            if fname == "partial_movie_file_list.txt":
                candidates.append(os.path.join(dirpath, fname))
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


def _parse_partial_list_paths(list_file: str) -> list[str]:
    """
    Parse clip paths from a Manim partial_movie_file_list.txt.

    Handles all known Manim format variants:
      file '/absolute/path.mp4'    ← single quotes, absolute (most common)
      file "/absolute/path.mp4"    ← double quotes, absolute
      file 'file:/absolute/path'   ← URI style inside quotes (Manim v0.20.1+)
      file 'relative/path.mp4'     ← relative to list file dir
      /absolute/path.mp4           ← bare path, no keyword
      file:///absolute/path.mp4    ← URI style (rare)

    Returns only paths that actually exist on disk.
    """
    list_dir = os.path.dirname(list_file)

    with open(list_file, "r", encoding="utf-8") as f:
        raw = f.read()

    console.print(f"[dim]  ── Partial list raw content ({len(raw)} bytes) ──[/dim]") if VERBOSE else None
    if VERBOSE:
        for i, line in enumerate(raw.splitlines()[:20], 1):
            console.print(f"[dim]  {i:02d}: {line}[/dim]")
        if len(raw.splitlines()) > 20:
            console.print(f"[dim]  … ({len(raw.splitlines())} lines total)[/dim]")

    candidates: list[str] =[]

    # Pattern 1: file 'path' or file "path"  (covers single and double quotes)
    for m in re.finditer(r"""^file\s+['"](.+?)['"]""", raw, re.MULTILINE):
        candidates.append(m.group(1).strip())

    # Pattern 2: bare path lines (no 'file' keyword)
    if not candidates:
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.lower().startswith("file"):
                continue
            if line.startswith("/") or line.startswith("./") or line.startswith("../") or line.endswith(".mp4"):
                candidates.append(line)

    # Pattern 3: file:///path URI
    if not candidates:
        for m in re.finditer(r"file:///(.+\.mp4)", raw):
            candidates.append("/" + m.group(1).strip())

    vprint(f"[dim]  Raw candidates extracted: {len(candidates)}[/dim]")
    if VERBOSE:
        for c in candidates[:8]:
            console.print(f"[dim]    → {c}[/dim]")
        if len(candidates) > 8:
            console.print(f"[dim]    … and {len(candidates) - 8} more[/dim]")

    # Resolve relative paths and verify existence
    resolved: list[str] =[]
    for p in candidates:
        # Strip standard URI prefixes that FFMPEG/Manim might inject inside the quotes
        if p.startswith("file://"):
            p = p[7:]
        elif p.startswith("file:"):
            p = p[5:]

        norm = os.path.normpath(p if os.path.isabs(p) else os.path.join(list_dir, p))
        if os.path.exists(norm):
            resolved.append(norm)
        else:
            vprint(f"[yellow]  ✗ Not found on disk: {norm}[/yellow]")

    vprint(f"[dim]  Resolved to {len(resolved)} existing files.[/dim]")
    return resolved

def extract_frames_from_partials(media_dir: str, frame_dir: str) -> tuple[list[str], dict] | None:
    """
    Extract the last frame of every partial clip in the Manim partial list.
    Returns (frame_paths, frame_timestamps) or None if no list found.
    """
    list_file = find_partial_movie_list(media_dir)
    if not list_file:
        console.print("[yellow]  No partial_movie_file_list.txt found in media/.[/yellow]")
        return None

    console.print(
        f"[cyan]  Found partial list: {file_link(list_file, os.path.relpath(list_file))}[/cyan]"
    )

    partial_paths = _parse_partial_list_paths(list_file)

    if not partial_paths:
        console.print("[bold yellow]  Partial list found but 0 valid paths after disk check.[/bold yellow]")
        console.print("[yellow]  See above for raw candidates and missing-path warnings.[/yellow]")
        return None

    console.print(f"[cyan]  ✓ {len(partial_paths)} valid partial clips to process.[/cyan]")
    os.makedirs(frame_dir, exist_ok=True)

    frame_paths: list[str] = []
    frame_timestamps: dict[str, float] = {}
    running_time = 0.0

    for i, mp4 in enumerate(partial_paths):
        seg_duration = get_video_duration(mp4) or 1.0
        running_time += seg_duration
        out_path = os.path.join(frame_dir, f"anim_{i:04d}.png")

        # -sseof -0.1: seek to 0.1s before end of this partial clip
        result = subprocess.run(
            ["ffmpeg", "-y", "-sseof", "-0.1", "-i", mp4,
             "-update", "1", "-frames:v", "1", out_path],
            capture_output=True,
        )

        if os.path.exists(out_path):
            frame_paths.append(out_path)
            frame_timestamps[out_path] = round(running_time - 0.1, 4)
            vprint(
                f"[dim]  [{i+1:03d}/{len(partial_paths)}] "
                f"t={running_time:.2f}s  dur={seg_duration:.2f}s  "
                f"{file_link(out_path, os.path.basename(out_path))}[/dim]"
            )
        else:
            # Very short clip fallback: grab first frame
            subprocess.run(
                ["ffmpeg", "-y", "-i", mp4, "-frames:v", "1", out_path],
                capture_output=True,
            )
            if os.path.exists(out_path):
                frame_paths.append(out_path)
                frame_timestamps[out_path] = round(running_time, 4)
                vprint(
                    f"[dim]  [{i+1:03d}/{len(partial_paths)}] "
                    f"t={running_time:.2f}s  dur={seg_duration:.2f}s  "
                    f"(first-frame fallback)  "
                    f"{file_link(out_path, os.path.basename(out_path))}[/dim]"
                )
            else:
                console.print(f"[yellow]  [{i+1:03d}] Failed to extract frame from {mp4}[/yellow]")

    console.print(f"[cyan]  ✓ Partial strategy: {len(frame_paths)} frames extracted.[/cyan]")
    return frame_paths, frame_timestamps


# ---------------------------------------------------------------------------
# Smart frame extraction — partials first, code-parse fallback
# ---------------------------------------------------------------------------

def extract_frames_smart(video_path, frame_dir, code: str = ""):
    os.makedirs(frame_dir, exist_ok=True)
    for f in glob.glob(f"{frame_dir}/**/*.png", recursive=True):
        os.remove(f)
    for f in glob.glob(f"{frame_dir}/*.png"):
        os.remove(f)

    duration   = get_video_duration(video_path) or 60.0
    max_frames = 40

    # ── Strategy 1: partial movie files ───────────────────────────────────
    partial_result = None
    for media_candidate in ["media", "../media"]:
        media_abs = os.path.abspath(media_candidate)
        if os.path.isdir(media_abs):
            partials_dir = os.path.join(frame_dir, "partials")
            partial_result = extract_frames_from_partials(media_abs, partials_dir)
            if partial_result:
                break

    if partial_result:
        partial_frame_paths, partial_timestamps = partial_result
        deduped, last_ts = [], -999.0
        for fp in partial_frame_paths:
            ts = partial_timestamps.get(fp, 0)
            if ts - last_ts >= 0.3:
                dest = os.path.join(frame_dir, f"frame_{len(deduped)+1:04d}_t{int(ts):04d}.png")
                shutil.copy(fp, dest)
                deduped.append((ts, dest))
                last_ts = ts
            if len(deduped) >= max_frames:
                break
        frame_timestamps = {p: ts for ts, p in deduped}
        frame_paths      = [p for _, p in deduped]
        vprint(
            f"[cyan]  ✓ Partial strategy: {len(partial_frame_paths)} raw → "
            f"{len(frame_paths)} after dedup.[/cyan]"
        )
        return frame_paths, frame_timestamps

    # ── Strategy 2: code-parse timestamps ─────────────────────────────────
    vprint("[yellow]  ⚠ Falling back to code-parse timestamp strategy.[/yellow]")
    SETTLE = 0.12
    anim_end_times: list[float] = []
    if code:
        raw_times = _parse_animation_end_times_from_code(code)
        anim_end_times = [
            min(t + SETTLE, duration - 0.05)
            for t in raw_times if t < duration
        ]
        vprint(
            f"[dim]  Code-parse: {len(raw_times)} animation calls → "
            f"{len(anim_end_times)} timestamps within {duration:.1f}s[/dim]"
        )

    fps_val = min(1.0, max_frames / max(duration, 1.0))
    if   fps_val >= 1.0:  fps_str, fps_float = "1",   1.0
    elif fps_val >= 0.5:  fps_str, fps_float = "1/2", 0.5
    elif fps_val >= 0.25: fps_str, fps_float = "1/4", 0.25
    else:                 fps_str, fps_float = "1/6", 1.0 / 6.0

    regular_dir = os.path.join(frame_dir, "regular")
    anim_dir    = os.path.join(frame_dir, "anim_ends")
    os.makedirs(regular_dir, exist_ok=True)
    os.makedirs(anim_dir,    exist_ok=True)

    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vf", f"fps={fps_str}", f"{regular_dir}/frame_%04d.png"],
        capture_output=True,
    )
    if anim_end_times:
        for k, ts in enumerate(anim_end_times[:max_frames]):
            out_path = os.path.join(anim_dir, f"anim_{k:04d}.png")
            subprocess.run(
                ["ffmpeg", "-y", "-ss", f"{ts:.3f}", "-i", video_path, "-frames:v", "1", out_path],
                capture_output=True,
            )

    regular_frames = sorted(glob.glob(f"{regular_dir}/frame_*.png"))
    anim_frames    = sorted(glob.glob(f"{anim_dir}/anim_*.png"))

    combined: list[tuple[float, str]] = []
    if anim_frames:
        combined += [(anim_end_times[k], p) for k, p in enumerate(anim_frames) if k < len(anim_end_times)]
    combined += [(i / fps_float, p) for i, p in enumerate(regular_frames)]
    combined.sort(key=lambda x: x[0])

    deduped, last_ts = [], -999.0
    for ts, src in combined:
        if ts - last_ts >= 0.4:
            dest = os.path.join(frame_dir, f"frame_{len(deduped)+1:04d}_t{int(ts):04d}.png")
            shutil.copy(src, dest)
            deduped.append((ts, dest))
            last_ts = ts
        if len(deduped) >= max_frames:
            break

    frame_timestamps = {p: ts for ts, p in deduped}
    frame_paths = [p for _, p in deduped]
    vprint(f"[cyan]  {len(frame_paths)} frames after dedup (code-parse fallback).[/cyan]")
    return frame_paths, frame_timestamps


def _parse_animation_end_times_from_code(code: str) -> list[float]:
    times: list[float] = []
    current_time = 0.0
    lines = code.splitlines()
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if re.match(r"self\.wait\s*\(", stripped):
            call = stripped
            depth = call.count("(") - call.count(")")
            j = i + 1
            while depth > 0 and j < len(lines):
                call += " " + lines[j].strip()
                depth += lines[j].count("(") - lines[j].count(")")
                j += 1
            duration = 1.0
            inner = re.search(r"self\.wait\s*\(([^)]*)\)", call)
            if inner:
                arg = inner.group(1).strip()
                dm = re.search(r"duration\s*=\s*([\d.]+)", arg)
                if dm:
                    duration = float(dm.group(1))
                elif re.match(r"[\d.]+$", arg):
                    duration = float(arg)
            current_time += duration
            times.append(round(current_time, 4))
            i = j
            continue
        if re.match(r"self\.play\s*\(", stripped):
            call = stripped
            depth = call.count("(") - call.count(")")
            j = i + 1
            while depth > 0 and j < len(lines):
                call += " " + lines[j].strip()
                depth += lines[j].count("(") - lines[j].count(")")
                j += 1
            duration = 1.0
            rm = re.search(r"run_time\s*=\s*([\d.]+)", call)
            if rm:
                duration = float(rm.group(1))
            current_time += duration
            times.append(round(current_time, 4))
            i = j
            continue
        i += 1
    return times


# ---------------------------------------------------------------------------
# Gemini TTS Service helper
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Gemini TTS Service helper
# ---------------------------------------------------------------------------

GEMINI_TTS_SERVICE_TEMPLATE = '''"""
GeminiTTSService — manim-voiceover compatible TTS using Gemini 2.5 TTS models.
Auto-generated by run_auto_pipeline.py.
"""
import os
import wave
import hashlib
import tempfile
from google import genai
from manim_voiceover.services.base import SpeechService


class GeminiTTSService(SpeechService):
    """
    Parameters
    ----------
    model : str
        "gemini-2.5-flash-preview-tts"  or  "gemini-2.5-pro-preview-tts"
    voice : str
        Prebuilt voice name:
          "Kore"    – calm, clear  (default, good for educational content)
          "Charon"  – measured, authoritative
          "Fenrir"  – energetic, engaging
          "Aoede"   – warm, approachable
    style_context : str
        Instruction prepended to every TTS request to set tone/pacing.
    """

    def __init__(
        self,
        model: str = "gemini-2.5-flash-preview-tts",
        voice: str = "Kore",
        style_context: str = "",
        **kwargs,
    ):
        self.tts_model = model
        self.voice = voice
        self.style_context = style_context.strip()
        self._client = genai.Client()
        SpeechService.__init__(self, **kwargs)

    def generate_from_text(
        self,
        text: str,
        cache_dir: str | None = None,
        path: str | None = None,
        **kwargs,
    ) -> dict:
        prompt = f"{self.style_context}\\n\\n{text}" if self.style_context else text

        # manim-voiceover tracker.py calls mutagen.mp3.MP3(path) hardcoded to get duration —
        # it cannot read WAV. We must deliver an MP3. Strategy: write raw PCM as WAV first,
        # then convert to MP3 via ffmpeg (already a project dependency for frame extraction).
        digest = hashlib.md5(f"{self.tts_model}:{self.voice}:{text}".encode()).hexdigest()
        fname = f"{digest}.mp3"  # MP3 — required by manim-voiceover tracker

        if cache_dir is None:
            cache_dir = self.cache_dir  # set by SpeechService.__init__
        os.makedirs(cache_dir, exist_ok=True)

        if path is None:
            path = os.path.join(cache_dir, fname)

        if not os.path.exists(path):
            audio_bytes = self._call_gemini_tts(prompt)
            self._pcm_to_mp3(audio_bytes, path)

        # Relative filename — base class resolves: Path(cache_dir) / dict["final_audio"]
        return {"original_audio": fname, "final_audio": fname}

    def _call_gemini_tts(self, text: str) -> bytes:
        response = self._client.models.generate_content(
            model=self.tts_model,
            contents=text,
            config=genai.types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=genai.types.SpeechConfig(
                    voice_config=genai.types.VoiceConfig(
                        prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(
                            voice_name=self.voice
                        )
                    )
                ),
            ),
        )
        return response.candidates[0].content.parts[0].inline_data.data

    @staticmethod
    def _pcm_to_mp3(pcm_bytes: bytes, out_path: str) -> None:
        """
        Convert raw 16-bit 24kHz mono PCM bytes → MP3 via ffmpeg.
        ffmpeg reads the PCM from stdin and writes MP3 to out_path.
        manim-voiceover uses mutagen.mp3.MP3() to get duration, so WAV won't work.
        """
        import subprocess
        cmd =[
            "ffmpeg", "-y",
            "-f", "s16le",       # raw signed 16-bit little-endian PCM
            "-ar", "24000",      # 24 kHz sample rate (Gemini TTS output)
            "-ac", "1",          # mono
            "-i", "pipe:0",      # read from stdin
            "-codec:a", "libmp3lame",
            "-q:a", "2",         # VBR quality ~190 kbps — good balance
            out_path,
        ]
        result = subprocess.run(cmd, input=pcm_bytes, capture_output=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg PCM→MP3 conversion failed:\\n{result.stderr.decode(errors='replace')}"
            )
'''

def purge_voiceover_cache():
    """Delete stale .mp3/audio files and the cache.json to avoid manim-voiceover corruption crashes."""
    removed_files = 0
    for root, dirs, files in os.walk("media/voiceovers"):
        for fname in files:
            if fname.endswith((".mp3", ".wav", ".json")):
                fpath = os.path.join(root, fname)
                try:
                    os.remove(fpath)
                    removed_files += 1
                except Exception:
                    pass
    if removed_files:
        console.print(f"[yellow]  Purged {removed_files} stale voiceover cache files (including cache.json).[/yellow]")


def write_gemini_tts_service(output_dir: str, purge_gtts_cache: bool = True) -> str:
    dest = os.path.join(output_dir, "gemini_tts_service.py")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(GEMINI_TTS_SERVICE_TEMPLATE)
    console.print(f"[green]  ✓ GeminiTTSService written: {file_link(dest, 'gemini_tts_service.py')}[/green]")

    if purge_gtts_cache:
        purge_voiceover_cache()

    return dest


def build_style_context_from_blueprint(blueprint: str) -> str:
    if not blueprint or len(blueprint) < 20:
        return (
            "You are narrating a calm, educational math animation. "
            "Speak clearly and at a measured pace with natural prosody."
        )
    snippet = blueprint[:300].replace("\n", " ").strip()
    return (
        f"You are narrating an educational math animation. "
        f"Adapt your tone and pacing to match this description: {snippet} "
        f"Speak clearly, at a measured pace, with natural prosody."
    )


def patch_scene_for_gemini_tts(output_file: str, tts_model: str, tts_voice: str, style_ctx: str) -> bool:
    """
    When --skip-gen is combined with --audio-model, patch an existing scene
    that may still use GTTSService to use GeminiTTSService instead.
    """
    try:
        with open(output_file, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception:
        return False

    if "GeminiTTSService" in code:
        console.print("[dim]  Scene already uses GeminiTTSService — no patch needed.[/dim]")
        return False

    if "GTTSService" not in code and "VoiceoverScene" not in code:
        console.print("[dim]  Scene has no audio service — nothing to patch.[/dim]")
        return False

    console.print("[bold yellow]  Patching scene: GTTSService → GeminiTTSService…[/bold yellow]")
    original = code

    # 1. Replace import line
    code = re.sub(
        r"from manim_voiceover\.services\.gtts import GTTSService\n?",
        "from gemini_tts_service import GeminiTTSService\n",
        code,
    )

    # 2. Replace set_speech_service call
    style_escaped = style_ctx[:120].replace('"', "'")
    replacement = (
        f'self.set_speech_service(GeminiTTSService('
        f'model="{tts_model}", voice="{tts_voice}", '
        f'style_context="{style_escaped}"))'
    )
    code = re.sub(
        r"self\.set_speech_service\s*\(\s*GTTSService\s*\([^)]*\)\s*\)",
        replacement,
        code,
    )

    if code == original:
        console.print("[yellow]  Audio patch: patterns not matched (check imports manually).[/yellow]")
        return False

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)
    console.print(f"[green]  ✓ Patched {file_link(output_file, os.path.basename(output_file))} "
                  f"(GTTSService → GeminiTTSService)[/green]")
    return True


# ---------------------------------------------------------------------------
# Patch utilities
# ---------------------------------------------------------------------------

def apply_patch_strreplace(file_path: str, patch_content: str, hint_line: int | None = None) -> bool:
    # 1. Flexible regex: Matches <<<SEARCH [content] >>>REPLACE [content] <<<END
    #    Captures content non-greedily until the next tag.
    pattern = re.compile(
        r"<<<SEARCH\s*(.*?)\s*>>>REPLACE\s*(.*?)\s*<<<END",
        re.DOTALL | re.IGNORECASE
    )
    blocks = pattern.findall(patch_content)
    
    # --- Smart Greedy Repair Logic ---
    if not blocks:
        # Check if we have the start tags but are missing the end tag
        search_match = re.search(r"<<<SEARCH\s*(.*?)\s*>>>REPLACE", patch_content, re.DOTALL | re.IGNORECASE)
        if search_match:
            vprint("[yellow]  str_replace: Found SEARCH/REPLACE tags but missing <<<END. Attempting smart repair...[/yellow]")
            search_raw = search_match.group(1)
            
            # Find where REPLACE starts, to get everything after it
            # We use the match end to locate the start of the REPLACE content
            replace_start_idx = search_match.end()
            replace_content_raw = patch_content[replace_start_idx:]
            
            # Heuristic: Stop at the next code fence if it exists, otherwise take it all
            # This handles cases where the model writes ``` at the end but forgets <<<END
            fence_match = re.search(r"\n\s*```", replace_content_raw)
            if fence_match:
                replace_raw = replace_content_raw[:fence_match.start()]
                vprint(f"[dim]  Smart repair: terminated REPLACE block at code fence (length {len(replace_raw)}).[/dim]")
            else:
                replace_raw = replace_content_raw
                vprint(f"[dim]  Smart repair: consumed remainder of text (length {len(replace_raw)}).[/dim]")
            
            blocks = [(search_raw, replace_raw)]
        else:
            console.print("[bold red]  str_replace: No valid <<<SEARCH ... >>>REPLACE block found.[/bold red]")
            if VERBOSE:
                console.print(Panel(patch_content, title="Raw Patch Content (Failed Parse)", border_style="dim"))
            return False

    before_hash = file_hash(file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    new_content = content
    
    for idx, (search_raw, replace_raw) in enumerate(blocks, 1):
        # 2. Cleanup: Remove markdown code fences if captured inside the block
        search_text = re.sub(r"^```\w*\s*\n", "", search_raw)
        search_text = re.sub(r"\n\s*```\s*$", "", search_text)
        replace_text = re.sub(r"^```\w*\s*\n", "", replace_raw)
        replace_text = re.sub(r"\n\s*```\s*$", "", replace_text)

        # Log exactly what we are working with
        if VERBOSE:
            console.print(f"[bold cyan]Block {idx} Extracted:[/bold cyan]")
            console.print(f"[dim]SEARCH:\n{search_text!r}[/dim]")
            console.print(f"[dim]REPLACE:\n{replace_text!r}[/dim]")

        # 3. Trim strict newlines/whitespace from ends for matching
        search_clean = search_text.strip()
        replace_clean = replace_text.strip()
        
        if not search_clean:
            console.print(f"[yellow]  str_replace block {idx}: Empty SEARCH block. Skipping.[/yellow]")
            continue

        # Strategy A: Exact literal match (best)
        if search_clean in new_content:
            count = new_content.count(search_clean)
            if count > 1:
                if hint_line is not None:
                    # Disambiguate: pick the occurrence whose start position is closest to hint_line
                    lines_so_far = new_content.splitlines(keepends=True)
                    occurrences = []
                    pos = 0
                    search_pos = 0
                    while True:
                        idx_found = new_content.find(search_clean, search_pos)
                        if idx_found == -1:
                            break
                        line_num = new_content[:idx_found].count("\n") + 1
                        occurrences.append((idx_found, line_num))
                        search_pos = idx_found + 1
                    best = min(occurrences, key=lambda x: abs(x[1] - hint_line))
                    console.print(f"[yellow]  str_replace block {idx}: {count} matches — picking line {best[1]} (closest to hint line {hint_line}).[/yellow]")
                    before = new_content[:best[0]]
                    after  = new_content[best[0] + len(search_clean):]
                    new_content = before + replace_clean + after
                    console.print(f"[green]  str_replace block {idx}/{len(blocks)} applied (exact match, hint-disambiguated).[/green]")
                    continue
                console.print(f"[yellow]  str_replace block {idx}: {count} matches (exact). Ambiguous. Skipping.[/yellow]")
                return False
            
            new_content = new_content.replace(search_clean, replace_clean, 1)
            console.print(f"[green]  str_replace block {idx}/{len(blocks)} applied (exact match).[/green]")
            continue
            
        console.print(f"[yellow]  str_replace block {idx}: Exact match failed. Trying fuzzy...[/yellow]")
        if VERBOSE:
             console.print(f"[dim]  Search block start: {search_clean[:60]!r}...[/dim]")

        # Strategy B: Line-by-line whitespace-insensitive match (Fuzzy)
        search_lines_strict = [l.strip() for l in search_text.splitlines() if l.strip()]
        if not search_lines_strict:
             console.print(f"[yellow]  str_replace block {idx}: SEARCH block contains no non-whitespace lines. Skipping.[/yellow]")
             continue
        
        if any(l == "..." for l in search_lines_strict):
            console.print(f"[yellow]  str_replace block {idx}: Warning: SEARCH block contains '...'. This often fails; models should use literal context.[/yellow]")

        content_lines = new_content.splitlines(keepends=True)
        content_info = [(i, l.strip()) for i, l in enumerate(content_lines) if l.strip()]
        content_filtered_indices = [x[0] for x in content_info]
        content_filtered_text = [x[1] for x in content_info]
        
        candidates = []
        n_search = len(search_lines_strict)
        
        for i in range(len(content_filtered_text) - n_search + 1):
            match = True
            for j in range(n_search):
                if content_filtered_text[i+j] != search_lines_strict[j]:
                    match = False
                    break
            if match:
                candidates.append(i)
        
        if not candidates:
            console.print(f"[bold red]  str_replace block {idx}: SEARCH block not found (fuzzy).[/bold red]")
            # (Diagnostic code omitted for brevity in prompt, but logic remains same)
            return False
            
        if len(candidates) > 1:
            if hint_line is not None:
                def _dist(c):
                    return abs(content_filtered_indices[c] + 1 - hint_line)
                candidates = [min(candidates, key=_dist)]
                console.print(f"[yellow]  str_replace block {idx}: {len(candidates)+len(candidates)-1} fuzzy matches — hint-disambiguated to line {content_filtered_indices[candidates[0]]+1}.[/yellow]")
            else:
                match_lines = [content_filtered_indices[c] + 1 for c in candidates]
                console.print(f"[yellow]  str_replace block {idx}: {len(candidates)} fuzzy matches. Ambiguous. Skipping.[/yellow]")
                return False
            
        f_start = candidates[0]
        f_end = f_start + n_search - 1
        start_line_orig = content_filtered_indices[f_start]
        end_line_orig = content_filtered_indices[f_end]
        original_snippet = "".join(content_lines[start_line_orig : end_line_orig + 1])
        
        replacement_to_use = replace_clean + ("\n" if replace_clean else "")
        new_content = new_content.replace(original_snippet, replacement_to_use, 1)
        console.print(f"[green]  str_replace block {idx}/{len(blocks)} applied (fuzzy match).[/green]")

    # --- SYNTAX CHECK (The "Safety Guard") ---
    # Before writing to disk, verify the new content is valid Python.
    is_valid, syntax_err = check_syntax(new_content)
    if not is_valid:
        console.print("[bold red]  SAFETY GUARD: Patch application resulted in invalid syntax! Rejecting patch.[/bold red]")
        console.print(f"[red]{syntax_err}[/red]")
        if VERBOSE:
             console.print("[dim]  Corrupted content preview (surrounding error):[/dim]")
             err_line = extract_error_line(syntax_err)
             if err_line:
                 lines = new_content.splitlines()
                 start = max(0, err_line - 5)
                 end = min(len(lines), err_line + 5)
                 for i in range(start, end):
                     marker = ">>>" if i + 1 == err_line else "   "
                     console.print(f"[dim]{marker} {i+1:4d} | {lines[i]}[/dim]")
        return False

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    after_hash = file_hash(file_path)
    if before_hash == after_hash:
        console.print("[bold red]str_replace patch: file unchanged.[/bold red]")
        return False
    console.print(f"[green]  File changed ({before_hash[:8]} → {after_hash[:8]}) via str_replace.[/green]")
    return True


def _parse_unified_diff(patch_text: str):
    hunks = []
    lines = patch_text.splitlines()
    i = 0
    while i < len(lines) and not lines[i].startswith("@@"):
        i += 1
    while i < len(lines):
        m = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", lines[i])
        if m:
            orig_start = int(m.group(1))
            orig_count = int(m.group(2)) if m.group(2) is not None else 1
            new_start  = int(m.group(3))
            new_count  = int(m.group(4)) if m.group(4) is not None else 1
            hunk_lines = []
            i += 1
            while i < len(lines) and not lines[i].startswith("@@"):
                hunk_lines.append(lines[i])
                i += 1
            hunks.append((orig_start, orig_count, new_start, new_count, hunk_lines))
        else:
            i += 1
    return hunks


def _apply_single_hunk(file_lines, hunk):
    orig_start, _, _, _, hunk_lines = hunk
    expected = [l[1:] for l in hunk_lines if l.startswith((" ", "-"))]
    target = orig_start - 1
    best_pos, best_score = None, -1
    for offset in range(-15, 16):
        pos = target + offset
        if pos < 0 or pos + len(expected) > len(file_lines):
            continue
        score = sum(
            1.0 if file_lines[pos + j].rstrip("\n") == e.rstrip("\n")
            else 0.5 if file_lines[pos + j].strip() == e.strip()
            else 0.0
            for j, e in enumerate(expected)
        )
        if score > best_score:
            best_score, best_pos = score, pos
    if best_pos is None or (len(expected) > 0 and best_score < len(expected) * 0.5):
        console.print(f"[bold red]  Hunk at line {orig_start}: context not found.[/bold red]")
        console.print(f"[dim]  Expected context (first 3 lines):[/dim]")
        for line in expected[:3]:
            console.print(f"[dim]    {line}[/dim]")
        return None
    new_lines: list[str] = []
    file_pos = best_pos
    for hl in hunk_lines:
        if hl.startswith(" "):
            new_lines.append(file_lines[file_pos] if file_pos < len(file_lines) else hl[1:] + "\n")
            file_pos += 1
        elif hl.startswith("-"):
            file_pos += 1
        elif hl.startswith("+"):
            content = hl[1:]
            new_lines.append(content if content.endswith("\n") else content + "\n")
    return file_lines[:best_pos] + new_lines + file_lines[file_pos:]


def apply_patch_python(file_path: str, patch_content: str) -> bool:
    before_hash = file_hash(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            file_lines = f.readlines()
    except Exception as e:
        console.print(f"[bold red]Could not read {file_path}: {e}[/bold red]")
        return False
    hunks = _parse_unified_diff(patch_content)
    if not hunks:
        console.print("[bold red]Python patch: no hunks parsed.[/bold red]")
        console.print(f"[dim]  Raw patch content start: {patch_content[:100]!r}...[/dim]")
        return False
    current = file_lines
    for idx, hunk in enumerate(hunks, 1):
        result = _apply_single_hunk(current, hunk)
        if result is None:
            console.print(f"[bold red]Python patch: hunk {idx}/{len(hunks)} failed.[/bold red]")
            return False
        console.print(f"[green]  Hunk {idx}/{len(hunks)} applied.[/green]")
        current = result
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(current)
    after_hash = file_hash(file_path)
    if before_hash == after_hash:
        console.print("[bold red]Python patch: file unchanged.[/bold red]")
        return False
    console.print(f"[green]  File changed ({before_hash[:8]} → {after_hash[:8]}) via Python patch.[/green]")
    return True


def apply_patch_shell(file_path: str, patch_content: str) -> bool:
    before_hash = file_hash(file_path)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as pf:
        pf.write(patch_content)
        patch_file_path = pf.name
    orig_path = file_path + ".orig"
    rej_path  = file_path + ".rej"
    try:
        result = subprocess.run(["patch", "--forward", file_path, patch_file_path], capture_output=True, text=True)
    except Exception as e:
        console.print(f"[bold red]Error running patch: {e}[/bold red]")
        return False
    finally:
        for f in [patch_file_path, orig_path, rej_path]:
            if os.path.exists(f):
                os.remove(f)
    if result.returncode != 0:
        console.print(Panel(result.stderr or result.stdout, title="[bold red]shell patch failed[/bold red]", border_style="red"))
        return False
    after_hash = file_hash(file_path)
    if before_hash == after_hash:
        console.print("[bold red]Shell patch: file unchanged.[/bold red]")
        return False
    console.print(f"[green]  File changed ({before_hash[:8]} → {after_hash[:8]}) via shell patch.[/green]")
    return True


def apply_patch_linerange(file_path: str, start_line: int, end_line: int, new_text: str) -> bool:
    """Replace lines [start_line, end_line] (1-indexed, inclusive) with new_text.
    This is the most reliable strategy when we know the exact error line numbers."""
    before_hash = file_hash(file_path)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        console.print(f"[bold red]apply_patch_linerange: can't read {file_path}: {e}[/bold red]")
        return False

    if start_line < 1 or end_line > len(lines) or start_line > end_line:
        console.print(f"[bold red]apply_patch_linerange: invalid range {start_line}–{end_line} (file has {len(lines)} lines)[/bold red]")
        return False

    block = new_text
    if block and not block.endswith("\n"):
        block += "\n"

    new_lines = lines[:start_line - 1] + [block] + lines[end_line:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    after_hash = file_hash(file_path)
    if before_hash == after_hash:
        console.print("[bold red]Line-range patch: file unchanged.[/bold red]")
        return False
    console.print(
        f"[green]  File changed ({before_hash[:8]} → {after_hash[:8]}) "
        f"via line-range patch (lines {start_line}–{end_line}).[/green]"
    )
    return True


def apply_patch(file_path: str, patch_content: str, hint_line: int | None = None) -> bool:
    attempted = False
    if re.search(r"<<<\s*SEARCH", patch_content):
        attempted = True
        vprint("[dim]Trying str_replace applicator…[/dim]")
        if apply_patch_strreplace(file_path, patch_content, hint_line=hint_line):
            return True
        vprint("[yellow]str_replace failed — trying unified diff…[/yellow]")
    
    if "@@" in patch_content:
        attempted = True
        vprint("[dim]Trying Python unified-diff applicator…[/dim]")
        if apply_patch_python(file_path, patch_content):
            return True
        vprint("[yellow]Python patch failed — falling back to shell patch…[/yellow]")
        return apply_patch_shell(file_path, patch_content)

    if not attempted:
        console.print("[bold red]apply_patch: no recognisable patch format.[/bold red]")
        console.print(f"[dim]  Patch content starts with: {patch_content[:100]!r}...[/dim]")
    return False


def sanitize_generated_code(code: str) -> str:
    """
    Auto-patch known patterns that always crash at runtime.
    Applied before every Manim invocation — defence-in-depth.
    """
    # Rule 1: self.wait(tracker.get_remaining_duration()) → max(0.01, ...) guard
    # Handles both bare call and calls with trailing whitespace/comments.
    code = re.sub(
        r"self\.wait\s*\(\s*tracker\.get_remaining_duration\s*\(\s*\)\s*\)",
        "self.wait(max(0.01, tracker.get_remaining_duration()))",
        code,
    )
    # Rule 2: catch any self.wait(0) or self.wait(0.0) literals too
    code = re.sub(
        r"self\.wait\s*\(\s*0(?:\.0+)?\s*\)",
        "self.wait(0.01)",
        code,
    )
    return code



def write_code_to_file(output_file, code):
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(code)
    with open(output_file, "r", encoding="utf-8") as f:
        written = f.read()
    if written.strip() != code.strip():
        console.print("[bold red]WARNING: File write verification failed![/bold red]")
        return False
    console.print(f"[green]  ✓ Written: {file_link(output_file, output_file)} ({len(code)} bytes)[/green]") if VERBOSE else None
    return True


def ask_for_targeted_rewrite(
    client, output_file, current_code, error_output, error_line,
    audio_instructions, no_audio_warning, model, blueprint,
):
    console.print("[bold magenta]Patch loop stuck — targeted rewrite.[/bold magenta]")
    context = extract_surgical_context(output_file, error_line) if error_line else "(no line info)"
    original_lines = len(current_code.splitlines())
    prompt = f"""
Patching failed multiple times. Fix ONLY the broken lines.

{MANIM_CHEAT_SHEET}
{no_audio_warning}
{audio_instructions}

THE EXACT ERROR:
{extract_traceback_summary(error_output)}

THE BROKEN LINES (>>> = crash line):
{context}

BLUEPRINT:
{blueprint}

Output the COMPLETE fixed Python file (the entire script) in a single ```python block.
Do NOT use a patch.
Target ~{original_lines} lines (±20%).
"""
    resp = safe_generate_content(client, model, prompt, _label=f"{model} [rewrite]")
    matches = list(re.finditer(r"```python\s*(.*?)```", resp.text, re.DOTALL | re.IGNORECASE))
    if not matches:
        console.print("[bold red]Rewrite failure: No ```python block found in response.[/bold red]")
        vprint(f"[dim]  Response start: {resp.text[:100]!r}...[/dim]")
        return None
    new_code = matches[-1].group(1).strip()
    ratio = len(new_code.splitlines()) / max(original_lines, 1)
    if ratio > 1.4 or ratio < 0.5:
        console.print(f"[bold red]Rewrite rejected: {ratio:.0%} size change.[/bold red]")
        return None
    return new_code


# ---------------------------------------------------------------------------
# Vision review
# ---------------------------------------------------------------------------

VISION_CONTENT_BAN = """
━━━ ABSOLUTE RESTRICTIONS ━━━
FORBIDDEN: suggesting content changes, wrong subject flags, different topics, voiceover edits.
ALLOWED: overlaps, clipping, z-order, contrast, label misalignment, frozen animations.
"""


def run_vision_review(client, current_code, latest_vid, output_log, model, blueprint):
    frame_dir = os.path.abspath("media/review_frames")
    frame_paths, frame_timestamps = extract_frames_smart(latest_vid, frame_dir, code=current_code)

    if not frame_paths:
        console.print("[bold red]Vision: no frames extracted.[/bold red]")
        return True, "No frames extracted.", None, [], {}, {}

    duration   = get_video_duration(latest_vid) or 60.0
    animations = parse_animation_log(output_log)
    anim_map   = build_anim_map_from_log(frame_timestamps, animations, duration)

    # ── Verbose frame table ────────────────────────────────────────────────
    table = Table(
        title=f"[bold cyan]Frames → Vision Agent ({model})[/bold cyan]",
        show_lines=True, expand=False
    )
    table.add_column("#",    style="bold cyan", width=4)
    table.add_column("t(s)", style="yellow",    width=7)
    table.add_column("~Animation", style="green", min_width=35)
    table.add_column("Open", style="dim")
    for i, fp in enumerate(frame_paths, 1):
        ts    = frame_timestamps.get(fp, 0)
        info  = anim_map.get(fp)
        label = f"Animation {info[0]}: {info[1]}" if info else "unknown"
        table.add_row(str(i), f"{ts:.1f}", label, file_link(fp, "🖼 view"))
    console.print(table)

    frame_annotation_lines = [
        f"Frame {i:02d}  t={frame_timestamps.get(fp,0):.1f}s  "
        f"~{'Animation ' + str(anim_map[fp][0]) + ': ' + anim_map[fp][1] if fp in anim_map else 'unknown'}"
        for i, fp in enumerate(frame_paths, 1)
    ]

    images = [Image.open(fp) for fp in frame_paths]

    if VERBOSE:
        console.print(Panel(
            f"[bold]Model:[/bold]       {model}\n"
            f"[bold]Frames:[/bold]      {len(images)}\n"
            f"[bold]Video dur:[/bold]   {duration:.1f}s\n"
            f"[bold]Anim events:[/bold] {len(animations)} parsed from log\n"
            f"[bold]Strategy:[/bold]    {'partial-movie' if any('partials' in p for p in frame_paths) else 'code-parse/uniform'}\n"
            f"[bold]Video:[/bold]       {file_link(latest_vid, os.path.basename(latest_vid))}",
            title="[bold magenta]Vision Request[/bold magenta]",
            border_style="magenta",
        ))
    else:
        console.print(f"[bold magenta]👁  Vision review[/bold magenta] — {len(images)} frames, {duration:.1f}s video…")

    vision_prompt = f"""
You are a strict RENDERING QA reviewer for Manim animations.
{VISION_CONTENT_BAN}

━━━ SEVERITY DEFINITIONS & COMMON PROBLEMS ━━━
- [CRITICAL]: Game-breaking or fundamental rendering failures.
  * Scene/Text Rotation: The entire scene or all text is rotated 90/180/270 degrees.
  * Unreadable Overlap: Text/shapes are stacked so densely they cannot be read at all.
  * Black/Flashing Screen: The render is empty, black, or has extreme visual artifacts.
  * Missing Core Elements: Objects defined in the blueprint that are essential for the math are simply not there.
- [MAJOR]: Significant visual bugs that distract or confuse.
  * Geometry Errors: Shapes are rendered wrong (e.g., a jagged "circle", broken lines).
  * Clear Overlaps: Text is overlapping shapes or other text in a way that is clearly unintended.
  * Misalignment: Objects are significantly offset from where they should be (e.g., label far from its target).
  * Clipping: Important elements are partially cut off by the screen edges.
- [MODERATE]: Noticeable aesthetic issues that don't destroy legibility.
  * Spacing/Margins: Inconsistent gaps between objects or uneven margins.
  * Alignment: Objects are slightly off-center or not perfectly aligned with neighbors.
  * Label Precision: Arrows or lines don't point exactly to the intended spot on a Mobject.
  * Font Inconsistency: Sudden jumps in text size or weight that weren't requested.
  * Minor Overlaps: Elements touch or slightly overlap but remain readable.
- [MINOR]: Tiny aesthetic imperfections.
  * Barely Touching: Two objects have a 1-pixel overlap or are just touching.
  * Sub-pixel Jitter: Tiny alignment issues barely visible to the naked eye.
  * Contrast: Color choices are slightly sub-optimal for high-speed viewing.

━━━ DEVELOPER BLUEPRINT ━━━
{blueprint}

━━━ FRAME REFERENCE ━━━
{chr(10).join(frame_annotation_lines)}

━━━ WHAT TO CHECK ━━━
For each frame, evaluate against the BLUEPRINT and the following UI/UX STANDARDS:
1. **The Rule of Halves**: For complex scenes, is the screen split (Left=Context, Right/Center=Active)?
2. **Vertical Alignment**: Are lists and derivations perfectly aligned to their LEFT edge?
3. **Hierarchy**: Is the main content (equations/graphs) prominent and centered/right-center?
4. **Safety Boundaries**: Are objects at least 0.5 units away from all screen edges?
5. **Legibility**: No overlapping text, no font clipping, and high contrast.

━━━ RESPONSE FORMAT ━━━
All good → reply PERFECT (just that word).

Otherwise, provide an ISSUE LIST:
- [LEVEL] Description of bug...
- [LEVEL] Description of bug...

Then, state the overall SEVERITY (the highest level of any issue found):
SEVERITY: MINOR, MODERATE, MAJOR, or CRITICAL

For ANY issue you report, you MUST include a SEARCH/REPLACE patch to fix it:
```
<<<SEARCH
[exact lines verbatim]
>>>REPLACE
[fixed lines]
<<<END
```

Current Code:
```python
{current_code}
```
"""

    vprint(
        f"[dim]  Sending {len(images)} frames + {len(vision_prompt)} char prompt to {model}…[/dim]"
    )
    t_start = time.time()
    v_res   = safe_generate_content(client, model, [vision_prompt, *images], _label=f"{model} [vision]")
    elapsed = time.time() - t_start
    response_text = v_res.text.strip()

    if VERBOSE:
        console.print(Panel(
            f"[bold]Elapsed:[/bold] {elapsed:.1f}s   "
            f"[bold]Response:[/bold] {len(response_text)} chars\n\n"
            + response_text[:2000]
            + ("…\n[dim](truncated)[/dim]" if len(response_text) > 2000 else ""),
            title="[bold magenta]Vision Response[/bold magenta]",
            border_style="magenta",
        ))
    else:
        console.print(f"[dim]  Vision responded in {elapsed:.1f}s.[/dim]")

    if response_text.upper().startswith("PERFECT"):
        return True, "Vision: no issues.", None, "PERFECT", frame_paths, frame_timestamps, anim_map

    sev_match = re.search(r"SEVERITY\s*:\s*(CRITICAL|MAJOR|MODERATE|MINOR)", response_text, re.IGNORECASE)
    severity  = sev_match.group(1).upper() if sev_match else "CRITICAL"

    patch = None
    m = re.search(r"```[^\n]*\n(.*?)```", response_text, re.DOTALL)
    raw = m.group(1) if m else response_text
    if "<<<SEARCH" in raw:
        patch = raw

    report = re.sub(r"```.*?```", "", response_text, flags=re.DOTALL).strip()
    return False, report, patch, severity, frame_paths, frame_timestamps, anim_map


def print_vision_report(report, frame_paths, frame_timestamps, anim_map):
    console.print(
        Panel(report, title="[bold red]Vision — Issues Found[/bold red]",
              border_style="red", padding=(1, 2))
    )


# ---------------------------------------------------------------------------
# Error-history helpers
# ---------------------------------------------------------------------------

def _push_error(history: list, summary: str, patch=None, maxlen: int = 4):
    if history and history[-1]["error_summary"].strip() == summary.strip():
        history[-1]["patch_attempted"] = patch
        return
    history.append({"error_summary": summary, "patch_attempted": patch})
    while len(history) > maxlen:
        history.pop(0)


def sanitize_patch(patch: str) -> str:
    cleaned = []
    for line in patch.splitlines():
        line = line.rstrip("\r")
        line = re.sub(r"^\d+:\s*(?=[ +\-@\\])", "", line)
        cleaned.append(line)
    result = "\n".join(cleaned)
    return result if result.endswith("\n") else result + "\n"


def _normalise_diff_headers(patch: str, output_file: str) -> str:
    for old, new in [
        ("--- a/output_scene.py", f"--- a/{output_file}"),
        ("+++ b/output_scene.py", f"+++ b/{output_file}"),
        ("--- current_code.py",   f"--- a/{output_file}"),
        ("+++ fixed_code.py",     f"+++ b/{output_file}"),
        ("--- MyScene.py",        f"--- a/{output_file}"),
        ("+++ MyScene.py",        f"+++ b/{output_file}"),
    ]:
        patch = patch.replace(old, new)
    return patch


def _extract_lines_for_search(file_path, error_line, context_before=6, context_after=6):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return None, None, None
    
    start = max(0, error_line - context_before - 1)
    end = min(len(lines), error_line + context_after)
    extracted = lines[start:end]
    vprint(f"[dim]  Extracted {len(extracted)} lines for SEARCH block (lines {start+1}–{end}).[/dim]")
    return extracted, start + 1, end


def _build_fix_prompt(
    current_code, traceback_summary, surgical_context,
    search_lines, search_start, history_string, blueprint,
    no_audio_warning, audio_instructions,
):
    # Standard patch format instruction — always used now.
    output_format = """
Output a PATCH to fix the code.
Format:
```
<<<SEARCH
[EXACT copy of the code to replace]
[Must match the file content character-for-character]
[Include all indentation and whitespace]
[NO "..." or comments like "# rest of code"]
>>>REPLACE
[The fixed code]
<<<END
```
"""

    focus_section = ""
    if search_lines:
        search_text = "".join(search_lines)
        focus_section = f"""
━━━ FOCUS AREA (Context around crash) ━━━
Lines {search_start}–{search_start + len(search_lines) - 1}:
```
{search_text}```
"""

    return f"""Expert Manim developer. Fix this crash.

{MANIM_CHEAT_SHEET}
{no_audio_warning}
{audio_instructions}

━━━ BLUEPRINT ━━━
{blueprint}

━━━ ERROR ━━━
{traceback_summary}

━━━ BROKEN LINES (>>> = crash) ━━━
{surgical_context}
{focus_section}
━━━ PAST FAILURES ━━━
{history_string if history_string.strip() else "(none)"}

━━━ FULL FILE ━━━
```python
{current_code}
```
{output_format}"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Standalone Auto-Fixing Manim Pipeline")
    parser.add_argument("--prompt",             type=str)
    parser.add_argument("--output",             type=str, default="output_scene.py")
    parser.add_argument("--no-audio",           action="store_true",
                        help="Disable voiceover")
    parser.add_argument("--audio-model",        type=str, default=None, metavar="MODEL",
                        help=(
                            "Use Gemini TTS instead of gTTS. Implies audio. "
                            "E.g.: gemini-2.5-flash-preview-tts  |  gemini-2.5-pro-preview-tts"
                        ))
    parser.add_argument("--audio-voice",        type=str, default="Kore", metavar="VOICE",
                        help="Gemini TTS voice: Kore(calm), Charon(auth), Fenrir(energetic), Aoede(warm). Default: Kore")
    parser.add_argument("--vision",             action="store_true")
    parser.add_argument("--skip-gen",           action="store_true")
    parser.add_argument("--gpu",                action="store_true")
    parser.add_argument("--model",              type=str, default="gemini-3-flash-preview")
    parser.add_argument("--vision-model",       type=str, default=None)
    parser.add_argument("--max-retries",        type=int, default=128)
    parser.add_argument("--max-vision-retries", type=int, default=128)
    parser.add_argument("--vision-threshold",   type=int, default=1, choices=[0, 1, 2, 3, 4],
                        help=(
                            "Acceptance threshold for visual issues (hits). Issues at or below this level are ignored.\n"
                            "0: Accept NOTHING (fix everything including tiny aesthetic flaws).\n"
                            "1: Accept MINOR (tiny overlaps, sub-pixel jitter, sub-optimal contrast).\n"
                            "2: Accept MODERATE (spacing inconsistency, imprecise labels, font size jumps).\n"
                            "3: Accept MAJOR (geometry errors, significant overlaps, misalignment, clipping).\n"
                            "4: Accept CRITICAL (whole scene rotated, unreadable overlap, missing core objects)."
                        ))
    parser.add_argument("--rewrite-threshold",  type=int, default=8)
    parser.add_argument("--verbose",             action="store_true",
                        help="Show full agent output, Manim stdout, and debug prints")
    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    # Audio defaults to True unless --no-audio is passed.
    # If --audio-model is passed, it overrides any --no-audio.
    use_audio        = (not args.no_audio) or bool(args.audio_model)
    use_gemini_tts   = bool(args.audio_model)
    gemini_tts_model = args.audio_model or ""
    gemini_tts_voice = args.audio_voice

    output_file  = args.output
    fix_model    = args.model
    vision_model = args.vision_model or args.model
    blueprint    = ""

    audio_instructions = ""
    if use_gemini_tts:
        audio_instructions = f"""
CRITICAL AUDIO SYNC AND HIGHLIGHTING (Gemini TTS):
1. Imports:
   from manim_voiceover import VoiceoverScene
   from gemini_tts_service import GeminiTTSService
2. Inherit from VoiceoverScene.
3. In construct():
   self.set_speech_service(GeminiTTSService(model="{gemini_tts_model}", voice="{gemini_tts_voice}"))
4. SYNC: BREAK narration into granular chunks (1-2 sentences). 
   Wrap EACH chunk in: `with self.voiceover(text="...") as tracker:`
   Animations inside must match the audio.
   ALWAYS end each chunk with: `self.wait(tracker.get_remaining_duration())`
5. HIGHLIGHTING (VGROUP DECOMPOSITION): Do NOT use character indexing (e.g. `eq[0][3:5]`). It crashes.
   Instead, build equations as VGroups of smaller MathTex objects and highlight the specific object.
   Example: `eq = VGroup(MathTex("x^2"), MathTex("+"), MathTex("y")).arrange(RIGHT)` -> `self.play(Indicate(eq[0]))`
NOTE: gemini_tts_service.py lives in the same directory — do NOT redefine it.
"""
    elif use_audio:
        audio_instructions = """
CRITICAL AUDIO SYNC AND HIGHLIGHTING:
1. from manim_voiceover import VoiceoverScene
   from manim_voiceover.services.gtts import GTTSService
2. Inherit from VoiceoverScene.
3. self.set_speech_service(GTTSService(lang="en"))
4. SYNC: BREAK narration into granular chunks (1-2 sentences). 
   Wrap EACH chunk in: `with self.voiceover(text="...") as tracker:`
   Animations inside must match the audio.
   ALWAYS end each chunk with: `self.wait(tracker.get_remaining_duration())`
5. HIGHLIGHTING (VGROUP DECOMPOSITION): Do NOT use character indexing (e.g. `eq[0][3:5]`). It crashes.
   Instead, build equations as VGroups of smaller MathTex objects and highlight the specific object.
   Example: `eq = VGroup(MathTex("x^2"), MathTex("+"), MathTex("y")).arrange(RIGHT)` -> `self.play(Indicate(eq[0]))`
"""

    no_audio_warning = (
        "IMPORTANT: No audio. Do NOT add VoiceoverScene, GTTSService, or voiceover blocks."
        if not use_audio else ""
    )

    try:
        client = genai.Client()
    except Exception as e:
        console.print(f"[bold red]Failed to init google.genai: {e}[/bold red]")
        return

    # Clear stale or corrupted audio cache before starting.
    if use_audio and not args.skip_gen:
        purge_voiceover_cache()

    # ── Initial generation ─────────────────────────────────────────────────
    if not args.skip_gen:
        pipeline = IntegratedPipeline()
        pipeline.swarm_model = fix_model   # track agent calls under the same model name
        raw_prompt = args.prompt if args.prompt else (
            open("curriculum_prompt.txt").read()
            if os.path.exists("curriculum_prompt.txt")
            else "Explain the Pythagorean Theorem visually"
        )
        full_prompt = raw_prompt + (f"\n\n{audio_instructions}" if use_audio else "")

        try:
            console.print("[bold blue]Running initial pipeline swarm…[/bold blue]")
            result, blueprint = pipeline.run_and_capture(full_prompt, audio_instructions=audio_instructions)
            with open("blueprint.txt", "w", encoding="utf-8") as f:
                f.write(blueprint)

            code_matches = list(re.finditer(r"```python\s*(.*?)```", str(result), re.DOTALL | re.IGNORECASE))
            if not code_matches:
                console.print("\n[bold red]FATAL: No Python code block in pipeline output.[/bold red]")
                return
            final_code = code_matches[-1].group(1).strip()
            valid, err = check_syntax(final_code)
            if not valid:
                console.print(f"[bold red]Generated code has syntax errors: {err}[/bold red]")
                return
            write_code_to_file(output_file, final_code)

            # Safety net: if CodeGenerator still wrote GTTSService despite instructions,
            # patch it now. This catches cases where the model hallucinated old patterns.
            if use_gemini_tts:
                _safetynet_style = build_style_context_from_blueprint(blueprint)
                patched = patch_scene_for_gemini_tts(output_file, gemini_tts_model, gemini_tts_voice, _safetynet_style)
                if patched:
                    console.print("[bold yellow]  Safety-net: CodeGenerator used GTTSService — auto-patched to GeminiTTSService.[/bold yellow]")
                else:
                    console.print("[dim]  Safety-net: GeminiTTSService confirmed in generated code.[/dim]")
        except Exception as e:
            console.print(f"[bold red]Generation Swarm Failed: {e}[/bold red]")
            return
    else:
        blueprint = (
            open("blueprint.txt").read()
            if os.path.exists("blueprint.txt")
            else "(No blueprint — evaluating on aesthetics only.)"
        )
        vprint(f"[dim]Loaded blueprint ({len(blueprint)} chars).[/dim]")

    # ── Gemini TTS setup ───────────────────────────────────────────────────
    if use_gemini_tts:
        output_dir = os.path.dirname(os.path.abspath(output_file))
        write_gemini_tts_service(output_dir)
        style_ctx = build_style_context_from_blueprint(blueprint)

        audio_instructions = f"""
CRITICAL AUDIO REQUIREMENT (Gemini TTS):
1. Imports:
   from manim_voiceover import VoiceoverScene
   from gemini_tts_service import GeminiTTSService
2. Inherit from VoiceoverScene.
3. In construct():
   self.set_speech_service(GeminiTTSService(
       model="{gemini_tts_model}",
       voice="{gemini_tts_voice}",
       style_context="{style_ctx[:120].replace('"', "'")}",
   ))
4. Wrap ALL animations: `with self.voiceover(text="...") as tracker:`
NOTE: gemini_tts_service.py is in the same directory.
"""

        console.print(Panel(
            f"[bold]TTS Model:[/bold]  {gemini_tts_model}\n"
            f"[bold]Voice:[/bold]      {gemini_tts_voice}\n"
            f"[bold]Style ctx:[/bold]  {style_ctx[:120]}…\n"
            f"[bold]Service:[/bold]    {file_link(os.path.join(output_dir, 'gemini_tts_service.py'), 'gemini_tts_service.py')}",
            title="[bold cyan]Gemini TTS Configuration[/bold cyan]",
            border_style="cyan",
        ))

        if args.skip_gen:
            console.print("[bold yellow]--skip-gen detected: checking scene for stale audio service…[/bold yellow]")
            patch_scene_for_gemini_tts(output_file, gemini_tts_model, gemini_tts_voice, style_ctx)

    # ── Fix loop ───────────────────────────────────────────────────────────
    max_retries                = args.max_retries
    max_vision_retries         = args.max_vision_retries
    rewrite_threshold          = args.rewrite_threshold
    error_history: list[dict]  = []
    consecutive_patch_failures = 0
    last_known_error_line      = None
    last_output_log: list[str] = []
    vision_attempts            = 0

    attempt_durations: list[float] = []   # track per-attempt render times for ETA

    for attempt in range(max_retries):
        attempt_start = time.time()
        _eta_str = ""
        if attempt_durations:
            avg = sum(attempt_durations) / len(attempt_durations)
            remaining_est = avg * (max_retries - attempt)
            mins, secs = divmod(int(remaining_est), 60)
            _eta_str = f"  [dim](avg {avg:.0f}s/attempt, ~{mins}m{secs:02d}s remaining if all retries used)[/dim]"

        console.rule(
            f"[bold yellow]Attempt {attempt + 1} / {max_retries}[/bold yellow]{_eta_str}"
        )

        if not os.path.exists(output_file):
            console.print(f"[bold red]File {output_file} not found.[/bold red]")
            break

        with open(output_file, "r", encoding="utf-8") as f:
            current_code = f.read()

        # Auto-fix known zero-duration crash patterns before every render attempt
        sanitized = sanitize_generated_code(current_code)
        if sanitized != current_code:
            console.print("[cyan]  Auto-sanitizer: patched zero-duration wait(s).[/cyan]")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(sanitized)
            current_code = sanitized

        current_hash = file_hash(output_file)
        vprint(
            f"[dim]  {file_link(output_file, os.path.basename(output_file))}  "
            f"hash={current_hash[:12]}  {len(current_code)} bytes[/dim]"
        )

        is_valid, syntax_err = check_syntax(current_code)
        error_output = None

        if not is_valid:
            error_output = syntax_err
            console.print(f"[bold red]Syntax Error:[/bold red]\n{syntax_err}")
            last_known_error_line = None
        else:
            media_dir = os.path.abspath("media")
            os.makedirs(media_dir, exist_ok=True)

            manim_cmd = ["manim", "-ql", "--media_dir", media_dir]
            if args.gpu:
                manim_cmd.extend(["--renderer=opengl", "--write_to_movie"])
            manim_cmd.append(output_file)
            scene_class = _extract_scene_class(output_file)
            if scene_class:
                manim_cmd.append(scene_class)
                vprint(f"[dim]Scene class: {scene_class}[/dim]")

            process = subprocess.Popen(
                manim_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
            )
            output_log, start_time, killed = [], time.time(), False

            if VERBOSE:
                # Verbose: stream all output directly
                n_anims_verbose = count_play_calls(current_code)
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        sys.stdout.write(line)
                        output_log.append(line)
                        lower = line.lower()
                        if any(k in lower for k in ("voiceover", "tts", "speech", "generating audio", "cached")):
                            console.print(f"[cyan]  🔊 {line.rstrip()}[/cyan]")
                        anim_v = re.search(r"animation\s+(\d+)", lower)
                        if anim_v:
                            idx = int(anim_v.group(1))
                            console.print(f"[dim]  ▶ Animation {idx} / ~{n_anims_verbose}[/dim]")
                    if time.time() - start_time > 240:
                        console.print("\n[bold red]HANG: Killing process…[/bold red]")
                        process.kill()
                        remaining = process.stdout.read()
                        if remaining:
                            output_log.append(remaining)
                        killed = True
                        break
            else:
                # Non-verbose: show a real progress bar (animation X / N_estimated)
                n_anims = count_play_calls(current_code)
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(bar_width=28),
                    MofNCompleteColumn(),
                    TextColumn("·"),
                    TimeElapsedColumn(),
                    console=console,
                    transient=True,
                ) as progress:
                    render_task = progress.add_task(
                        f"[cyan]Rendering[/cyan]",
                        total=n_anims,
                        completed=0,
                    )
                    current_anim = 0
                    while True:
                        line = process.stdout.readline()
                        if not line and process.poll() is not None:
                            break
                        if line:
                            output_log.append(line)
                            lower = line.lower()
                            # Surface TTS lines even in non-verbose
                            if any(k in lower for k in ("voiceover", "tts", "speech", "generating audio", "cached")):
                                progress.update(render_task, description=f"[cyan]🔊 TTS[/cyan] {line.rstrip()[:55]}")
                            else:
                                anim_m = re.search(r"animation\s+(\d+)", lower)
                                if anim_m:
                                    current_anim = int(anim_m.group(1))
                                    # Manim animation indices start at 0; cap at our estimate
                                    clamped = min(current_anim, n_anims)
                                    progress.update(
                                        render_task,
                                        completed=clamped,
                                        description=f"[cyan]Rendering[/cyan]",
                                    )
                        if time.time() - start_time > 240:
                            progress.stop()
                            console.print("\n[bold red]HANG: Killing process…[/bold red]")
                            process.kill()
                            remaining = process.stdout.read()
                            if remaining:
                                output_log.append(remaining)
                            killed = True
                            break

            try:
                remaining = process.stdout.read()
                if remaining:
                    if VERBOSE:
                        sys.stdout.write(remaining)
                    output_log.extend(remaining.splitlines(keepends=True))
            except Exception:
                pass

            last_output_log = output_log

            # Show generated audio files
            if use_audio and VERBOSE:
                audio_files = (
                    glob.glob("media/voiceovers/**/*.wav", recursive=True) +
                    glob.glob("media/voiceovers/**/*.mp3", recursive=True)
                )
                if audio_files:
                    aud_table = Table(
                        title=f"[bold cyan]Generated Audio ({len(audio_files)} files)[/bold cyan]",
                        show_lines=False, expand=False
                    )
                    aud_table.add_column("File", style="cyan")
                    aud_table.add_column("Dur", style="yellow", width=6)
                    aud_table.add_column("Open", style="dim")
                    for af in sorted(audio_files)[:20]:
                        dur = get_video_duration(af)
                        dur_str = f"{dur:.1f}s" if dur else "?"
                        aud_table.add_row(
                            os.path.basename(af), dur_str,
                            file_link(af, "🔊 listen")
                        )
                    console.print(aud_table)

            if killed:
                error_output = "TIMEOUT: Code hung >4 minutes.\n\n" + "".join(output_log[-20:])
            elif process.returncode != 0:
                error_output = "".join(output_log[-60:])
                console.print(f"\n[bold red]CRASH: exit code {process.returncode}[/bold red]")
                new_err_line = extract_error_line(error_output)
                if new_err_line:
                    last_known_error_line = new_err_line
                    console.print(f"[cyan]  Error at source line {last_known_error_line}[/cyan]")
            else:
                console.print("[bold green]Rendering successful![/bold green]")
                last_known_error_line  = None
                consecutive_patch_failures = 0

                if VERBOSE:
                    console.print("[dim]── Last Manim output ──[/dim]")
                    for l in output_log[-15:]:
                        console.print(f"[dim]{l.rstrip()}[/dim]")
                    console.print("[dim]──────────────────────[/dim]")

                latest_vid = get_latest_video(output_log)
                if not latest_vid:
                    console.print("[bold yellow]⚠ No video file found.[/bold yellow]")

                if args.vision and latest_vid:
                    if vision_attempts >= max_vision_retries:
                        console.print(Panel(
                            f"[bold yellow]Vision: max attempts ({max_vision_retries}) — accepting.[/bold yellow]",
                            border_style="yellow",
                        ))
                        console.print(f"\n[bold green]Final video:[/bold green] {file_link(latest_vid)}")
                        break

                    console.print("[bold magenta]Running vision review…[/bold magenta]")
                    is_perfect, report, vision_patch, severity, frame_paths, frame_timestamps, anim_map = \
                        run_vision_review(client, current_code, latest_vid, last_output_log, vision_model, blueprint)

                    if is_perfect:
                        console.print(Panel("[bold green]Vision: PERFECT[/bold green]", border_style="green"))
                        console.print(f"\n[bold green]Final video:[/bold green] {file_link(latest_vid)}")
                        break

                    print_vision_report(report, frame_paths, frame_timestamps, anim_map)
                    vision_attempts += 1

                    # Severity check logic
                    SEV_MAP = {"MINOR": 1, "MODERATE": 2, "MAJOR": 3, "CRITICAL": 4}
                    current_sev_val = SEV_MAP.get(severity, 4)
                    
                    if current_sev_val <= args.vision_threshold:
                        console.print(Panel(
                            f"[yellow]Vision: severity {severity} is within threshold {args.vision_threshold} — accepting.[/yellow]",
                            border_style="yellow"
                        ))
                        console.print(f"\n[bold green]Final video:[/bold green] {file_link(latest_vid)}")
                        break

                    if vision_patch:
                        console.print("[bold yellow]Applying vision patch…[/bold yellow]")
                        if VERBOSE:
                            console.print(Syntax(vision_patch, "text", theme="monokai", line_numbers=True))
                        success = apply_patch(output_file, vision_patch, hint_line=None)
                        if success:
                            console.print("[bold green]✓ Vision patch applied.[/bold green]")
                            consecutive_patch_failures = 0
                        else:
                            console.print("[bold red]✗ Vision patch failed.[/bold red]")
                            consecutive_patch_failures += 1
                        _push_error(error_history, f"VISUAL BUGS:\n{report}", vision_patch)
                        continue
                    else:
                        console.print("[bold red]Vision gave no patch — feeding to fix loop.[/bold red]")
                        error_output = "VISUAL RENDERING BUGS:\n\n" + report
                else:
                    if latest_vid:
                        console.print(f"\n[bold green]Pipeline finished![/bold green] {file_link(latest_vid)}")
                        try:
                            subprocess.Popen(["xdg-open" if sys.platform.startswith("linux") else
                                              "open" if sys.platform == "darwin" else "start", latest_vid])
                        except Exception:
                            pass
                    else:
                        console.print("\n[bold green]Pipeline finished![/bold green] (no video path)")
                    break

        # Track how long this attempt took for ETA estimation
        attempt_durations.append(time.time() - attempt_start)

        # Always show the running API usage summary
        console.print(stats.render_table())

        if error_output is None:
            continue
        if attempt == max_retries - 1:
            console.print("[bold red]Max retries exhausted.[/bold red]")
            break

        err_line          = extract_error_line(error_output, output_file)
        traceback_summary = extract_traceback_summary(error_output)
        surgical_context  = extract_surgical_context(output_file, err_line) if err_line else "(no line number)"

        _push_error(error_history, traceback_summary)

        history_string = ""
        for i, h in enumerate(error_history):
            history_string += f"\n--- PAST FAILURE {i + 1} ---\nError:\n{h['error_summary']}\n"
            if h.get("patch_attempted"):
                history_string += f"Patch tried:\n{h['patch_attempted']}\n"

        if consecutive_patch_failures >= rewrite_threshold:
            new_code = ask_for_targeted_rewrite(
                client, output_file, current_code, error_output, err_line,
                audio_instructions, no_audio_warning, fix_model, blueprint,
            )
            if new_code:
                valid, err = check_syntax(new_code)
                if valid:
                    write_code_to_file(output_file, new_code)
                    console.print("[bold green]Targeted rewrite applied.[/bold green]")
                    consecutive_patch_failures = 0
                    last_known_error_line = None
                    continue
                else:
                    console.print(f"[red]Rewrite syntax error: {err}[/red]")
            else:
                console.print("[bold red]Targeted rewrite returned no code.[/bold red]")

        if err_line:
            search_lines, search_start, search_end = _extract_lines_for_search(
                output_file, err_line, context_before=6, context_after=6
            )
        else:
            search_lines, search_start, search_end = None, None, None

        fix_prompt = _build_fix_prompt(
            current_code, traceback_summary, surgical_context,
            search_lines, search_start,
            history_string, blueprint,
            no_audio_warning, audio_instructions if use_audio else "",
        )

        console.print(f"[cyan]Requesting fix from [bold]{fix_model}[/bold]…[/cyan]")
        fix_response  = safe_generate_content(client, fix_model, fix_prompt, _label=f"{fix_model} [fix]")
        response_text = fix_response.text

        patch_content      = None
        patch_display_lang = "text"

        # (Removed apply_patch_linerange block — now relying on explicit SEARCH/REPLACE from LLM)

        if patch_content is None:
            if "<<<SEARCH" in response_text:
                m = re.search(r"```[^\n]*\n(.*?)```", response_text, re.DOTALL)
                raw = m.group(1) if m else response_text
                if "<<<SEARCH" in raw:
                    patch_content = raw
                    vprint("[yellow]Using model-generated SEARCH block (fallback).[/yellow]")
            if patch_content is None:
                m = re.search(r"```diff\s*(.*?)```", response_text, re.DOTALL | re.IGNORECASE)
                if m:
                    patch_content      = _normalise_diff_headers(sanitize_patch(m.group(1).strip()), output_file)
                    patch_display_lang = "diff"

        if patch_content:
            if patch_display_lang != "text" and VERBOSE:
                console.print(f"[bold yellow]Patch ({patch_display_lang}):[/bold yellow]")
                console.print(Syntax(patch_content, patch_display_lang, theme="monokai", line_numbers=True))
            success = apply_patch(output_file, patch_content, hint_line=search_start)
            if success:
                console.print("[bold green]✓ Patch applied.[/bold green]")
                # Do NOT reset consecutive_patch_failures here; only reset on successful RENDER.
                # consecutive_patch_failures = 0 
                error_history[-1]["patch_attempted"] = patch_content
                if search_start:
                    last_known_error_line = search_start
            else:
                console.print("[bold red]✗ Patch failed.[/bold red]")
                consecutive_patch_failures += 1
        else:
            has_python = "```python" in response_text
            console.print(f"[bold red]No recognisable patch block returned (Python block present: {has_python}).[/bold red]")
            console.print(f"[dim]  Response started with: {response_text.strip()[:140]!r}...[/dim]")
            if has_python and consecutive_patch_failures < rewrite_threshold - 1:
                console.print(f"[dim]  (Note: rewrite threshold is {rewrite_threshold}; current failure count: {consecutive_patch_failures})[/dim]")
            if VERBOSE:
                console.print(response_text)
            consecutive_patch_failures += 1


if __name__ == "__main__":
    main()
