"""
Beautiful console status display for RexTracking service
"""

import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading

try:
    import torch
    import pynvml
    GPU_AVAILABLE = True
except ImportError:
    torch = None
    pynvml = None
    GPU_AVAILABLE = False

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich import box
from rich.columns import Columns




class StatusDisplay:
    """Beautiful console status display for RexTracking service"""
    
    def __init__(self, service_manager=None):
        self.console = Console()
        self.service_manager = service_manager
        self.start_time = time.time()
        self.last_update = time.time()
        self.update_interval = 1.0  # Update every second
        
        # Socket monitoring
        self.socket_count_history = []
        self.max_history = 60  # Keep 60 seconds of history
        
        # GPU monitoring initialization
        self.nvml_initialized = False
        if GPU_AVAILABLE and pynvml:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
            except:
                self.nvml_initialized = False
        
        
        # Create layout
        self.layout = Layout()
        self._setup_layout()
    
    
    def _setup_layout(self):
        """Setup the console layout"""
        self.layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        self.layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        self.layout["left"].split_column(
            Layout(name="service_status", size=8),
            Layout(name="system_metrics", size=8),
            Layout(name="gpu_metrics", size=8),
            Layout(name="socket_info", size=8)
        )
        
        self.layout["right"].split_column(
            Layout(name="camera_grid"),
            Layout(name="activity_log", size=12)
        )
    
    def get_socket_count(self) -> int:
        """Get current number of open sockets for this process"""
        try:
            process = psutil.Process()
            return len(process.connections())
        except:
            return 0
    
    def get_websocket_info(self) -> Dict[str, Any]:
        """Get WebSocket connection and port information"""
        info = {
            "api_port": 8080,  # Default, will try to get from service manager
            "frontend_port": 3000,
            "websocket_connections": 0,
            "active_channels": {},
            "listening_ports": [],
            "server_running": False,
            "error": None
        }
        
        try:
            # Get API port from service manager if available
            if self.service_manager and hasattr(self.service_manager, 'config'):
                if hasattr(self.service_manager.config, 'service') and hasattr(self.service_manager.config.service, 'port'):
                    info["api_port"] = self.service_manager.config.service.port
            
            # Check if service manager is actually running
            if self.service_manager and hasattr(self.service_manager, 'running'):
                info["server_running"] = bool(self.service_manager.running)
            
            # Get process connections to find listening ports
            process = psutil.Process()
            connections = process.connections(kind='inet')
            
            listening_ports = []
            for conn in connections:
                if conn.status == 'LISTEN' and conn.laddr:
                    port = conn.laddr.port
                    if port not in listening_ports:
                        listening_ports.append(port)
            
            info["listening_ports"] = sorted(listening_ports)
            
            # Only try to get WebSocket stats if the server is actually running
            # and the API port is listening
            if (info["server_running"] and 
                info["api_port"] in info["listening_ports"] and 
                self.service_manager and 
                hasattr(self.service_manager, 'api_server')):
                
                try:
                    from ..api.websockets import manager as ws_manager
                    if ws_manager and hasattr(ws_manager, 'get_connection_stats'):
                        stats = ws_manager.get_connection_stats()
                        info["websocket_connections"] = stats.get("total_connections", 0)
                        info["active_channels"] = stats.get("channels", {})
                        
                        # Validate connection counts - sometimes stale connections remain
                        total_from_channels = sum(info["active_channels"].values())
                        if info["websocket_connections"] != total_from_channels:
                            # Fix inconsistent connection count
                            info["websocket_connections"] = total_from_channels
                            if hasattr(ws_manager, '_connection_count'):
                                ws_manager._connection_count = total_from_channels
                                
                except Exception as ws_error:
                    info["error"] = f"WebSocket stats error: {str(ws_error)}"
                    # Reset to safe values
                    info["websocket_connections"] = 0
                    info["active_channels"] = {}
            else:
                # Server not running or port not listening - no WebSocket connections should exist
                info["websocket_connections"] = 0
                info["active_channels"] = {}
                    
        except Exception as e:
            info["error"] = f"WebSocket info error: {str(e)}"
            
        return info
    
    def get_gpu_metrics(self) -> Dict[str, Any]:
        """Get GPU performance metrics"""
        metrics = {
            "cuda_available": False,
            "gpu_count": 0,
            "gpu_utilization": 0.0,
            "gpu_memory_used": 0.0,
            "gpu_memory_total": 0.0,
            "gpu_memory_percent": 0.0,
            "gpu_temperature": 0.0,
            "gpu_name": "N/A",
            "error": None
        }
        
        try:
            # Check CUDA availability
            if GPU_AVAILABLE and torch:
                metrics["cuda_available"] = torch.cuda.is_available()
                
                if metrics["cuda_available"]:
                    metrics["gpu_count"] = torch.cuda.device_count()
                    
                    # Get current device info
                    if metrics["gpu_count"] > 0:
                        current_device = torch.cuda.current_device()
                        props = torch.cuda.get_device_properties(current_device)
                        metrics["gpu_name"] = props.name
            
            # Get detailed GPU metrics via NVML
            if self.nvml_initialized and metrics["cuda_available"]:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # Get first GPU
                    
                    # GPU utilization
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    metrics["gpu_utilization"] = util.gpu
                    
                    # Memory info
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    metrics["gpu_memory_used"] = mem_info.used / 1024**3  # Convert to GB
                    metrics["gpu_memory_total"] = mem_info.total / 1024**3  # Convert to GB
                    metrics["gpu_memory_percent"] = (mem_info.used / mem_info.total) * 100
                    
                    # Temperature
                    try:
                        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                        metrics["gpu_temperature"] = temp
                    except:
                        pass  # Temperature might not be available
                        
                except Exception as e:
                    metrics["error"] = f"NVML error: {str(e)}"
                    
        except Exception as e:
            metrics["error"] = f"GPU metrics error: {str(e)}"
            
        return metrics
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            
            # Process-specific metrics
            process = psutil.Process()
            process_memory = process.memory_info()
            process_cpu = process.cpu_percent()
            
            return {
                "system_cpu": cpu_percent,
                "system_memory": memory.percent,
                "process_cpu": process_cpu,
                "process_memory_mb": process_memory.rss / 1024 / 1024,
                "process_threads": process.num_threads(),
                "system_load": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            }
        except Exception as e:
            return {
                "system_cpu": 0.0,
                "system_memory": 0.0, 
                "process_cpu": 0.0,
                "process_memory_mb": 0.0,
                "process_threads": 0,
                "system_load": 0.0,
                "error": str(e)
            }
    
    def _create_header(self) -> Panel:
        """Create header panel"""
        uptime = timedelta(seconds=int(time.time() - self.start_time))
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        header_text = Text()
        header_text.append("🎯 RexTracking Service Monitor", style="bold magenta")
        header_text.append(f"  •  Uptime: {uptime}", style="cyan")
        header_text.append(f"  •  {current_time}", style="dim")
        
        return Panel(
            Align.center(header_text),
            box=box.ROUNDED,
            style="bright_blue"
        )
    
    def _create_service_status(self) -> Panel:
        """Create service status panel"""
        if not self.service_manager:
            status_text = Text("Service Manager: Not Connected", style="red")
            return Panel(status_text, title="🔧 Service Status", box=box.ROUNDED)
        
        # Get service metrics
        running = getattr(self.service_manager, 'running', False)
        camera_count = len(getattr(self.service_manager, 'camera_workers', {}))
        
        status_table = Table(box=None, show_header=False, padding=(0, 1))
        status_table.add_column("Metric", style="cyan")
        status_table.add_column("Value")
        
        # Service status
        status_style = "green" if running else "red"
        status_text = "🟢 Running" if running else "🔴 Stopped"
        status_table.add_row("Status", f"[{status_style}]{status_text}[/{status_style}]")
        
        # Camera count
        status_table.add_row("Cameras", f"[yellow]{camera_count}[/yellow]")
        
        # Health check
        if running and hasattr(self.service_manager, 'is_healthy'):
            health = self.service_manager.is_healthy()
            health_text = "🟢 Healthy" if health else "🟡 Issues"
            health_style = "green" if health else "yellow"
            status_table.add_row("Health", f"[{health_style}]{health_text}[/{health_style}]")
        
        return Panel(
            status_table,
            title="🔧 Service Status",
            box=box.ROUNDED,
            border_style="green" if running else "red"
        )
    
    def _create_system_metrics(self) -> Panel:
        """Create system metrics panel"""
        metrics = self.get_system_metrics()
        
        metrics_table = Table(box=None, show_header=False, padding=(0, 1))
        metrics_table.add_column("Metric", style="cyan") 
        metrics_table.add_column("Value")
        metrics_table.add_column("Bar", width=20)
        
        # System CPU
        cpu_color = "green" if metrics["system_cpu"] < 50 else "yellow" if metrics["system_cpu"] < 80 else "red"
        cpu_bar = "█" * int(metrics["system_cpu"] / 5) + "░" * (20 - int(metrics["system_cpu"] / 5))
        metrics_table.add_row(
            "System CPU", 
            f"[{cpu_color}]{metrics['system_cpu']:.1f}%[/{cpu_color}]",
            f"[{cpu_color}]{cpu_bar}[/{cpu_color}]"
        )
        
        # System Memory
        mem_color = "green" if metrics["system_memory"] < 50 else "yellow" if metrics["system_memory"] < 80 else "red"
        mem_bar = "█" * int(metrics["system_memory"] / 5) + "░" * (20 - int(metrics["system_memory"] / 5))
        metrics_table.add_row(
            "System RAM",
            f"[{mem_color}]{metrics['system_memory']:.1f}%[/{mem_color}]",
            f"[{mem_color}]{mem_bar}[/{mem_color}]"
        )
        
        # Process Memory
        proc_mem_mb = metrics["process_memory_mb"]
        mem_style = "green" if proc_mem_mb < 500 else "yellow" if proc_mem_mb < 1000 else "red"
        metrics_table.add_row(
            "Proc. Memory", 
            f"[{mem_style}]{proc_mem_mb:.1f} MB[/{mem_style}]",
            ""
        )
        
        # Process Threads
        thread_count = metrics["process_threads"]
        thread_style = "green" if thread_count < 20 else "yellow" if thread_count < 50 else "red"
        metrics_table.add_row(
            "Threads",
            f"[{thread_style}]{thread_count}[/{thread_style}]",
            ""
        )
        
        return Panel(
            metrics_table,
            title="📊 System Metrics",
            box=box.ROUNDED,
            border_style="bright_cyan"
        )
    
    def _create_gpu_metrics(self) -> Panel:
        """Create GPU metrics panel"""
        metrics = self.get_gpu_metrics()
        
        gpu_table = Table(box=None, show_header=False, padding=(0, 1))
        gpu_table.add_column("Metric", style="cyan")
        gpu_table.add_column("Value")
        gpu_table.add_column("Bar", width=20)
        
        # CUDA availability
        cuda_status = "🟢 Available" if metrics["cuda_available"] else "🔴 Not Available"
        cuda_style = "green" if metrics["cuda_available"] else "red"
        gpu_table.add_row("CUDA", f"[{cuda_style}]{cuda_status}[/{cuda_style}]", "")
        
        if metrics["cuda_available"] and metrics["gpu_count"] > 0:
            # GPU name (truncated)
            gpu_name = metrics["gpu_name"][:15] + "..." if len(metrics["gpu_name"]) > 15 else metrics["gpu_name"]
            gpu_table.add_row("Device", f"[bright_white]{gpu_name}[/bright_white]", "")
            
            # GPU utilization
            if metrics["gpu_utilization"] > 0:
                util_color = "green" if metrics["gpu_utilization"] < 50 else "yellow" if metrics["gpu_utilization"] < 80 else "red"
                util_bar = "█" * int(metrics["gpu_utilization"] / 5) + "░" * (20 - int(metrics["gpu_utilization"] / 5))
                gpu_table.add_row(
                    "GPU Load",
                    f"[{util_color}]{metrics['gpu_utilization']:.1f}%[/{util_color}]",
                    f"[{util_color}]{util_bar}[/{util_color}]"
                )
            
            # GPU memory
            if metrics["gpu_memory_total"] > 0:
                mem_color = "green" if metrics["gpu_memory_percent"] < 50 else "yellow" if metrics["gpu_memory_percent"] < 80 else "red"
                mem_bar = "█" * int(metrics["gpu_memory_percent"] / 5) + "░" * (20 - int(metrics["gpu_memory_percent"] / 5))
                gpu_table.add_row(
                    "GPU Memory",
                    f"[{mem_color}]{metrics['gpu_memory_used']:.1f}/{metrics['gpu_memory_total']:.1f}GB[/{mem_color}]",
                    f"[{mem_color}]{mem_bar}[/{mem_color}]"
                )
            
            # GPU temperature
            if metrics["gpu_temperature"] > 0:
                temp_color = "green" if metrics["gpu_temperature"] < 70 else "yellow" if metrics["gpu_temperature"] < 85 else "red"
                gpu_table.add_row(
                    "Temperature",
                    f"[{temp_color}]{metrics['gpu_temperature']:.0f}°C[/{temp_color}]",
                    ""
                )
        else:
            # No GPU or CUDA not available
            if not GPU_AVAILABLE:
                gpu_table.add_row("Status", "[dim]GPU libraries not installed[/dim]", "")
            elif not metrics["cuda_available"]:
                gpu_table.add_row("Status", "[yellow]CPU inference only[/yellow]", "")
        
        # Error handling
        if metrics["error"]:
            gpu_table.add_row("Error", f"[red]{metrics['error'][:30]}[/red]", "")
        
        border_style = "bright_green" if metrics["cuda_available"] else "yellow"
        title_emoji = "🚀" if metrics["cuda_available"] else "💻"
        
        return Panel(
            gpu_table,
            title=f"{title_emoji} GPU Status",
            box=box.ROUNDED,
            border_style=border_style
        )
    
    def _create_socket_info(self) -> Panel:
        """Create socket and WebSocket information panel"""
        current_sockets = self.get_socket_count()
        ws_info = self.get_websocket_info()
        
        # Update socket history
        self.socket_count_history.append((time.time(), current_sockets))
        if len(self.socket_count_history) > self.max_history:
            self.socket_count_history.pop(0)
        
        # Calculate socket trend
        if len(self.socket_count_history) >= 2:
            older_count = self.socket_count_history[0][1]
            trend = current_sockets - older_count
            if trend > 0:
                trend_text = f"[red]↗ +{trend}[/red]"
            elif trend < 0:
                trend_text = f"[green]↘ {trend}[/green]"
            else:
                trend_text = "[dim]→ 0[/dim]"
        else:
            trend_text = "[dim]→ 0[/dim]"
        
        # Get max sockets in history
        max_sockets = max([s[1] for s in self.socket_count_history]) if self.socket_count_history else 0
        
        socket_table = Table(box=None, show_header=False, padding=(0, 1))
        socket_table.add_column("Metric", style="cyan")
        socket_table.add_column("Value")
        
        # Socket monitoring
        socket_color = "green" if current_sockets < 20 else "yellow" if current_sockets < 50 else "red"
        socket_table.add_row("Sockets", f"[{socket_color}]{current_sockets}[/{socket_color}]")
        socket_table.add_row("Trend", trend_text)
        
        # Server status
        server_running = ws_info["server_running"]
        server_status = "🟢 Running" if server_running else "🔴 Stopped"
        server_style = "green" if server_running else "red"
        socket_table.add_row("Server", f"[{server_style}]{server_status}[/{server_style}]")
        
        # API port with better status indication
        api_port = ws_info["api_port"]
        port_listening = api_port in ws_info["listening_ports"]
        if server_running and port_listening:
            port_status = "🟢"
            port_style = "green"
        elif server_running and not port_listening:
            port_status = "🟡"  # Server running but port not listening
            port_style = "yellow"
        else:
            port_status = "🔴"
            port_style = "red"
        socket_table.add_row("API Port", f"{port_status} [{port_style}]{api_port}[/{port_style}]")
        
        # WebSocket information - only show if server is running
        if server_running and port_listening:
            ws_connections = ws_info["websocket_connections"]
            ws_color = "green" if ws_connections < 10 else "yellow" if ws_connections < 20 else "red"
            socket_table.add_row("WebSockets", f"[{ws_color}]{ws_connections}[/{ws_color}]")
            
            # Show active WebSocket channels only if there are connections
            active_channels = ws_info["active_channels"]
            if active_channels and any(count > 0 for count in active_channels.values()):
                channels_text = ", ".join([f"{ch}:{count}" for ch, count in active_channels.items() if count > 0])
                if channels_text:
                    socket_table.add_row("Channels", f"[dim]{channels_text[:25]}[/dim]")
        else:
            # Server not running - show this clearly
            socket_table.add_row("WebSockets", "[dim]N/A (server stopped)[/dim]")
        
        # Listening ports (show first few)
        if ws_info["listening_ports"]:
            ports_str = ", ".join(map(str, ws_info["listening_ports"][:4]))
            if len(ws_info["listening_ports"]) > 4:
                ports_str += "..."
            socket_table.add_row("Ports", f"[dim]{ports_str}[/dim]")
        else:
            socket_table.add_row("Ports", "[dim]None listening[/dim]")
        
        # Error handling
        if ws_info["error"]:
            socket_table.add_row("Error", f"[red]{ws_info['error'][:20]}[/red]")
        
        return Panel(
            socket_table,
            title="🔌 Network & WebSockets",
            box=box.ROUNDED,
            border_style="bright_yellow"
        )
    
    def _create_camera_grid(self) -> Panel:
        """Create camera status grid"""
        if not self.service_manager or not hasattr(self.service_manager, 'camera_workers'):
            return Panel(
                Align.center("No cameras configured"),
                title="📹 Cameras",
                box=box.ROUNDED,
                style="dim"
            )
        
        cameras = []
        for camera_id, worker in self.service_manager.camera_workers.items():
            metrics = worker.get_metrics() if hasattr(worker, 'get_metrics') else None
            
            if metrics:
                # Status indicator
                status_emoji = {
                    "running": "🟢",
                    "starting": "🟡", 
                    "stopping": "🟡",
                    "stopped": "🔴",
                    "error": "🔴"
                }.get(metrics.status, "⚪")
                
                # Create camera info box
                camera_info = f"{status_emoji} {camera_id[:12]}\n"
                camera_info += f"FPS: {metrics.fps_processed:.1f}\n"
                camera_info += f"Objects: {metrics.objects_count}\n"
                
                if metrics.latency_ms > 0:
                    camera_info += f"Latency: {metrics.latency_ms:.0f}ms"
                
                style = {
                    "running": "green",
                    "starting": "yellow",
                    "stopping": "yellow", 
                    "stopped": "red",
                    "error": "red"
                }.get(metrics.status, "dim")
                
                cameras.append(Panel(
                    camera_info,
                    style=style,
                    width=20,
                    height=6
                ))
        
        if not cameras:
            return Panel(
                Align.center("No active cameras"),
                title="📹 Cameras",
                box=box.ROUNDED,
                style="dim"
            )
        
        # Create columns of camera panels
        return Panel(
            Columns(cameras, equal=True, expand=True),
            title=f"📹 Cameras ({len(cameras)})",
            box=box.ROUNDED,
            border_style="bright_green"
        )
    
    def _create_activity_log(self) -> Panel:
        """Create recent activity summary panel"""
        log_text = Text()
        log_text.append("📝 Recent Activity\n", style="bold")
        
        if self.service_manager:
            log_text.append("• Service manager connected\n", style="green")
            
            if hasattr(self.service_manager, 'camera_workers'):
                active_cameras = len([w for w in self.service_manager.camera_workers.values() 
                                    if w.get_metrics().status == "running"])
                log_text.append(f"• {active_cameras} cameras active\n", style="cyan")
        else:
            log_text.append("• Waiting for service connection...\n", style="yellow")
        
        log_text.append(f"• Socket monitoring active\n", style="blue")
        log_text.append(f"• Last update: {datetime.now().strftime('%H:%M:%S')}", style="dim")
        
        return Panel(
            log_text,
            title="📋 Activity Log",
            box=box.ROUNDED,
            border_style="bright_magenta"
        )
    
    
    def _create_footer(self) -> Panel:
        """Create footer panel"""
        footer_text = Text()
        footer_text.append("Press ", style="dim")
        footer_text.append("Ctrl+C", style="bold red")
        footer_text.append(" to exit  •  Updates every ", style="dim")
        footer_text.append(f"{self.update_interval}s", style="bold")
        footer_text.append("  •  Socket leak monitoring enabled", style="dim green")
        
        return Panel(
            Align.center(footer_text),
            box=box.ROUNDED,
            style="dim"
        )
    
    def update_display(self):
        """Update all display components"""
        # Update layout components
        self.layout["header"].update(self._create_header())
        self.layout["service_status"].update(self._create_service_status())
        self.layout["system_metrics"].update(self._create_system_metrics())
        self.layout["gpu_metrics"].update(self._create_gpu_metrics())
        self.layout["socket_info"].update(self._create_socket_info())
        self.layout["camera_grid"].update(self._create_camera_grid())
        self.layout["activity_log"].update(self._create_activity_log())
        self.layout["footer"].update(self._create_footer())
        
        self.last_update = time.time()
    
    def run_live(self):
        """Run the live display"""
        try:
            with Live(
                self.layout,
                console=self.console,
                refresh_per_second=1,
                screen=True,
                vertical_overflow="visible"
            ) as live:
                try:
                    while True:
                        self.update_display()
                        time.sleep(self.update_interval)
                except KeyboardInterrupt:
                    pass
                finally:
                    self.cleanup()
        except Exception as e:
            print(f"Display not available: {e}")
            self.cleanup()
    
    
    def set_service_manager(self, service_manager):
        """Set the service manager reference"""
        self.service_manager = service_manager
    
    def cleanup_websockets(self):
        """Clean up stale WebSocket connections when server is stopped"""
        try:
            from ..api.websockets import manager as ws_manager
            if ws_manager:
                # If server is not running, clear all WebSocket connections
                if (not self.service_manager or 
                    not hasattr(self.service_manager, 'running') or 
                    not self.service_manager.running):
                    
                    # Clear all connection lists
                    for channel in ws_manager.active_connections:
                        ws_manager.active_connections[channel].clear()
                    
                    # Reset connection count
                    ws_manager._connection_count = 0
                    
                    # Cleaned up stale WebSocket connections
        except Exception:
            pass
    
    def cleanup(self):
        """Cleanup resources"""
        try:
            # Clean up WebSocket connections if needed
            self.cleanup_websockets()
            
            pass  # Log handler cleanup removed
        except Exception:
            pass