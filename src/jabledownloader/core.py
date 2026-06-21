import os
import re
import ssl
import m3u8
import urllib.request
import requests
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from Crypto.Cipher import AES
import cloudscraper
import html

from .crawler import CustomCrawler
from .settings_manager import SettingsManager
from .config import headers
from .merge import mergeMp4_ffmpeg, mergeMp4
from .delete import deleteMp4, deleteM3u8

class JableDownloaderCore:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.is_running = True
        self.crawler = None

    def report_progress(self, start_val, message):
        if self.progress_callback:
            self.progress_callback(start_val, message)
        else:
            print(f"[{start_val}%] {message}")

    def stop(self):
        self.is_running = False
        if self.crawler:
            self.crawler.is_running = False
            self.crawler.stop()

    def download(self, url, platform=None, save_loc="jav_paths", video_name=None):
        # Use provided platform or auto-detect
        if platform and platform != "Auto":
            if platform == "Jable":
                self.download_jable(url)
            elif platform == "91":
                self.download_91(url)
            elif platform == "M3U8":
                self.download_m3u8(url, save_loc=save_loc, video_name=video_name)
            else:
                 self.download_jable(url)
            return

        # Auto-detect platform
        if "jable.tv" in url:
            self.download_jable(url)
        elif "91porn.com" in url or "91.com" in url:  # Adjust as needed for 91 domains
            self.download_91(url)
        elif url.endswith(".m3u8") or ".m3u8?" in url:
            self.download_m3u8(url, save_loc=save_loc, video_name=video_name)
        else:
             # Default to Jable if unknown, or maybe error out?
             # For now default to Jable as per previous behavior
             self.download_jable(url)

    def download_jable(self, url):
        try:
            # 准备阶段
            self.report_progress(0, "准备下载 Jable...")
            self.crawler = CustomCrawler(self.report_progress)
            
            if not self.is_running:
                return

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
            
            m3u8url = None
            videoName = "unknown_video"
            downloadurl = ""
            soup = None

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
                    videoName = url.split('/')[-1] or "unknown_video"
                
                # 使用正则表达式找到m3u8 URL
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
                dr.quit()
                self.report_progress(22, "浏览器已关闭")
            
            if not m3u8url:
                return

            # 獲取文件路径
            settings = SettingsManager()
            folderPath = settings.get_valid_path("jav_paths")
            
            if not folderPath:
                folderPath = os.path.join(os.getcwd(), "videos", "JAV")

            # 确保基础目录存在
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)

            # 拼接具体视频目录
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
                m3u8keyurl = downloadurl + '/' + m3u8uri
                response = requests.get(m3u8keyurl, headers=headers, timeout=10)
                content_key = response.content
                vt = m3u8iv.replace("0x", "")[:16].encode()
                decryptor = AES.new(content_key, AES.MODE_CBC, vt)
            
            self.report_progress(45, "准备下载视频片段...")
            if os.path.exists(m3u8file):
                os.remove(m3u8file)
            
            # 启动多线程下载
            self.crawler.startCrawl(decryptor, folderPath, ts_list)
            
            if not self.is_running:
                return
            
            self.report_progress(95, "合并视频片段...")
            try:
                mergeMp4_ffmpeg(folderPath, ts_list, videoName)
            except Exception as e:
                self.report_progress(-1, f"合并失败: {str(e)}")
                raise e
            
            self.report_progress(98, "清理临时文件...")
            try:
                deleteMp4(folderPath, videoName)
            except Exception as e:
                 self.report_progress(98, f"清理临时文件失败: {str(e)}")

            # 下载封面
            self.report_progress(99, "下载封面...")
            try:
                if soup:
                    image_meta = soup.find('meta', property='og:image')
                    if image_meta:
                        image_url = image_meta.get('content')
                        image_path = os.path.join(folderPath, 'cover.jpg').replace('\\','/')
                        urllib.request.urlretrieve(image_url, image_path)
            except Exception as e:
                self.report_progress(-1, f"下载封面失败: {str(e)}")

            self.report_progress(100, f"下载完成: {videoName}")

        except Exception as e:
            self.report_progress(-1, f"发生错误: {str(e)}")
            raise e

    def download_91(self, url):
        self.crawler = CustomCrawler(self.report_progress)
        try:
            # 准备阶段
            self.report_progress(0, "准备下载91视频...")

            # 内部辅助函数
            def strencode(encoded_str):
                encoded_str = html.unescape(encoded_str)
                hex_values = re.findall(r'%([0-9a-fA-F]{2})', encoded_str)
                decoded_str = ''.join([chr(int(hex_val, 16)) for hex_val in hex_values])
                return decoded_str
            
            self.report_progress(5, "启动浏览器...")
            
            options = ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-extensions')
            options.add_argument('--headless')
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36")

            driver = webdriver.Chrome(options=options)

            m3u8url = None
            try:
                self.report_progress(10, "加载网页...")
                driver.get(url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                rendered_html = driver.page_source
                self.report_progress(20, "解析页面内容...")

                encoded_pattern = re.search(r"document\.write\(strencode2\(\"(.*?)\"\)\);", rendered_html)
                if encoded_pattern:
                    try:
                        encoded_content = encoded_pattern.group(1)
                        decrypted_html = strencode(encoded_content)
                        source_pattern = re.search(r'<source src=[\'"]([^\'\"]+(?:\.mp4|\.m3u8)[^\'\"]*?)[\'"]', decrypted_html)
                        if source_pattern:
                            m3u8url = source_pattern.group(1)
                            self.report_progress(25, f"找到视频源: {m3u8url[:50]}...")
                    except Exception as e:
                        self.report_progress(-1, f"解密内容时出错: {str(e)}")
                
                if not m3u8url:
                    try:
                        soup = BeautifulSoup(rendered_html, 'html.parser')
                        source_tag = soup.find('source')
                        if source_tag:
                            m3u8url = source_tag.get('src')
                    except Exception as e:
                        # self.report_progress(-1, f"查找source标签时出错: {str(e)}")
                        pass
                
                if not m3u8url:
                    try:
                        video_js_pattern = re.search(r'src=[\'\"](https?://[^\'\"]+\.(?:m3u8|mp4))[\'"]', rendered_html)
                        if video_js_pattern:
                            m3u8url = video_js_pattern.group(1)
                    except Exception as e:
                         # self.report_progress(-1, f"查找video.js链接时出错: {str(e)}")
                         pass
            finally:
                driver.quit()
                self.report_progress(22, "浏览器已关闭")
            
            if not m3u8url:
                self.report_progress(-1, "未能找到视频源URL")
                return
                
            self.report_progress(30, "获取视频信息...")

            # 获取视频标题
            cookies={"language":'zh_ZH'}
            videoName = None
            try:
                scraper = cloudscraper.create_scraper(browser={'browser': 'firefox','platform': 'android','desktop': False}, delay=10)
                htmlfile = scraper.get(url, cookies=cookies)
                
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
            
            if not videoName:
                videoName = url.split('/')[-1] or "unknownVideo"
            
            characters = "\nChinese homemade video"
            for x in characters:
                videoName = videoName.replace(x,"")
            
            videoName = re.sub(r'[\\/*?:"<>|]', '_', videoName)
            self.report_progress(35, f"准备下载: {videoName}")

            # 确定存储路径
            settings = SettingsManager()
            folderPath = settings.get_valid_path("shortvideo_paths")
            
            if not folderPath:
                folderPath = os.path.join(os.getcwd(), "videos", "shortvideos")
            
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)
            
            final_video_path = os.path.join(folderPath, videoName + '.mp4')
            if os.path.exists(final_video_path):
                self.report_progress(100, "视频已存在，跳过下载")
                return

            base_url = m3u8url
            is_m3u8 = base_url.endswith('.m3u8') or '.m3u8?' in base_url
            
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
                    urllib.request.urlretrieve(base_url, m3u8file)
                
                self.report_progress(45, "解析m3u8文件...")
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

                self.report_progress(55, "下载分片...")
                if os.path.exists(m3u8file):
                    os.remove(m3u8file)
                    
                self.crawler.startCrawl(decryptor, folderPath, ts_list)
                
                if not self.is_running:
                    return

                self.report_progress(95, "合并视频...")
                mergeMp4(folderPath, ts_list, videoName)
                
                self.report_progress(98, "清理...")
                try:
                   deleteMp4(folderPath, videoName)
                except Exception:
                   pass
            else:
                # Direct MP4 download
                self.report_progress(40, "直接下载MP4...")
                saveName = os.path.join(folderPath, videoName + ".mp4")
                response = requests.get(base_url, headers=headers, stream=True, timeout=30)
                total_size = int(response.headers.get('content-length', 0))
                block_size = 1024
                wrote = 0
                with open(saveName, 'wb') as f:
                    for data in response.iter_content(block_size):
                        if not self.is_running:
                            break
                        wrote = wrote + len(data)
                        f.write(data)
                        if total_size != 0:
                            progress = int(wrote / total_size * 100)
                            # Dont report too often
                            if progress % 5 == 0:
                                self.report_progress(progress, f"下载中: {progress}%")

            self.report_progress(100, f"下载完成: {videoName}")

        except Exception as e:
            self.report_progress(-1, f"错误: {str(e)}")
            raise e

    def download_m3u8(self, url, video_name=None, save_loc="jav_paths"):
        self.crawler = CustomCrawler(self.report_progress)
        try:
            self.report_progress(0, "准备下载m3u8视频...")
            
            if not video_name:
                video_name = "m3u8_video_" + str(int(time.time()))

            video_name = re.sub(r'[\\/*?:"<>|]', '_', video_name)
            
            # Extract folder name from jav id if possible
            folder_name = self.extract_folder_name(video_name)
            
            settings = SettingsManager()
            # Default to JAV path for m3u8 generally
            if save_loc not in ["jav_paths", "shortvideo_paths"]:
                save_loc = "jav_paths"
                
            base_path = settings.get_valid_path(save_loc)
            if not base_path:
                suffix = "JAV" if save_loc == "jav_paths" else "shortvideos"
                base_path = os.path.join(os.getcwd(), "videos", suffix)
            
            folderPath = os.path.join(base_path, folder_name)
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)

            final_video_path = os.path.join(folderPath, video_name + '.mp4')
            if os.path.exists(final_video_path):
                 self.report_progress(100, "视频已存在")
                 return

            if url.lower().endswith('.mp4') or '.mp4?' in url.lower():
                # Simple mp4 download
                saveName = final_video_path
                response = requests.get(url, headers=headers, stream=True, timeout=30)
                if response.status_code == 200:
                    with open(saveName, 'wb') as f:
                         for chunk in response.iter_content(1024*1024):
                             if not self.is_running: break
                             f.write(chunk)
                self.report_progress(100, "下载完成")
                return

            # M3U8 process
            m3u8file = os.path.join(folderPath, f'temp_{int(time.time())}.m3u8')
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                with open(m3u8file, 'wb') as f:
                     f.write(response.content)
            except:
                urllib.request.urlretrieve(url, m3u8file)

            with open(m3u8file, 'r', encoding='utf-8') as f:
                content = f.read()
            m3u8obj = m3u8.loads(content)

            # 处理 master 主清单：选择最高画质子清单后重新抓取解析
            if m3u8obj.is_variant and m3u8obj.playlists:
                best = max(
                    m3u8obj.playlists,
                    key=lambda p: (p.stream_info.bandwidth or 0)
                )
                variant_uri = best.uri
                if not variant_uri.startswith('http'):
                    variant_uri = url.rsplit('/', 1)[0] + '/' + variant_uri
                self.report_progress(10, "检测到主清单，切换到最佳画质子清单...")
                url = variant_uri
                resp = requests.get(url, headers=headers, timeout=10)
                content = resp.text
                m3u8obj = m3u8.loads(content)

            ts_list = []
            base_uri = url.rsplit('/', 1)[0]
            for seg in m3u8obj.segments:
                if seg.uri.startswith('http'):
                    ts_list.append(seg.uri)
                else:
                    ts_list.append(base_uri + '/' + seg.uri)
            
            self.report_progress(20, f"发现 {len(ts_list)} 个分片")
            
            # Key/IV logic omitted for generic m3u8 simple implementation or copy from above if needed
            # Assuming standard encrypted m3u8 for now which crawler handles if key is provided
            # But generic m3u8 usually relies on internal key URI, which CustomCrawler might not fully automate without the decryptor object pre-made.
            # My current copy of CustomCrawler expects a decryptor passed in.
            
            # For simplicity, if standard encryption is used:
            decryptor = None
            if m3u8obj.keys and m3u8obj.keys[0]:
                 key = m3u8obj.keys[0]
                 if key.uri:
                     key_url = key.uri if key.uri.startswith('http') else base_uri + '/' + key.uri
                     try:
                        k_resp = requests.get(key_url, headers=headers)
                        key_val = k_resp.content
                        iv_val = bytes.fromhex(key.iv.replace('0x', '')) if key.iv else b'\0'*16
                        decryptor = AES.new(key_val, AES.MODE_CBC, iv_val)
                     except Exception as e:
                        self.report_progress(-1, f"获取Key失败: {e}")

            if os.path.exists(m3u8file):
                os.remove(m3u8file)

            self.crawler.startCrawl(decryptor, folderPath, ts_list)
            
            if not self.is_running: return

            mergeMp4_ffmpeg(folderPath, ts_list, video_name)
            try:
                deleteMp4(folderPath, video_name)
            except: pass
            
            self.report_progress(100, f"下载完成: {video_name}")

        except Exception as e:
            self.report_progress(-1, f"错误: {str(e)}")
            raise e

    def extract_folder_name(self, video_name):
        try:
            # 常见的番号格式模式
            patterns = [
                r'^([A-Z]{2,5}-\d{2,5})',
                r'^(\d[A-Z]{2,4}-\d{2,5})',
                r'^(FC2-(?:PPV-|)\d{4,7})',
                r'^(\d{6,})',
                r'^([A-Z]{2,5}\d{2,5})',
            ]
            for pattern in patterns:
                match = re.search(pattern, video_name.upper())
                if match:
                    return match.group(1)
            
            if len(video_name) > 20:
                return video_name[:20].rstrip()
            return video_name
        except:
            return "default_m3u8"

