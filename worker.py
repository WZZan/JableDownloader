import os
import re
import ssl
import m3u8
import urllib.request
import requests
import cloudscraper
from PyQt5.QtCore import QThread
from signals import WorkerSignals
from crawler import CustomCrawler
from settings_manager import SettingsManager

class DownloadWorker(QThread):
    """下载视频的工作线程"""
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = WorkerSignals()
        self.is_running = True
        self.crawler = None

    def run(self):
        try:
            # 自定义下载逻辑，用于集成进度报告
            self.crawler = CustomCrawler(self.report_progress)
            
            if not self.is_running:
                return
                
            # 调用主函数处理下载
            self.custom_main_jabel(self.url)
            
            if self.is_running:
                self.signals.finished.emit(self.url)
        except Exception as e:
            if self.is_running:
                self.signals.error.emit(self.url, str(e))
    
    def custom_main_jabel(self, url):
        """自定义main_jabel函数，集成进度报告"""
        try:
            # 准备阶段
            self.report_progress(0, "准备下载...")
            
            # 从原main_jabel获取必要的参数
            # 不再导入未使用的模块
            
            # 获取m3u8参数
            import re
            import m3u8
            import urllib.request
            import ssl
            from bs4 import BeautifulSoup
            from selenium import webdriver
            from selenium.webdriver.firefox.options import Options
            
            self.report_progress(5, "获取视频信息...")
            
            ssl._create_default_https_context = ssl._create_unverified_context
            
            # 获取URL中的目录名
            urlSplit = url.split('/')
            if len(urlSplit) >= 2:
                dirName = urlSplit[-2]
            else:
                dirName = "unknown_dir"
            
            # 设置浏览器选项
            options = Options()
            options.add_argument('--headless')
            
            self.report_progress(10, "启动浏览器...")
            
            # 打开浏览器获取页面内容 
            dr = webdriver.Firefox(options=options)
            
            try:
                dr.get(url)
                
                self.report_progress(20, "分析页面内容...")
                
                htmlfile = dr.page_source
                soup = BeautifulSoup(htmlfile, 'html.parser')
                if soup.title and soup.title.string:
                    videoName = soup.title.string
                    if len(videoName) > 33:
                        videoName = videoName[:-33]
                else:
                    # 如果无法获取标题，使用URL的一部分作为默认名称
                    videoName = url.split('/')[-1] or "unknown_video"
                
                # 使用正则表达式找到m3u8 URL
                # 修改為更精確的正則表達式，避免貪婪匹配
                result = re.search(r"https?://[^\"']+\.m3u8", htmlfile)
                if not result:
                    self.report_progress(-1, "未能找到m3u8视频链接")
                    return
                m3u8url = result.group(0)
                self.report_progress(21, f"找到m3u8链接: {m3u8url}")
                
                m3u8urlList = m3u8url.split('/')
                m3u8urlList.pop(-1)
                downloadurl = ('/'.join(m3u8urlList)).replace('\\','/')
            finally:
                # 确保浏览器在任何情况下都会被关闭
                dr.quit()
                self.report_progress(22, "浏览器已关闭")
            
            # 獲取文件路径
            settings = SettingsManager()
            folderPath = settings.get_valid_path("jav_paths")
            
            if not folderPath:
                # Should not happen with default settings, but as a fallback
                folderPath = os.path.join("D:/Game/xeditor.crx/JableTVDownload/videos/JAV", dirName)
                if not os.path.exists(folderPath):
                    os.makedirs(folderPath)
            else:
                folderPath = os.path.join(folderPath, dirName)
                if not os.path.exists(folderPath):
                    os.makedirs(folderPath)
            
            # 检查完整视频文件是否已存在
            final_video_path = os.path.join(folderPath, videoName + '.mp4')
            if os.path.exists(final_video_path):
                self.report_progress(100, "视频已存在，跳过下载")
                return
                
            self.report_progress(30, "下载m3u8文件...")
            
            # 下载m3u8文件
            m3u8file = os.path.join(folderPath, dirName + '.m3u8').replace('\\','/')
            urllib.request.urlretrieve(m3u8url, m3u8file)
            
            # 解析m3u8文件
            with open(m3u8file, 'r', encoding='utf-8') as f:
                content = f.read()
            m3u8obj = m3u8.loads(content)
            m3u8uri = ''
            m3u8iv = ''
            
            for key in m3u8obj.keys:
                if key:
                    m3u8uri = key.uri
                    m3u8iv = key.iv
            
            # 获取所有ts文件URL
            ts_list = []
            for seg in m3u8obj.segments:
                ts_url = downloadurl + '/' + seg.uri
                ts_list.append(ts_url)
            
            # 处理加密
            decryptor = None
            if m3u8uri:
                self.report_progress(40, "处理加密...")
                
                import requests
                from config import headers
                from Crypto.Cipher import AES
                
                m3u8keyurl = downloadurl + '/' + m3u8uri  # 获取key的URL
                
                # 获取key内容
                response = requests.get(m3u8keyurl, headers=headers, timeout=10)
                content_key = response.content
                
                vt = m3u8iv.replace("0x", "")[:16].encode()  # IV取前16位
                
                decryptor = AES.new(content_key, AES.MODE_CBC, vt)  # 构建解码器
            
            # 删除m3u8文件
            self.report_progress(45, "准备下载视频片段...")
            
            if os.path.exists(m3u8file):
                os.remove(m3u8file)
            
            # 这里使用我们自定义的爬虫进行下载
            self.crawler.startCrawl(decryptor, folderPath, ts_list)
            
            # 如果下载被停止，就退出
            if not self.is_running:
                return
            
            self.report_progress(95, "合并视频片段...")
            
            # 合成mp4
            try:
                from merge import mergeMp4_ffmpeg
                mergeMp4_ffmpeg(folderPath, ts_list, videoName)
            except Exception as e:
                self.report_progress(-1, f"合并失败: {str(e)}")
                raise e
            
            # 删除临时文件
            self.report_progress(98, "清理临时文件...")
            try:
                from delete import deleteMp4
                deleteMp4(folderPath, videoName)
            except Exception as e:
                self.report_progress(-1, f"清理文件失败: {str(e)}")
            
            # 下载封面
            self.report_progress(99, "下载封面...")
            try:
                # 下载封面图片的逻辑
                image_meta = soup.find('meta', property='og:image')
                if image_meta:
                    image_url = image_meta.get('content')
                    image_path = os.path.join(folderPath, 'cover.jpg').replace('\\','/')
                    urllib.request.urlretrieve(image_url, image_path)
            except Exception as e:
                self.report_progress(-1, f"下载封面失败: {str(e)}")
            
            # 完成
            self.report_progress(100, "下载完成")
            
        except Exception as e:
            self.report_progress(-1, f"错误: {str(e)}")
            raise e
    
    def report_progress(self, progress, status_message):
        """向主线程报告进度"""
        if self.is_running:
            self.signals.progress.emit(progress, status_message)
    
    def stop(self):
        """停止下载进程"""
        self.is_running = False
        if self.crawler:
            self.crawler.stop()

class DownloadM3u8Worker(QThread):
    """专门下载m3u8视频的工作线程"""
    def __init__(self, url, video_name="", path_type="jav"):
        super().__init__()
        self.url = url
        self.video_name = video_name or "m3u8_video"
        self.path_type = path_type  # "jav" 或 "91"
        self.signals = WorkerSignals()
        self.is_running = True
        self.crawler = None

    def run(self):
        try:
            if not self.is_running:
                return
                
            # 调用主函数处理m3u8下载
            self.download_m3u8_video(self.url)
            
            if self.is_running:
                self.signals.finished.emit(self.url)
        except Exception as e:
            if self.is_running:
                self.signals.error.emit(self.url, str(e))

    def download_m3u8_video(self, m3u8_url):
        """下载m3u8视频的主要函数（先尝试m3u8，失败则按MP4下载）"""
        try:
            self.report_progress(0, "准备下载m3u8视频...")

            # 导入必要的模块
            import requests
            import os
            import re
            import m3u8
            import urllib.request
            from Crypto.Cipher import AES
            from config import headers
            from merge import mergeMp4_ffmpeg
            from delete import deleteMp4

            def looks_like_m3u8(u: str) -> bool:
                return u.lower().endswith('.m3u8') or '.m3u8?' in u.lower()

            def looks_like_mp4(u: str) -> bool:
                return u.lower().endswith('.mp4') or '.mp4?' in u.lower()

            def is_mp4_by_head(u: str) -> bool:
                try:
                    r = requests.head(u, headers=headers, allow_redirects=True, timeout=10)
                    ct = (r.headers.get('content-type') or '').lower()
                    return 'video/mp4' in ct
                except Exception:
                    return False

            base_url = m3u8_url

            # 清理视频名称
            video_name = re.sub(r'[\\/*?:"<>|]', '_', self.video_name)

            self.report_progress(10, f"准备下载: {video_name}")

            # 从视频名称中提取番号作为文件夹名
            folder_name = self.extract_folder_name(video_name)

            # 根据路径类型确定存储路径
            settings = SettingsManager()
            if self.path_type == "91":
                base_folder_path = settings.get_valid_path("shortvideo_paths")
                self.report_progress(11, "使用91视频路径保存")
            else:
                base_folder_path = settings.get_valid_path("jav_paths")
                self.report_progress(11, "使用JAV路径保存")

            if not base_folder_path:
                # Fallback if settings fail
                base_folder_path = "D:/Game/xeditor.crx/JableTVDownload/videos/JAV"
                os.makedirs(base_folder_path, exist_ok=True)

            # 创建番号文件夹
            folder_path = os.path.join(base_folder_path, folder_name)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                self.report_progress(12, f"创建文件夹: {folder_name}")
            else:
                self.report_progress(12, f"使用现有文件夹: {folder_name}")

            # 检查视频是否已存在
            final_video_path = os.path.join(folder_path, video_name + '.mp4')
            if os.path.exists(final_video_path):
                self.report_progress(100, "视频已存在，跳过下载")
                return

            # 先尝试按 m3u8 流程处理
            m3u8_processed = False
            m3u8_error = None
            try:
                self.report_progress(15, "下载m3u8文件...")

                # m3u8 基础 URL
                m3u8_url_parts = base_url.split('/')
                if len(m3u8_url_parts) > 1:
                    m3u8_url_parts.pop(-1)
                download_base_url = '/'.join(m3u8_url_parts)

                # 下载 m3u8 文件
                m3u8_file = os.path.join(folder_path, video_name + '.m3u8')

                resp = requests.get(base_url, headers=headers, timeout=30)
                resp.raise_for_status()
                with open(m3u8_file, 'wb') as f:
                    f.write(resp.content)

                self.report_progress(20, "解析m3u8文件...")

                with open(m3u8_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                m3u8_obj = m3u8.loads(content)

                # 主播放列表处理
                if m3u8_obj.playlists:
                    self.report_progress(22, "检测到主播放列表，选择最高质量...")
                    best_playlist = max(
                        m3u8_obj.playlists,
                        key=lambda p: p.stream_info.bandwidth if p.stream_info and p.stream_info.bandwidth else 0
                    )
                    if best_playlist.uri.startswith('http'):
                        sub_m3u8_url = best_playlist.uri
                    else:
                        sub_m3u8_url = download_base_url + '/' + best_playlist.uri

                    self.report_progress(23, f"下载子播放列表: {best_playlist.uri}")

                    resp = requests.get(sub_m3u8_url, headers=headers, timeout=30)
                    resp.raise_for_status()
                    with open(m3u8_file, 'wb') as f:
                        f.write(resp.content)

                    with open(m3u8_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    m3u8_obj = m3u8.loads(content)

                    # 更新 base url
                    sub_url_parts = sub_m3u8_url.split('/')
                    if len(sub_url_parts) > 1:
                        sub_url_parts.pop(-1)
                    download_base_url = '/'.join(sub_url_parts)

                # 加密信息
                m3u8_key_uri = ''
                m3u8_iv = ''
                for key in m3u8_obj.keys:
                    if key:
                        m3u8_key_uri = key.uri
                        m3u8_iv = key.iv
                        break

                # TS 列表
                ts_list = []
                for seg in m3u8_obj.segments:
                    if seg.uri.startswith('http'):
                        ts_url = seg.uri
                    else:
                        ts_url = download_base_url + '/' + seg.uri
                    ts_list.append(ts_url)

                if not ts_list:
                    raise RuntimeError("未找到视频片段")

                self.report_progress(24, f"找到 {len(ts_list)} 个视频片段")

                # 解密器
                decryptor = None
                if m3u8_key_uri:
                    self.report_progress(25, "处理加密...")
                    key_url = m3u8_key_uri if m3u8_key_uri.startswith('http') else download_base_url + '/' + m3u8_key_uri
                    r = requests.get(key_url, headers=headers, timeout=10)
                    content_key = r.content
                    vt = m3u8_iv.replace("0x", "")[:16].encode() if m3u8_iv else b'\0' * 16
                    decryptor = AES.new(content_key, AES.MODE_CBC, vt)

                # 删除 m3u8 文件
                if os.path.exists(m3u8_file):
                    os.remove(m3u8_file)

                self.report_progress(30, "开始下载视频片段...")

                # 下载 TS 片段
                self.crawler = CustomCrawler(self.report_progress)
                self.crawler.startCrawl(decryptor, folder_path, ts_list)

                if not self.is_running:
                    return

                self.report_progress(95, "合并视频片段...")
                mergeMp4_ffmpeg(folder_path, ts_list, video_name)

                self.report_progress(98, "清理临时文件...")
                try:
                    deleteMp4(folder_path, video_name)
                except Exception as e:
                    self.report_progress(-1, f"清理文件失败: {str(e)}")

                m3u8_processed = True

            except Exception as e:
                m3u8_error = e
                self.report_progress(45, f"m3u8处理失败，准备尝试MP4下载: {str(e)}")

            if not m3u8_processed:
                # 如果 URL 看起来是 MP4，或者通过 HEAD 判断为 MP4，则尝试按 MP4 下载
                treat_as_mp4 = looks_like_mp4(base_url) or is_mp4_by_head(base_url)
                if not treat_as_mp4:
                    self.report_progress(-1, "m3u8处理失败且URL不是MP4")
                    if m3u8_error:
                        raise m3u8_error
                    return

                self.report_progress(50, "开始下载MP4视频...")

                mp4_path = os.path.join(folder_path, video_name + '.mp4')
                try:
                    with requests.get(base_url, headers=headers, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        total_size = int(r.headers.get('content-length', 0))
                        downloaded = 0
                        with open(mp4_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if not self.is_running:
                                    return
                                if chunk:
                                    f.write(chunk)
                                    if total_size:
                                        downloaded += len(chunk)
                                        progress = int(55 + downloaded / total_size * 40)
                                        self.report_progress(progress, f"下载进度: {downloaded / total_size:.1%}")

                    self.report_progress(98, "下载完成，检查文件...")
                    if os.path.exists(m3u8_file):
                        os.remove(m3u8_file)

                except Exception as e:
                    self.report_progress(-1, f"下载MP4文件失败: {str(e)}")
                    # 备选下载方法
                    try:
                        urllib.request.urlretrieve(base_url, mp4_path)
                    except Exception as e2:
                        self.report_progress(-1, f"备选方法也失败: {str(e2)}")
                        raise e2

            self.report_progress(100, "下载完成")

        except Exception as e:
            self.report_progress(-1, f"下载m3u8视频时出错: {str(e)}")
            raise e
    
    def extract_folder_name(self, video_name):
        """从视频名称中提取番号作为文件夹名"""
        try:
            # 常见的番号格式模式
            patterns = [
                # 标准格式: ABC-123, ABCD-123
                r'^([A-Z]{2,5}-\d{2,5})',
                # 带数字的格式: 1ABC-123
                r'^(\d[A-Z]{2,4}-\d{2,5})',
                # FC2格式: FC2-PPV-123456, FC2-123456
                r'^(FC2-(?:PPV-|)\d{4,7})',
                # 纯数字格式: 123456 (6位或以上数字)
                r'^(\d{6,})',
                # 其他格式: ABC123, ABCD123 (字母+数字)
                r'^([A-Z]{2,5}\d{2,5})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, video_name.upper())
                if match:
                    folder_name = match.group(1)
                    self.report_progress(11, f"检测到番号: {folder_name}")
                    return folder_name
            
            # 如果没有匹配到番号，使用视频名称的前20个字符作为文件夹名
            if len(video_name) > 20:
                # 确保在合适的位置截断，避免截断中文字符
                folder_name = video_name[:20].rstrip()
            else:
                folder_name = video_name
            self.report_progress(11, f"未检测到标准番号，使用: {folder_name}")
            return folder_name
            
        except Exception as e:
            # 如果提取失败，使用默认文件夹名
            self.report_progress(11, f"番号提取失败，使用默认名称: {str(e)}")
            return "default_m3u8"
            
    def report_progress(self, progress, status_message):
        """向主线程报告进度"""
        if self.is_running:
            self.signals.progress.emit(progress, status_message)
    
    def stop(self):
        """停止下载进程"""
        self.is_running = False
        if self.crawler:
            self.crawler.stop()

class Download91Worker(QThread):
    """下载91视频的工作线程"""
    def __init__(self, url):
        super().__init__()
        self.url = url
        self.signals = WorkerSignals()
        self.is_running = True
        self.crawler = None

    def run(self):
        try:
            if not self.is_running:
                return
                
            # 调用主函数处理91视频下载
            self.custom_main_91(self.url)
            
            if self.is_running:
                self.signals.finished.emit(self.url)
        except Exception as e:
            if self.is_running:
                self.signals.error.emit(self.url, str(e))
    
    def custom_main_91(self, url):
        """自定义main_91函数，集成进度报告"""
        try:
            # 准备阶段
            self.report_progress(0, "准备下载91视频...")
            
            # 导入必要的模块
            import ssl
            import requests
            import os
            import re
            import m3u8
            import urllib.request
            from Crypto.Cipher import AES
            from config import headers
            from merge import mergeMp4
            from delete import deleteM3u8, deleteMp4
            import time
            import cloudscraper
            from bs4 import BeautifulSoup
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import html
            
            def strencode(encoded_str):
                """
                Decode the encoded string found in the JavaScript strencode2 function
                """
                # Remove HTML entities and decode the string
                encoded_str = html.unescape(encoded_str)
                
                # Extract the hex values from the string
                hex_values = re.findall(r'%([0-9a-fA-F]{2})', encoded_str)
                
                # Convert hex values to characters
                decoded_str = ''.join([chr(int(hex_val, 16)) for hex_val in hex_values])
                
                return decoded_str
            
            self.report_progress(5, "启动浏览器...")
            
            # 使用ChromeDriver启动浏览器
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-extensions')
            options.add_argument('--headless')
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36")

            driver = webdriver.Chrome(options=options)

            try:
                self.report_progress(10, "加载网页...")
                
                # 加载网页
                driver.get(url)

                # 等待页面完全加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # 获取渲染后的页面源码
                rendered_html = driver.page_source

                self.report_progress(20, "解析页面内容...")

                # 查找strencode2加密的视频源
                encoded_pattern = re.search(r"document\.write\(strencode2\(\"(.*?)\"\)\);", rendered_html)
                
                m3u8url = None
                if encoded_pattern:
                    try:
                        # 需要解密strencode2函数
                        encoded_content = encoded_pattern.group(1)
                        
                        # 使用Python版本的解码函数
                        decrypted_html = strencode(encoded_content)
                        
                        # 从解密后的HTML中提取视频源URL - 匹配mp4或m3u8链接
                        source_pattern = re.search(r'<source src=[\'"]([^\'\"]+(?:\.mp4|\.m3u8)[^\'\"]*?)[\'"]', decrypted_html)
                        if source_pattern:
                            m3u8url = source_pattern.group(1)
                            # 记录找到的URL供调试
                            self.report_progress(25, f"找到视频源: {m3u8url[:50]}...")
                    except Exception as e:
                        self.report_progress(-1, f"解密内容时出错: {str(e)}")
                
                # 如果上面的方法失败，尝试直接查找source标签
                if not m3u8url:
                    try:
                        soup = BeautifulSoup(rendered_html, 'html.parser', from_encoding='iso-8859-1')
                        source_tag = soup.find('source')
                        if source_tag:
                            m3u8url = source_tag.get('src')
                    except Exception as e:
                        self.report_progress(-1, f"查找source标签时出错: {str(e)}")
                
                # 如果仍然找不到，可能视频嵌在video.js播放器中
                if not m3u8url:
                    try:
                        video_js_pattern = re.search(r'src=[\'\"](https?://[^\'\"]+\.(?:m3u8|mp4))[\'"]', rendered_html)
                        if video_js_pattern:
                            m3u8url = video_js_pattern.group(1)
                    except Exception as e:
                        self.report_progress(-1, f"查找video.js链接时出错: {str(e)}")
            finally:
                # 确保浏览器在任何情况下都会被关闭
                driver.quit()
                self.report_progress(22, "浏览器已关闭")
            
            if not m3u8url:
                self.report_progress(-1, "未能找到视频源URL")
                return
                
            self.report_progress(30, "获取视频信息...")

            # 对视频URL进行简单处理，确保其有效
            if '?' in m3u8url:
                base_url = m3u8url
            else:
                base_url = m3u8url
            
            # 确认文件类型，决定使用哪种下载方法
            is_m3u8 = base_url.endswith('.m3u8') or '.m3u8?' in base_url
            is_mp4 = base_url.endswith('.mp4') or '.mp4?' in base_url
            
            # 获取视频标题
            cookies={"language":'zh_ZH'}
            videoName = None
            try:
                htmlfile = cloudscraper.create_scraper(browser={
                    'browser': 'firefox',
                    'platform': 'android',
                    'desktop': False
                }, delay=10).get(url, cookies=cookies)
                
                for encoding in ['utf-8', 'iso-8859-1', 'gbk', 'big5']:
                    try:
                        htmlfile.encoding = encoding
                        soup = BeautifulSoup(htmlfile.text, 'html.parser')
                        if soup.title and soup.title.string:
                            videoName = soup.title.string
                            break
                    except UnicodeDecodeError:
                        continue
            except Exception as e:
                self.report_progress(-1, f"获取页面内容时出错: {str(e)}")
            
            # 如果没有获取到标题，使用默认名称
            if not videoName:
                videoName = url.split('/')[-1] or "unknownVideo"
            
            characters = "\nChinese homemade video"
            if videoName:
                for x in range(len(characters)):
                    videoName = videoName.replace(characters[x],"")
            else:
                videoName = "unknownVideo"
            
            # 清理文件名中不允许的字符
            import re
            videoName = re.sub(r'[\\/*?:"<>|]', '_', videoName)  # 替换Windows不允许的文件名字符
            
            self.report_progress(35, f"准备下载: {videoName}")

            # 确定存储路径
            settings = SettingsManager()
            folderPath = settings.get_valid_path("shortvideo_paths")
            
            if not folderPath:
                folderPath = "J:/xeditor/videos/shortvideos"
                if not os.path.exists(folderPath):
                    os.makedirs(folderPath)
            
            # 检查完整视频文件是否已存在
            final_video_path = os.path.join(folderPath, videoName + '.mp4')
            if os.path.exists(final_video_path):
                self.report_progress(100, "视频已存在，跳过下载")
                return

            if is_m3u8:
                m3u8urlList = base_url.split('/')
                m3u8urlList.pop(-1)
                downloadurl = '/'.join(m3u8urlList)
                
                self.report_progress(40, "下载m3u8文件...")
                
                m3u8file = os.path.join(folderPath, videoName + '.m3u8')
                
                try:
                    response = requests.get(base_url, headers=headers, timeout=10)
                    with open(m3u8file, 'wb') as f:
                        f.write(response.content)
                except Exception as e:
                    self.report_progress(-1, f"下载m3u8文件失败: {str(e)}")
                    urllib.request.urlretrieve(base_url, m3u8file)
                
                self.report_progress(45, "解析m3u8文件...")
                
                try:
                    with open(m3u8file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    m3u8obj = m3u8.loads(content)
                    m3u8uri = ''
                    m3u8iv = ''
                    
                    for key in m3u8obj.keys:
                        if key:
                            m3u8uri = key.uri
                            m3u8iv = key.iv
                    
                    ts_list = []
                    for seg in m3u8obj.segments:
                        ts_url = downloadurl + '/' + seg.uri
                        ts_list.append(ts_url)
                    
                    decryptor = None
                    if m3u8uri:
                        self.report_progress(50, "处理加密...")
                        
                        m3u8keyurl = downloadurl + '/' + m3u8uri
                        
                        response = requests.get(m3u8keyurl, headers=headers, timeout=10)
                        content_key = response.content
                        
                        vt = m3u8iv.replace("0x", "")[:16].encode() if m3u8iv else b'\0' * 16
                        
                        decryptor = AES.new(content_key, AES.MODE_CBC, vt)
                    
                    if os.path.exists(m3u8file):
                        os.remove(m3u8file)
                        
                    self.report_progress(55, "准备下载视频片段...")
                    
                    self.crawler = CustomCrawler(self.report_progress)
                    self.crawler.startCrawl(decryptor, folderPath, ts_list)
                    
                    if not self.is_running:
                        return
                        
                    self.report_progress(95, "合并视频片段...")
                    
                    try:
                        from merge import mergeMp4_ffmpeg
                        mergeMp4_ffmpeg(folderPath, ts_list, videoName)
                    except Exception as e:
                        self.report_progress(-1, f"合并失败: {str(e)}")
                        raise e
                    
                    self.report_progress(98, "清理临时文件...")
                    try:
                        from delete import deleteMp4
                        deleteMp4(folderPath, videoName)
                    except Exception as e:
                        self.report_progress(-1, f"清理文件失败: {str(e)}")
                except Exception as e:
                    self.report_progress(-1, f"处理m3u8文件失败: {str(e)}")
                    raise e
            
            elif is_mp4:
                self.report_progress(40, "开始下载MP4视频...")
                
                mp4_path = os.path.join(folderPath, videoName + '.mp4')
                
                try:
                    with requests.get(base_url, headers=headers, stream=True, timeout=30) as r:
                        r.raise_for_status()
                        total_size = int(r.headers.get('content-length', 0))
                        
                        if total_size == 0:
                            self.report_progress(-1, "无法获取文件大小信息")
                            self.report_progress(50, "使用备选下载方法...")
                            urllib.request.urlretrieve(base_url, mp4_path)
                            self.report_progress(100, "下载完成")
                            return
                        
                        downloaded = 0
                        with open(mp4_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if not self.is_running:
                                    return
                                if chunk:
                                    f.write(chunk)
                                    downloaded += len(chunk)
                                    progress = int(50 + downloaded / total_size * 45)
                                    self.report_progress(progress, f"下载进度: {downloaded / total_size:.1%}")
                        
                        self.report_progress(98, "下载完成，检查文件...")
                        
                except Exception as e:
                    self.report_progress(-1, f"下载MP4文件失败: {str(e)}")
                    self.report_progress(50, "使用备选下载方法...")
                    urllib.request.urlretrieve(base_url, mp4_path)
            
            else:
                self.report_progress(-1, "无法识别视频类型，既不是m3u8也不是mp4")
                return
            
            self.report_progress(100, "下载完成")
            
        except Exception as e:
            self.report_progress(-1, f"下载视频时出错: {str(e)}")
            raise e
            
    def report_progress(self, progress, status_message):
        """向主线程报告进度"""
        if self.is_running:
            self.signals.progress.emit(progress, status_message)
    
    def stop(self):
        """停止下载进程"""
        self.is_running = False
        if self.crawler:
            self.crawler.stop()
