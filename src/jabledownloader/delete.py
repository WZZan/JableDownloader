import os

def deleteMp4(folderPath,videoName):
    print("正在刪除合成完的影片")
    files = os.listdir(folderPath)
    originFile = videoName + '.mp4'
    
    for file in files:
        if file.endswith('.mp4'):
            if file != originFile:
                os.remove(os.path.join(folderPath, file))
    print("刪除完畢")            
            


def deleteM3u8(folderPath):
    files = os.listdir(folderPath)
    for file in files:
        if file.endswith('.m3u8'):
            os.remove(os.path.join(folderPath, file))
