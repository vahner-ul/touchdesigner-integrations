"""
Network scanner for IP cameras
"""
import asyncio
import socket
import ipaddress
from typing import List, Dict, Optional, Set
import aiohttp
import concurrent.futures
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class DiscoveredCamera:
    ip: str
    port: int
    protocol: str  # "rtsp", "http", "onvif"
    url: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    is_accessible: bool = False

class NetworkScanner:
    """Сканер сети для поиска IP камер"""
    
    def __init__(self, network_range: str = "192.168.1.0/24", timeout: float = 2.0):
        self.network_range = network_range
        self.timeout = timeout
        self.common_ports = {
            80: "http",
            8080: "http", 
            554: "rtsp",
            8554: "rtsp",
            8000: "rtsp",
            9000: "rtsp"
        }
        
        # Стандартные учетные данные для камер
        self.common_credentials = [
            ("admin", "admin"),
            ("admin", "password"),
            ("admin", "12345"),
            ("admin", "123456"),
            ("admin", ""),
            ("root", "root"),
            ("root", "password"),
            ("user", "user"),
            ("", "")
        ]
    
    async def scan_network(self) -> List[DiscoveredCamera]:
        """Сканирует сеть на наличие IP камер"""
        logger.info(f"Starting network scan for range: {self.network_range}")
        
        try:
            network = ipaddress.IPv4Network(self.network_range, strict=False)
            ip_addresses = [str(ip) for ip in network.hosts()]
        except ValueError as e:
            logger.error(f"Invalid network range {self.network_range}: {e}")
            return []
        
        discovered_cameras = []
        
        # Сканируем IP адреса на наличие открытых портов
        open_ips = await self._scan_ports(ip_addresses)
        logger.info(f"Found {len(open_ips)} IPs with open camera ports")
        
        # Проверяем каждый IP на наличие камеры
        for ip, ports in open_ips.items():
            for port in ports:
                camera = await self._check_camera(ip, port)
                if camera:
                    discovered_cameras.append(camera)
        
        logger.info(f"Discovered {len(discovered_cameras)} cameras")
        return discovered_cameras
    
    async def _scan_ports(self, ip_addresses: List[str]) -> Dict[str, Set[int]]:
        """Сканирует порты на указанных IP адресах"""
        open_ips = {}
        
        # Создаем задачи для сканирования портов
        tasks = []
        for ip in ip_addresses:
            task = self._scan_ip_ports(ip)
            tasks.append(task)
        
        # Выполняем сканирование параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, dict) and result:
                open_ips[ip_addresses[i]] = result
        
        return open_ips
    
    async def _scan_ip_ports(self, ip: str) -> Set[int]:
        """Сканирует порты на одном IP адресе"""
        open_ports = set()
        
        # Создаем задачи для каждого порта
        tasks = []
        for port in self.common_ports.keys():
            task = self._check_port(ip, port)
            tasks.append(task)
        
        # Выполняем проверку портов параллельно
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, is_open in enumerate(results):
            if isinstance(is_open, bool) and is_open:
                port = list(self.common_ports.keys())[i]
                open_ports.add(port)
        
        return open_ports
    
    async def _check_port(self, ip: str, port: int) -> bool:
        """Проверяет, открыт ли порт на IP адресе"""
        try:
            # Используем ThreadPoolExecutor для синхронных операций
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = loop.run_in_executor(
                    executor, 
                    self._check_port_sync, 
                    ip, 
                    port
                )
                return await asyncio.wait_for(future, timeout=self.timeout)
        except (asyncio.TimeoutError, Exception):
            return False
    
    def _check_port_sync(self, ip: str, port: int) -> bool:
        """Синхронная проверка порта"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((ip, port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    async def _check_camera(self, ip: str, port: int) -> Optional[DiscoveredCamera]:
        """Проверяет, является ли устройство камерой"""
        protocol = self.common_ports.get(port, "unknown")
        
        if protocol == "rtsp":
            return await self._check_rtsp_camera(ip, port)
        elif protocol == "http":
            return await self._check_http_camera(ip, port)
        
        return None
    
    async def _check_rtsp_camera(self, ip: str, port: int) -> Optional[DiscoveredCamera]:
        """Проверяет RTSP камеру"""
        # Стандартные RTSP пути
        rtsp_paths = [
            "/live/ch0",
            "/live/ch00_0",
            "/live/ch01_0",
            "/live/av0",
            "/live/av1",
            "/live",
            "/cam/realmonitor",
            "/axis-media/media.amp",
            "/onvif1",
            "/onvif2",
            "/h264Preview_01_main",
            "/h264Preview_01_sub",
            "/live/ch0_0",
            "/live/ch0_1",
            "/live/ch1_0",
            "/live/ch1_1"
        ]
        
        for path in rtsp_paths:
            url = f"rtsp://{ip}:{port}{path}"
            if await self._test_rtsp_url(url):
                return DiscoveredCamera(
                    ip=ip,
                    port=port,
                    protocol="rtsp",
                    url=url,
                    is_accessible=True
                )
        
        # Если не нашли рабочий путь, возвращаем базовый URL
        return DiscoveredCamera(
            ip=ip,
            port=port,
            protocol="rtsp",
            url=f"rtsp://{ip}:{port}/live",
            is_accessible=False
        )
    
    async def _check_http_camera(self, ip: str, port: int) -> Optional[DiscoveredCamera]:
        """Проверяет HTTP камеру"""
        try:
            url = f"http://{ip}:{port}"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return DiscoveredCamera(
                            ip=ip,
                            port=port,
                            protocol="http",
                            url=url,
                            is_accessible=True
                        )
        except Exception:
            pass
        
        return None
    
    async def _test_rtsp_url(self, url: str) -> bool:
        """Тестирует RTSP URL (базовая проверка)"""
        try:
            # Для RTSP используем простую проверку через curl или ffprobe
            # В реальной реализации можно использовать библиотеку для работы с RTSP
            import subprocess
            
            # Пробуем использовать ffprobe для проверки RTSP потока
            cmd = [
                "ffprobe", 
                "-v", "quiet", 
                "-print_format", "json", 
                "-show_streams", 
                "-timeout", str(int(self.timeout * 1000000)),  # в микросекундах
                url
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                await asyncio.wait_for(process.communicate(), timeout=self.timeout)
                return process.returncode == 0
            except asyncio.TimeoutError:
                process.terminate()
                return False
                
        except (FileNotFoundError, Exception):
            # Если ffprobe недоступен, возвращаем True (предполагаем что камера есть)
            return True
    
    async def test_camera_credentials(self, camera: DiscoveredCamera) -> List[tuple]:
        """Тестирует стандартные учетные данные для камеры"""
        working_credentials = []
        
        if camera.protocol == "rtsp":
            for username, password in self.common_credentials:
                if await self._test_rtsp_credentials(camera.url, username, password):
                    working_credentials.append((username, password))
        
        return working_credentials
    
    async def _test_rtsp_credentials(self, url: str, username: str, password: str) -> bool:
        """Тестирует учетные данные для RTSP"""
        try:
            # Извлекаем базовый URL без учетных данных
            if "://" in url:
                protocol, rest = url.split("://", 1)
                if "@" in rest:
                    rest = rest.split("@", 1)[1]
                base_url = f"{protocol}://{rest}"
            else:
                base_url = url
            
            # Формируем URL с учетными данными
            if username and password:
                test_url = f"{protocol}://{username}:{password}@{rest}"
            elif username:
                test_url = f"{protocol}://{username}@{rest}"
            else:
                test_url = url
            
            return await self._test_rtsp_url(test_url)
            
        except Exception:
            return False

# Глобальный экземпляр сканера
_network_scanner: Optional[NetworkScanner] = None

def get_network_scanner(network_range: str = "192.168.1.0/24") -> NetworkScanner:
    """Получает глобальный экземпляр сканера сети"""
    global _network_scanner
    if _network_scanner is None or _network_scanner.network_range != network_range:
        _network_scanner = NetworkScanner(network_range)
    return _network_scanner
