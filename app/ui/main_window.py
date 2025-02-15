import os
import time
import logging
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QThread, QTimer, Signal, Slot, QObject
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QFrame, QHBoxLayout, QPushButton

from chrome_manager import ChromeProfileManager

from ui.components.dialogs import CreateProfileDialog, ProxyDialog, DeleteConfirmDialog
from ui.components.profile_list import ProfileList
from ui.components.status_bar import StatusBar
from ui.components.theme_switch import ThemeSwitch
from utils.profile_metadata import ProfileMetadata
from ui.managers import WindowManager, StyleManager
from utils.logger import get_logger


class ProfileCreatorWorker(QThread):
    progress = Signal(int, int)
    finished = Signal()
    
    def __init__(self, profile_manager, name, count, proxy, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.name = name
        self.count = count
        self.proxy = proxy
        
        
    def run(self):
        for i in range(self.count):
            time.sleep(1.5)
            self.profile_manager.create_profile(self.name, self.proxy)
            self.progress.emit(i + 1, self.count)
        self.finished.emit()


class ProfileDeleterWorker(QThread):
    progress = Signal(int, int)
    finished = Signal()
    
    def __init__(self, profile_manager, profiles, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.profiles = profiles
       
        
    def run(self):
        total = len(self.profiles)
        for i, profile in enumerate(self.profiles):
            self.profile_manager.delete_profile(profile)
            self.progress.emit(i + 1, total)
        self.finished.emit()


class ProfileTerminatorWorker(QThread):
    progress = Signal(int, int)
    finished = Signal()
    
    def __init__(self, profile_manager, profiles, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.profiles = profiles
        self.logger = get_logger("profile_terminator")
        
        
    def run(self):
        total = len(self.profiles)
        for i, profile_id in enumerate(self.profiles):
            self.profile_manager.process_manager.terminate_profile(profile_id)
            profile_path = os.path.join(self.profile_manager.base_dir, str(profile_id))
            try:
                metadata = ProfileMetadata(profile_path)
                metadata.update_status(False)
            except Exception as e:
                self.logger.error(f"Error updating metadata for profile {profile_id}: {e}")
            time.sleep(0.2)
            self.progress.emit(i + 1, total)
        self.finished.emit()


class ProxyUpdaterWorker(QThread):
    progress = Signal(int, int)
    finished = Signal()
    
    def __init__(self, profile_manager, profiles, proxy, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.profiles = profiles
        self.proxy = proxy
    
        
    def run(self):
        total = len(self.profiles)
        for i, profile in enumerate(self.profiles):
            self.profile_manager.update_profile_proxy(profile, self.proxy)
            self.progress.emit(i + 1, total)
        self.finished.emit()


class SmoothProgressUpdater(QObject):
    progressUpdated = Signal(str)
    
    def __init__(self, labelGetter, labelSetter, parent=None):
        super().__init__(parent)
        self.labelGetter = labelGetter
        self.labelSetter = labelSetter
        self.oldValue = 0
        self.newValue = 0
        self.targetTotal = 0
        self.currentValue = 0
        self.stepTimer = QTimer(self)
        self.stepTimer.setInterval(30)
        self.stepTimer.timeout.connect(self._step)
    
        
    def setProgressRange(self, oldVal, newVal, total):
        self.oldValue = oldVal
        self.currentValue = oldVal
        self.newValue = newVal
        self.targetTotal = total
        
        if not self.stepTimer.isActive():
            self.stepTimer.start()
            
    def _step(self):
        if self.currentValue < self.newValue:
            self.currentValue += 1
        elif self.currentValue > self.newValue:
            self.currentValue -= 1
        else:
            self.stepTimer.stop()
        self.progressUpdated.emit(f"{self.currentValue}/{self.targetTotal}")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.logger = get_logger("main_window")
        self.logger.debug("Initializing main window")
        
        self.setWindowTitle("Veil")
        self.setWindowIcon(QIcon("app/ui/styles/images/icon.svg")) 
        self.resize(1920, 1080)

        self.profile_manager = ChromeProfileManager()
        self.window_manager = WindowManager()
        self.style_manager = StyleManager()

        self._updating_buttons = False
        
        self.logger.debug("Setting up UI components")
        self._setup_ui()
        self._setup_connections()
        self._load_initial_state()

        self.status_timer = QTimer(self)
        self.status_timer.setInterval(3000)
        self.status_timer.timeout.connect(self._poll_profile_statuses)
        self.status_timer.start()
        
        self.createProgress = SmoothProgressUpdater(lambda: "", lambda val: None, self)
        self.deleteProgress = SmoothProgressUpdater(lambda: "", lambda val: None, self)
        self.createProgress.progressUpdated.connect(self._updateCreateProgressText)
        self.deleteProgress.progressUpdated.connect(self._updateDeleteProgressText)

        self._launch_queue = []
        self._close_queue = []
        self.logger.info("Main window initialization completed")


    def _setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)

        self.top_panel = self._create_top_panel()
        self.top_panel.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.top_panel)

        self.profile_list = ProfileList(self.profile_manager, self.launch_profile_action)
        main_layout.addWidget(self.profile_list)

        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)


    def _create_top_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("topPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(15)

        top_row = QHBoxLayout()
        action_group = QHBoxLayout()
        action_group.setSpacing(10)

        self.create_btn = self._create_button("Создать профили", "primary")
        self.launch_selected_btn = self._create_button("Запустить выбранные", "secondary")
        self.close_selected_btn = self._create_button("Закрыть выбранные", "secondary")

        action_group.addWidget(self.create_btn)
        action_group.addWidget(self.launch_selected_btn)
        action_group.addWidget(self.close_selected_btn)

        top_row.addLayout(action_group)
        top_row.addStretch()

        window_group = QHBoxLayout()
        window_group.setSpacing(10)

        self.arrange_windows_btn = self._create_button("Распределить", "window")
        self.cascade_windows_btn = self._create_button("Каскадом", "window")
        self.tile_horizontal_btn = self._create_button("Горизонтально", "window")
        self.tile_vertical_btn = self._create_button("Вертикально", "window")

        window_group.addWidget(self.arrange_windows_btn)
        window_group.addWidget(self.cascade_windows_btn)
        window_group.addWidget(self.tile_horizontal_btn)
        window_group.addWidget(self.tile_vertical_btn)

        top_row.addLayout(window_group)
        top_row.addStretch()

        right_group = QHBoxLayout()
        right_group.setSpacing(10)

        self.proxy_selected_btn = self._create_button("Изменить прокси", "action")
        self.delete_selected_btn = self._create_button("Удалить", "danger")
        self.theme_switch = ThemeSwitch()

        right_group.addWidget(self.proxy_selected_btn)
        right_group.addWidget(self.delete_selected_btn)
        right_group.addWidget(self.theme_switch)

        top_row.addLayout(right_group)
        panel_layout.addLayout(top_row)
        return panel


    def _create_button(self, text: str, style: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedHeight(36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setProperty("type", style)
        
        if style == "primary":
            btn.setStyleSheet("""
                QPushButton { 
                    background-color: #5B88C7; 
                    color: white; 
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #6999DE;
                }
                QPushButton:pressed {
                    background-color: #4F75AC;
                }
                QPushButton:disabled {
                    background-color: rgba(91, 136, 199, 0.5);
                    color: rgba(255, 255, 255, 0.7);
                }
            """)
            
        elif style == "danger":
            btn.setStyleSheet("""
                QPushButton { 
                    background-color: #CB726B; 
                    color: white; 
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #E88178;
                }
                QPushButton:pressed {
                    background-color: #B36359;
                }
                QPushButton:disabled {
                    background-color: rgba(203, 114, 107, 0.5);
                    color: rgba(255, 255, 255, 0.7);
                }
            """)
        return btn


    def _setup_connections(self):
        self.create_btn.clicked.connect(self._show_create_dialog)
        self.launch_selected_btn.clicked.connect(self._launch_selected)
        self.close_selected_btn.clicked.connect(self._close_selected)
        self.proxy_selected_btn.clicked.connect(self._edit_proxy_selected)
        self.delete_selected_btn.clicked.connect(self._delete_selected)
        self.arrange_windows_btn.clicked.connect(self._arrange_windows)
        self.cascade_windows_btn.clicked.connect(self._cascade_windows)
        self.tile_horizontal_btn.clicked.connect(self._tile_horizontal)
        self.tile_vertical_btn.clicked.connect(self._tile_vertical)
        self.theme_switch.theme_changed.connect(self._change_theme)
        self.profile_list.selection_changed.connect(self._update_buttons_state)
        self.profile_list.table.itemChanged.connect(lambda item:
                                                    self._update_buttons_state() if item.column() == 0 else None)


    def _load_initial_state(self):
        self.profile_list.load_profiles()
        self._update_buttons_state()
        saved_theme = self.style_manager.get_saved_theme()
        self._change_theme(saved_theme)


    @Slot()
    def _poll_profile_statuses(self):
        running_profiles = self.profile_manager.process_manager.get_running_profiles()
        self._update_profile_statuses_with_result(running_profiles)


    @Slot(dict)
    def _update_profile_statuses_with_result(self, running_profiles):
        try:
            for row in range(self.profile_list.table.rowCount()):
                profile_id = int(self.profile_list.table.item(row, 1).text())
                old_status = self.profile_list.table.item(row, 4).text()
                is_running = running_profiles.get(profile_id, False)
                new_status = "Active" if is_running else "Inactive"
                if old_status != new_status:
                    self.profile_list.table.item(row, 4).setText(new_status)
                    cellWidget = self.profile_list.table.cellWidget(row, 7)
                    if cellWidget:
                        action_btn = cellWidget.findChild(QPushButton)
                        if action_btn:
                            if new_status == "Active":
                                action_btn.setText("Закрыть")
                                action_btn.setProperty("type", "close")
                            else:
                                action_btn.setText("Открыть")
                                action_btn.setProperty("type", "open")
                            action_btn.style().unpolish(action_btn)
                            action_btn.style().polish(action_btn)
                    self.profile_list.update_profile_status(profile_id, is_running)
        except Exception as e:
            self.logger.error(f"Error updating statuses: {e}")


    def _arrange_windows(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.logger.warning("No profiles selected for window arrangement")
            self.status_bar.show_warning("Выберите профили для распределения окон")
            return
            
        try:
            self.logger.info(f"Arranging windows for profiles: {selected}")
            self.window_manager.arrange_windows(selected)
            self.status_bar.show_message("Начато распределение окон")
        except Exception as e:
            self.logger.error(f"Failed to arrange windows: {str(e)}", exc_info=True)
            self.status_bar.show_error(f"Ошибка при распределении окон: {str(e)}")


    def _cascade_windows(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.status_bar.show_warning("Выберите профили для каскадного расположения")
            return
        try:
            self.window_manager.cascade_windows(selected)
            self.status_bar.show_message("Начато каскадное расположение окон")
        except Exception as e:
            self.status_bar.show_error(f"Ошибка при каскадном расположении: {str(e)}")


    def _tile_horizontal(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.status_bar.show_warning("Выберите профили для горизонтального расположения")
            return
        try:
            self.window_manager.tile_windows_horizontally(selected)
            self.status_bar.show_message("Начато горизонтальное расположение окон")
        except Exception as e:
            self.status_bar.show_error(f"Ошибка при горизонтальном расположении: {str(e)}")


    def _tile_vertical(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.status_bar.show_warning("Выберите профили для вертикального расположения")
            return
        try:
            self.window_manager.tile_windows_vertically(selected)
            self.status_bar.show_message("Начато вертикальное расположение окон")
        except Exception as e:
            self.status_bar.show_error(f"Ошибка при вертикальном расположении: {str(e)}")


    def _close_selected(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.logger.warning("No profiles selected for closing")
            self.status_bar.show_warning("Выберите профили для закрытия")
            return
            
        self.logger.info(f"Initiating close sequence for profiles: {selected}")
        self.status_bar.show_message("Закрытие выбранных профилей...")
        self._close_queue = list(selected)
        self._close_next_profile()


    def _close_next_profile(self):
        if self._close_queue:
            profile_id = self._close_queue.pop(0)
            self.logger.debug(f"Closing profile: {profile_id}")
            self.profile_manager.close_profile(profile_id)
            QTimer.singleShot(3000, self._close_next_profile)
        else:
            self.logger.info("Profile closing sequence completed")
            self.status_bar.show_message("Закрытие завершено.")
            self.profile_list.load_profiles()


    def _show_create_dialog(self):
        self.logger.debug("Showing create profile dialog")
        dialog = CreateProfileDialog(self)
        if dialog.exec():
            display_name, count, proxy = dialog.get_data()
            self.logger.info(f"Creating {count} profiles with name: {display_name}")
            self.status_bar.show_message("Подготовка к созданию профилей...")
            
            self.creator_thread = ProfileCreatorWorker(
                self.profile_manager, display_name or "", count, proxy, self
            )
            self.creator_thread.progress.connect(self._on_create_progress)
            self.creator_thread.finished.connect(self._on_create_finished)
            self.creator_thread.start()


    def _on_create_progress(self, current, total):
        old_val = getattr(self, "_create_last_val", 0)
        self.createProgress.setProgressRange(old_val, current, total)
        self._create_last_val = current


    def _updateCreateProgressText(self, text):
        self.status_bar.show_message("Создание профилей: " + text)



    def _updateDeleteProgressText(self, text):
        self.status_bar.show_message("Удаление: " + text)


    def _on_create_finished(self):
        self._create_last_val = 0
        self.profile_list.load_profiles()
        self.status_bar.show_message("Все профили созданы")


    def _launch_selected(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.logger.warning("No profiles selected for launch")
            self.status_bar.show_warning("Выберите профили для запуска")
            return

        already_running = []
        for profile_id in selected:
            if self.profile_manager.process_manager.is_profile_running(profile_id):
                already_running.append(profile_id)
                
        if already_running:
            self.logger.warning(f"Profiles already running: {already_running}")
            self.status_bar.show_warning(f"Профили {', '.join(map(str, already_running))} уже запущены")
            selected = [pid for pid in selected if pid not in already_running]
            
        if not selected:
            return
            
        self.logger.info(f"Initiating launch sequence for profiles: {selected}")
        self.status_bar.show_message(f"Запуск {len(selected)} профилей...")
        self._launch_queue = list(selected)
        self._launch_next_profile()


    def _launch_next_profile(self):
        if self._launch_queue:
            profile_id = self._launch_queue[0]
            try:
                self.logger.debug(f"Launching profile: {profile_id}")
                if self.profile_manager.launch_profile(profile_id):
                    QThread.sleep(3)
                    self._launch_queue.pop(0)
                    delay = min(2000 + (len(self._launch_queue) * 500), 10000)
                    QTimer.singleShot(delay, self._launch_next_profile)
                    self.status_bar.show_message(f"Запущен профиль {profile_id}")
                else:
                    self.logger.error(f"Failed to launch profile {profile_id}")
                    self._launch_queue.pop(0)
                    QTimer.singleShot(1000, self._launch_next_profile)
            except Exception as e:
                self.logger.error(f"Error launching profile {profile_id}: {e}", exc_info=True)
                self._launch_queue.pop(0)
                QTimer.singleShot(1000, self._launch_next_profile)
        else:
            self.logger.info("Profile launch sequence completed")
            self.status_bar.show_message("Запуск завершён.")
            self.profile_list.load_profiles()

 
    def _edit_proxy_selected(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.logger.warning("No profiles selected for proxy update")
            self.status_bar.show_warning("Выберите профили для изменения прокси")
            return
            
        self.logger.debug(f"Opening proxy dialog for profiles: {selected}")
        current_proxy = None
        if selected:
            current_proxy = self.profile_manager.get_proxy_from_background_js(selected[0])
            
        dialog = ProxyDialog(selected, self, current_proxy)
        if dialog.exec():
            proxy = dialog.get_proxy_string()
            self.logger.info(f"Updating proxy settings for {len(selected)} profiles")
            self.status_bar.show_message("Обновление настроек прокси...")
            
            self.proxy_updater_thread = ProxyUpdaterWorker(
                self.profile_manager, selected, proxy, self
            )
            self.proxy_updater_thread.progress.connect(
                lambda current, total: self.status_bar.show_message(f"Обновление прокси: {current}/{total}")
            )
            self.proxy_updater_thread.finished.connect(self._on_proxy_update_finished)
            self.proxy_updater_thread.start()


    def _on_proxy_update_finished(self):
        self.profile_list.load_profiles()
        self.status_bar.show_message("Настройки прокси обновлены")


    def _delete_selected(self):
        selected = self.profile_list.get_selected_profiles()
        if not selected:
            self.status_bar.show_warning("Выберите профили для удаления")
            return
            
        dialog = DeleteConfirmDialog(len(selected), self)
        if dialog.exec():
            total = len(selected)
            self.status_bar.show_message(f"Удаление: 0/{total}")
            self.deleter_thread = ProfileDeleterWorker(self.profile_manager, selected, self)
            self.deleter_thread.progress.connect(lambda current, total: 
                self.status_bar.show_message(f"Удаление: {current}/{total}"))
            self.deleter_thread.finished.connect(self._on_delete_finished)
            self.deleter_thread.start()


    def _on_delete_finished(self):
        self.profile_list.load_profiles()
        self.status_bar.show_message("Удаление завершено")


    def _change_theme(self, theme: str):
        self.style_manager.apply_theme(theme)
        self.status_bar.show_message(f"Применена тема: {theme}")


    def _update_buttons_state(self):
        if self._updating_buttons:
            return
        self._updating_buttons = True
        try:
            selected = self.profile_list.get_selected_profiles()
            has_selected = len(selected) > 0
            for btn in [
                self.launch_selected_btn,
                self.proxy_selected_btn,
                self.delete_selected_btn,
                self.close_selected_btn,
                self.arrange_windows_btn,
                self.cascade_windows_btn,
                self.tile_horizontal_btn,
                self.tile_vertical_btn
            ]:
                btn.setEnabled(has_selected)
        finally:
            self._updating_buttons = False


    def launch_profile_action(self, profile_id):
        if self.profile_manager.launch_profile(profile_id):
            self.status_bar.show_message(f"Профиль {profile_id} запущен.")
        else:
            self.status_bar.show_error(f"Ошибка запуска профиля {profile_id}.")
        self.profile_list.load_profiles()


    def closeEvent(self, event):
        if hasattr(self, 'status_timer'):
            self.status_timer.stop()
        super().closeEvent(event)
