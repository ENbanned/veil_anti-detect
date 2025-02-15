from datetime import datetime
from functools import partial
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QHeaderView,
    QAbstractItemView, QPushButton, QTableWidgetItem, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtGui import QColor, QPalette

from utils.logger import get_logger
from ui.components.profile_list.table import HoverableTableWidget
from ui.components.profile_list.cells import createEditableCell
from ui.components.profile_list.delegates import RowHighlightDelegate
from ui.components.profile_list.labels import HeaderCheckBox
from ui.components.dialogs import show_edit_field_dialog, ProxyDialog


class ProfileList(QWidget):
    selection_changed = Signal()
    
    def __init__(self, profile_manager, launch_callback, parent=None):
        super().__init__(parent)
        self.logger = get_logger("profile_list")
        self.logger.debug("Initializing profile list")
        
        self.profile_manager = profile_manager
        self.launch_profile_callback = launch_callback
        self._is_updating = False
        
        self._setup_ui()
        self.logger.info("Profile list initialization completed")


    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        table_container = QFrame()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(1, 1, 1, 1)
        
        self.table = HoverableTableWidget()
        self.table.setFrameShape(QFrame.NoFrame)
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.setColumnCount(8)
        self.table.setWordWrap(True)
        self.table.setShowGrid(False)
        self.table.setGridStyle(Qt.SolidLine)
        self.table.horizontalHeader().setDefaultSectionSize(self.table.columnWidth(0))
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        
        header = self.table.horizontalHeader()
        self.table.setHorizontalHeaderLabels([" ", "ID", "Имя", "Заметки", "Статус", "Прокси", "Последний запуск", "Действие"])
        self.table.setAlternatingRowColors(False)
        header.setSectionsClickable(True)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 50)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 200)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.table.setColumnWidth(3, 750)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        self.table.setColumnWidth(4, 100)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 250)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.table.setColumnWidth(6, 150)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(70)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        
        self.rowHighlightDelegate = RowHighlightDelegate(self.table)
        for col in [1, 4, 6]:
            self.table.setItemDelegateForColumn(col, self.rowHighlightDelegate)
        
        self.header_checkbox = HeaderCheckBox(header)
        self._updateHeaderCheckBoxGeometry()
        header.sectionResized.connect(lambda idx, oldSize, newSize: self._updateHeaderCheckBoxGeometry())
        self.header_checkbox.toggled.connect(self._onHeaderToggled)
        
        self.table.viewport().installEventFilter(self)
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_container)
        
        app = QApplication.instance()
        self.is_dark_theme = False
        app.paletteChanged.connect(self._update_theme)
        self.table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
    def eventFilter(self, source, event):
        if source is self.table.viewport():
            if event.type() == QEvent.MouseMove:
                pos = event.pos()
                row = self.table.rowAt(pos.y())
                for col in [2, 3, 5]:
                    widget = self.table.cellWidget(row, col)
                    if widget:
                        btn = widget.findChild(QPushButton, "editButton")
                        if btn:
                            btn.setVisible(True)
                            
                for r in range(self.table.rowCount()):
                    if r != row:
                        for col in [2, 3, 5]:
                            widget = self.table.cellWidget(r, col)
                            if widget:
                                btn = widget.findChild(QPushButton, "editButton")
                                if btn:
                                    btn.setVisible(False)
                return False
            elif event.type() == QEvent.Leave:
                for r in range(self.table.rowCount()):
                    for col in [2, 3, 5]:
                        widget = self.table.cellWidget(r, col)
                        if widget:
                            btn = widget.findChild(QPushButton, "editButton")
                            if btn:
                                btn.setVisible(False)
                return False
        return super().eventFilter(source, event)


    def _updateHeaderCheckBoxGeometry(self):
        header = self.table.horizontalHeader()
        checkbox_size = self.header_checkbox.sizeHint()
        left_margin = 15
        x = header.sectionPosition(0) + left_margin
        y = (header.height() - checkbox_size.height()) // 2
        self.header_checkbox.setGeometry(x, y, checkbox_size.width(), checkbox_size.height())
        self.header_checkbox.raise_()
        self.header_checkbox.show()


    def _onHeaderToggled(self, state):
        if not self._is_updating:
            try:
                self._is_updating = True
                for row in range(self.table.rowCount()):
                    item = self.table.item(row, 0)
                    if item:
                        item.setCheckState(Qt.Checked if state else Qt.Unchecked)
                self._update_buttons_state()
            finally:
                self._is_updating = False


    def load_profiles(self, preserve_selection: bool = True):
        self.logger.debug("Loading profiles")
        try:
            selected_ids = []
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item and item.checkState() == Qt.Checked:
                    selected_ids.append(int(self.table.item(row, 1).text()))
            
            profiles = self.profile_manager.list_profiles()
            self.table.setRowCount(len(profiles))
            
            running_profiles = self.profile_manager.process_manager.get_running_profiles()
            self.logger.info(f"Found {len(profiles)} profiles, {len(running_profiles)} running")
            
            for row, profile in enumerate(profiles):
                pid = profile["id"]
                is_running = running_profiles.get(pid, False)
                profile["status"] = "Active" if is_running else "Inactive"
                
                checkbox_item = QTableWidgetItem()
                checkbox_item.setTextAlignment(Qt.AlignCenter)
                checkbox_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                checkbox_item.setCheckState(Qt.Checked if pid in selected_ids else Qt.Unchecked)
                self.table.setItem(row, 0, checkbox_item)
                
                id_item = QTableWidgetItem(str(pid))
                id_item.setTextAlignment(Qt.AlignCenter)
                id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 1, id_item)
                
                display_name = profile.get("display_name", "").strip() or "-"
                name_widget = createEditableCell(
                    display_name,
                    partial(self.edit_name, pid, profile.get("display_name", ""))
                )
                self.table.setCellWidget(row, 2, name_widget)
                
                notes_text = profile.get("notes", "").strip() or "-"
                notes_widget = createEditableCell(
                    notes_text,
                    partial(self.edit_notes, pid, profile.get("notes", ""))
                )
                self.table.setCellWidget(row, 3, notes_widget)
                
                status_item = QTableWidgetItem(profile["status"])
                status_item.setTextAlignment(Qt.AlignCenter)
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                status_item.setForeground(QColor("#b38f4e") if profile["status"] == "Active" else QColor("#888888"))
                self.table.setItem(row, 4, status_item)
                
                proxy_val = profile.get("proxy_ip", "").strip() or "-"
                proxy_widget = createEditableCell(
                    proxy_val,
                    partial(self.edit_proxy, pid)
                )
                self.table.setCellWidget(row, 5, proxy_widget)
                
                if profile.get("last_launch"):
                    try:
                        dt = datetime.strptime(profile["last_launch"], "%d.%m.%Y %H:%M:%S")
                        formatted_date = f"{dt.strftime('%d.%m.%Y')}\n{dt.strftime('%H:%M:%S')}"
                    except:
                        formatted_date = "-"
                else:
                    formatted_date = "-"
                time_item = QTableWidgetItem(formatted_date)
                time_item.setTextAlignment(Qt.AlignCenter)
                time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 6, time_item)
                
                action_container = self._create_action_cell(pid, profile["status"] == "Active")
                self.table.setCellWidget(row, 7, action_container)
            
            self._update_buttons_state()
            
        except Exception as e:
            self.logger.error(f"Failed to load profiles: {e}", exc_info=True)


    def _on_item_changed(self, item):
        if not self._is_updating and item.column() == 0:
            try:
                self._is_updating = True
                all_checked = True
                for row in range(self.table.rowCount()):
                    row_item = self.table.item(row, 0)
                    if row_item and row_item.checkState() != Qt.Checked:
                        all_checked = False
                        break
                self.header_checkbox.setChecked(all_checked)
                self._update_buttons_state()
            finally:
                self._is_updating = False


    def _update_buttons_state(self, has_selected=None):
        self.selection_changed.emit()


    def get_selected_profiles(self):
        selected_ids = []
        try:
            for row in range(self.table.rowCount()):
                item = self.table.item(row, 0)
                if item is not None and item.checkState() == Qt.Checked:
                    id_item = self.table.item(row, 1)
                    if id_item is not None:
                        selected_ids.append(int(id_item.text()))
        except Exception as e:
            return []
        return selected_ids


    def update_profile_status(self, profile_id: int, is_active: bool):
        try:
            for row in range(self.table.rowCount()):
                
                if str(self.table.item(row, 1).text()) == str(profile_id):
                    status_item = QTableWidgetItem("Active" if is_active else "Inactive")
                    status_item.setTextAlignment(Qt.AlignCenter)
                    status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                    status_item.setForeground(QColor("#b38f4e") if is_active else QColor("#888888"))
                    self.table.setItem(row, 4, status_item)

                    if is_active:
                        now = datetime.now()
                        formatted_date = f"{now.strftime('%d.%m.%Y')}\n{now.strftime('%H:%M:%S')}"
                        time_item = QTableWidgetItem(formatted_date)
                        time_item.setTextAlignment(Qt.AlignCenter)
                        time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
                        self.table.setItem(row, 6, time_item)

                    action_container = self._create_action_cell(profile_id, is_active)
                    self.table.setCellWidget(row, 7, action_container)

                    self.table.viewport().update()
                    break

        except Exception as e:
            self.logger.error(f"Error updating profile status: {e}")
            
            
    def edit_name(self, pid, current):
        if not pid:
            return
        new_val, ok = show_edit_field_dialog(self.window(), "Редактировать имя", "Имя:", current)
        if ok:
            metadata = self.profile_manager.process_manager.get_profile_metadata(pid)
            data = metadata.load()
            data["display_name"] = new_val or ""
            metadata.save(data)
            self.load_profiles(False)


    def edit_notes(self, pid, current):
        if not pid:
            self.logger.error("Invalid profile id for editing notes")
            return
        new_val, ok = show_edit_field_dialog(self.window(), "Редактировать заметки", "Заметки:", current)
        if ok:
            try:
                metadata = self.profile_manager.process_manager.get_profile_metadata(pid)
                data = metadata.load()
                data["notes"] = new_val or ""
                metadata.save(data)
                self.load_profiles(True)
            except Exception as e:
                self.logger.error(f"Error saving notes: {e}")


    def edit_proxy(self, pid):
        if not pid:
            self.logger.error("Invalid profile id for editing proxy")
            return
        
        current_proxy = self.profile_manager.get_proxy_from_background_js(pid)
        dialog = ProxyDialog([pid], self.window(), current_proxy)
        
        if dialog.exec():
            new_proxy = dialog.get_proxy_string()
            QApplication.processEvents()
            if self.profile_manager.update_profile_proxy(pid, new_proxy):
                self.logger.info(f"Прокси для профиля {pid} обновлены")
            else:
                self.logger.error(f"Ошибка обновления прокси для профиля {pid}")
            self.load_profiles(False)


    def _handle_action(self, profile_id, button):
        if button.text() == "Открыть":
            self.launch_profile_callback(profile_id)
        else:
            if self.profile_manager.close_profile(profile_id):
                QTimer.singleShot(200, lambda: self.update_profile_status(profile_id, False))
                button.setText("Открыть")
                button.setProperty("type", "open")
                button.style().unpolish(button)
                button.style().polish(button)
                self.update_profile_status(profile_id, False)


    def _update_theme(self):
        window_color = self.palette().color(QPalette.Window)
        self.is_dark_theme = window_color.lightness() < 128
        self.table.viewport().update()
        
        
    def _create_action_cell(self, profile_id: int, is_active: bool) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignCenter)

        icon_container = QWidget()
        icon_container.setFixedWidth(29)
        icon_layout = QHBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        show_window_btn = QPushButton()
        show_window_btn.setFixedSize(24, 24)
        show_window_btn.setObjectName("showWindowButton")
        show_window_btn.setCursor(Qt.PointingHandCursor)
        show_window_btn.clicked.connect(lambda: self._handle_show_window(profile_id))
        show_window_btn.setVisible(is_active)
        icon_layout.addWidget(show_window_btn)

        action_btn = QPushButton()
        action_btn.setFixedSize(100, 30)
        
        if is_active:
            action_btn.setText("Закрыть")
            action_btn.setProperty("type", "close")
        else:
            action_btn.setText("Открыть")
            action_btn.setProperty("type", "open")
            
        action_btn.clicked.connect(lambda: self._handle_action(profile_id, action_btn))

        layout.addWidget(icon_container)
        layout.addWidget(action_btn)

        return container

    def _handle_show_window(self, profile_id: int):
        try:
            window_manager = self.window().window_manager
            if window_manager.bring_window_to_front(profile_id):
                self.window().status_bar.show_message(f"Окно профиля {profile_id} развернуто")
            else:
                self.window().status_bar.show_warning(f"Не удалось найти окно профиля {profile_id}")
        except Exception as e:
            self.window().status_bar.show_error(f"Ошибка при разворачивании окна: {str(e)}")
            