"""Graphical User Interface for CDA analyzer"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import folium
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np
import threading
from icon import LOGO_BASE64
from fit_parser import FITParser
from analyzer import CDAAnalyzer
from weather import WeatherService
from config import DEFAULT_PARAMETERS

class GUIInterface:
    def __init__(self, root=None):
        # Use provided root or create new
        self.root = root if root else tk.Tk()
        self.root.withdraw()  # Hide main window until splash is done
        self.root.title("CdA Analyzer")
        self.root.geometry("1200x1000")
        self.root.geometry("1200x1000")
        
        # Set window icon (from embedded icon.py)
        self._set_window_icon()

        # Initialize data
        self.fit_file_path = None
        self.parameters = DEFAULT_PARAMETERS.copy()
        self.ride_data = None
        self.analysis_results = None
        self.segment_data_map = {}  # Map segment IDs to data indices
        
        # Keep track of matplotlib objects for cleanup
        self.current_figure = None
        self.current_canvas = None

        self.analyzer = CDAAnalyzer(self.parameters)
        self.weather_service = WeatherService()

        # Show splash screen and then setup UI
        self._show_splash_and_start()
    
    def _show_splash_and_start(self):
        """Show splash screen, then initialize UI"""
        splash = tk.Toplevel(self.root)
        splash.overrideredirect(True)
        splash.geometry("600x400")
        splash.configure(bg="white")

        # Center splash
        splash.update_idletasks()
        x = (splash.winfo_screenwidth() // 2) - (600 // 2)
        y = (splash.winfo_screenheight() // 2) - (400 // 2)
        splash.geometry(f"600x400+{x}+{y}")

        # Try to load logo from icon.py
        try:
            from icon import LOGO_BASE64
            import base64
            from PIL import Image, ImageTk
            import io

            image_data = base64.b64decode(LOGO_BASE64)
            image_stream = io.BytesIO(image_data)
            pil_image = Image.open(image_stream)
            pil_image = pil_image.resize((200, 200), Image.Resampling.LANCZOS)
            tk_image = ImageTk.PhotoImage(pil_image)

            splash.image = tk_image  # Keep reference
            label = tk.Label(splash, image=tk_image, bg="white")
            label.pack(pady=40)
        except Exception as e:
            print(f"Could not load splash image: {e}")
            tk.Label(splash, text="🚴‍♂️", font=("Arial", 100), bg="white").pack(pady=50)

        # Title and subtitle
        tk.Label(
            splash,
            text="CdA Analyzer",
            font=("Arial", 24, "bold"),
            fg="#2c3e50",
            bg="white"
        ).pack(pady=10)
        
        tk.Label(
            splash,
            text="Analyzing bike aerodynamics...",
            font=("Arial", 12),
            fg="#7f8c8d",
            bg="white"
        ).pack(pady=5)

        # Destroy splash and start app
        def start_app():
            splash.destroy()
            self.root.deiconify()  # Show main window
            self.root.lift()
            self.root.focus_force()
            self._setup_ui()  # Now set up the UI

        # Show splash for 2.5 seconds
        splash.after(2500, start_app)
    
    def _setup_ui(self):
        """Setup the user interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Setup tabs
        self._setup_file_tab()
        self._setup_parameters_tab()
        self._setup_results_tab()
    
    def _setup_file_tab(self):
        """Setup file selection tab"""
        self.file_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.file_frame, text="File Selection")
        
        # File selection
        ttk.Label(self.file_frame, text="Select FIT File:", font=("Arial", 12, "bold")).pack(pady=10)
        
        file_button_frame = ttk.Frame(self.file_frame)
        file_button_frame.pack(pady=10)
        
        ttk.Button(file_button_frame, text="Browse FIT File", command=self._browse_fit_file).pack(side=tk.LEFT, padx=5)
        self.file_label = ttk.Label(file_button_frame, text="No file selected")
        self.file_label.pack(side=tk.LEFT, padx=10)
        
        # Load button
        ttk.Button(self.file_frame, text="Load and Parse FIT File", 
                  command=self._load_fit_file, style="Accent.TButton").pack(pady=20)
        
        # Status text
        self.file_status = tk.Text(self.file_frame, height=10, width=80)
        self.file_status.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Next button
        ttk.Button(self.file_frame, text="Next → Parameters", 
                  command=lambda: self.notebook.select(self.parameters_frame)).pack(pady=10)
    
    def _setup_parameters_tab(self):
        """Setup parameters configuration tab"""
        self.parameters_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.parameters_frame, text="Parameters")
        
        # Parameters form
        params_canvas = tk.Canvas(self.parameters_frame)
        params_scrollbar = ttk.Scrollbar(self.parameters_frame, orient="vertical", command=params_canvas.yview)
        params_frame = ttk.Frame(params_canvas)
        
        params_canvas.configure(yscrollcommand=params_scrollbar.set)
        params_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        params_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        params_canvas.create_window((0, 0), window=params_frame, anchor="nw")
        
        params_frame.bind("<Configure>", lambda e: params_canvas.configure(scrollregion=params_canvas.bbox("all")))
        
        ttk.Label(params_frame, text="Analysis Parameters:", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.param_entries = {}
        for key, value in self.parameters.items():
            frame = ttk.Frame(params_frame)
            frame.pack(fill=tk.X, padx=20, pady=5)
            
            ttk.Label(frame, text=key.replace('_', ' ').title(), width=20).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=20)
            entry.insert(0, str(value))
            entry.pack(side=tk.LEFT, padx=10)
            self.param_entries[key] = entry
        
        # Buttons
        button_frame = ttk.Frame(self.parameters_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="← Previous", 
                  command=lambda: self.notebook.select(self.file_frame)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Run Analysis", 
                  command=self._run_analysis, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
    
    def _setup_results_tab(self):
        """Setup results tab with integrated analysis"""
        self.results_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.results_frame, text="Results & Analysis")
    
        # Analysis section at the top
        analysis_section = ttk.LabelFrame(self.results_frame, text="Analysis")
        analysis_section.pack(fill=tk.X, padx=10, pady=5)
    
        # Progress bar and status
        self.progress = ttk.Progressbar(analysis_section, mode='indeterminate')
        self.progress.pack(pady=10, padx=20, fill=tk.X)
    
        self.analysis_status = ttk.Label(analysis_section, text="Ready to analyze")
        self.analysis_status.pack(pady=5)
    
        # Create notebook for results sub-tabs
        self.results_notebook = ttk.Notebook(self.results_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
        # Summary tab
        self.summary_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.summary_frame, text="Summary")
        self.summary_text = tk.Text(self.summary_frame, height=25, width=80)
        self.summary_text.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # Map tab
        self.map_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.map_frame, text="Map")
        
        # Updated map label to reflect Tkinter window display
        self.map_label = ttk.Label(self.map_frame, 
                                text="Interactive map will open in a new window after analysis\n"
                                    "Click 'Generate and Show Map' to display ride segments",
                                justify=tk.CENTER,
                                font=('Arial', 10))
        self.map_label.pack(expand=True)
        
        self.map_button = ttk.Button(self.map_frame, text="Generate and Show Map",
                                command=self._generate_map,
                                style='Accent.TButton')  # Optional: styled button
        self.map_button.pack(pady=10)
    
        # Plot tab
        self.plot_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.plot_frame, text="Plots")
        self.plot_label = ttk.Label(self.plot_frame, text="Plots will be displayed here after analysis")
        self.plot_label.pack(expand=True)
        self.plot_button = ttk.Button(self.plot_frame, text="Generate Plots",
                                    command=self._generate_plots)
        self.plot_button.pack(pady=10)
        # Bottom buttons
        button_frame = ttk.Frame(self.results_frame)
        button_frame.pack(pady=10)
    
        ttk.Button(button_frame, text="← Previous",
                command=lambda: self.notebook.select(self.parameters_frame)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Results",
                command=self._export_results).pack(side=tk.LEFT, padx=5)
    def _browse_fit_file(self):
        """Browse for FIT file"""
        file_path = filedialog.askopenfilename(
            title="Select FIT File",
            filetypes=[("FIT files", "*.fit"), ("All files", "*.*")]
        )
        if file_path:
            self.fit_file_path = file_path
            self.file_label.config(text=Path(file_path).name)
    
    def _load_fit_file(self):
        """Load and parse FIT file"""
        if not self.fit_file_path:
            messagebox.showerror("Error", "Please select a FIT file first")
            return
        
        try:
            self.file_status.delete(1.0, tk.END)
            self.file_status.insert(tk.END, "Loading FIT file...\n")
            self.root.update()
            
            fit_parser = FITParser()
            self.ride_data = fit_parser.parse_fit_file(self.fit_file_path)
            
            self.file_status.insert(tk.END, f"Successfully loaded {len(self.ride_data)} data points\n")
            self.file_status.insert(tk.END, f"Columns: {', '.join(self.ride_data.columns[:10])}\n")
            
            if len(self.ride_data.columns) > 10:
                self.file_status.insert(tk.END, f"... and {len(self.ride_data.columns) - 10} more columns\n")
            
            self.parameters = DEFAULT_PARAMETERS.copy()
            self.analyzer = CDAAnalyzer(self.parameters)
            self.weather_service = WeatherService()
            self._enable_segment_parameters()
            
        except Exception as e:
            error_msg = f"Error loading FIT file: {str(e)}"
            self.file_status.insert(tk.END, error_msg + "\n")
            messagebox.showerror("Error", error_msg)
    
    def _save_parameters(self):
        """Save parameters from GUI entries"""
        try:
            for key, entry in self.param_entries.items():
                value = entry.get()
                # Convert to appropriate type
                if isinstance(self.parameters[key], int):
                    self.parameters[key] = int(value)
                elif isinstance(self.parameters[key], float):
                    self.parameters[key] = float(value)
                else:
                    self.parameters[key] = value
        except Exception as e:
            messagebox.showerror("Error", f"Error saving parameters: {str(e)}")

    def _disable_segment_parameters(self):
        """Disable first 8 parameters after analysis is run"""
        for i, key in enumerate(list(self.parameters.keys())[:8]):
            if key in self.param_entries:
                self.param_entries[key].config(state='disabled')

    def _enable_segment_parameters(self):
        """Disable first 8 parameters after analysis is run"""
        for i, key in enumerate(list(self.parameters.keys())[:8]):
            if key in self.param_entries:
                self.param_entries[key].config(state='normal')
    
    def _cleanup_results(self):
        """Clean up only the previous plot canvas, not the UI."""
        try:
            # Close matplotlib figure
            if self.current_figure is not None:
                plt.close(self.current_figure)
                self.current_figure = None

            # Destroy canvas widget if exists
            if self.current_canvas is not None:
                self.current_canvas.get_tk_widget().destroy()
                self.current_canvas = None
        except Exception as e:
            print(f"Cleanup error: {e}")

    def _run_analysis(self):
        """Run the CDA analysis"""
        if self.ride_data is None:
            messagebox.showerror("Error", "Please load a FIT file first")
            return

        # Clean up any previous plots first
        self._cleanup_results()

        self._save_parameters()
        self.analyzer.update_parameters(self.parameters)
        self.notebook.select(self.results_frame)

        # Start analysis in a new thread
        self.progress.config(mode='indeterminate')
        self.progress.start()
        self.analysis_status.config(text="Running analysis in background...")
        self.root.update_idletasks()  # Refresh UI

        analysis_thread = threading.Thread(target=self._run_analysis_worker, daemon=True)
        analysis_thread.start()

    def _run_analysis_worker(self):
        """Worker function that runs in background thread"""
        try:
            # This runs in background thread
            analyzer = self.analyzer
            weather_service = self.weather_service
            
            analyzer.update_parameters

            results = analyzer.analyze_ride(self.ride_data, weather_service)

            # Schedule GUI update on main thread
            self.root.after(0, lambda: self._on_analysis_complete(results, error=None))
        except Exception as e:
            import traceback
            traceback.print_exc()  # For debugging
            self.root.after(0, lambda: self._on_analysis_complete(None, error=str(e)))

    def _on_analysis_complete(self, results, error):
        """Safely update GUI with results (called on main thread)"""
        self.progress.stop()
        self.progress.config(mode='determinate',  maximum=100)
        self.analysis_status.config(text="Analysis complete!" if error is None else "Analysis failed")
        self._disable_segment_parameters()
        self.summary_text.delete(1.0, tk.END)

        if error:
            self.progress['value'] = 0
            self.progress.update()
            self.analysis_results = None
            self.summary_text.insert(tk.END, f"Error during analysis: {error}\n")
            messagebox.showerror("Error", f"Analysis failed: {error}")
        else:
            self.progress['value'] = 100
            self.progress.update()
            self.analysis_results = results
            self._create_segment_mapping()
            self._display_analysis_results()

    def _create_segment_mapping(self):
        """Create mapping from segment IDs to data indices"""
        if not self.analysis_results or self.ride_data is None:
            return
            
        self.segment_data_map = {}
        for segment in self.analysis_results['segments']:
            segment_id = segment['segment_id']
            start_time = segment['start_time']
            end_time = segment['end_time']
            
            # Find indices in original data that correspond to this segment
            # Use proper pandas timestamp comparison
            try:
                mask = (self.ride_data['timestamp'] >= start_time) & (self.ride_data['timestamp'] <= end_time)
                indices = self.ride_data[mask].index.tolist()
                self.segment_data_map[segment_id] = indices
            except Exception as e:
                print(f"Error creating segment mapping for segment {segment_id}: {e}")
                self.segment_data_map[segment_id] = []
    
    def _display_analysis_results(self):
        """Display analysis results in the text area"""
        if not self.analysis_results:
            return
        
        results = self.analysis_results
        text = self.summary_text
        
        text.insert(tk.END, "="*100 + "\n")
        text.insert(tk.END, "CDA ANALYSIS RESULTS\n")
        text.insert(tk.END, "="*100 + "\n\n")
        
        # Parameters
        text.insert(tk.END, "Parameters used:\n")
        for key, value in results['parameters'].items():
            text.insert(tk.END, f"  {key}: {value}\n")
        text.insert(tk.END, "\n")
        
        # Segment results
        text.insert(tk.END, f"Segment Analysis ({len(results['segments'])} steady segments found):\n")
        text.insert(tk.END, "-"*130 + "\n")
        text.insert(tk.END, f"{'ID':<3} {'Dur':<6} {'Dist':<8} {'Speed':<6} {'AirSpd':<6} {'Wind':<5} {'Angle':<6} {'Slope':<6} {'Power':<6} {'CdA':<7}\n")
        text.insert(tk.END, "-"*130 + "\n")
        
        for segment in results['segments']:
            text.insert(tk.END, f"{segment['segment_id']:<3} "
                            f"{segment['duration']:<6.0f} "
                            f"{segment['distance']:<8.0f} "
                            f"{segment['speed']:<6.2f} "
                            f"{segment['air_speed']:<6.2f} "
                            f"{segment['effective_wind']:<5.1f} "
                            f"{segment['wind_angle']:<6.0f} "
                            f"{segment['slope']:<6.1f} "
                            f"{segment['power']:<6.0f} "
                            f"{segment['cda']:<7.4f} \n")
        
        # Summary
        text.insert(tk.END, "\nSummary:\n")
        text.insert(tk.END, "-"*60 + "\n")
        summary = results['summary']
        if summary:
            text.insert(tk.END, f"Total segments analyzed: {summary['total_segments']}\n")
            text.insert(tk.END, f"Weighted CdA: {summary['weighted_cda']:.4f}\n")
            text.insert(tk.END, f"Average CdA: {summary['average_cda']:.4f}\n")
            text.insert(tk.END, f"CdA standard deviation: {summary['cda_std']:.4f}\n")

            if summary.get('wind_coefficients'):
                a, b, c = summary['wind_coefficients']
                text.insert(tk.END, f"Wind Angle Formula: CdA = {a:.2e}*θ² + {b:.2e}*θ + {c:.2e} (θ in degrees)\n")
            else:
                text.insert(tk.END, "Wind Angle Formula: Insufficient data\n")

            text.insert(tk.END, f"Average wind speed: {summary['avg_wind_speed']:.1f} m/s\n")
            text.insert(tk.END, f"Average air speed: {summary['avg_air_speed']:.2f} m/s\n")
            text.insert(tk.END, f"Total analysis duration: {summary['total_duration']:.0f} seconds\n")
            text.insert(tk.END, f"Total distance analyzed: {summary['total_distance']:.0f} meters\n")
        else:
            text.insert(tk.END, "No steady segments found for analysis\n")
    
    def _generate_segment_colors(self, n_segments):
        """
        Generate distinct colors for segments using tab20, tab20b, tab20c (60 total).
        Cycles with rotation if more than 60 segments to avoid visual repetition.
        """
        # Combine three 20-color categorical colormaps
        base_colors = []
        for cmap_name in ['tab20', 'tab20b', 'tab20c']:
            cmap = plt.cm.get_cmap(cmap_name)
            base_colors.extend([cmap(i) for i in range(20)])  # 20 colors each → 60 total

        if n_segments <= 60:
            return base_colors[:n_segments]

        # For >60: cycle with rotation to avoid adjacent similarity
        colors = []
        rotation_step = 7  # Prime number for good dispersion across cycles
        for i in range(n_segments):
            # Rotate starting index every full cycle
            offset = (i // 60) * rotation_step
            idx = (i + offset) % 60
            colors.append(base_colors[idx])
        return colors

    def _generate_map(self):
        """Generate and display map with highlighted segments"""
        if not self.analysis_results or self.ride_data is None:
            messagebox.showerror("Error", "Please run analysis first")
            return

        try:
            if 'latitude' not in self.ride_data.columns or 'longitude' not in self.ride_data.columns:
                messagebox.showerror("Error", "No GPS data available in FIT file")
                return

            valid_coords = self.ride_data.dropna(subset=['latitude', 'longitude'])
            if len(valid_coords) == 0:
                messagebox.showerror("Error", "No valid GPS coordinates found")
                return

            # Center map
            mid_idx = len(valid_coords) // 2
            center_lat = valid_coords.iloc[mid_idx]['latitude']
            center_lon = valid_coords.iloc[mid_idx]['longitude']

            m = folium.Map(location=[center_lat, center_lon], zoom_start=13)

            # Full ride path
            full_path = list(zip(valid_coords['latitude'], valid_coords['longitude']))
            if len(full_path) > 1:
                folium.PolyLine(full_path, color='gray', weight=2, opacity=0.5, tooltip="Full Ride").add_to(m)

            segments = self.analysis_results['segments']
            if not segments:
                messagebox.showwarning("No Segments", "No steady segments to display on map.")
                return

            # Generate consistent colors using the same logic
            colors = self._generate_segment_colors(len(segments))
            colors_hex = [f"#{int(c[0]*255):02x}{int(c[1]*255):02x}{int(c[2]*255):02x}" for c in colors]

            # Add each segment
            for i, segment in enumerate(segments):
                seg_id = segment['segment_id']
                if seg_id not in self.segment_data_map:
                    continue

                idx = self.segment_data_map[seg_id]
                if len(idx) == 0:
                    continue

                segment_data = self.ride_data.iloc[idx]
                segment_coords = list(zip(segment_data['latitude'], segment_data['longitude']))

                if len(segment_coords) < 2:
                    continue

                color = colors_hex[i]
                popup_text = (
                    f"<b>Segment {seg_id}</b><br>"
                    f"CdA: {segment['cda']:.4f}<br>"
                    f"Speed: {segment['speed']:.2f} m/s<br>"
                    f"Power: {segment['power']:.0f} W<br>"
                    f"Slope: {segment['slope']:.2f}°"
                )

                # Segment line
                folium.PolyLine(
                    segment_coords,
                    color=color,
                    weight=5,
                    opacity=0.9,
                    tooltip=f"Segment {seg_id}",
                    popup=folium.Popup(popup_text, max_width=250)
                ).add_to(m)

                # Start marker with colored circle
                start_lat, start_lon = segment_coords[0]
                folium.Marker(
                    location=[start_lat, start_lon],
                    icon=folium.DivIcon(html=f"""
                    <div style="
                        background-color: {color};
                        border: 2px solid white;
                        border-radius: 50%;
                        width: 24px;
                        height: 24px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        color: white;
                        font-weight: bold;
                        font-size: 12px;
                        box-shadow: 0 0 5px rgba(0,0,0,0.5);
                    ">{seg_id}</div>"""),
                    tooltip=f"Segment {seg_id} Start"
                ).add_to(m)

            # Save map to temporary HTML file
            temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
            m.save(temp_file.name)
            temp_file.close()

            # Display in window
            self._show_map_in_window(temp_file.name)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error generating map: {str(e)}")

    def _show_map_in_window(self, html_file_path):
        """Display the HTML map in a PyQt5 window using QWebEngineView"""
        try:
            from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QHBoxLayout
            from PyQt5.QtWebEngineWidgets import QWebEngineView
            from PyQt5.QtCore import QUrl
            import webbrowser
            import sys
            import os

            # Ensure QApplication exists
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)

            # Main window
            map_window = QMainWindow()
            map_window.setWindowTitle("Ride Analysis Map")
            map_window.resize(1200, 800)
            map_window.setMinimumSize(800, 600)

            # Central widget with vertical layout
            central_widget = QWidget()
            layout = QVBoxLayout()
            central_widget.setLayout(layout)
            map_window.setCentralWidget(central_widget)

            # Web view
            webview = QWebEngineView()
            layout.addWidget(webview)

            def load_map():
                try:
                    file_url = QUrl.fromLocalFile(os.path.abspath(html_file_path))
                    webview.load(file_url)
                except Exception as e:
                    print(f"Error loading map: {e}")
                    # Fallback: load HTML content directly
                    try:
                        with open(html_file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        webview.setHtml(content)
                    except Exception as e2:
                        print(f"Fallback also failed: {e2}")

            # Buttons
            button_layout = QHBoxLayout()
            layout.addLayout(button_layout)

            refresh_btn = QPushButton("Refresh Map")
            refresh_btn.clicked.connect(load_map)
            button_layout.addWidget(refresh_btn)

            open_btn = QPushButton("Open in Browser")
            open_btn.clicked.connect(lambda: webbrowser.open(f"file://{os.path.abspath(html_file_path)}"))
            button_layout.addWidget(open_btn)

            close_btn = QPushButton("Close")
            close_btn.clicked.connect(map_window.close)
            button_layout.addWidget(close_btn)

            # Load map initially
            load_map()

            # Show the window
            map_window.show()

            # If QApplication was newly created, start the event loop
            if not QApplication.instance().startingUp():
                app.exec_()

        except Exception as e:
            print(f"Could not display map window: {e}")

            
        except ImportError:
            messagebox.showinfo("Package Required", 
                            "To display maps in Tkinter window, please install tkinterweb:\n"
                            "pip install tkinterweb\n\n"
                            "Opening in browser instead...")
            self._open_in_browser(html_file_path)
        except Exception as e:
            messagebox.showerror("Error", f"Error displaying map: {str(e)}")
            self._open_in_browser(html_file_path)
            
    def _generate_plots(self):
        """Generate and display plots with highlighted segments using unique colors per segment"""
        if not self.analysis_results or self.ride_data is None:
            messagebox.showerror("Error", "Please run analysis first")
            return

        try:
            # Clean up any existing plots first
            self._cleanup_results()

            # Hide initial label and button
            # self.plot_label.pack_forget()
            # self.plot_button.pack_forget()

            segments = self.analysis_results['segments']
            if not segments:
                messagebox.showwarning("No Data", "No steady segments found for plotting.")
                self._cleanup_results()
                return

            # Generate distinct colors for each segment
            colors = self._generate_segment_colors(len(segments))
            colors_hex = [f"#{int(c[0]*255):02x}{int(c[1]*255):02x}{int(c[2]*255):02x}" for c in colors]

            # Create figure
            self.current_figure = plt.figure(figsize=(16, 10), constrained_layout=False)
            gs = self.current_figure.add_gridspec(3, 2, hspace=0.4, wspace=0.3)

            # --- 1. Speed vs Distance ---
            ax1 = self.current_figure.add_subplot(gs[0, 0])
            if 'speed' in self.ride_data.columns and 'distance' in self.ride_data.columns:
                ax1.plot(self.ride_data['distance']/1000, self.ride_data['speed'],
                        color='lightgray', alpha=0.5, linewidth=1, label='Full Ride')

                for i, segment in enumerate(segments):
                    seg_id = segment['segment_id']
                    if seg_id in self.segment_data_map:
                        idx = self.segment_data_map[seg_id]
                        if len(idx) > 0:
                            distances = self.ride_data.iloc[idx]['distance']/1000
                            speeds = self.ride_data.iloc[idx]['speed']
                            ax1.plot(distances, speeds, color=colors[i], linewidth=2,
                                    label=f'Segment {seg_id}', alpha=0.9)

                ax1.set_title('Speed vs distance', fontsize=10, fontweight='bold')
                ax1.set_xlabel('Distance (km)', fontsize=8)
                ax1.set_ylabel('Speed (m/s)', fontsize=8)
                ax1.tick_params(axis='x', labelsize=6)
                ax1.grid(True, alpha=0.3)
                if len(segments) <= 10:
                    ax1.legend(loc='upper right', fontsize=6)

            # --- 2. Power vs Distance ---
            ax2 = self.current_figure.add_subplot(gs[0, 1])
            if 'power' in self.ride_data.columns and 'distance' in self.ride_data.columns:
                ax2.plot(self.ride_data['distance'], self.ride_data['power'],
                        color='lightgray', alpha=0.5, linewidth=1)

                for i, segment in enumerate(segments):
                    seg_id = segment['segment_id']
                    if seg_id in self.segment_data_map:
                        idx = self.segment_data_map[seg_id]
                        if len(idx) > 0:
                            distances = self.ride_data.iloc[idx]['distance']
                            power = self.ride_data.iloc[idx]['power']
                            ax2.plot(distances, power, color=colors[i], linewidth=2, alpha=0.9)

                ax2.set_title('Power vs distance', fontsize=10, fontweight='bold')
                ax2.set_xlabel('Distance (km)', fontsize=8)
                ax2.set_ylabel('Power (W)', fontsize=8)
                ax2.tick_params(axis='x', labelsize=6)
                ax2.grid(True, alpha=0.3)

            # --- 3. CdA vs Air Speed ---
            ax3 = self.current_figure.add_subplot(gs[1, 0])
            cda_vals = [s['cda'] for s in segments]
            air_speeds = [s.get('air_speed', 0) for s in segments]
            seg_ids = [s['segment_id'] for s in segments]

            ax3.scatter(air_speeds, cda_vals, c=colors, s=100, alpha=0.8,
                        edgecolors='k', linewidth=0.5)

            # x2 = np.array(air_speeds)
            # y2 = np.array(cda_vals)

            # # --- Linear fit (order 1) ---
            # coeffs1 = np.polyfit(x2, y2, 1)
            # poly_eq1 = np.poly1d(coeffs1)
            # x_fit = np.linspace(min(x2), max(x2), 200)
            # ax3.plot(x_fit, poly_eq1(x_fit), color='red',linewidth=1)

            # # Add formulas to plot
            # formula_lin = f"y = {coeffs1[0]:.3e}x + {coeffs1[1]:.3e}"
            # ax3.text(0.95, 0.15, formula_lin, transform=ax3.transAxes,
            #         fontsize=7, color='red', ha='right', va='bottom',
            #         bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

            ax3.set_title('CdA vs Air Speed', fontsize=10, fontweight='bold')
            ax3.set_xlabel('Air Speed (m/s)', fontsize=8)
            ax3.set_ylabel('CdA', fontsize=8)
            ax3.grid(True, alpha=0.3)

            for i, seg_id in enumerate(seg_ids):
                ax3.annotate(str(seg_id), (air_speeds[i], cda_vals[i]),
                            xytext=(5, 5), textcoords='offset points',
                            fontsize=6, alpha=0.8, ha='left')

            # --- 4. Speed vs Power ---
            ax4 = self.current_figure.add_subplot(gs[1, 1])
            speeds = [s['speed'] for s in segments]
            powers = [s['power'] for s in segments]

            ax4.scatter(speeds, powers, c=colors, s=100, alpha=0.8,
                        edgecolors='k', linewidth=0.5)

            # x4 = np.array(speeds)
            # y4 = np.array(powers)

            # # --- Quadratic fit (order 2) ---
            # coeffs4 = np.polyfit(x4, y4, 2)
            # poly_eq4 = np.poly1d(coeffs4)
            # x_fit4 = np.linspace(min(x4), max(x4), 200)
            # ax4.plot(x_fit4, poly_eq4(x_fit4), color='red', linewidth=1)

            # # Add formula to plot
            # formula_quad4 = f"y = {coeffs4[0]:.3e}x² + {coeffs4[1]:.3e}x + {coeffs4[2]:.3e}"
            # ax4.text(0.95, 0.05, formula_quad4, transform=ax4.transAxes,
            #         fontsize=7, color='red', ha='right', va='bottom',
            #         bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

            ax4.set_title('Segment Speed vs Power', fontsize=10, fontweight='bold')
            ax4.set_xlabel('Speed (m/s)', fontsize=8)
            ax4.set_ylabel('Power (W)', fontsize=8)
            ax4.grid(True, alpha=0.3)

            for i, seg_id in enumerate(seg_ids):
                ax4.annotate(str(seg_id), (speeds[i], powers[i]),
                            xytext=(5, 5), textcoords='offset points',
                            fontsize=6, alpha=0.8, ha='left')

            # --- 5. CdA by Segment (Bar Chart) ---
            ax5 = self.current_figure.add_subplot(gs[2, 0])
            bars = ax5.bar(seg_ids, cda_vals, color=colors, alpha=0.8, edgecolor='k', linewidth=0.7)
            ax5.set_title('CdA by Segment', fontsize=10, fontweight='bold')
            ax5.set_xlabel('Segment ID', fontsize=8)
            ax5.set_ylabel('CdA', fontsize=8)
            ax5.tick_params(axis='x', rotation=0, labelsize=9)
            ax5.grid(True, axis='y', alpha=0.3)

            for bar, cda in zip(bars, cda_vals):
                height = bar.get_height()
                ax5.text(bar.get_x() + bar.get_width() / 2., height + 0.001,
                        f'{cda:.3f}', ha='center', va='bottom', fontsize=5)

            # Ax6: CdA vs Wind Angle, colored by Air Speed
            ax6 = self.current_figure.add_subplot(gs[2, 1])
            cda_vals = [s['cda'] for s in segments]
            wind_angles = [s.get('wind_angle', 0) for s in segments]
            air_speeds = [s.get('air_speed', 0) for s in segments]

            for i in range(len(wind_angles)):
                if wind_angles[i] > 180:
                    wind_angles[i] -= 360
                if wind_angles[i] < -180:
                    wind_angles[i] += 360

            sc = ax6.scatter(
                wind_angles, cda_vals, c=air_speeds, cmap='viridis',
                s=100, alpha=0.8, edgecolors='k', linewidth=0.5
            )

            ax6.set_title('CdA vs Air Angle', fontsize=10, fontweight='bold')
            ax6.set_xlabel('Air Angle (°) — Headwind [±180], Tailwind [±0]', fontsize=8)
            ax6.set_ylabel('CdA', fontsize=8)
            ax6.grid(True, alpha=0.3)

            # Fit a 2nd order polynomial
            coeffs = np.polyfit(wind_angles, cda_vals, 2)
            poly_fn = np.poly1d(coeffs)

            # Create smooth x values for the fit line
            x_fit = np.linspace(-180, 180, 300)
            y_fit = poly_fn(x_fit)

            # Plot the best-fit curve without legend
            ax6.plot(x_fit, y_fit, color='red', linewidth=1.0)

            # Add the formula as text on the plot (top right corner)
            formula_text = f"y = {coeffs[0]:.3e}x² + {coeffs[1]:.3e}x + {coeffs[2]:.3e}"
            ax6.text(0.95, 0.05, formula_text, transform=ax6.transAxes,
                     fontsize=7, color='red', ha='right', va='bottom',
                     bbox=dict(facecolor='white', alpha=0.6, edgecolor='none'))

            avg_cda = np.mean(cda_vals)
            min_cda = np.min(cda_vals)
            max_cda = np.max(cda_vals)
            max_deviation = max(abs(avg_cda - min_cda), abs(max_cda - avg_cda))

            # Add some padding (e.g. 10%)
            padding = max_deviation * 0.1
            ylim_lower = avg_cda - max_deviation - padding
            ylim_upper = avg_cda + max_deviation + padding

            ax6.set_ylim(ylim_lower, ylim_upper)

            # Set symmetrical limits so 0 is centered
            ax6.set_xlim(-180, 180)
            ax6.set_xticks([-180, -135, -90, -45, 0, 45, 90, 135, 180])

            # Add segment labels
            for i, seg_id in enumerate(seg_ids):
                ax6.annotate(
                    str(seg_id), (wind_angles[i], cda_vals[i]),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=6, alpha=0.8, ha='left'
                )

            # Colorbar for Air Speed
            cbar = self.current_figure.colorbar(sc, ax=ax6)
            cbar.set_label('Air Speed (m/s)', fontsize=8)

            # Summary
            weighted_cda = np.average(cda_vals, weights=[s['distance'] for s in segments])
            avg_cda = np.mean(cda_vals)
            std_cda = np.std(cda_vals)
            total_distance = sum([s['distance'] for s in segments])

            summary_text = (
                f"Weighted CdA: {weighted_cda:.3f}\n"
                f"Average CdA: {avg_cda:.3f}\n"
                f"CdA Std Dev: {std_cda:.3f}\n"
                f"Total Distance Analyzed: {total_distance:.1f} km"
            )

            # Position: just below the plotscd
            self.current_figure.text(
                0.45, 0.1,  # X=middle-ish, Y=slightly above bottom
                summary_text,
                ha='center', va='top',
                fontsize=9,
                fontweight='bold',
                bbox=dict(facecolor='white', edgecolor='black', boxstyle='round,pad=0.5')
)

            # Final layout
            self.current_figure.suptitle("CDA Analysis Plots", fontsize=12, fontweight='bold', y=0.98)
            plt.subplots_adjust(top=0.95, bottom=0.15, left=0.05, right=0.95)

            # Embed in Tkinter
            self.current_canvas = FigureCanvasTkAgg(self.current_figure, self.plot_frame)
            self.current_canvas.draw()
            self.current_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        except Exception as e:
            self._cleanup_results()
            messagebox.showerror("Error", f"Error generating plots: {str(e)}")
                            
    def _export_results(self):
        """Export results to file"""
        if not self.analysis_results:
            messagebox.showerror("Error", "No results to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Export Results",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                if file_path.endswith('.json'):
                    # Convert datetime objects for JSON
                    export_data = self.analysis_results.copy()
                    for segment in export_data['segments']:
                        if 'start_time' in segment:
                            segment['start_time'] = segment['start_time'].isoformat()
                        if 'end_time' in segment:
                            segment['end_time'] = segment['end_time'].isoformat()
                    
                    with open(file_path, 'w') as f:
                        json.dump(export_data, f, indent=2)
                
                elif file_path.endswith('.csv'):
                    # Export segments as CSV
                    segments_df = pd.DataFrame(self.analysis_results['segments'])
                    segments_df.to_csv(file_path, index=False)
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting results: {str(e)}")
    
    def __del__(self):
        """Cleanup when the object is destroyed"""
        try:
            self._cleanup_results()
        except:
            pass
    
    def run(self):
        """Run the GUI application"""
        # Configure style
        style = ttk.Style()
        style.configure("Accent.TButton")
        
        # Set up proper cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        self.root.mainloop()
    
    def _on_closing(self):
        """Handle window closing event"""
        try:
            # Clean up matplotlib resources
            self._cleanup_results()
            # Close the main window
            self.root.quit()
            self.root.destroy()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            # Force close if cleanup fails
            self.root.quit()

    def _set_window_icon(self):
        """Set the window icon using embedded base64 data."""
        try:
            import base64
            import os
            import tempfile

            # Decode the icon
            icon_data = base64.b64decode(LOGO_BASE64)

            # Create a temporary .ico file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ico') as tmp:
                tmp.write(icon_data)
                tmp_path = tmp.name

            # Set the icon
            self.root.iconbitmap(tmp_path)

            # Schedule cleanup of the temp file when window closes
            def cleanup():
                try:
                    self.root.destroy()
                    os.unlink(tmp_path)
                except:
                    pass

            self.root.protocol("WM_DELETE_WINDOW", cleanup)

        except Exception as e:
            print(f"Could not set window icon: {e}")

def main():
    app = GUIInterface()
    app.run()

if __name__ == "__main__":
    main()