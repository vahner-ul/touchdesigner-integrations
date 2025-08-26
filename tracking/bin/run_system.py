#!/usr/bin/env python3
"""
Скрипт для запуска всей системы RexTracking
Включает FastAPI сервер и веб-интерфейс
"""
import subprocess
import sys
import os
import time
import signal
import argparse
from pathlib import Path

def run_command(cmd, cwd=None, env=None):
    """Запуск команды с выводом в реальном времени"""
    print(f"Running: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
            shell=True  # Добавляем shell=True для Windows
        )
        
        # Выводим логи в реальном времени
        for line in process.stdout:
            print(line.rstrip())
        
        return process.wait()
    except FileNotFoundError as e:
        print(f"Error: Command not found - {e}")
        return 1
    except Exception as e:
        print(f"Error running command: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="RexTracking System Launcher")
    parser.add_argument("--api-port", type=int, default=8080, help="FastAPI server port")
    parser.add_argument("--web-port", type=int, default=3000, help="Web interface port")
    parser.add_argument("--api-only", action="store_true", help="Run only FastAPI server")
    parser.add_argument("--web-only", action="store_true", help="Run only web interface")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    
    args = parser.parse_args()
    
    # Определяем пути
    base_dir = Path(__file__).parent
    web_dir = base_dir / "web"
    
    # Проверяем наличие необходимых файлов
    if not (base_dir / "server.py").exists():
        print("Error: server.py not found")
        sys.exit(1)
    
    if not web_dir.exists():
        print("Error: web directory not found")
        sys.exit(1)
    
    # Устанавливаем переменные окружения
    env = os.environ.copy()
    if args.config:
        env["REXTRACKING_CONFIG"] = args.config
    
    # Устанавливаем порт для веб-интерфейса
    env["NEXT_PUBLIC_API_URL"] = f"http://localhost:{args.api_port}"
    
    processes = []
    
    try:
        if not args.web_only:
            print("=" * 50)
            print("Starting FastAPI Server...")
            print("=" * 50)
            
            # Запускаем FastAPI сервер
            api_cmd = [
                sys.executable, "server.py",
                "--host", "0.0.0.0",
                "--port", str(args.api_port),
                "--log-level", "info"
            ]
            
            if args.config:
                api_cmd.extend(["--config", args.config])
            
            api_process = subprocess.Popen(
                api_cmd,
                cwd=base_dir,
                env=env
            )
            processes.append(("FastAPI Server", api_process))
            
            # Ждем немного, чтобы сервер запустился
            time.sleep(3)
        
        if not args.api_only:
            print("=" * 50)
            print("Starting Web Interface...")
            print("=" * 50)
            
            # Проверяем наличие npm
            try:
                subprocess.run(["npm", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("Error: npm not found. Please install Node.js and npm first.")
                print("Download from: https://nodejs.org/")
                if not args.web_only:
                    print("Continuing with API server only...")
                else:
                    sys.exit(1)
            
            # Проверяем, установлены ли зависимости веб-интерфейса
            if not (web_dir / "node_modules").exists():
                print("Installing web dependencies...")
                if run_command(["npm", "install"], cwd=web_dir) != 0:
                    print("Error: Failed to install web dependencies")
                    if not args.web_only:
                        print("Continuing with API server only...")
                    else:
                        sys.exit(1)
            
            # Запускаем веб-интерфейс
            try:
                web_cmd = ["npm", "run", "dev", "--", "--port", str(args.web_port)]
                web_process = subprocess.Popen(
                    web_cmd,
                    cwd=web_dir,
                    env=env,
                    shell=True  # Добавляем shell=True для Windows
                )
                processes.append(("Web Interface", web_process))
            except Exception as e:
                print(f"Error starting web interface: {e}")
                if not args.web_only:
                    print("Continuing with API server only...")
                else:
                    sys.exit(1)
        
        print("=" * 50)
        print("System started successfully!")
        print("=" * 50)
        
        if not args.web_only:
            print(f"FastAPI Server: http://localhost:{args.api_port}")
            print(f"API Documentation: http://localhost:{args.api_port}/docs")
        
        if not args.api_only:
            print(f"Web Interface: http://localhost:{args.web_port}")
        
        print("=" * 50)
        print("Press Ctrl+C to stop all services")
        print("=" * 50)
        
        # Ждем завершения процессов
        try:
            while processes:
                for name, process in processes[:]:
                    if process.poll() is not None:
                        print(f"{name} stopped with code {process.returncode}")
                        processes.remove((name, process))
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down services...")
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    finally:
        # Останавливаем все процессы
        for name, process in processes:
            print(f"Stopping {name}...")
            try:
                if os.name == 'nt':  # Windows
                    process.terminate()
                else:  # Unix/Linux
                    process.terminate()
                
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"Force killing {name}...")
                    if os.name == 'nt':  # Windows
                        process.kill()
                    else:  # Unix/Linux
                        process.kill()
            except Exception as e:
                print(f"Error stopping {name}: {e}")
        
        print("All services stopped")

if __name__ == "__main__":
    main()
