import logging
import os
from pathlib import Path
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from .font_manager import FontManager
from utils.logger import get_logger


class StyleManager:
    def __init__(self):
        self.current_theme = "light"
        self.logger = get_logger("style_manager")
        self.logger.debug("Initializing style manager")
        self._load_styles()
        self._setup_font()
    
    
    def _setup_font(self):
        try:
            font = FontManager.load_fonts()
            QApplication.setFont(font)
            self.logger.debug("Application font configured successfully")
        except Exception as e:
            self.logger.error(f"Failed to setup application font: {e}", exc_info=True)
    
    
    def _load_styles(self):
        current_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        styles_dir = current_dir.parent / "styles"
        
        self.light_style = self._read_style_file(styles_dir / "light.qss")
        self.dark_style = self._read_style_file(styles_dir / "dark.qss")
        self.logger.debug("Style files loaded")
    
    
    def _read_style_file(self, filename: str) -> str:
        style_path = os.path.join(os.path.dirname(__file__), "styles", filename)
        
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                self.logger.debug(f"Successfully loaded style file: {filename}")
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to load style file {filename}: {e}", exc_info=True)
            return ""
    
    
    def apply_theme(self, theme: str):
        self.logger.info(f"Applying theme: {theme}")
        self.current_theme = theme
        style = self.dark_style if theme == "dark" else self.light_style
        QApplication.instance().setStyle("Fusion")
        QApplication.instance().setStyleSheet("")
        QApplication.instance().setStyleSheet(style)
        self._save_theme(theme)
        self.logger.debug("Theme applied successfully")
    
    
    def get_saved_theme(self) -> str:
        settings = QSettings()
        theme = settings.value("theme", "light")
        self.logger.debug(f"Retrieved saved theme: {theme}")
        
        return theme
    
    
    def _save_theme(self, theme: str):
        self.logger.debug(f"Saving theme preference: {theme}")
        settings = QSettings()
        settings.setValue("theme", theme)