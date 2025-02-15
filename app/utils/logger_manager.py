import logging
import os

class ProfileLoggerManager:
    _loggers = {}
    
    @classmethod
    def get_logger(cls, profile_path: str) -> logging.Logger:
        if profile_path not in cls._loggers:
            logger_name = f"profile_{hash(profile_path)}"
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.INFO)
            log_path = os.path.join(profile_path, 'profile.log')
            
            try:
                handler = logging.FileHandler(log_path, encoding='utf-8')
                handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
                logger.addHandler(handler)
                cls._loggers[profile_path] = {
                    'logger': logger,
                    'handler': handler,
                    'path': log_path
                }
            except Exception as e:
                print(f"Logger setup error: {e}")
                return logging.getLogger()
                
        return cls._loggers[profile_path]['logger']
    
    
    @classmethod
    def cleanup_logger(cls, profile_path: str):
        if profile_path in cls._loggers:
            try:
                logger_data = cls._loggers[profile_path]
                handler = logger_data['handler']
                logger = logger_data['logger']
                
                handler.flush()
                handler.close()
                logger.removeHandler(handler)
                
                del cls._loggers[profile_path]
                
                log_path = logger_data['path']
                if os.path.exists(log_path):
                    try:
                        with open(log_path, 'a') as f:
                            f.flush()
                            os.fsync(f.fileno())
                    except:
                        pass
                        
            except Exception as e:
                print(f"Logger cleanup error: {e}")


    @classmethod
    def cleanup_all(cls):
        for profile_path in list(cls._loggers.keys()):
            cls.cleanup_logger(profile_path)