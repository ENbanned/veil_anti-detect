import logging
import os
import shutil
import subprocess
import sys
import time
from typing import Optional

from utils.logger import get_logger
from utils.profile_metadata import ProfileMetadata

HEARTBEAT_THRESHOLD = 5


class ChromeProcessManager:
    def __init__(self, base_dir: str = "chrome_profiles"):
        self.base_dir = os.path.abspath(base_dir)
        self.logger = get_logger("process_manager", console_output=True)
        
        self.logger.debug("Initializing ChromeProcessManager")
        self.logger.info(f"Base directory set to: {self.base_dir}")


    def get_profile_metadata(self, profile_id: int) -> ProfileMetadata:
        profile_path = self._get_profile_path(profile_id)
        self.logger.debug(f"Getting metadata for profile {profile_id}")
        return ProfileMetadata(profile_path)


    def _normalize_path(self, path: str) -> str:
        return os.path.normcase(os.path.normpath(os.path.abspath(path)))


    def _get_profile_path(self, profile_id: int) -> str:
        return os.path.join(self.base_dir, str(profile_id))


    def launch_profile(self, profile_path: str) -> Optional[int]:
        self.logger.info(f"Attempting to launch profile at {profile_path}")
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

            launcher_path = os.path.join(profile_path, "launcher.py")
            python_exe = sys.executable

            env = os.environ.copy()
            if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
                env["PYTHONPATH"] = os.pathsep.join(sys.path)
                env["VIRTUAL_ENV"] = sys.prefix

            process = subprocess.Popen(
                [python_exe, launcher_path],
                startupinfo=startupinfo,
                cwd=profile_path,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            self.logger.info(f"Successfully launched profile with PID {process.pid}")
            return process.pid

        except Exception as e:
            self.logger.error(f"Failed to launch profile: {str(e)}", exc_info=True)
            return None


    def is_profile_running(self, profile_id: int) -> bool:
        self.logger.debug(f"Checking status for profile {profile_id}")
        try:
            profile_path = self._get_profile_path(profile_id)
            metadata = ProfileMetadata(profile_path)
            data = metadata.load()
            status = data.get("status", "Inactive")
            heartbeat = data.get("last_heartbeat", 0)
            
            is_running = status == "Active" and (time.time() - heartbeat) < HEARTBEAT_THRESHOLD
            self.logger.debug(f"Profile {profile_id} running status: {is_running}")
            return is_running

        except Exception as e:
            self.logger.error(f"Error checking status for profile {profile_id}: {e}", exc_info=True)
            return False


    def close_profile(self, profile_id: int) -> bool:
        self.logger.info(f"Attempting to close profile {profile_id}")
        try:
            profile_path = self._get_profile_path(profile_id)
            shutdown_file = os.path.join(profile_path, "shutdown.flag")
            
            with open(shutdown_file, "w") as f:
                f.write("shutdown")
                
            self.logger.info(f"Created shutdown flag for profile {profile_id}")
            time.sleep(0.1)
            return True

        except Exception as e:
            self.logger.error(f"Failed to close profile {profile_id}: {e}", exc_info=True)
            return False


    def terminate_profile(self, profile_id: int) -> bool:
        self.logger.debug(f"Terminating profile {profile_id}")
        return self.close_profile(profile_id)


    def get_running_profiles(self) -> dict:
        self.logger.debug("Getting status of all profiles")
        result = {}
        
        if os.path.isdir(self.base_dir):
            for folder in os.listdir(self.base_dir):
                if folder.isdigit():
                    try:
                        profile_id = int(folder)
                        result[profile_id] = self.is_profile_running(profile_id)
                    except Exception as e:
                        self.logger.error(f"Error checking profile {folder}: {e}", exc_info=True)
                        continue

        self.logger.debug(f"Found {len(result)} profiles")
        return result
