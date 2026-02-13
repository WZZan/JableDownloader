import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from nicegui import ui, app
from core import JableDownloaderCore
import sys

# 任务数据结构
@dataclass
class DownloadTask:
    id: str
    url: str
    platform: str
    save_loc: str
    video_name: str
    status: str = "等待中"
    progress: float = 0.0
    logs: List[str] = field(default_factory=list)

class WebAppState:
    def __init__(self):
        # Input fields
        self.input_url = ""
        self.input_platform = "Auto"
        self.input_save_loc = "JAV"
        self.input_video_name = ""
        
        # Task management
        self.queue: List[DownloadTask] = []
        self.current_task: Optional[DownloadTask] = None
        self.is_processing = False
        
        # Core downloader instance
        self.downloader: Optional[JableDownloaderCore] = None

state = WebAppState()

def log_message(task: DownloadTask, message: str):
    task.logs.append(message)
    # UI updates are handled by binding or timers
    
def worker_loop():
    while True:
        if not state.is_processing and state.queue:
            # Get next pending task
            next_task = None
            for task in state.queue:
                if task.status == "等待中":
                    next_task = task
                    break
            
            if next_task:
                process_task(next_task)
            else:
                time.sleep(1)
        else:
            time.sleep(1)

def process_task(task: DownloadTask):
    state.is_processing = True
    state.current_task = task
    task.status = "初始化..."
    task.progress = 0.0
    
    def on_progress(val, msg):
        task.progress = val / 100.0
        task.status = msg
        # log_message(task, f"[{val}%] {msg}")

    state.downloader = JableDownloaderCore(progress_callback=on_progress)
    
    try:
        # Configuration mapping
        save_loc_key = "jav_paths"
        if task.save_loc == "ShortValues":
            save_loc_key = "shortvideo_paths"
        
        real_name = task.video_name if task.video_name.strip() else None
        
        state.downloader.download(
            task.url, 
            task.platform, 
            save_loc=save_loc_key, 
            video_name=real_name
        )
        task.status = "完成"
        task.progress = 1.0
    except Exception as e:
        task.status = f"錯誤: {str(e)}"
        log_message(task, f"Error: {str(e)}")
    finally:
        state.downloader = None
        state.current_task = None
        state.is_processing = False

# Start background worker
t = threading.Thread(target=worker_loop, daemon=True)
t.start()

def add_task_to_queue():
    if not state.input_url:
        ui.notify("請輸入網址", type='warning')
        return

    new_task = DownloadTask(
        id=str(uuid.uuid4()),
        url=state.input_url,
        platform=state.input_platform,
        save_loc=state.input_save_loc,
        video_name=state.input_video_name
    )
    state.queue.append(new_task)
    ui.notify("已加入佇列")
    
    # Reset input (optional)
    # state.input_url = ""
    # state.input_video_name = ""

def remove_task(task):
    if task in state.queue:
        if task == state.current_task:
            ui.notify("無法刪除正在執行的任務", type='warning')
            return
        state.queue.remove(task)
        ui.notify("任務已移除")

def stop_current_task():
    if state.downloader and state.current_task:
        state.downloader.stop()
        ui.notify("正在停止當前任務...")

@ui.page('/')
def main_page():
    ui.colors(primary='#5898d4')
    
    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4'):
        ui.label('Jable Downloader Web (多任務版)').classes('text-3xl font-bold text-center w-full mb-4')
        
        # --- Input Section ---
        with ui.card().classes('w-full p-4'):
            ui.label('新增下載任務').classes('text-lg font-bold mb-2')
            
            ui.input('影片網址', placeholder='https://...').bind_value(state, 'input_url').classes('w-full')
            
            with ui.row().classes('w-full gap-4 mt-2'):
                ui.select(['Auto', 'Jable', '91', 'M3U8'], label='模式', value='Auto').bind_value(state, 'input_platform').classes('w-1/4')
                ui.select(['JAV', 'ShortValues'], label='儲存位置', value='JAV').bind_value(state, 'input_save_loc').classes('w-1/4')
                ui.input('自定義檔名 (可選)').bind_value(state, 'input_video_name').classes('flex-grow')
            
            ui.button('加入佇列', on_click=add_task_to_queue).classes('w-full mt-4')

        # --- Status & Current Task ---
        with ui.card().classes('w-full p-4'):
            ui.label('當前狀態').classes('text-lg font-bold mb-2')
            
            # Using a container to refresh content
            status_container = ui.column().classes('w-full')
            
            def update_status_area():
                status_container.clear()
                with status_container:
                    if state.current_task:
                        task = state.current_task
                        ui.label(f"正在下載: {task.video_name or task.url}").classes('font-bold')
                        ui.linear_progress(value=0).bind_value_from(task, 'progress').classes('h-4 rounded mt-2')
                        ui.label().bind_text_from(task, 'status').classes('text-sm text-gray-600')
                        ui.button('停止當前任務', on_click=stop_current_task, color='red').classes('mt-2')
                    else:
                        ui.label("無正在執行的任務").classes('text-gray-500 italic')
            
            ui.timer(0.5, update_status_area)

        # --- Queue List ---
        with ui.card().classes('w-full p-4'):
            ui.label('任務佇列').classes('text-lg font-bold mb-2')
            
            queue_container = ui.column().classes('w-full gap-2')
            
            def update_queue_list():
                queue_container.clear()
                with queue_container:
                    if not state.queue:
                        ui.label("佇列為空").classes('text-gray-400')
                        return
                        
                    for task in state.queue:
                        with ui.row().classes('w-full items-center p-2 border rounded bg-gray-50'):
                            # Status Icon/Color
                            color = 'gray'
                            if task.status == '完成': color = 'green'
                            elif '錯誤' in task.status: color = 'red'
                            elif task == state.current_task: color = 'blue'
                            
                            ui.icon('circle', color=color).classes('mr-2')
                            
                            with ui.column().classes('flex-grow overflow-hidden'):
                                ui.label(task.video_name or task.url).classes('truncate font-medium')
                                ui.label(f"{task.platform} | {task.status}").classes('text-xs text-gray-500')
                            
                            if task.status not in ['完成'] and task != state.current_task:
                                ui.button(icon='delete', on_click=lambda t=task: remove_task(t)).props('flat dense color=red')
                            
                            # Show logs button (optional expansion)

            ui.timer(1.0, update_queue_list)

ui.run(title="Jable Downloader", port=8081, show=False, reload=False)
