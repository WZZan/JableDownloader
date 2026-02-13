import os
import time
import re
import subprocess
def mergeMp4(folderPath,tsList,videoName):
	# 開始時間
    start_time = time.time()
    print('開始合成影片..')

    for i in range(len(tsList)):
        # 尝试匹配 crawler 生成的 00000.mp4 格式
        file = f"{i:05d}.mp4"
        full_path = os.path.join(folderPath, file)
        
        # 如果找不到，尝试旧的命名逻辑 (fallback)
        if not os.path.exists(full_path):
             file = tsList[i].split('/')[-1][0:-3] + '.mp4'
             full_path = os.path.join(folderPath, file)

        if os.path.exists(full_path):
            with open(full_path, 'rb') as f1:
                with open(os.path.join(folderPath, videoName + '.mp4'), 'ab') as f2:
                    f2.write(f1.read())
        else:
            print(file + " 失敗 ")
    end_time = time.time()
    print('花費 {0:.2f} 秒合成影片'.format(end_time - start_time))
    print('下載完成!')



def mergeMp4_ffmpeg(folderPath, tsList, videoName):
    start_time = time.time()
    temp_file = os.path.join(folderPath, f"{videoName}_tmp.mp4")
    output_file = os.path.join(folderPath, f"{videoName}.mp4")

    print('開始合成影片..')

    # 先用 append 合併成臨時檔
    with open(temp_file, 'wb') as f2:  # 建立空的臨時檔
        for i, ts in enumerate(tsList):
            # 新規則：依索引命名
            indexed_name = f"{i:05d}.mp4"
            full_path = os.path.join(folderPath, indexed_name)

            # 後備：相容舊規則（依 URL 截檔名）
            if not os.path.exists(full_path):
                last = ts.split('/')[-1]
                last = last.split('?')[0]  # 去掉 query string
                # 去除 .ts 或其他副檔名
                base = re.sub(r'\.[^.]*$', '', last)
                legacy_name = base + '.mp4'
                legacy_path = os.path.join(folderPath, legacy_name)
                if os.path.exists(legacy_path):
                    full_path = legacy_path

            if os.path.exists(full_path):
                with open(full_path, 'rb') as f1:
                    f2.write(f1.read())
            else:
                print(os.path.basename(full_path) + " 失敗 ")

    print('原始合併完成，開始封裝...')
    
    # 自動使用 ffmpeg 進行轉封裝
    cmd = ['ffmpeg', '-y', '-f', 'mpegts', '-i', temp_file, '-c', 'copy', output_file]
    subprocess.run(cmd, check=True)

    # 刪除臨時檔
    os.remove(temp_file)

    end_time = time.time()
    print('花費 {0:.2f} 秒合成影片'.format(end_time - start_time))
    print('影片生成完成:', output_file)
