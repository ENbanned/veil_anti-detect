import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import urlparse
from typing import Optional

from extensions.browser_extension import BrowserExtension
from extensions.hardware_profiles import HardwareProfileGenerator
from process_manager import ChromeProcessManager
from utils.profile_metadata import ProfileMetadata
from utils.ip_info import IPInfoManager

from utils.logger import get_logger


class ChromeProfileManager:
    def __init__(self, base_dir: str = "chrome_profiles"):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.join(self.project_root, base_dir)
        self.hw_generator = HardwareProfileGenerator()
        self.process_manager = ChromeProcessManager(self.base_dir)
        self.logger = get_logger("chrome_manager")
        os.makedirs(self.base_dir, exist_ok=True)


    def _create_launcher(self, profile_path: str):
        template_path = os.path.join(self.project_root, "launcher_template.py")
        launcher_path = os.path.join(profile_path, "launcher.py")
        shutil.copy2(template_path, launcher_path)

        profile_utils_dir = os.path.join(profile_path, "utils")
        profile_extensions_dir = os.path.join(profile_path, "extensions")
        os.makedirs(profile_utils_dir, exist_ok=True)
        os.makedirs(profile_extensions_dir, exist_ok=True)

        utils_src = os.path.join(self.project_root, "utils")
        required_files = ['__init__.py', 'ip_info.py', 'countries.py', 'random_user_agent.py', 'profile_metadata.py', 'logger_manager.py', 'canvas_url.py']
        for file in required_files:
            src_file = os.path.join(utils_src, file)
            dst_file = os.path.join(profile_utils_dir, file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
            else:
                self.logger.warning(f"Required file not found: {src_file}")

        extensions_src = os.path.join(self.project_root, "extensions")
        required_extensions = ['__init__.py', 'hardware_profiles.py', 'browser_extension.py']
        for file in required_extensions:
            src_file = os.path.join(extensions_src, file)
            dst_file = os.path.join(profile_extensions_dir, file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_file)
            else:
                self.logger.warning(f"Required extension file not found: {src_file}")

        activate_path = os.path.join(profile_path, "activate.bat")
        venv_activate = os.path.join(os.path.dirname(os.path.dirname(sys.executable)), "Scripts", "activate.bat")
        activate_content = f'''@echo off
call "{venv_activate}"
python "%~dp0launcher.py"
if errorlevel 1 (
    echo.
    echo An error occurred while launching the profile.
    echo Check profile.log for details.
    pause
)'''
        with open(activate_path, 'w', encoding='utf-8') as f:
            f.write(activate_content)

        bat_path = os.path.join(profile_path, "start.bat")
        bat_content = '''@echo off
start /min "" cmd /c "chcp 65001 > nul & title Chrome Profile & cd /d "%~dp0" & call activate.bat"'''
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)


    def get_proxy_from_background_js(self, profile_id: int) -> Optional[str]:
        try:
            profile_name = str(profile_id)
            ext_path = os.path.join(self.base_dir, profile_name, "extensions", "proxy_extension", "background.js")
            
            if not os.path.exists(ext_path):
                return None
            
            with open(ext_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            host_match = re.search(r'host:\s*"([^"]+)"', content)
            port_match = re.search(r'port:\s*(\d+)', content)
            username_match = re.search(r'username:\s*"([^"]*)"', content)
            password_match = re.search(r'password:\s*"([^"]*)"', content)
            
            if host_match and port_match:
                host = host_match.group(1)
                port = port_match.group(1)
                username = username_match.group(1) if username_match else ""
                password = password_match.group(1) if password_match else ""
                auth_part = f"{username}:{password}@" if username or password else ""
                return f"http://{auth_part}{host}:{port}"
            
            return None
        except Exception as e:
            self.logger.error(f"Error reading proxy from background.js: {str(e)}")
            return None


    def update_profile_proxy(self, profile_id: str, proxy: Optional[str]) -> bool:
        try:
            profile_path = os.path.join(self.base_dir, str(profile_id))
            if not os.path.exists(profile_path):
                self.logger.error(f"Profile {profile_id} not found")
                return False

            self.process_manager.terminate_profile(int(profile_id))

            metadata = ProfileMetadata(profile_path)
            hardware_profile = metadata.load()
            if not hardware_profile:
                self.logger.error(f"No hardware_profile found for {profile_id}")
                return False

            paths_to_clear = [
                ("Default/Network/Network Persistent State", False),
                ("Default/Service Worker", True),
                ("Default/Extension State", True),
                ("extensions/proxy_extension", True)
            ]
            
            for rel_path, is_dir in paths_to_clear:
                fp = os.path.join(profile_path, rel_path)
                if os.path.exists(fp):
                    try:
                        if is_dir:
                            shutil.rmtree(fp)
                        else:
                            with open(fp, 'w') as f:
                                f.write('{"net":{"http_server_properties":{"servers":[],"version":5},"network_qualities":{}}}')
                    except Exception as e:
                        self.logger.warning(f"Error clearing {rel_path}: {e}")

            extension = BrowserExtension(profile_path=profile_path)

            if proxy:
                parsed = urlparse(proxy)
                hardware_profile.setdefault("proxy", {})
                hardware_profile["proxy"]["host"] = parsed.hostname
                hardware_profile["proxy"]["port"] = parsed.port
                hardware_profile["proxy"]["username"] = parsed.username or ""
                hardware_profile["proxy"]["password"] = parsed.password or ""
                hardware_profile["proxy_ip"] = parsed.hostname

                geo_data = IPInfoManager.get_ip_info(parsed.hostname)
                if geo_data:
                    hardware_profile["lang"] = geo_data.languages
                    hardware_profile["timezone"] = geo_data.timezone
                    hardware_profile["browser_language"] = geo_data.languages.split('-')[0]
                else:
                    hardware_profile["lang"] = hardware_profile.get("lang", "en-US")
                    hardware_profile["timezone"] = hardware_profile.get("timezone", "UTC")
                    hardware_profile["browser_language"] = hardware_profile.get("browser_language", "en")

                geo_loc = extension._get_location_data()
                hardware_profile = extension.hw_generator._apply_geolocation(hardware_profile, geo_loc)

            else:
                hardware_profile["proxy"] = {}
                hardware_profile["proxy_ip"] = ""

                geo_loc = extension._get_random_location()
                hardware_profile = extension.hw_generator._apply_geolocation(hardware_profile, geo_loc)

            metadata.save(hardware_profile)

            extension.setup(hardware_profile, "Chrome Proxy", "1.0.0")

            self.logger.info(
                f"Profile {profile_id} proxy updated:"
                f"\nProxy: {proxy if proxy else 'None'}"
                f"\nLanguage: {hardware_profile.get('lang', 'en-US')}"
                f"\nTimezone: {hardware_profile.get('timezone', 'UTC')}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error updating proxy for profile {profile_id}: {e}")
            return False


    def _get_next_id(self) -> int:
        existing_ids = []
        if os.path.isdir(self.base_dir):
            for folder in os.listdir(self.base_dir):
                if folder.isdigit():
                    existing_ids.append(int(folder))
        return max(existing_ids) + 1 if existing_ids else 1


    def create_profile(self, display_name: str, proxy: Optional[str] = None) -> bool:
        try:
            new_id = self._get_next_id()
            folder_name = str(new_id)
            profile_path = os.path.join(self.base_dir, folder_name)
            os.makedirs(profile_path)

            hardware_profile = self.hw_generator.generate_profile(display_name)
            hardware_profile["display_name"] = display_name
            hardware_profile["status"] = "Inactive"
            hardware_profile["proxy_ip"] = ""
            hardware_profile["last_launch"] = None
            hardware_profile["last_heartbeat"] = 0
            hardware_profile["notes"] = ""

            from utils.canvas_url import CanvasDataUrl
            canvas_obj = CanvasDataUrl()
            try:
                hardware_profile["canvas_data_url"] = canvas_obj.get_fingerprint()
            except:
                hardware_profile["canvas_data_url"] = "data:image/png;base64,ANY_DEFAULT_IF_NEEDED"

            mac = hardware_profile["device"]["mac"]
            mac_nosep = mac.replace(':', '')
            hardware_profile["audio"] = {
                "deviceId": f"audio_{mac_nosep}",
                "label": 'High Definition Audio Device',
                "groupId": f"audio_group_{mac_nosep}"
            }
            hardware_profile["video"] = {
                "deviceId": f"video_{mac_nosep}",
                "label": f"{hardware_profile['gpu']['vendor']} Camera",
                "groupId": f"video_group_{mac_nosep}"
            }

            if not hardware_profile.get("user_agent"):
                hardware_profile["user_agent"] = (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/113.0.0.0 Safari/537.36"
                )

            if proxy:
                parsed = urlparse(proxy)
                if parsed.hostname:
                    hardware_profile["proxy_ip"] = parsed.hostname
                    geo_data = IPInfoManager.get_ip_info(parsed.hostname)
                    if geo_data:
                        hardware_profile["lang"] = geo_data.languages
                        hardware_profile["timezone"] = geo_data.timezone
                        hardware_profile["browser_language"] = geo_data.languages.split('-')[0]
                    else:
                        hardware_profile["lang"] = "en-US"
                        hardware_profile["timezone"] = "UTC"
                        hardware_profile["browser_language"] = "en"

                    hardware_profile["proxy"] = {
                        "host": parsed.hostname,
                        "port": parsed.port,
                        "username": parsed.username or "",
                        "password": parsed.password or ""
                    }
                else:
                    hardware_profile["proxy"] = {}
            else:
                hardware_profile["proxy"] = {}

            metadata = ProfileMetadata(profile_path)
            metadata.save(hardware_profile)

            extension = BrowserExtension(profile_path=profile_path)
            extension.setup(hardware_profile, "Chrome Proxy", "1.0.0")

            self._create_launcher(profile_path)
            self.logger.info(f"Profile with ID {new_id} created at {profile_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error creating profile: {e}")
            if os.path.exists(profile_path):
                shutil.rmtree(profile_path)
            return False


    def list_profiles(self) -> list:
        results = []
        if not os.path.exists(self.base_dir):
            return results

        running_profiles = self.process_manager.get_running_profiles()

        for folder in os.listdir(self.base_dir):
            if folder.isdigit():
                try:
                    profile_id = int(folder)
                    profile_path = os.path.join(self.base_dir, folder)
                    metadata = ProfileMetadata(profile_path)
                    data = metadata.load()
                    is_running = running_profiles.get(profile_id, False)
                    heartbeat = data.get("last_heartbeat", 0)
                    if is_running and (time.time() - heartbeat > 10):
                        is_running = False
                        metadata.update_status(False)
                        data["status"] = "Inactive"
                    results.append({
                        "id": profile_id,
                        "display_name": data.get("display_name", ""),
                        "status": data.get("status", "Inactive"),
                        "proxy_ip": data.get("proxy_ip", ""),
                        "last_launch": data.get("last_launch", ""),
                        "notes": data.get("notes", "")
                    })
                except Exception as e:
                    self.logger.error(f"Error retrieving info for profile {folder}: {str(e)}")
                    continue

        return sorted(results, key=lambda x: x["id"])


    def launch_profile(self, pid: int) -> bool:
        try:
            folder_name = str(pid)
            profile_path = os.path.join(self.base_dir, folder_name)
            launcher_path = os.path.join(profile_path, "launcher.py")
            if not os.path.exists(launcher_path):
                self.logger.error(f"launcher.py not found for profile ID {pid}")
                return False

            if self.process_manager.is_profile_running(pid):
                self.logger.info(f"Profile {pid} is already running")
                return True

            pythonw_exe = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
            startup_info = subprocess.STARTUPINFO()
            startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            subprocess.Popen(
                [pythonw_exe, launcher_path],
                cwd=profile_path,
                startupinfo=startup_info,
                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            self.logger.info(f"Launched profile {pid} (asynchronously)")
            return True

        except Exception as e:
            self.logger.error(f"Error launching profile {pid}: {e}")
            return False


    def close_profile(self, pid: int) -> bool:
        return self.process_manager.close_profile(pid)


    def delete_profile(self, pid: int) -> bool:
        try:
            profile_path = os.path.join(self.base_dir, str(pid))
            self.logger.info(f"Deleting profile {pid} at {profile_path}")

            if self.process_manager.is_profile_running(pid):
                self.logger.info(f"Terminating running profile {pid}")
                self.process_manager.terminate_profile(pid)
                time.sleep(2)

            metadata = ProfileMetadata(profile_path)
            try:
                metadata.cleanup()
            except Exception as e:
                self.logger.warning(f"Error cleaning up metadata for profile {pid}: {e}")

            for name in list(logging.root.manager.loggerDict.keys()):
                if str(pid) in name:
                    logger = logging.getLogger(name)
                    for handler in logger.handlers[:]:
                        try:
                            handler.close()
                            logger.removeHandler(handler)
                        except:
                            pass
                    logging.root.manager.loggerDict.pop(name, None)

            def force_close_files(directory):
                import psutil
                current_process = psutil.Process()
                for handler in current_process.open_files():
                    if directory in handler.path:
                        try:
                            os.close(handler.fd)
                        except:
                            pass

            force_close_files(profile_path)

            import gc
            gc.collect()

            time.sleep(0.5)

            if os.path.exists(profile_path):
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        log_file = os.path.join(profile_path, "profile.log")
                        if os.path.exists(log_file):
                            try:
                                os.chmod(log_file, 0o777)
                                os.unlink(log_file)
                            except:
                                pass

                        def on_error(func, path, exc_info):
                            try:
                                os.chmod(path, 0o777)
                                func(path)
                            except:
                                pass

                        shutil.rmtree(profile_path, onerror=on_error)
                        self.logger.info(f"Profile {pid} successfully deleted")
                        return True
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            self.logger.error(f"Failed to delete profile {pid} after {max_attempts} attempts: {e}")
                            return False
                        self.logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                        time.sleep(2)
            else:
                self.logger.info(f"Profile folder {pid} already deleted")
                return True

        except Exception as e:
            self.logger.error(f"Error deleting profile {pid}: {str(e)}")
            return False
        