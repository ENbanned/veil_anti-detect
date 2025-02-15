import os
from pathlib import Path
from PySide6.QtGui import QFontDatabase, QFont

class FontManager:
    @staticmethod
    def load_fonts():
        try:
            current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
            fonts_dir = current_dir.parent / "styles" / "fonts"
            
            fonts_dir.mkdir(parents=True, exist_ok=True)
            
            font_path = fonts_dir / "Nunito-SemiBold.ttf"
            
            if font_path.exists():
                font_id = QFontDatabase.addApplicationFont(str(font_path))
                if font_id != -1:
                    font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
                    return QFont(font_family)
                else:
                    raise Exception("Ошибка загрузки шрифта")
            else:
                raise FileNotFoundError(f"Файл шрифта не найден: {font_path}")
                
        except Exception as e:
            return QFont("system-ui")