import os
import json

class SettingsManager:
    DEFAULT_SETTINGS = {
        "jav_paths": [
            "J:/xeditor/videos/JAV",
            "E:/xeditor/videos/JAV",
            "D:/Game/xeditor.crx/JableTVDownload/videos/JAV"
        ],
        "shortvideo_paths": [
            "J:/xeditor/videos/shortvideos",
            "D:/Game/xeditor.crx/JableTVDownload/videos/shortvideos",
            "D:/Game/xeditor.crx/JableTVDownload/videos/JAV",
            "E:/xeditor/videos/shortvideos"
        ]
    }

    def __init__(self, settings_file="settings.json"):
        self.settings_file = settings_file
        self.settings = self.load_settings()

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return self.DEFAULT_SETTINGS.copy()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return self.DEFAULT_SETTINGS.copy()

    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    def get_paths(self, key):
        return self.settings.get(key, [])

    def set_paths(self, key, paths):
        self.settings[key] = paths
        self.save_settings()

    def add_path(self, key, path):
        if key not in self.settings:
            self.settings[key] = []
        if path not in self.settings[key]:
            self.settings[key].append(path)
            self.save_settings()

    def remove_path(self, key, index):
        if key in self.settings and 0 <= index < len(self.settings[key]):
            self.settings[key].pop(index)
            self.save_settings()

    def get_valid_path(self, key):
        """返回第一個存在的路徑，如果都不存在則返回列表中的最後一個（並嘗試創建）"""
        paths = self.get_paths(key)
        if not paths:
            return None
            
        # 嘗試尋找已存在的路徑
        for path in paths:
            if os.path.exists(path):
                return path
                
        # 如果都不存在，返回最後一個路徑（預設路徑）
        # 通常邏輯是嘗試創建它
        default_path = paths[-1]
        try:
            if not os.path.exists(default_path):
                os.makedirs(default_path)
        except:
            pass
        return default_path
