#!/usr/bin/env python3
"""Tkinter UI for mkmapdiary - A travel journal generator."""

import io
import os
import pathlib
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from tkinter import filedialog, scrolledtext, ttk
from typing import Any

import click
import darkdetect
import sv_ttk

from .commands.build import build as build_command
from .commands.calibrate import file as calibrate_file_command
from .commands.config import config as config_command
from .commands.generate_demo import generate_demo as generate_demo_command
from .commands.inspect import inspect as inspect_command

# Setup logging


def capture_command_output(
    func: Callable[..., Any], *args: Any, **kwargs: Any
) -> tuple[str, int]:
    """Capture output from a Click command."""
    output_buffer = io.StringIO()
    error_buffer = io.StringIO()

    try:
        with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
            func(*args, **kwargs)

        output = output_buffer.getvalue()
        error = error_buffer.getvalue()

        if error:
            output += "\n" + error

        return output, 0
    except SystemExit as e:
        output = output_buffer.getvalue()
        error = error_buffer.getvalue()

        if error:
            output += "\n" + error

        return output, e.code if isinstance(e.code, int) else 1
    except Exception as e:
        output = output_buffer.getvalue()
        error = error_buffer.getvalue()

        error_msg = f"\nError: {str(e)}"
        if error:
            output += "\n" + error
        output += error_msg

        return output, 1


class MkmapdiaryUI:
    """Tkinter UI for mkmapdiary."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("mkmapdiary - Travel Journal Generator")

        # Theme-aware colors for better contrast
        self.colors = {
            "ready": "#808080",  # Medium gray - visible in both modes
            "success": "#00AA00",  # Brighter green - visible in both modes
            "error": "#FF0000",  # Bright red - visible in both modes
            "progress": "#FF8800",  # Bright orange - visible in both modes
            "info": "#6B6B6B",  # Dark gray for info text
        }

        # Set window size: appropriate width with full height
        screen_height = root.winfo_screenheight()
        window_width = 1000
        x_position = 50
        y_position = 0

        # Set temporary geometry and update to get actual window decoration size
        self.root.geometry(f"{window_width}x{screen_height}+{x_position}+{y_position}")
        self.root.update_idletasks()

        # Calculate decoration height (title bar + borders)
        decoration_height = self.root.winfo_rooty() - y_position
        window_height = screen_height - decoration_height

        # Set final geometry with corrected height
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")

        # Track operation states
        self.build_running = False
        self.demo_running = False
        self.calibrate_running = False
        self.config_running = False
        self.inspect_running = False

        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Create tabs
        self.create_build_tab()
        self.create_demo_tab()
        self.create_calibrate_tab()
        self.create_config_tab()
        self.create_inspect_tab()
        self.create_help_tab()

    def browse_directory(self, entry_widget: ttk.Entry) -> None:
        """Open directory picker and update entry widget."""
        current = entry_widget.get()
        initial_dir = (
            current
            if current and pathlib.Path(current).exists()
            else str(pathlib.Path.cwd())
        )

        directory = filedialog.askdirectory(
            title="Select Directory", initialdir=initial_dir
        )

        if directory:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, directory)
            # Update browser button state if this is the dist directory
            if hasattr(self, "dist_dir") and entry_widget == self.dist_dir:
                self.update_browser_button_state()
            # Also update if source dir changes (affects default dist dir)
            if hasattr(self, "source_dir") and entry_widget == self.source_dir:
                self.update_browser_button_state()

    def browse_file(self, entry_widget: ttk.Entry) -> None:
        """Open file picker and update entry widget."""
        current = entry_widget.get()
        initial_dir = (
            str(pathlib.Path(current).parent)
            if current and pathlib.Path(current).exists()
            else str(pathlib.Path.cwd())
        )

        filename = filedialog.askopenfilename(
            title="Select File", initialdir=initial_dir
        )

        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def toggle_expert_options(self) -> None:
        """Toggle the visibility of expert options in the Build tab."""
        if self.expert_options_visible.get():
            # Hide expert options
            self.expert_options_container.pack_forget()
            self.expert_toggle_btn.config(text="▶ Show Expert Options")
            self.expert_options_visible.set(False)
        else:
            # Show expert options
            self.expert_options_container.pack(
                fill="x", pady=5, before=self.build_button_frame
            )
            self.expert_toggle_btn.config(text="▼ Hide Expert Options")
            self.expert_options_visible.set(True)

    def get_dist_directory(self) -> pathlib.Path | None:
        """Get the distribution directory path."""
        dist_dir = self.dist_dir.get()
        if dist_dir:
            return pathlib.Path(dist_dir)

        source_dir = self.source_dir.get()
        if source_dir:
            source_path = pathlib.Path(source_dir)
            return source_path.with_name(source_path.name + "_dist")

        return None

    def update_browser_button_state(self) -> None:
        """Update the browser button state based on whether index.html exists."""
        if self.build_running:
            self.browser_button.config(state="disabled")
            return

        dist_dir = self.get_dist_directory()
        if dist_dir and dist_dir.exists():
            index_path = dist_dir / "index.html"
            if index_path.exists():
                self.browser_button.config(state="normal")
                return

        self.browser_button.config(state="disabled")

    def open_in_browser(self) -> None:
        """Open the generated diary in the default web browser."""
        dist_dir = self.get_dist_directory()
        if dist_dir:
            index_path = dist_dir / "index.html"
            if index_path.exists():
                webbrowser.open(index_path.as_uri())

    def create_build_tab(self) -> None:
        """Create the Build Diary tab."""
        build_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(build_frame, text="Build Diary")

        # Title
        title = ttk.Label(
            build_frame,
            text="Build a map diary from your travel data",
            font=("Helvetica", 12, "bold"),
        )
        title.pack(pady=10)

        # Source Directory
        src_frame = ttk.LabelFrame(build_frame, text="Source Directory *", padding=10)
        src_frame.pack(fill="x", pady=5)

        src_entry_frame = ttk.Frame(src_frame)
        src_entry_frame.pack(fill="x")

        self.source_dir = ttk.Entry(src_entry_frame)
        self.source_dir.pack(side="left", fill="x", expand=True)
        # Track changes to update browser button state (affects default dist dir)
        self.source_dir.bind(
            "<KeyRelease>", lambda e: self.update_browser_button_state()
        )
        self.source_dir.bind("<FocusOut>", lambda e: self.update_browser_button_state())

        ttk.Button(
            src_entry_frame,
            text="Browse...",
            command=lambda: self.browse_directory(self.source_dir),
        ).pack(side="left", padx=(5, 0))

        ttk.Label(
            src_frame,
            text="Directory containing GPS tracks, photos, and notes",
            foreground=self.colors["info"],
        ).pack(anchor="w")

        # Distribution Directory
        dist_frame = ttk.LabelFrame(
            build_frame, text="Distribution Directory (optional)", padding=10
        )
        dist_frame.pack(fill="x", pady=5)

        dist_entry_frame = ttk.Frame(dist_frame)
        dist_entry_frame.pack(fill="x")

        self.dist_dir = ttk.Entry(dist_entry_frame)
        self.dist_dir.pack(side="left", fill="x", expand=True)
        # Track changes to update browser button state
        self.dist_dir.bind("<KeyRelease>", lambda e: self.update_browser_button_state())
        self.dist_dir.bind("<FocusOut>", lambda e: self.update_browser_button_state())

        ttk.Button(
            dist_entry_frame,
            text="Browse...",
            command=lambda: self.browse_directory(self.dist_dir),
        ).pack(side="left", padx=(5, 0))

        ttk.Label(
            dist_frame,
            text="Output directory (defaults to the Source Directory with '_dist' suffix)",
            foreground=self.colors["info"],
        ).pack(anchor="w")

        # Expert Options (collapsible)
        expert_toggle_frame = ttk.Frame(build_frame)
        expert_toggle_frame.pack(fill="x", pady=5)

        self.expert_options_visible = tk.BooleanVar(value=False)
        self.expert_toggle_btn = ttk.Button(
            expert_toggle_frame,
            text="▶ Show Expert Options",
            command=self.toggle_expert_options,
        )
        self.expert_toggle_btn.pack(anchor="w")

        # Expert Options Container (hidden by default)
        self.expert_options_container = ttk.Frame(build_frame)
        # Don't pack initially - will be shown when toggled

        options_frame = ttk.LabelFrame(
            self.expert_options_container, text="Expert Options", padding=10
        )
        options_frame.pack(fill="x", pady=5)

        self.persistent_build = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame,
            text="Persistent Build Directory",
            variable=self.persistent_build,
        ).pack(anchor="w")

        self.always_execute = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame,
            text="Always Execute (rebuild everything)",
            variable=self.always_execute,
        ).pack(anchor="w")

        self.debug_fast = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame, text="Debug Fast Mode", variable=self.debug_fast
        ).pack(anchor="w")

        self.no_cache = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame, text="Disable Cache", variable=self.no_cache
        ).pack(anchor="w")

        # Build Directory
        ttk.Label(options_frame, text="Build Directory (optional):").pack(
            anchor="w", pady=(5, 0)
        )
        self.build_dir = ttk.Entry(options_frame)
        self.build_dir.pack(fill="x")

        # Number of processes
        proc_frame = ttk.Frame(options_frame)
        proc_frame.pack(fill="x", pady=5)
        ttk.Label(proc_frame, text="Parallel Processes:").pack(side="left")
        self.num_processes = tk.IntVar(value=os.cpu_count() or 4)
        ttk.Spinbox(
            proc_frame,
            from_=1,
            to=os.cpu_count() or 16,
            textvariable=self.num_processes,
            width=10,
        ).pack(side="left", padx=5)

        # Config params
        ttk.Label(options_frame, text="Configuration Parameters (one per line):").pack(
            anchor="w", pady=(5, 0)
        )
        self.config_params = scrolledtext.ScrolledText(options_frame, height=4)
        self.config_params.pack(fill="x")

        # Status and Build button
        self.build_button_frame = ttk.Frame(build_frame)
        self.build_button_frame.pack(pady=10)

        self.build_button = ttk.Button(
            self.build_button_frame, text="🚀 Build Diary", command=self.run_build
        )
        self.build_button.pack(side="left", padx=5)

        self.browser_button = ttk.Button(
            self.build_button_frame,
            text="🌐 Show in Browser",
            command=self.open_in_browser,
            state="disabled",
        )
        self.browser_button.pack(side="left", padx=5)

        self.build_status_label = ttk.Label(
            self.build_button_frame,
            text="⚪ Ready",
            font=("", 10, "bold"),
            foreground=self.colors["ready"],
        )
        self.build_status_label.pack(side="left", padx=10)

        self.build_progress = ttk.Progressbar(
            self.build_button_frame, mode="indeterminate", length=200
        )
        # Don't pack initially - will be shown when building starts

        # Output
        output_frame = ttk.LabelFrame(build_frame, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, pady=5)

        self.build_output = scrolledtext.ScrolledText(
            output_frame, height=20, wrap=tk.WORD
        )
        self.build_output.pack(fill="both", expand=True)

    def create_demo_tab(self) -> None:
        """Create the Generate Demo tab."""
        demo_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(demo_frame, text="Generate Demo")

        title = ttk.Label(
            demo_frame,
            text="Generate demo data for testing",
            font=("Helvetica", 12, "bold"),
        )
        title.pack(pady=10)

        info = ttk.Label(
            demo_frame,
            text="This creates a sample project with placeholder GPS data, photos, and notes.",
            wraplength=800,
        )
        info.pack(pady=5)

        # Output Directory
        dir_frame = ttk.LabelFrame(demo_frame, text="Output Directory", padding=10)
        dir_frame.pack(fill="x", pady=10)

        entry_frame = ttk.Frame(dir_frame)
        entry_frame.pack(fill="x")

        self.demo_dir = ttk.Entry(entry_frame)
        self.demo_dir.insert(0, "demo")
        self.demo_dir.pack(side="left", fill="x", expand=True)

        ttk.Button(
            entry_frame,
            text="Browse...",
            command=lambda: self.browse_directory(self.demo_dir),
        ).pack(side="left", padx=(5, 0))

        # Status and Generate button
        button_frame = ttk.Frame(demo_frame)
        button_frame.pack(pady=10)

        self.demo_button = ttk.Button(
            button_frame, text="🎨 Generate Demo Data", command=self.run_demo
        )
        self.demo_button.pack(side="left", padx=5)

        self.demo_status_label = ttk.Label(
            button_frame,
            text="⚪ Ready",
            font=("", 10, "bold"),
            foreground=self.colors["ready"],
        )
        self.demo_status_label.pack(side="left", padx=10)

        self.demo_progress = ttk.Progressbar(
            button_frame, mode="indeterminate", length=200
        )
        # Don't pack initially - will be shown when building starts

        # Output
        output_frame = ttk.LabelFrame(demo_frame, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, pady=5)

        self.demo_output = scrolledtext.ScrolledText(
            output_frame, height=25, wrap=tk.WORD
        )
        self.demo_output.pack(fill="both", expand=True)

    def create_help_tab(self) -> None:
        """Create the Help tab."""
        help_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(help_frame, text="Help & Info")

        help_text = scrolledtext.ScrolledText(help_frame, wrap=tk.WORD, height=30)
        help_text.pack(fill="both", expand=True)

        help_content = """
🗺️ mkmapdiary - Travel Journal Generator

About
=====
mkmapdiary is a travel journal generator that creates beautiful map-based websites
from GPS tracks, photos, and notes.

Quick Start
===========
1. Prepare your data: Create a directory with:
   - GPS tracks (.gpx, .kml, or other formats)
   - Photos with location data
   - Text notes (.txt or .md files)

2. Build the diary: Use the "Build Diary" tab to generate your website

3. View the result: Open the generated website in your browser

Try the Demo
============
Not sure where to start? Use the "Generate Demo" tab to create sample data,
then build it to see what mkmapdiary can do!

Source Directory Structure
==========================
Your source directory should contain:
- GPS files: .gpx, .kml, .fit, .tcx
- Photos: .jpg, .png, .heic, etc.
- Notes: .txt, .md files
- Optional: config.yaml for custom settings

Configuration
=============
You can customize the build with configuration parameters in the format:
  site.title=My Travel Journal
  site.locale=en_US
  features.transcription.enabled=False

Documentation
=============
For more information, visit: https://bytehexe.github.io/mkmapdiary/

License
=======
PolyForm Noncommercial License 1.0.0
Copyright Janna Hopp

Bon voyage! Have fun travelling and stay safe! 🌍✈️
        """

        help_text.insert("1.0", help_content)
        help_text.config(state="disabled")

    def run_build(self) -> None:
        """Run the build command."""
        if self.build_running:
            return

        source_dir = self.source_dir.get()

        if not source_dir:
            self.build_output.delete("1.0", tk.END)
            self.build_output.insert(
                "1.0", "❌ Error: Please specify a source directory"
            )
            self.build_status_label.config(
                text="❌ Error", foreground=self.colors["error"]
            )
            return

        def build_thread() -> None:
            # Start progress
            self.build_running = True
            self.build_button.config(state="disabled")
            self.browser_button.config(state="disabled")
            self.build_progress.pack(side="left", padx=5)
            self.build_progress.start(10)
            self.build_status_label.config(
                text="⏳ Building...", foreground=self.colors["progress"]
            )

            self.build_output.delete("1.0", tk.END)
            self.build_output.insert("1.0", "Building...\n")
            self.build_output.see(tk.END)

            source_path = pathlib.Path(source_dir)
            dist_path = (
                pathlib.Path(self.dist_dir.get()) if self.dist_dir.get() else None
            )
            build_path = (
                pathlib.Path(self.build_dir.get()) if self.build_dir.get() else None
            )

            # Parse config params
            params = []
            config_text = self.config_params.get("1.0", tk.END).strip()
            if config_text:
                for param in config_text.split("\n"):
                    param = param.strip()
                    if param and not param.startswith("#"):
                        params.append(param)
            params_tuple = tuple(params)

            if dist_path is None:
                dist_path = source_path.with_name(source_path.name + "_dist")

            ctx = click.Context(build_command)
            ctx.obj = {"verbose": 0, "quiet": 0}

            try:
                output, returncode = capture_command_output(
                    ctx.invoke,
                    build_command,
                    source_dir=source_path,
                    dist_dir=dist_path,
                    build_dir=build_path,
                    persistent_build=self.persistent_build.get(),
                    params=params_tuple,
                    always_execute=self.always_execute.get(),
                    num_processes=self.num_processes.get(),
                    no_cache=self.no_cache.get(),
                    profile=False,
                    debug_fast=self.debug_fast.get(),
                )

                self.build_output.delete("1.0", tk.END)
                if returncode == 0:
                    self.build_output.insert(
                        "1.0",
                        f"✅ Build completed successfully!\n\nOutput directory: {dist_path}\n\n{output}",
                    )
                    self.build_output.see(tk.END)
                    self.build_status_label.config(
                        text="✅ Success", foreground=self.colors["success"]
                    )
                else:
                    self.build_output.insert(
                        "1.0", f"❌ Build failed (exit code {returncode})\n\n{output}"
                    )
                    self.build_output.see(tk.END)
                    self.build_status_label.config(
                        text="❌ Failed", foreground=self.colors["error"]
                    )
            except Exception as e:
                self.build_output.delete("1.0", tk.END)
                self.build_output.insert("1.0", f"❌ Error: {str(e)}")
                self.build_output.see(tk.END)
                self.build_status_label.config(
                    text="❌ Error", foreground=self.colors["error"]
                )
            finally:
                # Stop progress
                self.build_progress.stop()
                self.build_progress.pack_forget()
                self.build_button.config(state="normal")
                self.build_running = False
                # Update browser button state after build completes
                self.update_browser_button_state()

        threading.Thread(target=build_thread, daemon=True).start()

    def run_demo(self) -> None:
        """Run the demo generation command."""
        if self.demo_running:
            return

        output_dir = self.demo_dir.get()

        if not output_dir:
            self.demo_output.delete("1.0", tk.END)
            self.demo_output.insert(
                "1.0", "❌ Error: Please specify an output directory"
            )
            self.demo_status_label.config(
                text="❌ Error", foreground=self.colors["error"]
            )
            return

        def demo_thread() -> None:
            # Start progress
            self.demo_running = True
            self.demo_button.config(state="disabled")
            self.demo_progress.pack(side="left", padx=5)
            self.demo_progress.start(10)
            self.demo_status_label.config(
                text="⏳ Generating...", foreground=self.colors["progress"]
            )

            self.demo_output.delete("1.0", tk.END)
            self.demo_output.insert("1.0", "Generating demo data...\n")
            self.demo_output.see(tk.END)

            output_path = pathlib.Path(output_dir)

            ctx = click.Context(generate_demo_command)
            ctx.obj = {"verbose": 0, "quiet": 0}

            try:
                output, returncode = capture_command_output(
                    ctx.invoke,
                    generate_demo_command,
                    output_dir=output_path,
                )

                self.demo_output.delete("1.0", tk.END)
                if returncode == 0:
                    self.demo_output.insert(
                        "1.0",
                        f"✅ Demo data generated successfully in {output_path}\n\n{output}",
                    )
                    self.demo_output.see(tk.END)
                    self.demo_status_label.config(
                        text="✅ Success", foreground=self.colors["success"]
                    )
                else:
                    self.demo_output.insert(
                        "1.0",
                        f"❌ Error generating demo data (exit code {returncode})\n\n{output}",
                    )
                    self.demo_output.see(tk.END)
                    self.demo_status_label.config(
                        text="❌ Failed", foreground=self.colors["error"]
                    )
            except Exception as e:
                self.demo_output.delete("1.0", tk.END)
                self.demo_output.insert("1.0", f"❌ Error: {str(e)}")
                self.demo_output.see(tk.END)
                self.demo_status_label.config(
                    text="❌ Error", foreground=self.colors["error"]
                )
            finally:
                # Stop progress
                self.demo_progress.stop()
                self.demo_progress.pack_forget()
                self.demo_button.config(state="normal")
                self.demo_running = False

        threading.Thread(target=demo_thread, daemon=True).start()

    def run_calibrate(self) -> None:
        """Run the calibrate command."""
        if self.calibrate_running:
            return

        image = self.calibrate_image.get()
        ref_time = self.calibrate_ref_time.get()

        if not image or not ref_time:
            self.calibrate_output_text.delete("1.0", tk.END)
            self.calibrate_output_text.insert(
                "1.0", "❌ Error: Please specify both image file and reference time"
            )
            self.calibrate_status_label.config(
                text="❌ Error", foreground=self.colors["error"]
            )
            return

        def calibrate_thread() -> None:
            # Start progress
            self.calibrate_running = True
            self.calibrate_button.config(state="disabled")
            self.calibrate_progress.pack(side="left", padx=5)
            self.calibrate_progress.start(10)
            self.calibrate_status_label.config(
                text="⏳ Calibrating...", foreground=self.colors["progress"]
            )

            self.calibrate_output_text.delete("1.0", tk.END)
            self.calibrate_output_text.insert("1.0", "Calibrating...\n")
            self.calibrate_output_text.see(tk.END)

            image_path = pathlib.Path(image)
            output_path = (
                pathlib.Path(self.calibrate_output.get())
                if self.calibrate_output.get()
                else None
            )

            ctx = click.Context(calibrate_file_command)
            ctx.obj = {"verbose": 0, "quiet": 0}

            try:
                output, returncode = capture_command_output(
                    ctx.invoke,
                    calibrate_file_command,
                    image=image_path,
                    ref_time=ref_time,
                    camera_tz=self.calibrate_camera_tz.get(),
                    ref_tz=self.calibrate_ref_tz.get(),
                    output=output_path,
                    dry_run=self.calibrate_dry_run.get(),
                )

                self.calibrate_output_text.delete("1.0", tk.END)
                if returncode == 0:
                    self.calibrate_output_text.insert(
                        "1.0", f"✅ Calibration completed successfully!\n\n{output}"
                    )
                    self.calibrate_output_text.see(tk.END)
                    self.calibrate_status_label.config(
                        text="✅ Success", foreground=self.colors["success"]
                    )
                else:
                    self.calibrate_output_text.insert(
                        "1.0",
                        f"❌ Calibration failed (exit code {returncode})\n\n{output}",
                    )
                    self.calibrate_output_text.see(tk.END)
                    self.calibrate_status_label.config(
                        text="❌ Failed", foreground=self.colors["error"]
                    )
            except Exception as e:
                self.calibrate_output_text.delete("1.0", tk.END)
                self.calibrate_output_text.insert("1.0", f"❌ Error: {str(e)}")
                self.calibrate_output_text.see(tk.END)
                self.calibrate_status_label.config(
                    text="❌ Error", foreground=self.colors["error"]
                )
            finally:
                # Stop progress
                self.calibrate_progress.stop()
                self.calibrate_progress.pack_forget()
                self.calibrate_button.config(state="normal")
                self.calibrate_running = False

        threading.Thread(target=calibrate_thread, daemon=True).start()

    def run_config(self) -> None:
        """Run the config command."""
        if self.config_running:
            return

        params_text = self.config_params_text.get("1.0", tk.END).strip()

        if not params_text:
            self.config_output.delete("1.0", tk.END)
            self.config_output.insert(
                "1.0", "❌ Error: Please specify at least one configuration parameter"
            )
            self.config_status_label.config(
                text="❌ Error", foreground=self.colors["error"]
            )
            return

        is_user = self.config_user.get()
        source_dir = self.config_source_dir.get()

        if not is_user and not source_dir:
            self.config_output.delete("1.0", tk.END)
            self.config_output.insert(
                "1.0",
                "❌ Error: Please specify a source directory or check 'Write to user config'",
            )
            self.config_status_label.config(
                text="❌ Error", foreground=self.colors["error"]
            )
            return

        def config_thread() -> None:
            # Start progress
            self.config_running = True
            self.config_button.config(state="disabled")
            self.config_progress.pack(side="left", padx=5)
            self.config_progress.start(10)
            self.config_status_label.config(
                text="⏳ Applying config...", foreground=self.colors["progress"]
            )

            self.config_output.delete("1.0", tk.END)
            self.config_output.insert("1.0", "Applying configuration...\n")
            self.config_output.see(tk.END)

            # Parse params
            params = []
            for param in params_text.split("\n"):
                param = param.strip()
                if param and not param.startswith("#"):
                    params.append(param)
            params_tuple = tuple(params)

            source_path = pathlib.Path(source_dir) if source_dir else None

            ctx = click.Context(config_command)
            ctx.obj = {"verbose": 0, "quiet": 0}

            try:
                output, returncode = capture_command_output(
                    ctx.invoke,
                    config_command,
                    params=params_tuple,
                    user=is_user,
                    source_dir=source_path,
                )

                self.config_output.delete("1.0", tk.END)
                if returncode == 0:
                    self.config_output.insert(
                        "1.0", f"✅ Configuration applied successfully!\n\n{output}"
                    )
                    self.config_output.see(tk.END)
                    self.config_status_label.config(
                        text="✅ Success", foreground=self.colors["success"]
                    )
                else:
                    self.config_output.insert(
                        "1.0",
                        f"❌ Configuration failed (exit code {returncode})\n\n{output}",
                    )
                    self.config_output.see(tk.END)
                    self.config_status_label.config(
                        text="❌ Failed", foreground=self.colors["error"]
                    )
            except Exception as e:
                self.config_output.delete("1.0", tk.END)
                self.config_output.insert("1.0", f"❌ Error: {str(e)}")
                self.config_output.see(tk.END)
                self.config_status_label.config(
                    text="❌ Error", foreground=self.colors["error"]
                )
            finally:
                # Stop progress
                self.config_progress.stop()
                self.config_progress.pack_forget()
                self.config_button.config(state="normal")
                self.config_running = False

        threading.Thread(target=config_thread, daemon=True).start()

    def run_inspect(self) -> None:
        """Run the inspect command."""
        if self.inspect_running:
            return

        source = self.inspect_source.get()

        if not source:
            self.inspect_output.delete("1.0", tk.END)
            self.inspect_output.insert(
                "1.0", "❌ Error: Please specify a source file or directory"
            )
            self.inspect_status_label.config(
                text="❌ Error", foreground=self.colors["error"]
            )
            return

        def inspect_thread() -> None:
            # Start progress
            self.inspect_running = True
            self.inspect_button.config(state="disabled")
            self.inspect_progress.pack(side="left", padx=5)
            self.inspect_progress.start(10)
            self.inspect_status_label.config(
                text="⏳ Inspecting...", foreground=self.colors["progress"]
            )

            self.inspect_output.delete("1.0", tk.END)
            self.inspect_output.insert("1.0", "Inspecting...\n")
            self.inspect_output.see(tk.END)

            source_path = pathlib.Path(source)

            ctx = click.Context(inspect_command)
            ctx.obj = {"verbose": 0, "quiet": 0}

            try:
                output, returncode = capture_command_output(
                    ctx.invoke,
                    inspect_command,
                    source=source_path,
                    tz=self.inspect_tz.get(),
                )

                self.inspect_output.delete("1.0", tk.END)
                if returncode == 0:
                    self.inspect_output.insert(
                        "1.0", f"✅ Inspection completed successfully!\n\n{output}"
                    )
                    self.inspect_output.see(tk.END)
                    self.inspect_status_label.config(
                        text="✅ Success", foreground=self.colors["success"]
                    )
                else:
                    self.inspect_output.insert(
                        "1.0",
                        f"❌ Inspection failed (exit code {returncode})\n\n{output}",
                    )
                    self.inspect_output.see(tk.END)
                    self.inspect_status_label.config(
                        text="❌ Failed", foreground=self.colors["error"]
                    )
            except Exception as e:
                self.inspect_output.delete("1.0", tk.END)
                self.inspect_output.insert("1.0", f"❌ Error: {str(e)}")
                self.inspect_output.see(tk.END)
                self.inspect_status_label.config(
                    text="❌ Error", foreground=self.colors["error"]
                )
            finally:
                # Stop progress
                self.inspect_progress.stop()
                self.inspect_progress.pack_forget()
                self.inspect_button.config(state="normal")
                self.inspect_running = False

        threading.Thread(target=inspect_thread, daemon=True).start()

    def create_calibrate_tab(self) -> None:
        """Create the Calibrate tab."""
        calibrate_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(calibrate_frame, text="Calibrate")

        title = ttk.Label(
            calibrate_frame,
            text="Calibrate camera timestamps",
            font=("Helvetica", 12, "bold"),
        )
        title.pack(pady=10)

        info = ttk.Label(
            calibrate_frame,
            text="Calibrate camera timestamps using a reference image and time.",
            wraplength=800,
        )
        info.pack(pady=5)

        # Image File
        image_frame = ttk.LabelFrame(calibrate_frame, text="Image File *", padding=10)
        image_frame.pack(fill="x", pady=5)

        image_entry_frame = ttk.Frame(image_frame)
        image_entry_frame.pack(fill="x")

        self.calibrate_image = ttk.Entry(image_entry_frame)
        self.calibrate_image.pack(side="left", fill="x", expand=True)

        ttk.Button(
            image_entry_frame,
            text="Browse...",
            command=lambda: self.browse_file(self.calibrate_image),
        ).pack(side="left", padx=(5, 0))

        # Reference Time
        time_frame = ttk.LabelFrame(
            calibrate_frame, text="Reference Time *", padding=10
        )
        time_frame.pack(fill="x", pady=5)

        ttk.Label(
            time_frame,
            text="Format: YYYY-MM-DD HH:MM:SS",
            foreground=self.colors["info"],
        ).pack(anchor="w")

        self.calibrate_ref_time = ttk.Entry(time_frame)
        self.calibrate_ref_time.pack(fill="x")

        # Options
        options_frame = ttk.LabelFrame(calibrate_frame, text="Options", padding=10)
        options_frame.pack(fill="x", pady=5)

        ttk.Label(options_frame, text="Camera Timezone:").pack(anchor="w")
        self.calibrate_camera_tz = ttk.Entry(options_frame)
        self.calibrate_camera_tz.insert(0, "localtime")
        self.calibrate_camera_tz.pack(fill="x", pady=(0, 5))

        ttk.Label(options_frame, text="Reference Timezone:").pack(anchor="w")
        self.calibrate_ref_tz = ttk.Entry(options_frame)
        self.calibrate_ref_tz.insert(0, "localtime")
        self.calibrate_ref_tz.pack(fill="x", pady=(0, 5))

        ttk.Label(options_frame, text="Output File (optional):").pack(anchor="w")
        self.calibrate_output = ttk.Entry(options_frame)
        self.calibrate_output.pack(fill="x")

        self.calibrate_dry_run = tk.BooleanVar()
        ttk.Checkbutton(
            options_frame, text="Dry Run", variable=self.calibrate_dry_run
        ).pack(anchor="w", pady=(5, 0))

        # Status and Run button
        button_frame = ttk.Frame(calibrate_frame)
        button_frame.pack(pady=10)

        self.calibrate_button = ttk.Button(
            button_frame, text="📷 Calibrate", command=self.run_calibrate
        )
        self.calibrate_button.pack(side="left", padx=5)

        self.calibrate_status_label = ttk.Label(
            button_frame,
            text="⚪ Ready",
            font=("", 10, "bold"),
            foreground=self.colors["ready"],
        )
        self.calibrate_status_label.pack(side="left", padx=10)

        self.calibrate_progress = ttk.Progressbar(
            button_frame, mode="indeterminate", length=200
        )
        # Don't pack initially - will be shown when running starts

        # Output
        output_frame = ttk.LabelFrame(calibrate_frame, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, pady=5)

        self.calibrate_output_text = scrolledtext.ScrolledText(
            output_frame, height=15, wrap=tk.WORD
        )
        self.calibrate_output_text.pack(fill="both", expand=True)

    def create_config_tab(self) -> None:
        """Create the Config tab."""
        config_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(config_frame, text="Config")

        title = ttk.Label(
            config_frame,
            text="Write configuration to config.yaml",
            font=("Helvetica", 12, "bold"),
        )
        title.pack(pady=10)

        info = ttk.Label(
            config_frame,
            text="Apply configuration parameters and write them to a config.yaml file.",
            wraplength=800,
        )
        info.pack(pady=5)

        # Source Directory
        dir_frame = ttk.LabelFrame(config_frame, text="Source Directory", padding=10)
        dir_frame.pack(fill="x", pady=5)

        dir_entry_frame = ttk.Frame(dir_frame)
        dir_entry_frame.pack(fill="x")

        self.config_source_dir = ttk.Entry(dir_entry_frame)
        self.config_source_dir.pack(side="left", fill="x", expand=True)

        ttk.Button(
            dir_entry_frame,
            text="Browse...",
            command=lambda: self.browse_directory(self.config_source_dir),
        ).pack(side="left", padx=(5, 0))

        self.config_user = tk.BooleanVar()
        ttk.Checkbutton(
            dir_frame,
            text="Write to user config (ignore source directory)",
            variable=self.config_user,
        ).pack(anchor="w", pady=(5, 0))

        # Config params
        params_frame = ttk.LabelFrame(
            config_frame, text="Configuration Parameters", padding=10
        )
        params_frame.pack(fill="x", pady=5)

        ttk.Label(
            params_frame,
            text="One parameter per line (format: key=value)",
            foreground=self.colors["info"],
        ).pack(anchor="w")

        self.config_params_text = scrolledtext.ScrolledText(params_frame, height=6)
        self.config_params_text.pack(fill="x")

        # Status and Apply button
        button_frame = ttk.Frame(config_frame)
        button_frame.pack(pady=10)

        self.config_button = ttk.Button(
            button_frame, text="⚙️ Apply Config", command=self.run_config
        )
        self.config_button.pack(side="left", padx=5)

        self.config_status_label = ttk.Label(
            button_frame,
            text="⚪ Ready",
            font=("", 10, "bold"),
            foreground=self.colors["ready"],
        )
        self.config_status_label.pack(side="left", padx=10)

        self.config_progress = ttk.Progressbar(
            button_frame, mode="indeterminate", length=200
        )
        # Don't pack initially - will be shown when running starts

        # Output
        output_frame = ttk.LabelFrame(config_frame, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, pady=5)

        self.config_output = scrolledtext.ScrolledText(
            output_frame, height=15, wrap=tk.WORD
        )
        self.config_output.pack(fill="both", expand=True)

    def create_inspect_tab(self) -> None:
        """Create the Inspect tab."""
        inspect_frame = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(inspect_frame, text="Inspect")

        title = ttk.Label(
            inspect_frame,
            text="Inspect assets from source",
            font=("Helvetica", 12, "bold"),
        )
        title.pack(pady=10)

        info = ttk.Label(
            inspect_frame,
            text="Inspect and display asset information from a source file or directory.",
            wraplength=800,
        )
        info.pack(pady=5)

        # Source
        source_frame = ttk.LabelFrame(
            inspect_frame, text="Source File or Directory *", padding=10
        )
        source_frame.pack(fill="x", pady=5)

        source_entry_frame = ttk.Frame(source_frame)
        source_entry_frame.pack(fill="x")

        self.inspect_source = ttk.Entry(source_entry_frame)
        self.inspect_source.pack(side="left", fill="x", expand=True)

        ttk.Button(
            source_entry_frame,
            text="Browse File...",
            command=lambda: self.browse_file(self.inspect_source),
        ).pack(side="left", padx=(5, 0))
        ttk.Button(
            source_entry_frame,
            text="Browse Dir...",
            command=lambda: self.browse_directory(self.inspect_source),
        ).pack(side="left", padx=(5, 0))

        # Timezone
        tz_frame = ttk.LabelFrame(inspect_frame, text="Timezone", padding=10)
        tz_frame.pack(fill="x", pady=5)

        self.inspect_tz = ttk.Entry(tz_frame)
        self.inspect_tz.insert(0, "localtime")
        self.inspect_tz.pack(fill="x")

        # Status and Run button
        button_frame = ttk.Frame(inspect_frame)
        button_frame.pack(pady=10)

        self.inspect_button = ttk.Button(
            button_frame, text="🔍 Inspect", command=self.run_inspect
        )
        self.inspect_button.pack(side="left", padx=5)

        self.inspect_status_label = ttk.Label(
            button_frame,
            text="⚪ Ready",
            font=("", 10, "bold"),
            foreground=self.colors["ready"],
        )
        self.inspect_status_label.pack(side="left", padx=10)

        self.inspect_progress = ttk.Progressbar(
            button_frame, mode="indeterminate", length=200
        )
        # Don't pack initially - will be shown when running starts

        # Output
        output_frame = ttk.LabelFrame(inspect_frame, text="Output", padding=10)
        output_frame.pack(fill="both", expand=True, pady=5)

        self.inspect_output = scrolledtext.ScrolledText(
            output_frame, height=15, wrap=tk.WORD
        )
        self.inspect_output.pack(fill="both", expand=True)


@click.command()
@click.option(
    "--theme", type=click.Choice(["light", "dark", "system"]), default="system"
)
def main(theme: str) -> None:
    """Main entry point for the UI."""
    root = tk.Tk()
    MkmapdiaryUI(root)

    # Set theme
    if theme == "system":
        theme = darkdetect.theme()

    sv_ttk.set_theme(theme)

    root.mainloop()


if __name__ == "__main__":
    main()
