import urllib.request
import m3u8
import os

def test_urllib_local():
    print("Testing urllib local path...")
    path = "D:/test/file.txt"
    try:
        urllib.request.urlopen(path)
    except Exception as e:
        print(f"urlopen(path) failed: {e}")

    try:
        urllib.request.urlretrieve(path, "test_output.txt")
    except Exception as e:
        print(f"urlretrieve(path, ...) failed: {e}")

def test_m3u8_load():
    print("Testing m3u8.load local path...")
    path = "D:/test/test.m3u8"
    # Create dummy m3u8
    os.makedirs("D:/test", exist_ok=True)
    with open(path, "w") as f:
        f.write("#EXTM3U")
    
    try:
        m3u8.load(path)
        print("m3u8.load(path) success")
    except Exception as e:
        print(f"m3u8.load(path) failed: {e}")

if __name__ == "__main__":
    test_urllib_local()
    test_m3u8_load()
