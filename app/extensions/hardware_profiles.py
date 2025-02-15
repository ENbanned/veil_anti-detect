import hashlib
import os
import random
import string
import sys
from typing import Any, Dict, Tuple

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.random_user_agent import AdvancedUserAgentGenerator
from utils.countries import COUNTRY_LANG_MAP


class HardwareProfileGenerator:
    def __init__(self):
        self.cpu_manufacturers = {
            'Intel': {
                'prefixes': ['Core i9', 'Core i7', 'Core i5', 'Core i3', 'Pentium', 'Celeron'],
                'generations': list(range(2, 13)),
                'suffixes': ['', 'K', 'F', 'T', 'H', 'HK', 'HQ', 'U', 'Y', 'G7', 'G4', 'G3', 'P', 'S', 'X', 'XE', 'TE', 'M', 'E']
            },
            'AMD': {
                'prefixes': ['Ryzen 9', 'Ryzen 7', 'Ryzen 5', 'Ryzen 3', 'Athlon', 'Phenom', 'FX'],
                'generations': list(range(1, 8)),
                'suffixes': ['', 'X', 'XT', 'G', 'GE', 'H', 'U', 'HX', 'HS', 'PRO', 'Mobile', 'MAX', 'Ultra']
            }
        }

        self.gpu_manufacturers = {
            'NVIDIA': {
                'prefixes': ['GeForce RTX', 'GeForce GTX', 'GeForce GT', 'GeForce'],
                'generations': {
                    'RTX': ['4090', '4080', '4070 Ti', '4070', '4060 Ti', '4060', 
                           '3090 Ti', '3090', '3080 Ti', '3080', '3070 Ti', '3070', '3060 Ti', '3060',
                           '2080 Ti', '2080 SUPER', '2080', '2070 SUPER', '2070', '2060 SUPER', '2060'],
                    'GTX': ['1660 Ti', '1660 SUPER', '1660', '1650 SUPER', '1650',
                           '1080 Ti', '1080', '1070 Ti', '1070', '1060', '1050 Ti', '1050',
                           '980 Ti', '980', '970', '960', '950', 
                           '780 Ti', '780', '770', '760', '750 Ti', '750', 
                           '680', '670', '660 Ti', '660', '650 Ti BOOST', '650 Ti', '650',
                           '580', '570', '560 Ti', '560', '560 SE', '550 Ti', '520', '510'],
                    'GT': ['1030', '730', '710', '640', '630', '620', '610', '520', '440', '430', '420', '240', '220'],
                    'GEFORCE': ['GTX 590', 'GTX 580', 'GTX 570', 'GTX 480', 'GTX 470', 'GTX 465', 
                               'GTX 295', 'GTX 285', 'GTX 280', 'GTX 275', 'GTX 260', 'GT 340', 'GT 330', 
                               'GT 320', 'GT 240', 'GT 220', 'GT 130', 'GT 120', 'GTS 450', 'GTS 250', 
                               'GTS 150', 'GT 110', 'GT 100', '9800 GTX+', '9800 GTX', '9800 GT', 
                               '9600 GT', '9600 GSO', '9500 GT', '9400 GT', '8800 ULTRA', '8800 GTX', 
                               '8800 GTS 640', '8800 GTS 512', '8800 GT', '8600 GTS', '8600 GT', '8500 GT', 
                               '7950 GT', '7800 GTX 512', '7800 GTX', '7600 GT', '7300 GT']
                },
                'memory_configs': {
                    '4090': [24],
                    '4080': [16],
                    '4070 Ti': [12],
                    '4070': [12],
                    '4060 Ti': [8],
                    '4060': [8],
                    '3090 Ti': [24],
                    '3090': [24],
                    '3080 Ti': [12],
                    '3080': [10, 12],
                    '3070 Ti': [8],
                    '3070': [8],
                    '3060 Ti': [8],
                    '3060': [12],
                    '2080 Ti': [11],
                    '2080 SUPER': [8],
                    '2080': [8],
                    '2070 SUPER': [8],
                    '2070': [8],
                    '2060 SUPER': [8],
                    '2060': [6],
                    '1660 Ti': [6],
                    '1660 SUPER': [6],
                    '1660': [6],
                    '1650 SUPER': [4],
                    '1650': [4],
                    '1080 Ti': [11],
                    '1080': [8],
                    '1070 Ti': [8],
                    '1070': [8],
                    '1060': [3, 6],
                    '1050 Ti': [4],
                    '1050': [2, 3]
                }
            },
            'AMD': {
                'prefixes': ['Radeon RX'],
                'generations': ['7900 XTX', '7900 XT', '7800 XT', '7700 XT', '7600 XT', '7600',
                              '6950 XT', '6900 XT', '6800 XT', '6800', '6750 XT', '6700 XT', '6650 XT', '6600 XT', '6600',
                              '5700 XT', '5700', '5600 XT', '5600', '5500 XT', '5500'],
                'memory_configs': {
                    '7900 XTX': [24],
                    '7900 XT': [20],
                    '7800 XT': [16],
                    '7700 XT': [12],
                    '7600 XT': [8],
                    '7600': [8],
                    '6950 XT': [16],
                    '6900 XT': [16],
                    '6800 XT': [16],
                    '6800': [16],
                    '6750 XT': [12],
                    '6700 XT': [12],
                    '6650 XT': [8],
                    '6600 XT': [8],
                    '6600': [8],
                    '5700 XT': [8],
                    '5700': [8],
                    '5600 XT': [6],
                    '5600': [6],
                    '5500 XT': [4, 8],
                    '5500': [4, 8]
                }
            },
            'Intel': {
                'prefixes': ['Arc'],
                'generations': ['A770', 'A750', 'A580', 'A380'],
                'memory_configs': {
                    'A770': [16, 8],
                    'A750': [8],
                    'A580': [8],
                    'A380': [6]
                }
            }
        }

        self.device_name_patterns = [
            ('DESKTOP', 8),
            ('LAPTOP', 8),
            ('PC', 9),
            ('WORKSTATION', 7),
            ('NB', 9),
            ('COMPUTER', 7),
            ('AIO', 6),
            ('TOWER', 6)
        ]

        self.mac_oui_database = [
            '00:02:B3', '00:03:47', '00:04:23', '00:0C:F1', '00:0E:0C', '00:0E:35', '00:11:11', '00:11:75', '00:12:F0',
            '00:13:02', '00:13:20', '00:13:CE', '00:13:E8', '00:15:00', '00:15:17', '00:16:6F', '00:16:76', '00:18:DE',
            '00:06:5B', '00:08:74', '00:0B:DB', '00:0D:56', '00:0F:1F', '00:11:43', '00:12:3F', '00:13:72', '00:14:22',
            '00:15:C5', '00:16:F0', '00:18:8B', '00:19:B9', '00:1A:A0', '00:1C:23', '00:1D:09', '00:1E:4F', '00:21:70',
            '00:01:E7', '00:02:A5', '00:04:EA', '00:08:02', '00:0B:CD', '00:0D:88', '00:0E:7F', '00:0F:20', '00:10:83',
            '00:11:0A', '00:11:85', '00:13:21', '00:14:38', '00:15:60', '00:16:35', '00:17:08', '00:18:71', '00:19:BB',
            '00:09:2D', '00:0C:CC', '00:0E:9B', '00:11:25', '00:12:FE', '00:13:A3', '00:14:9F', '00:15:B8', '00:16:41',
            '00:17:06', '00:18:13', '00:1A:6B', '00:1B:24', '00:1C:25', '00:1D:72', '00:1F:16', '00:20:91', '00:21:CC',
            '00:0C:6E', '00:0E:A6', '00:11:2F', '00:11:D8', '00:13:D4', '00:15:F2', '00:17:31', '00:18:F3', '00:1A:92',
            '00:1B:FC', '00:1D:60', '00:1E:8C', '00:1F:C6', '00:22:15', '00:23:54', '00:24:8C', '00:26:18', '00:27:84'
        ]
        
        self.ua_generator = AdvancedUserAgentGenerator()


    def _generate_deterministic_seed(self, identifier: str = None) -> int:
        if identifier:
            hash_object = hashlib.sha256(identifier.encode())
            return int(hash_object.hexdigest(), 16)
        return random.randint(0, 2**32 - 1)


    def _get_cpu_tier(self, cpu_name: str) -> str:
        if any(x in cpu_name for x in ['i9', 'Ryzen 9']):
            return 'high'
        elif any(x in cpu_name for x in ['i7', 'Ryzen 7']):
            return 'mid-high'  
        elif any(x in cpu_name for x in ['i5', 'Ryzen 5']):
            return 'mid'
        else:
            return 'low'


    def _generate_cpu(self, seed: int = None) -> Tuple[str, int]:
        if seed:
            random.seed(seed)
            
        manufacturer = random.choices(list(self.cpu_manufacturers.keys()), weights=[0.7, 0.3])[0]
        prefix = random.choice(self.cpu_manufacturers[manufacturer]['prefixes'])
        
        if manufacturer == 'Intel':
            generation = random.choices(self.cpu_manufacturers[manufacturer]['generations'], 
                                        weights=[0.02, 0.03, 0.05, 0.1, 0.15, 0.2, 0.3, 0.35, 0.4, 0.35, 0.3])[0]
        else:
            generation = random.choices(self.cpu_manufacturers[manufacturer]['generations'], 
                                        weights=[0.05, 0.1, 0.2, 0.3, 0.4, 0.35, 0.3])[0]

        suffix = random.choice(self.cpu_manufacturers[manufacturer]['suffixes']) 
        
        model, cores = self._generate_cpu_model_and_cores(manufacturer, prefix, generation, suffix)

        return model, cores
    

    def _generate_cpu_model_and_cores(self, manufacturer, prefix, generation, suffix):
        if manufacturer == 'Intel':
            model = f"{prefix}-{generation}{''.join(random.choices(string.digits, k=3))}{suffix}"
            if 'i9' in prefix:
                cores = 8
            elif 'i7' in prefix:
                cores = 6
            elif 'i5' in prefix:
                cores = 4
            else:
                cores = 2
        else:
            model = f"{prefix} {generation}{''.join(random.choices(string.digits, k=3))}{suffix}"
            if 'Ryzen 9' in prefix:
                cores = 12
            elif 'Ryzen 7' in prefix:  
                cores = 8  
            elif 'Ryzen 5' in prefix:
                cores = 6
            else:
                cores = 4
        return model, cores


    def _generate_gpu(self, cpu_tier: str, seed: int = None) -> Dict[str, Any]:
        if seed:
            random.seed(seed)
            
        if cpu_tier == 'high':
            manufacturers = ['NVIDIA', 'AMD']
            weights = [0.8, 0.2]  
        elif cpu_tier == 'mid-high':
            manufacturers = ['NVIDIA', 'AMD']
            weights = [0.7, 0.3]
        elif cpu_tier == 'mid':
            manufacturers = ['NVIDIA', 'AMD', 'Intel'] 
            weights = [0.6, 0.3, 0.1]
        else:
            manufacturers = ['NVIDIA', 'AMD', 'Intel']
            weights = [0.4, 0.4, 0.2]
        
        manufacturer = random.choices(manufacturers, weights=weights)[0]
        data = self.gpu_manufacturers[manufacturer]
        
        if manufacturer == 'NVIDIA':
            prefix_weights = [0.5, 0.3, 0.15, 0.05]
            prefix = random.choices(data['prefixes'], weights=prefix_weights)[0]
            
            if 'RTX' in prefix:
                gen_key = 'RTX'
            elif 'GTX' in prefix:
                gen_key = 'GTX'
            elif 'GT' in prefix:
                gen_key = 'GT'
            else:
                gen_key = 'GEFORCE'
            model = random.choice(data['generations'][gen_key])
            full_name = f"{prefix} {model}"
            renderer = f"ANGLE (NVIDIA {full_name} Direct3D11 vs_5_0 ps_5_0)"
        elif manufacturer == 'AMD':
            prefix = random.choice(data['prefixes'])
            model = random.choice(data['generations'])
            full_name = f"{prefix} {model}"
            renderer = f"ANGLE (AMD {full_name} Direct3D11 vs_5_0 ps_5_0)"
        else: 
            prefix = random.choice(data['prefixes'])
            model = random.choice(data['generations'])
            full_name = f"{prefix} {model}"
            renderer = f"ANGLE (Intel {full_name} Direct3D11 vs_5_0 ps_5_0)"
        
        memory = random.choice(data['memory_configs'].get(model, [2, 4, 8, 12]))
        
        return {
            'vendor': f'Google Inc. ({manufacturer})',
            'renderer': renderer,
            'memory': memory * 1024
        }


    def _generate_device_name(self, seed: int = None) -> str:
        if seed:
            random.seed(seed)
            
        prefix, length = random.choices(self.device_name_patterns, weights=[0.3, 0.25, 0.2, 0.1, 0.07, 0.05, 0.02, 0.01])[0]
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        return f"{prefix}-{suffix}"


    def _generate_mac_address(self, seed=None):
        oui = random.Random(seed).choice(self.mac_oui_database)
        counter = int(hashlib.shake_128(str(seed).encode()).hexdigest(2), 16)
        nic = f"{counter:06X}"
        return f"{oui}:{nic[:2]}:{nic[2:4]}:{nic[4:6]}"


    def _generate_user_agent(self, platform: str) -> str:
        return self.ua_generator.generate_for_chrome_major(132)
    
    
    def _calculate_ram(self, cpu_tier: str, cpu_cores: int, cpu_model) -> int:
        base_values = {
            'high': [8, 8],
            'mid-high': [8, 8],
            'mid': [4, 8],
            'low': [4, 4]
        }
        ram = random.choice(base_values[cpu_tier])
        return ram
    
    def _generate_speech_voices(self, seed: int) -> list:

        random.seed(seed)

        possible_langs = []

        for country in COUNTRY_LANG_MAP.values():
            lang = country['lang']
            possible_langs.append(lang)

        random.shuffle(possible_langs)
        voices_count = random.randint(2, 4)
        chosen = possible_langs[:voices_count]

        voices = []
        for i, lang in enumerate(chosen):
            voices.append({
                "default": True if i == 0 else False,
                "lang": lang,
                "localService": True,
                "name": f"Voice_{lang}_{seed}_{i}",
                "voiceURI": f"Voice_{lang}_{seed}_{i}"
            })
        return voices
    
       
    def _get_chrome_version(self) -> Dict[str, str]:
        versions = {
            '120.0.0.0': {
                'full': '120.0.6099.130',
                'js_api': '120.0.0.0',
                'webkit': '537.36',
                'weight': 0.7
            },
            '121.0.0.0': {
                'full': '121.0.6167.87',
                'js_api': '121.0.0.0',
                'webkit': '537.36',
                'weight': 0.3
            }
        }
        
        version = random.choices(list(versions.keys()), 
                            weights=[v['weight'] for v in versions.values()])[0]
        return versions[version]


    def _generate_browser_data(self, platform: str) -> dict:
        chrome_versions = {
            '120.0.0.0': {
                'full': '120.0.6099.130',
                'js_api': '120.0.0.0',
                'webkit': '537.36'
            },
            '121.0.0.0': {
                'full': '121.0.6167.87',
                'js_api': '121.0.0.0',
                'webkit': '537.36'
            }
        }
        
        version = random.choices(list(chrome_versions.keys()), 
                            weights=[0.7, 0.3])[0]
        
        return {
            'version': chrome_versions[version]['full'],
            'js_api_version': chrome_versions[version]['js_api'],
            'webkit_version': chrome_versions[version]['webkit'],
            'build_id': f'20231107{random.randint(100000, 999999)}'
        }
        
        
    def _generate_platform_info(self) -> dict:
        platform = random.choice(["windows", "macos", "linux"])
        
        platforms = {
            "windows": {
                "versions": ["10.0.19041", "10.0.19042", "10.0.19043", "10.0.19044"],
                "builds": ["19041.1288", "19042.1348", "19043.1348", "19044.1288"],
                "weight": 0.85
            },
            "macos": {
                "versions": ["10.15.7", "11.6.1", "12.0.1", "12.1"],
                "builds": ["20G224", "20G165", "21A559", "21C52"],
                "weight": 0.1
            },
            "linux": {
                "versions": ["5.10", "5.11", "5.13", "5.15"],
                "builds": ["debian", "ubuntu", "fedora"],
                "weight": 0.05
            }
        }
        
        platform = random.choices(list(platforms.keys()), 
                                weights=[p["weight"] for p in platforms.values()])[0]
        platform_data = platforms[platform]
        
        return {
            "name": platform,
            "version": random.choice(platform_data["versions"]),
            "build": random.choice(platform_data["builds"]),
            "arch": "x64"
        }


    def _apply_geolocation(self, hardware_profile: dict, geo_location) -> dict:
        hardware_profile['latitude'] = geo_location.latitude
        hardware_profile['longitude'] = geo_location.longitude
        hardware_profile['geo_accuracy'] = geo_location.accuracy
        return hardware_profile
    
    def _generate_clientrects_noise(self) -> float:
        salt = random.randint(100_000_000, 999_999_999)
        fraction_str = f"0.{salt}"
        fraction_val = float(fraction_str)

        noise_val = fraction_val * 9e-6 + 1e-7
        
        return noise_val


    def generate_profile(self, identifier: str = None) -> Dict[str, Any]:
        seed = self._generate_deterministic_seed(identifier)
        random.seed(seed)
        
        platform_info = self._generate_platform_info()
        
        cpu_model, cpu_cores = self._generate_cpu(seed)
        cpu_tier = self._get_cpu_tier(cpu_model)
        gpu = self._generate_gpu(cpu_tier, seed)
        
        ram = self._calculate_ram(cpu_tier, cpu_cores, cpu_model)
        browser_data = self._generate_browser_data(platform_info['name'])
        
        profile = {
            'cpu': {'model': cpu_model, 'cores': cpu_cores},
            'ram': ram,
            'gpu': gpu,
            'device': {
                'name': self._generate_device_name(seed),
                'mac': self._generate_mac_address(seed)
            },
            'webgl': {
                'vendor': gpu['vendor'],
                'renderer': gpu['renderer'],
                'max_texture_size': gpu['memory'] * random.randint(128, 160),
                'max_viewport_dims': [random.randint(16000, 16500), random.randint(16000, 16500)],
                'max_vertex_uniforms': random.randint(3800, 4096),
                'aliased_line_width_range': [1, random.choice([1, 2])],
                'aliased_point_size_range': [1, random.randint(1000, 2048)],
                'max_vertex_attribs': random.randint(12, 16),
                'max_vertex_texture_image_units': random.randint(12, 20),
                'max_varying_vectors': random.randint(28, 32),
                'max_combined_texture_image_units': random.randint(30, 36)
            },
            'user_agent': self._generate_user_agent(platform_info['name']),
            'oc': platform_info['name'],
            'platform': platform_info,
            'browser': browser_data
        }
        
        chrome_version = self._get_chrome_version()
        profile['browser'].update({
            'version': chrome_version['full'],
            'webkit_version': chrome_version['webkit']
        })
        
        profile['user_agent'] = profile['user_agent'].replace(
            "Chrome/\\d+\\.\\d+\\.\\d+\\.\\d+",
            f"Chrome/{chrome_version['full']}"
        )
        
        profile['clientrect_noise'] = self._generate_clientrects_noise()
        profile["speech_voices"] = self._generate_speech_voices(seed)
        
        return profile
    