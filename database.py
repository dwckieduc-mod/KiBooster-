    import os
import json
import requests

GIST_ID = os.getenv("GIST_ID")
GITHUB_TOKEN = os.getenv("GITHUB_ID")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
} if GITHUB_TOKEN else {}

DEFAULT_DATA = {
    "links": {},    # { "guild_id": { "child_role_id": "parent_role_id" } }
    "history": {}   # { "guild_id": { "user_id": ["child_role_id_1", ...] } }
}

def load_data() -> dict:
    """Tải dữ liệu liên kết và lịch sử gỡ role từ Gist."""
    if not GIST_ID:
        print("[DATABASE] Thiếu GIST_ID trong môi trường!")
        return DEFAULT_DATA.copy()
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        if res.status_code == 200:
            files = res.json().get("files", {})
            if "roles.json" in files:
                content = files["roles.json"]["content"]
                data = json.loads(content) if content else {}
                
                # Chuyển đổi dữ liệu cũ sang cấu trúc mới nếu cần
                if "links" not in data:
                    data = {"links": data, "history": {}}
                if "history" not in data:
                    data["history"] = {}
                return data
    except Exception as e:
        print(f"[DATABASE] Lỗi khi tải dữ liệu từ Gist: {e}")
    return DEFAULT_DATA.copy()

def save_data(data: dict) -> bool:
    """Lưu dữ liệu vào Gist."""
    if not GIST_ID or not GITHUB_TOKEN:
        print("[DATABASE] Thiếu GIST_ID hoặc GITHUB_ID!")
        return False
    
    url = f"https://api.github.com/gists/{GIST_ID}"
    payload = {
        "files": {
            "roles.json": {
                "content": json.dumps(data, indent=4)
            }
        }
    }
    try:
        res = requests.patch(url, headers=HEADERS, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"[DATABASE] Lỗi khi lưu dữ liệu lên Gist: {e}")
        return False
        
