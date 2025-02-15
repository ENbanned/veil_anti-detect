from __future__ import annotations

import json
import os
import random
import shutil
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import urlparse

from utils.canvas_url import CanvasDataUrl
from utils.ip_info import IPInfoManager
from utils.logger import get_logger
from .hardware_profiles import HardwareProfileGenerator


@dataclass
class GeoLocation:
    latitude: float
    longitude: float
    accuracy: float
    timezone: str = "UTC"
    lang: str = "en-US"


class BrowserExtension:
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, 
                 username: str = "", password: str = "", profile_path: str = "") -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.profile_path = profile_path
        self.extension_js_dir = os.path.join(os.path.dirname(__file__), 'extension_js')
        
        self.logger = get_logger("browser_extension")
        self.logger.debug("Initializing BrowserExtension")
        self.logger.info(f"Configuration - Host: {self.host}, Port: {self.port}")
        self.logger.info(f"Profile path: {self.profile_path}")
        
        self.canvas = CanvasDataUrl()
        self.hw_generator = HardwareProfileGenerator()


    def _get_random_location(self) -> GeoLocation:
        self.logger.debug("Generating random geolocation")
        realistic_locations = [
            {"city": "London", "lat": 51.5074, "lon": -0.1278, "country": "GB"},
            {"city": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "FR"},
            {"city": "Berlin", "lat": 52.5200, "lon": 13.4050, "country": "DE"},
            {"city": "Madrid", "lat": 40.4168, "lon": -3.7038, "country": "ES"},
            {"city": "Rome", "lat": 41.9028, "lon": 12.4964, "country": "IT"},
            {"city": "Amsterdam", "lat": 52.3676, "lon": 4.9041, "country": "NL"},
            {"city": "Vienna", "lat": 48.2082, "lon": 16.3738, "country": "AT"},
            {"city": "Stockholm", "lat": 59.3293, "lon": 18.0686, "country": "SE"},
            {"city": "Prague", "lat": 50.0755, "lon": 14.4378, "country": "CZ"},
            {"city": "Brussels", "lat": 50.8503, "lon": 4.3517, "country": "BE"}
        ]
        location = random.choice(realistic_locations)
        lat_offset: float = random.uniform(-0.01, 0.01)
        lon_offset: float = random.uniform(-0.01, 0.01)
        return GeoLocation(
            latitude=location["lat"] + lat_offset,
            longitude=location["lon"] + lon_offset,
            accuracy=random.uniform(50, 100),
            timezone="UTC"
        )


    def _get_location_data(self) -> GeoLocation:
        self.logger.debug(f"Attempting to get location data for host: {self.host}")
        if self.host:
            try:
                geo_data = IPInfoManager.get_ip_info(self.host)
                if geo_data:
                    self.logger.info(f"Got location data for host {self.host}")
                    return GeoLocation(
                        latitude=geo_data.latitude,
                        longitude=geo_data.longitude,
                        accuracy=geo_data.accuracy,
                        timezone=geo_data.timezone,
                        lang=geo_data.languages
                    )
            except Exception as e:
                self.logger.error(f"Failed to get IP location data: {e}", exc_info=True)
        
        self.logger.debug("Using random location as fallback")
        return self._get_random_location()


    def _load_js_file(self, filename: str) -> str:
        self.logger.debug(f"Loading JS file: {filename}")
        file_path = os.path.join(self.extension_js_dir, filename)
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()


    def setup(self, hardware_profile: dict | None = None, 
             name: str = "Chrome Proxy", version: str = "1.0.0") -> str:
        self.logger.info("Setting up browser extension")
        self.logger.debug(f"Extension name: {name}, version: {version}")
        
        proxy_folder = self.get_path()
        os.makedirs(proxy_folder, exist_ok=True)
        self.logger.info(f"Using proxy folder: {proxy_folder}")

        if hardware_profile is None:
            self.logger.debug("Generating new hardware profile")
            hardware_profile = self.hw_generator.generate_profile()
            c_obj = CanvasDataUrl()
            try:
                hardware_profile["canvas_data_url"] = c_obj.get_fingerprint()
            except:
                hardware_profile["canvas_data_url"] = "data:image/png;base64,DEFAULT"

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

            geo_location = self._get_location_data()
            hardware_profile = self.hw_generator._apply_geolocation(hardware_profile, geo_location)

            if not hardware_profile.get("user_agent"):
                hardware_profile["user_agent"] = "Mozilla/5.0 ..."

            if not hardware_profile.get("lang"):
                hardware_profile["lang"] = "en-US"
            if not hardware_profile.get("timezone"):
                hardware_profile["timezone"] = "UTC"

        else:
            self.logger.debug("Using existing hardware profile with updates")
            if "canvas_data_url" not in hardware_profile:
                c_obj = CanvasDataUrl()
                try:
                    hardware_profile["canvas_data_url"] = c_obj.get_fingerprint()
                except:
                    hardware_profile["canvas_data_url"] = "data:image/png;base64,DEFAULT"
                    
            if "device" not in hardware_profile or "mac" not in hardware_profile["device"]:
                new_prof = self.hw_generator.generate_profile()
                hardware_profile["device"] = new_prof["device"]

            if "audio" not in hardware_profile:
                mac_nosep = hardware_profile["device"]["mac"].replace(':', '')
                hardware_profile["audio"] = {
                    "deviceId": f"audio_{mac_nosep}",
                    "label": 'High Definition Audio Device',
                    "groupId": f"audio_group_{mac_nosep}"
                }
            if "video" not in hardware_profile:
                mac_nosep = hardware_profile["device"]["mac"].replace(':', '')
                hardware_profile["video"] = {
                    "deviceId": f"video_{mac_nosep}",
                    "label": f"{hardware_profile['gpu']['vendor']} Camera",
                    "groupId": f"video_group_{mac_nosep}"
                }

            if not hardware_profile.get("user_agent"):
                hardware_profile["user_agent"] = "Mozilla/5.0 ..."
            if not hardware_profile.get("lang"):
                hardware_profile["lang"] = "en-US"
            if not hardware_profile.get("timezone"):
                hardware_profile["timezone"] = "UTC"

        self.logger.info("Writing extension files")
        canvas_data_url = hardware_profile["canvas_data_url"]

        proxy_data = hardware_profile.get("proxy", {})
        self.host = proxy_data.get("host")
        self.port = proxy_data.get("port")
        self.username = proxy_data.get("username", "")
        self.password = proxy_data.get("password", "")

        manifest = self._load_js_file('manifest.json')
        manifest = manifest.replace("<ext_ver>", version).replace("<ext_name>", name)
        with open(os.path.join(proxy_folder, "manifest.json"), "w", encoding="utf-8") as f:
            f.write(manifest)

        content_js = self._load_js_file('content.js')
        with open(os.path.join(proxy_folder, "content.js"), "w", encoding="utf-8") as f:
            f.write(content_js)

        injected_js = self._load_js_file('injected.js')
        injected_js = injected_js.replace("<HARDWARE_PROFILE>", json.dumps(hardware_profile))
        injected_js = injected_js.replace("<CANVAS_DATA_URL>", canvas_data_url)
        injected_js = injected_js.replace("<browser_language>", hardware_profile["lang"])
        with open(os.path.join(proxy_folder, "injected.js"), "w", encoding="utf-8") as f:
            f.write(injected_js)

        has_proxy = bool(self.host) and bool(self.port)
        background_js = self._generate_background_js(has_proxy, hardware_profile["user_agent"])
        with open(os.path.join(proxy_folder, "background.js"), "w", encoding="utf-8") as f:
            f.write(background_js)

        with open(os.path.join(proxy_folder, "hardware_profile.json"), "w", encoding="utf-8") as f:
            json.dump(hardware_profile, f, indent=4)

        main_content = self._load_js_file('content_main.js')
        clientrect_noise = hardware_profile.get('clientrect_noise', 0)
        main_content = main_content.replace('<CLIENTRECT_NOISE>', str(clientrect_noise))
        with open(os.path.join(proxy_folder, "content_main.js"), "w", encoding="utf-8") as f:
            f.write(main_content)

        isolated_content = self._load_js_file('content_isolated.js')
        with open(os.path.join(proxy_folder, "content_isolated.js"), "w", encoding="utf-8") as f:
            f.write(isolated_content)

        self.logger.info("Extension setup completed successfully")
        return proxy_folder


    def get_path(self) -> str:
        if self.profile_path:
            return os.path.join(self.profile_path, "extensions", "proxy_extension")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "proxy_extension")


    def _generate_background_js(self, has_proxy: bool = False, user_agent: Optional[str] = None) -> str:
        base_js = r"""
        chrome.privacy.network.webRTCIPHandlingPolicy.set({
            value: 'disable_non_proxied_udp'
        });
        chrome.privacy.network.networkPredictionEnabled.set({
            value: false
        });

        function setupWebRTC(details) {
            chrome.scripting.executeScript({
                target: { tabId: details.tabId },
                func: () => {
                    const rtcObject = {
                        close: () => {},
                        createDataChannel: () => {},
                        createOffer: () => Promise.reject(new Error('Failed')),
                        createAnswer: () => Promise.reject(new Error('Failed')),
                        setLocalDescription: () => Promise.reject(new Error('Failed')),
                        setRemoteDescription: () => Promise.reject(new Error('Failed'))
                    };
                    window.RTCPeerConnection = function() { return rtcObject; };
                    window.webkitRTCPeerConnection = function() { return rtcObject; };

                    if (navigator.mediaDevices) {
                        navigator.mediaDevices.getUserMedia = () => Promise.reject(new Error('Failed'));
                        navigator.mediaDevices.getDisplayMedia = () => Promise.reject(new Error('Failed'));
                    }
                },
                world: "MAIN",
                runAt: "document_start"
            });
        }
        chrome.webNavigation.onCommitted.addListener(setupWebRTC);
        
        chrome.webNavigation.onCreatedNavigationTarget.addListener((details) => {
        chrome.scripting.executeScript({
            target: { tabId: details.tabId },
            files: ["content.js"],
            world: "MAIN", 
            runAt: "document_start"
        }, () => {
            console.log("Injected content scripts into new tab", details.tabId);
        });
        });
        """
        if has_proxy and self.host and self.port:
            proxy_js = f"""
            var config = {{
                mode: "fixed_servers",
                rules: {{
                    singleProxy: {{
                        scheme: "http",
                        host: "{self.host}",
                        port: {self.port}
                    }},
                    bypassList: ["localhost"]
                }}
            }};

            chrome.proxy.settings.set({{
                value: config,
                scope: "regular"
            }}, function(){{}});

            function callbackFn(details) {{
                return {{
                    authCredentials: {{
                        username: "{self.username}",
                        password: "{self.password}"
                    }}
                }};
            }}
            chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{ urls: ["<all_urls>"] }},
                ['blocking']
            );
            """
            return base_js + proxy_js
        else:
            return base_js


    def update_proxy(self, proxy: Optional[str] = None) -> bool:
        self.logger.info(f"Updating proxy configuration: {proxy}")
        
        if not self.profile_path:
            self.logger.error("No profile path specified")
            return False
            
        ext_dir = os.path.join(self.profile_path, "extensions", "proxy_extension")
        if not os.path.exists(ext_dir):
            self.logger.error(f"Extension directory not found: {ext_dir}")
            return False

        try:
            manifest_path = os.path.join(ext_dir, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                version = manifest.get('version', '1.0.0').split('.')
                version[-1] = str(int(version[-1]) + 1)
                manifest['version'] = '.'.join(version)
                
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest, f, indent=4)
                self.logger.info(f"Updated extension version to {manifest['version']}")

            if proxy:
                parsed = urlparse(proxy)
                self.host = parsed.hostname
                self.port = parsed.port
                self.username = parsed.username or ""
                self.password = parsed.password or ""
                new_bg_js = self._generate_background_js(has_proxy=True)
                self.logger.info(f"Configured proxy: {self.host}:{self.port}")
            else:
                self.host = None
                self.port = None
                self.username = ""
                self.password = ""
                new_bg_js = self._generate_background_js(has_proxy=False)
                self.logger.info("Disabled proxy configuration")

            bg_path = os.path.join(ext_dir, "background.js")
            with open(bg_path, "w", encoding="utf-8") as f:
                f.write(new_bg_js)
            self.logger.debug("Updated background.js")

            state_path = os.path.join(os.path.dirname(self.profile_path), "Extension State")
            if os.path.exists(state_path):
                shutil.rmtree(state_path)
                self.logger.debug("Removed Extension State directory")

            return True

        except Exception as e:
            self.logger.error(f"Failed to update proxy configuration: {str(e)}", exc_info=True)
            return False


    def update_geoconfig(self, hardware_profile: dict) -> Tuple[str, str]:
        self.logger.info("Updating geolocation configuration")
        
        if self.host:
            try:
                geo_data = IPInfoManager.get_ip_info(self.host)
                if geo_data:
                    self.logger.info(f"Got geolocation data for {self.host}")
                    geo_location = GeoLocation(
                        latitude=geo_data.latitude,
                        longitude=geo_data.longitude,
                        accuracy=geo_data.accuracy,
                        timezone=geo_data.timezone
                    )
                    updated_profile = self.hw_generator._apply_geolocation(hardware_profile, geo_location)
                    self.logger.debug(f"Applied geolocation: {geo_data.timezone}")
                    return geo_data.languages, geo_data.timezone, updated_profile
                    
            except Exception as e:
                self.logger.error(f"Failed to get geolocation info: {str(e)}", exc_info=True)

        self.logger.debug("Using fallback random location")
        random_location = self._get_random_location()
        updated_profile = self.hw_generator._apply_geolocation(hardware_profile, random_location)
        return 'en-US', random_location.timezone, updated_profile
    