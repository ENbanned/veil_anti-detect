import gc
import json
import os
import time
import logging
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

class ProfileMetadata:
    def __init__(self, profile_path: str):
        self.profile_path = profile_path
        self.config_path = os.path.join(profile_path, "hardware_profile.json")
        self._file_handlers: List[logging.FileHandler] = []
        self._file_objects = []

    def load(self) -> dict:
        max_attempts = 3
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data
                return {}
            except json.JSONDecodeError as e:
                last_exception = e
                time.sleep(0.1)
            except Exception as e:
                return {}
                
        return {}


    def cleanup(self):        
        for handler in self._file_handlers:
            try:
                handler.flush()
                handler.close()
            except:
                pass
                
        for file_obj in self._file_objects:
            try:
                file_obj.close()
            except:
                pass
                
        self._file_handlers.clear()
        self._file_objects.clear()
        gc.collect()


    def save(self, data: dict):
        temp_path = self.config_path + '.tmp'
                
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            
            if os.path.exists(self.config_path):
                os.replace(temp_path, self.config_path)
            else:
                os.rename(temp_path, self.config_path)
                                
        except Exception as e:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass


    def update_proxy(self, proxy: Optional[str]):
        data = self.load()
        
        if proxy:
            parsed = urlparse(proxy)
            data["proxy"] = proxy
            data["proxy_ip"] = parsed.hostname
        else:
            data["proxy"] = ""
            data["proxy_ip"] = ""
            
        self.save(data)


    def update_status(self, is_active: bool):
        try:
            data = self.load()
            current_time = time.time()
            
            if is_active:
                data["status"] = "Active"
                data["last_heartbeat"] = current_time
                data["activation_time"] = current_time
            else:
                data["status"] = "Inactive"
                data["last_heartbeat"] = 0
                data["activation_time"] = 0
                
            self.save(data) 
        except:
            pass


    def update_last_launch(self):
        data = self.load()
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        data["last_launch"] = timestamp
        self.save(data)
        

    def __del__(self):
        self.cleanup()
