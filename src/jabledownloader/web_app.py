import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict
from nicegui import ui
from .core import JableDownloaderCore

# ──────────────────────────────────────────────
# 資料結構
# ──────────────────────────────────────────────

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
        # 輸入欄位
        self.input_url = ""
        self.input_platform = "Auto"
        self.input_save_loc = "JAV"
        self.input_video_name = ""

        # 任務管理
        self.queue: List[DownloadTask] = []
        self.active_tasks: List[DownloadTask] = []   # 正在執行的任務
        self.lock = threading.Lock()                  # 保護 active_tasks / downloaders
        self.max_concurrent: int = 2                  # 最大同時下載數（可由 UI 調整）

        # 每個任務對應的下載器 {task.id -> JableDownloaderCore}
        self.downloaders: Dict[str, JableDownloaderCore] = {}


state = WebAppState()


# ──────────────────────────────────────────────
# 任務處理邏輯
# ──────────────────────────────────────────────

def process_task(task: DownloadTask):
    """在獨立執行緒中處理單一下載任務"""
    # 加入活躍清單
    with state.lock:
        state.active_tasks.append(task)

    task.status = "初始化..."
    task.progress = 0.0

    def on_progress(val, msg):
        task.progress = max(0.0, val / 100.0)
        task.status = msg

    downloader = JableDownloaderCore(progress_callback=on_progress)

    with state.lock:
        state.downloaders[task.id] = downloader

    try:
        save_loc_key = "jav_paths"
        if task.save_loc == "ShortValues":
            save_loc_key = "shortvideo_paths"

        real_name = task.video_name.strip() or None

        downloader.download(
            task.url,
            task.platform,
            save_loc=save_loc_key,
            video_name=real_name
        )
        task.status = "✅ 完成"
        task.progress = 1.0

    except Exception as e:
        task.status = f"❌ 錯誤: {e}"
        task.logs.append(f"Error: {e}")

    finally:
        with state.lock:
            state.downloaders.pop(task.id, None)
            if task in state.active_tasks:
                state.active_tasks.remove(task)


def worker_loop():
    """
    背景調度執行緒。
    每 0.5s 檢查一次：若活躍任務數 < max_concurrent，
    就從佇列頭部取出等待中的任務並啟動新執行緒。
    """
    while True:
        with state.lock:
            active_count = len(state.active_tasks)
            max_c = int(state.max_concurrent) if state.max_concurrent else 2
            slots = max_c - active_count

            if slots > 0:
                pending = [t for t in state.queue if t.status == "等待中"]
                to_start = pending[:slots]
                # 立刻改狀態，避免下次迴圈重複選取
                for t in to_start:
                    t.status = "啟動中..."
            else:
                to_start = []

        # 在鎖外啟動執行緒，避免死鎖
        for task in to_start:
            thread = threading.Thread(target=process_task, args=(task,), daemon=True)
            thread.start()

        time.sleep(0.5)


# 啟動調度執行緒
threading.Thread(target=worker_loop, daemon=True).start()


# ──────────────────────────────────────────────
# UI 操作函式
# ──────────────────────────────────────────────

def add_task_to_queue():
    if not state.input_url.strip():
        ui.notify("請輸入網址", type='warning')
        return

    new_task = DownloadTask(
        id=str(uuid.uuid4()),
        url=state.input_url.strip(),
        platform=state.input_platform,
        save_loc=state.input_save_loc,
        video_name=state.input_video_name,
    )
    state.queue.append(new_task)
    ui.notify(f"✅ 已加入佇列：{new_task.video_name or new_task.url[:40]}")


def remove_task(task: DownloadTask):
    with state.lock:
        is_active = task in state.active_tasks

    if is_active:
        ui.notify("無法刪除正在執行的任務", type='warning')
        return

    if task in state.queue:
        state.queue.remove(task)
        ui.notify("🗑️ 任務已移除")


def stop_task(task_id: str):
    with state.lock:
        downloader = state.downloaders.get(task_id)

    if downloader:
        downloader.stop()
        ui.notify("⏹️ 正在停止任務...")
    else:
        ui.notify("找不到執行中的下載器", type='warning')


def clear_finished():
    finished = [t for t in state.queue if "完成" in t.status or "錯誤" in t.status]
    for t in finished:
        state.queue.remove(t)
    ui.notify(f"已清除 {len(finished)} 筆已完成/錯誤任務")


# ──────────────────────────────────────────────
# NiceGUI 頁面
# ──────────────────────────────────────────────

@ui.page('/')
def main_page():
    ui.colors(primary='#5898d4')

    with ui.column().classes('w-full max-w-4xl mx-auto p-4 gap-4'):

        # 標題
        ui.label('🎬 Jable Downloader Web').classes(
            'text-3xl font-bold text-center w-full mb-2'
        )
        ui.label('多線並行下載版').classes(
            'text-sm text-center text-gray-400 w-full -mt-2 mb-4'
        )

        # ── 新增任務 ──────────────────────────────
        with ui.card().classes('w-full p-4'):
            ui.label('新增下載任務').classes('text-lg font-bold mb-3')

            ui.input('影片網址', placeholder='https://jable.tv/videos/...').bind_value(
                state, 'input_url'
            ).classes('w-full')

            with ui.row().classes('w-full gap-3 mt-2 flex-wrap'):
                ui.select(
                    ['Auto', 'Jable', '91', 'M3U8'],
                    label='平台',
                    value='Auto'
                ).bind_value(state, 'input_platform').classes('w-28')

                ui.select(
                    ['JAV', 'ShortValues'],
                    label='儲存位置',
                    value='JAV'
                ).bind_value(state, 'input_save_loc').classes('w-28')

                ui.input('自定義檔名（可選）').bind_value(
                    state, 'input_video_name'
                ).classes('flex-grow')

            with ui.row().classes('w-full gap-3 mt-3 items-center'):
                ui.button('➕ 加入佇列', on_click=add_task_to_queue).classes(
                    'flex-grow'
                )
                ui.separator().props('vertical')
                ui.label('同時下載數：').classes('text-sm text-gray-500 whitespace-nowrap')
                ui.select(
                    options={1: '1 個', 2: '2 個', 3: '3 個', 4: '4 個', 5: '5 個'},
                    value=2,
                ).bind_value(state, 'max_concurrent').classes('w-24').tooltip(
                    '設定最多幾個影片同時下載'
                )

        # ── 正在下載 ──────────────────────────────
        with ui.card().classes('w-full p-4'):
            with ui.row().classes('w-full items-center justify-between mb-2'):
                ui.label('正在下載').classes('text-lg font-bold')
                active_count_label = ui.label('0 個進行中').classes(
                    'text-sm text-gray-400'
                )

            active_container = ui.column().classes('w-full gap-3')

            def update_active_area():
                with state.lock:
                    current_active = list(state.active_tasks)

                active_count_label.text = (
                    f'{len(current_active)} 個進行中'
                    if current_active
                    else '無進行中任務'
                )

                active_container.clear()
                with active_container:
                    if not current_active:
                        ui.label('目前無正在執行的任務').classes(
                            'text-gray-400 italic text-sm'
                        )
                        return

                    for task in current_active:
                        with ui.card().classes(
                            'w-full p-3 bg-blue-50 border border-blue-200'
                        ):
                            with ui.row().classes('w-full items-center gap-2'):
                                ui.spinner('dots', color='blue', size='sm')
                                ui.label(task.video_name or task.url).classes(
                                    'font-semibold flex-grow truncate text-sm'
                                )
                                ui.badge(task.platform, color='blue').classes(
                                    'text-xs'
                                )
                                ui.button(
                                    icon='stop_circle',
                                    on_click=lambda tid=task.id: stop_task(tid),
                                ).props('flat dense color=red').tooltip('停止此任務')

                            ui.linear_progress(value=0).bind_value_from(
                                task, 'progress'
                            ).classes('h-2 rounded-full mt-2')

                            ui.label().bind_text_from(task, 'status').classes(
                                'text-xs text-gray-500 mt-1'
                            )

            ui.timer(0.5, update_active_area)

        # ── 任務佇列 ──────────────────────────────
        with ui.card().classes('w-full p-4'):
            with ui.row().classes('w-full items-center justify-between mb-2'):
                ui.label('任務佇列').classes('text-lg font-bold')
                ui.button(
                    '🗑 清除已完成',
                    on_click=clear_finished,
                ).props('flat dense color=gray').classes('text-xs')

            queue_container = ui.column().classes('w-full gap-1')

            def update_queue_list():
                queue_container.clear()
                with queue_container:
                    if not state.queue:
                        ui.label('佇列為空').classes('text-gray-400 text-sm italic')
                        return

                    with state.lock:
                        active_ids = {t.id for t in state.active_tasks}

                    for task in state.queue:
                        # 判斷顏色
                        if '完成' in task.status:
                            dot_color = 'positive'
                        elif '錯誤' in task.status:
                            dot_color = 'negative'
                        elif task.id in active_ids or task.status == '啟動中...':
                            dot_color = 'primary'
                        else:
                            dot_color = 'grey-5'

                        with ui.row().classes(
                            'w-full items-center p-2 border rounded gap-2 '
                            + ('bg-blue-50' if task.id in active_ids else 'bg-gray-50')
                        ):
                            ui.icon('circle', color=dot_color).classes('text-sm')

                            with ui.column().classes('flex-grow overflow-hidden min-w-0'):
                                ui.label(task.video_name or task.url).classes(
                                    'truncate font-medium text-sm'
                                )
                                ui.label(
                                    f'{task.platform} ｜ {task.status}'
                                ).classes('text-xs text-gray-400')

                            # 活躍任務顯示迷你進度條
                            if task.id in active_ids:
                                ui.linear_progress(value=0).bind_value_from(
                                    task, 'progress'
                                ).classes('w-24 h-1.5')

                            # 等待中的任務可刪除
                            if (
                                task.status == '等待中'
                                and task.id not in active_ids
                            ):
                                ui.button(
                                    icon='delete',
                                    on_click=lambda t=task: remove_task(t),
                                ).props('flat dense color=red')

            ui.timer(1.0, update_queue_list)


def main():
    ui.run(title='Jable Downloader', port=8000, show=False, reload=False)


if __name__ in {"__main__", "__mp_main__"}:
    main()
