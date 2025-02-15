import json
import logging
import os
import sys
import time
import traceback
import ctypes
import threading
import undetected_chromedriver as uc

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from utils.ip_info import IPInfoManager
    from utils.profile_metadata import ProfileMetadata
except ImportError:
    parent_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if parent_project_root not in sys.path:
        sys.path.insert(0, parent_project_root)
    from utils.ip_info import IPInfoManager
    from utils.profile_metadata import ProfileMetadata

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
VENV_PATH = os.path.dirname(os.path.dirname(sys.executable)) if (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)) else None
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(
    filename=os.path.join(os.path.dirname(__file__), 'profile.log'),
    mode='a',
    encoding='utf-8'
)
file_handler.setFormatter(
    logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
)
logger.addHandler(file_handler)
logger.propagate = False

def get_sys_info(proxy):
    try:
        if not proxy:
            logger.warning("Proxy not provided, using default system info")
            return 'en-US', 'UTC'
        geo_data = IPInfoManager.get_ip_info(proxy["host"])
        if geo_data:
            logger.info(f"Got system info: lang={geo_data.languages}, tz={geo_data.timezone}")
            return geo_data.languages, geo_data.timezone
        logger.warning("Failed to get geo data, using defaults")
        return 'en-US', 'UTC'
    except Exception as e:
        logger.error(f"Failed to get system info: {e}", exc_info=True)
        return 'en-US', 'UTC'

def configure_proxy(profile_path):
    try:
        extension_path = os.path.join(profile_path, "extensions", "proxy_extension")
        if not os.path.exists(extension_path):
            logger.warning("Proxy extension directory not found")
            return None
        
        manifest_path = os.path.join(extension_path, "manifest.json")
        background_path = os.path.join(extension_path, "background.js")
        
        if not all(os.path.exists(p) for p in [manifest_path, background_path]):
            logger.error("Missing proxy extension files")
            return None
            
        logger.info("Found proxy extension at: %s", extension_path)
        return extension_path
    except Exception as e:
        logger.error("Proxy configuration failed: %s", str(e), exc_info=True)
        return None

def load_hardware_profile():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    profile_path = os.path.join(base_dir, "extensions", "proxy_extension", "hardware_profile.json")
    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
            logger.info("Hardware profile loaded successfully")
            return profile
    except Exception as e:
        logger.error("Failed to load hardware profile: %s", str(e), exc_info=True)
        raise

def update_heartbeat(profile_path: str, stop_event: threading.Event):
    metadata = ProfileMetadata(profile_path)
    while not stop_event.is_set():
        try:
            data = metadata.load()
            data["last_heartbeat"] = time.time()
            metadata.save(data)
        except Exception as e:
            logger.error("Heartbeat update failed: %s", str(e), exc_info=True)
        time.sleep(2)

def launch_profile():
    try:
        stop_heartbeat = threading.Event()
        kernel32 = ctypes.WinDLL('kernel32')
        user32 = ctypes.WinDLL('user32')
        SW_HIDE = 0
        hWnd = kernel32.GetConsoleWindow()
        if hWnd:
            user32.ShowWindow(hWnd, SW_HIDE)
        if not VENV_PATH:
            raise RuntimeError("Script must be run from a virtual environment")

        profile_path = os.path.dirname(os.path.abspath(__file__))
        shutdown_file = os.path.join(profile_path, "shutdown.flag")
        if os.path.exists(shutdown_file):
            try:
                os.remove(shutdown_file)
                logger.info("Removed stale shutdown.flag file on startup.")
            except Exception as e:
                logger.error(f"Failed to remove existing shutdown.flag: {e}", exc_info=True)

        metadata = ProfileMetadata(profile_path)

        hardware_profile = metadata.load()
        hardware_profile_path = os.path.join(profile_path, "hardware_profile.json")
        if not os.path.exists(hardware_profile_path):
            raise RuntimeError("hardware_profile.json not found")

        with open(hardware_profile_path, 'r', encoding='utf-8') as f:
            hardware_profile = json.load(f)

        options = uc.ChromeOptions()

        extension_path = configure_proxy(profile_path)
        if extension_path:
            options.add_argument(f'--load-extension={extension_path}')

        options.add_argument(f'--user-data-dir={profile_path}')

        user_agent = hardware_profile.get('user_agent')
        if user_agent:
            options.add_argument(f'--user-agent={user_agent}')
            logger.info(f"Using User-Agent from profile: {user_agent}")

        logger.info('Trying to get profile data')
        profile_data = load_hardware_profile()
        logger.info('Profile data: ' + str(profile_data))
        lang = profile_data.get("lang", "en-US")
        logger.info(f'Lang: {lang}')
        timezone = profile_data.get("timezone", "UTC")
        logger.info(f'Timezone: {timezone}')
        logger.info(lang, timezone)

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=ChromeWhatsNewUI')
        options.add_argument('--proxy-bypass-list=<-loopback>')
        options.add_argument('--disable-sync')
        options.add_argument('--disable-features=PreconnectToSearch,NetworkPrediction,NetworkService')
        options.add_argument('--disable-features=NetworkPrediction')
        options.add_argument('--no-first-run')
        options.add_argument('--disable-site-isolation-trials')
        options.add_argument('--disable-features=TranslateUI')
        options.add_argument('--disable-hang-monitor')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--start-maximized')
        options.add_argument(f'--lang={lang}')
        options.add_argument(f"--force-language={lang}")  
        options.add_argument(f"--accept-lang={lang}")
        options.add_argument(f'--timezone={timezone}')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--disable-logging-redirect')
        
        prefs = {
            "intl.accept_languages": lang
        }
        options.add_experimental_option("prefs", prefs)

        driver = uc.Chrome(
            options=options,
            headless=False,
            use_subprocess=False        
        )
        
        driver.execute_cdp_cmd("Emulation.setTimezoneOverride", {"timezoneId": f"{timezone}"})
        
        geo_data = hardware_profile.get('geo', {
            'latitude': 0,
            'longitude': 0,
            'accuracy': 100
        })
        
        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {
            "latitude": geo_data['latitude'],
            "longitude": geo_data['longitude'],
            "accuracy": geo_data['accuracy']
        })

        driver.maximize_window()
        logger.info("Browser successfully launched and configured")

        metadata.update_status(True)
        metadata.update_last_launch()

        heartbeat_thread = threading.Thread(
            target=update_heartbeat, 
            args=(profile_path, stop_heartbeat), 
            daemon=True
        )
        heartbeat_thread.start()

        shutdown_file = os.path.join(profile_path, "shutdown.flag")
        while True:
            if os.path.exists(shutdown_file):
                try:
                    stop_heartbeat.set()
                    heartbeat_thread.join(timeout=3)
                    driver.quit()
                except Exception as ex:
                    logger.error("Error closing driver on shutdown flag: " + str(ex), exc_info=True)
                os.remove(shutdown_file)
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
                sys.exit(0)
                break

            try:
                _ = driver.title
            except Exception as e:
                logger.info("Browser closed manually. Shutting down driver...")
                try:
                    driver.quit()
                except Exception as ex:
                    logger.error("Error closing driver after manual shutdown: " + str(ex), exc_info=True)
                for handler in logger.handlers[:]:
                    handler.close()
                    logger.removeHandler(handler)
                sys.exit(0)
                break

            time.sleep(3)

        metadata.update_status(False)
        return driver

    except Exception as e:
        logger.error(f"Error launching profile:\n{str(traceback.format_exc())}", exc_info=True)
        input("\nPress Enter to exit...")
        sys.exit(1)

def close_loggers():
    try:
        profile_path = os.path.dirname(os.path.abspath(__file__))
        profile_id = os.path.basename(profile_path)
        
        for name in list(logging.root.manager.loggerDict.keys()):
            if profile_id in name:
                logger = logging.getLogger(name)
                handlers = logger.handlers[:]
                for handler in handlers:
                    try:
                        handler.flush()
                        handler.close()
                        logger.removeHandler(handler)
                    except Exception as e:
                        logger.error(f"Failed to close handler: {e}", exc_info=True)
                logging.root.manager.loggerDict.pop(name, None)

        log_path = os.path.join(profile_path, 'profile.log')
        if os.path.exists(log_path):
            try:
                with open(log_path, 'a') as f:
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as e:
                logger.error(f"Failed to flush log file: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"Logger cleanup failed: {e}", exc_info=True)
    finally:
        import gc
        gc.collect()

if __name__ == "__main__":
    try:
        driver = launch_profile()
        if not driver:
            logger.error("Failed to launch profile")
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            sys.exit(1)
        while True:
            time.sleep(1)
    except Exception as e:
        logger.error("Critical error occurred", exc_info=True)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)
        sys.exit(1)