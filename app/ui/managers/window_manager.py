from dataclasses import dataclass
import logging
import math
import time
from typing import Dict, List, Optional, Tuple

import psutil
from PySide6.QtCore import QObject, Signal
from utils.logger import get_logger

import win32api
import win32con
import win32gui
import win32process


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    pid: int
    profile_id: Optional[int]


class WindowManager(QObject):    
    window_arranged = Signal(int)
    window_restored = Signal(int)
    error_occurred = Signal(str)
    
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_positions: Dict[int, Tuple[int, int, int, int]] = {}
        self.logger = get_logger("window_manager")
        self.logger.debug("Initializing window manager")
        self._monitors = self._get_monitor_info()
        
        
    def _get_monitor_info(self) -> List[dict]:
        monitors = []
        try:
            monitor_info = []
            for i in range(65536):
                try:
                    info = win32api.GetMonitorInfo(win32api.MonitorFromPoint((i*1920, 0)))
                    monitor_info.append(info)
                except:
                    break

            for i, info in enumerate(monitor_info):
                monitors.append({
                    'handle': i,
                    'rect': info['Monitor'],
                    'working_area': info['Work']
                })
            
            if not monitors:
                monitors.append({
                    'handle': 0,
                    'rect': (0, 0, 1920, 1080),
                    'working_area': (0, 0, 1920, 1040)
                })

            self.logger.info(f"Found {len(monitors)} monitors")
            
            return monitors

        except Exception as e:
            self.logger.error(f"Failed to get monitor information: {e}", exc_info=True)
            return [{
                'handle': 0,
                'rect': (0, 0, 1920, 1080),
                'working_area': (0, 0, 1920, 1040)
            }]
            
    
    def _find_profile_windows(self, profile_ids: List[int]) -> List[WindowInfo]:
        chrome_windows = []
        
        
        def callback(hwnd, ctx):
            if not win32gui.IsWindowVisible(hwnd):
                return True
                
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                proc = psutil.Process(pid)
                
                if proc.name().lower() == 'chrome.exe':
                    cmdline = ' '.join(proc.cmdline())
                    
                    for profile_id in profile_ids:
                        if f"chrome_profiles\\{profile_id}" in cmdline:
                            title = win32gui.GetWindowText(hwnd)
                            if title and "Chrome" in title:
                                chrome_windows.append(WindowInfo(
                                    hwnd=hwnd,
                                    title=title,
                                    pid=pid,
                                    profile_id=profile_id
                                ))
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            return True
            
        win32gui.EnumWindows(callback, None)
        
        return chrome_windows
    
    
    def _save_window_position(self, hwnd: int):
        try:
            rect = win32gui.GetWindowRect(hwnd)
            self._original_positions[hwnd] = rect
        except Exception as e:
            self.error_occurred.emit(f"Ошибка сохранения позиции окна: {str(e)}")
    
    def arrange_windows(self, profile_ids: List[int], monitor_index: int = 0):
        try:
            windows = self._find_profile_windows(profile_ids)
            if not windows:
                self.error_occurred.emit("Активные окна браузера не найдены")
                return
            
            if monitor_index >= len(self._monitors):
                monitor_index = 0
            monitor = self._monitors[monitor_index]
            
            x, y, right, bottom = monitor['working_area']
            width = right - x
            height = bottom - y
            
            count = len(windows)
            cols = int(math.sqrt(count))
            rows = math.ceil(count / cols)
            
            window_width = width // cols
            window_height = height // rows
            
            for i, window in enumerate(windows):
                row = i // cols
                col = i % cols
                
                self._save_window_position(window.hwnd)
                
                new_x = x + (col * window_width)
                new_y = y + (row * window_height)
                
                try:
                    win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                    
                    win32gui.SetWindowPos(
                        window.hwnd,
                        win32con.HWND_TOP,
                        new_x,
                        new_y,
                        window_width,
                        window_height,
                        win32con.SWP_SHOWWINDOW
                    )
                    
                    time.sleep(0.1)
                    
                    self.window_arranged.emit(window.profile_id)
                    
                except Exception as e:
                    self.error_occurred.emit(f"Ошибка перемещения окна: {str(e)}")
                    
        except Exception as e:
            self.error_occurred.emit(f"Ошибка распределения окон: {str(e)}")
            
    
    def cascade_windows(self, profile_ids: List[int], monitor_index: int = 0):
        try:
            windows = self._find_profile_windows(profile_ids)
            if not windows:
                return
                
            monitor = self._monitors[monitor_index]
            x, y, right, bottom = monitor['working_area']
            
            offset = 30
            
            for i, window in enumerate(windows):
                try:
                    self._save_window_position(window.hwnd)
                    
                    win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                    
                    new_x = x + (i * offset)
                    new_y = y + (i * offset)
                    width = (right - x) // 2
                    height = (bottom - y) // 2
                    
                    win32gui.SetWindowPos(
                        window.hwnd,
                        win32con.HWND_TOP,
                        new_x, new_y, width, height,
                        win32con.SWP_SHOWWINDOW
                    )
                    
                    self.window_arranged.emit(window.profile_id)
                    
                except Exception as e:
                    self.error_occurred.emit(f"Ошибка каскадного размещения окна: {str(e)}")
                    
        except Exception as e:
            self.error_occurred.emit(f"Ошибка каскадного размещения окон: {str(e)}")
            
    
    def tile_windows_horizontally(self, profile_ids: List[int], monitor_index: int = 0):
        try:
            windows = self._find_profile_windows(profile_ids)
            if not windows:
                return
                
            monitor = self._monitors[monitor_index]
            x, y, right, bottom = monitor['working_area']
            width = right - x
            height = bottom - y
            
            window_height = height // len(windows)
            
            for i, window in enumerate(windows):
                try:
                    self._save_window_position(window.hwnd)
                    win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                    
                    win32gui.SetWindowPos(
                        window.hwnd,
                        win32con.HWND_TOP,
                        x,
                        y + (i * window_height),
                        width,
                        window_height,
                        win32con.SWP_SHOWWINDOW
                    )
                    
                    self.window_arranged.emit(window.profile_id)
                    
                except Exception as e:
                    self.error_occurred.emit(f"Ошибка горизонтального размещения окна: {str(e)}")
                    
        except Exception as e:
            self.error_occurred.emit(f"Ошибка горизонтального размещения окон: {str(e)}")
    
    
    def tile_windows_vertically(self, profile_ids: List[int], monitor_index: int = 0):
        try:
            windows = self._find_profile_windows(profile_ids)
            if not windows:
                return
                
            monitor = self._monitors[monitor_index]
            x, y, right, bottom = monitor['working_area']
            width = right - x
            height = bottom - y
            
            window_width = width // len(windows)
            
            for i, window in enumerate(windows):
                try:
                    self._save_window_position(window.hwnd)
                    win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                    
                    win32gui.SetWindowPos(
                        window.hwnd,
                        win32con.HWND_TOP,
                        x + (i * window_width),
                        y,
                        window_width,
                        height,
                        win32con.SWP_SHOWWINDOW
                    )
                    
                    self.window_arranged.emit(window.profile_id)
                    
                except Exception as e:
                    self.error_occurred.emit(f"Ошибка вертикального размещения окна: {str(e)}")
                    
        except Exception as e:
            self.error_occurred.emit(f"Ошибка вертикального размещения окон: {str(e)}")

    def bring_window_to_front(self, profile_id: int) -> bool:
        try:
            windows = self._find_profile_windows([profile_id])
            if not windows:
                return False
                
            window = windows[0]
            try:
                win32gui.ShowWindow(window.hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(window.hwnd)
                return True
            except Exception as e:
                self.error_occurred.emit(f"Ошибка при разворачивании окна: {str(e)}")
                return False
                
        except Exception as e:
            self.error_occurred.emit(f"Ошибка поиска окна: {str(e)}")
            return False