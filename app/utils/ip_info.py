import logging
from dataclasses import dataclass
from typing import Optional

import requests

try:
    from .countries import COUNTRY_LANG_MAP
except ImportError:
    from utils.countries import COUNTRY_LANG_MAP


logger = logging.getLogger(__name__)


@dataclass
class GeoData:
    latitude: float
    longitude: float
    accuracy: float
    timezone: str
    country_code: str
    languages: str


class IPInfoManager:
    _cache = {}
    
    @classmethod
    def get_ip_info(cls, ip: str, max_retries: int = 3, retry_delay: int = 2) -> Optional[GeoData]:
        if ip in cls._cache:
            return cls._cache[ip]
            
        url = f'http://ip-api.com/json/{ip}'
        
        for attempt in range(max_retries):
            try:
                resp = requests.get(url)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('status') == 'success':
                        country_code = data.get('countryCode', 'US')
                        country_data = COUNTRY_LANG_MAP.get(country_code, COUNTRY_LANG_MAP['US'])
                        
                        geo_data = GeoData(
                            latitude=float(data.get('lat')),
                            longitude=float(data.get('lon')),
                            accuracy=100.0,
                            timezone=data.get('timezone', 'UTC'),
                            country_code=country_code,
                            languages=country_data['lang']
                        )
                        cls._cache[ip] = geo_data
                        return geo_data
                        
                logger.warning(f"Attempt {attempt + 1}: API returned status {resp.status_code}")
                
            except Exception as e:
                logger.error(f"Error getting IP info: {str(e)}")
                
        return None
    
    
