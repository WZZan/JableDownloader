from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLineEdit, QLabel, QScrollArea, 
                            QMessageBox, QComboBox, QDialog, QListWidget, 
                            QInputDialog, QFileDialog, QTabWidget)
from download_item import DownloadItem
from settings_manager import SettingsManager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = SettingsManager()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("下載設定")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout()
        
        # Tabs for different path types
        tabs = QTabWidget()
        self.jav_tab = self.create_path_tab("jav_paths", "JAV 下載路徑 (按優先級排序)")
        self.short_tab = self.create_path_tab("shortvideo_paths", "91/短視頻 下載路徑 (按優先級排序)")
        
        tabs.addTab(self.jav_tab['widget'], "JAV路徑")
        tabs.addTab(self.short_tab['widget'], "91/短視頻路徑")
        
        layout.addWidget(tabs)
        
        # Save button
        save_btn = QPushButton("保存設定")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        self.setLayout(layout)
        
    def create_path_tab(self, key, label_text):
        widget = QWidget()
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel(label_text))
        
        list_widget = QListWidget()
        paths = self.settings_manager.get_paths(key)
        for path in paths:
            list_widget.addItem(path)
            
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加路徑")
        remove_btn = QPushButton("移除選中")
        
        add_btn.clicked.connect(lambda: self.add_path(list_widget))
        remove_btn.clicked.connect(lambda: self.remove_path(list_widget))
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(remove_btn)
        
        layout.addWidget(list_widget)
        layout.addLayout(btn_layout)
        widget.setLayout(layout)
        
        return {'widget': widget, 'list': list_widget, 'key': key}
        
    def add_path(self, list_widget):
        path = QFileDialog.getExistingDirectory(self, "選擇下載目錄")
        if path:
            # Check if path already exists in list
            items = [list_widget.item(i).text() for i in range(list_widget.count())]
            if path not in items:
                list_widget.addItem(path)
    
    def remove_path(self, list_widget):
        current_row = list_widget.currentRow()
        if current_row >= 0:
            list_widget.takeItem(current_row)
            
    def save_settings(self):
        # Save JAV paths
        jav_paths = []
        for i in range(self.jav_tab['list'].count()):
            jav_paths.append(self.jav_tab['list'].item(i).text())
        self.settings_manager.set_paths("jav_paths", jav_paths)
        
        # Save Shortvideo paths
        short_paths = []
        for i in range(self.short_tab['list'].count()):
            short_paths.append(self.short_tab['list'].item(i).text())
        self.settings_manager.set_paths("shortvideo_paths", short_paths)
        
        QMessageBox.information(self, "成功", "設定已保存！")
        self.accept()

class MainWindow(QMainWindow):
    """主應用視窗"""
    def __init__(self):
        super().__init__()
        self.download_items = []
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("影片下載器")
        self.setMinimumSize(800, 600)
        
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # URL輸入部分
        url_layout = QHBoxLayout()
        
        url_label = QLabel("影片URL:")
        self.url_input = QLineEdit()
        
        # 添加平台選擇下拉框
        self.platform_selector = QComboBox()
        self.platform_selector.addItem("Jable")
        self.platform_selector.addItem("91影片")
        self.platform_selector.addItem("M3U8")
        
        add_button = QPushButton("添加")
        
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        url_layout.addWidget(self.platform_selector)
        url_layout.addWidget(add_button)
        
        main_layout.addLayout(url_layout)
        
        # M3U8檔案名和路徑選擇區域（在下載列表上方）
        self.m3u8_layout = QHBoxLayout()
        
        # M3U8檔案名輸入框（初始隱藏）
        self.filename_label = QLabel("檔案名:")
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("輸入影片檔案名（不含副檔名）")
        self.filename_input.setMinimumWidth(500)  # 設置最小寬度為450像素（更寬）
        
        # M3U8路徑選擇器（初始隱藏）
        self.path_label = QLabel("儲存到:")
        self.path_selector = QComboBox()
        self.path_selector.addItem("JAV資料夾", "jav")
        self.path_selector.addItem("91影片資料夾", "91")
        
        # 初始隱藏M3U8相關輸入框
        self.filename_label.hide()
        self.filename_input.hide()
        self.path_label.hide()
        self.path_selector.hide()
        
        self.m3u8_layout.addWidget(self.filename_label)
        self.m3u8_layout.addWidget(self.filename_input)
        self.m3u8_layout.addWidget(self.path_label)
        self.m3u8_layout.addWidget(self.path_selector)
        self.m3u8_layout.addStretch()  # 添加彈性空間
        
        main_layout.addLayout(self.m3u8_layout)
        
        # 下載區域
        downloads_label = QLabel("下載列表:")
        main_layout.addWidget(downloads_label)
        
        # 下載列表的滾動區域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.downloads_widget = QWidget()
        self.downloads_layout = QVBoxLayout(self.downloads_widget)
        self.downloads_layout.addStretch()
        
        scroll_area.setWidget(self.downloads_widget)
        main_layout.addWidget(scroll_area)
        
        # 控制按鈕
        control_layout = QHBoxLayout()
        
        start_all_button = QPushButton("全部開始")
        stop_all_button = QPushButton("全部停止")
        remove_all_button = QPushButton("全部移除")
        settings_button = QPushButton("設定")
        
        control_layout.addWidget(start_all_button)
        control_layout.addWidget(stop_all_button)
        control_layout.addWidget(remove_all_button)
        control_layout.addWidget(settings_button)
        
        main_layout.addLayout(control_layout)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # 連接信號
        add_button.clicked.connect(self.add_download)
        self.url_input.returnPressed.connect(self.add_download)
        start_all_button.clicked.connect(self.start_all_downloads)
        stop_all_button.clicked.connect(self.stop_all_downloads)
        remove_all_button.clicked.connect(self.remove_all_downloads)
        settings_button.clicked.connect(self.open_settings)
        
        # 連接平台選擇器的變化事件
        self.platform_selector.currentTextChanged.connect(self.on_platform_changed)
        
        # 初始化顯示狀態
        self.on_platform_changed(self.platform_selector.currentText())
        
    def open_settings(self):
        """打開設定對話框"""
        dialog = SettingsDialog(self)
        dialog.exec_()

    def on_platform_changed(self, platform):
        """處理平台選擇變化"""
        if platform == "M3U8":
            # 顯示M3U8相關輸入框
            self.filename_label.show()
            self.filename_input.show()
            self.path_label.show()
            self.path_selector.show()
        else:
            # 隱藏M3U8相關輸入框
            self.filename_label.hide()
            self.filename_input.hide()
            self.path_label.hide()
            self.path_selector.hide()
        
        # 強制更新佈局
        self.update()
        
    def add_download(self):
        """添加新的下載到列表"""
        url = self.url_input.text().strip()
        platform = self.platform_selector.currentText()
        
        if not url:
            QMessageBox.warning(self, "無效URL", "請輸入有效的URL。")
            return
        
        # 如果是M3U8平台，檢查檔案名和路徑選擇
        if platform == "M3U8":
            filename = self.filename_input.text().strip()
            if not filename:
                QMessageBox.warning(self, "缺少檔案名", "請輸入M3U8影片的檔案名。")
                return
            
            # 獲取選擇的路徑類型
            selected_path_type = self.path_selector.currentData()
            
            # 創建下載項時傳遞自定義檔案名和路徑類型
            download_item = DownloadItem(url, platform, filename, selected_path_type)
        else:
            # 其他平台不需要自定義檔案名和路徑選擇
            download_item = DownloadItem(url, platform)
        
        self.download_items.append(download_item)
        
        # 在末尾伸展前插入新項目
        self.downloads_layout.insertWidget(self.downloads_layout.count() - 1, download_item)
        
        # 連接信號
        download_item.start_button.clicked.connect(lambda: download_item.start_download())
        download_item.stop_button.clicked.connect(lambda: download_item.stop_download())
        download_item.remove_button.clicked.connect(lambda: self.remove_download(download_item))
        
        # 清除輸入
        self.url_input.clear()
        if platform == "M3U8":
            self.filename_input.clear()
            # 路徑選擇器保持用戶的選擇，不清除
        
    def remove_download(self, download_item):
        """從列表中移除下載"""
        download_item.stop_download()
        self.downloads_layout.removeWidget(download_item)
        self.download_items.remove(download_item)
        download_item.deleteLater()
            
    def start_all_downloads(self):
        """開始所有下載"""
        for item in self.download_items:
            if not item.is_running:
                item.start_download()
                
    def stop_all_downloads(self):
        """停止所有下載"""
        for item in self.download_items:
            if item.is_running:
                item.stop_download()
                
    def remove_all_downloads(self):
        """移除所有下載"""
        # 先停止所有下載
        self.stop_all_downloads()
        
        # 移除所有項目
        while self.download_items:
            item = self.download_items[0]
            self.remove_download(item)
            
    def closeEvent(self, event):
        """處理視窗關閉事件"""
        # 關閉前停止所有下載
        running_downloads = any(item.is_running for item in self.download_items)
        
        if running_downloads:
            reply = QMessageBox.question(self, "確認退出",
                                         "下載仍在進行中。確定要退出嗎？",
                                         QMessageBox.Yes | QMessageBox.No,
                                         QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.stop_all_downloads()
                event.accept()
            else:
                event.ignore()
