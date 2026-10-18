import requests

BASE_URL = "https://lottery-predict-198a.onrender.com"

def trigger_update():
    try:
        requests.get(f"{BASE_URL}/", timeout=60)
        print("新澳門更新完成")
    except Exception as e:
        print(f"新澳門錯誤: {e}")
    
    try:
        requests.get(f"{BASE_URL}/oldmacau", timeout=60)
        print("舊澳門更新完成")
    except Exception as e:
        print(f"舊澳門錯誤: {e}")
    
    try:
        requests.get(f"{BASE_URL}/hk", timeout=60)
        print("香港更新完成")
    except Exception as e:
        print(f"香港錯誤: {e}")

if __name__ == "__main__":
    trigger_update()