import random


class AdvancedUserAgentGenerator:
    
    WINDOWS_PLATFORMS = [
        "Windows NT 10.0; Win64; x64",  
        "Windows NT 10.0",              
        "Windows NT 6.1; Win64; x64",
        "Windows NT 6.1",
        "Windows NT 6.3; Win64; x64",
    ]

    def generate_for_chrome_major(self, major_version: int) -> str:
        os_type = random.choice(["win"])
        
        if os_type == "win":
            os_string = random.choice(self.WINDOWS_PLATFORMS)

        
        minor = random.randint(0, 5)
        build = random.randint(1000, 9999)
        patch = random.randint(0, 150)
        
        user_agent = (
            f"Mozilla/5.0 ({os_string}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) "
            f"Chrome/{major_version}.{minor}.{build}.{patch} "
            f"Safari/537.36"
        )
        return user_agent
