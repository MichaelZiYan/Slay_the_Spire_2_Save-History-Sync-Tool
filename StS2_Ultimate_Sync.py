import os
import winreg
import shutil
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# ================= 配置 =================
CACHE_FILE = "paths_config.txt"
FULL_SAVE_NAME = "全存档.save"
BACKUP_NAME = "我的原始存档备份.save"
STS2_APPID = "2868840"

# ================= 工具函数 =================
def find_all_possible_paths():
    """全自动脱敏探测存档位置"""
    detected_paths = []
    appdata = os.environ.get('APPDATA')
    
    suffixes = [
        os.path.join("modded", "profile1", "saves", "progress.save"),
        os.path.join("profile1", "saves", "progress.save")
    ]

    # 1. 探测 AppData 目录 (GSE & Steam 缓存)
    if appdata:
        search_dirs = [
            os.path.join(appdata, "GSE Saves", STS2_APPID, "remote"),
            os.path.join(appdata, "SlayTheSpire2", "steam")
        ]
        for base in search_dirs:
            if not os.path.exists(base): continue
            # 如果是 Steam 目录，下面还有一层 SteamID 文件夹
            if "SlayTheSpire2" in base:
                for sid in os.listdir(base):
                    sid_path = os.path.join(base, sid)
                    if os.path.isdir(sid_path):
                        for s in suffixes:
                            p = os.path.join(sid_path, s)
                            if os.path.exists(p): detected_paths.append(p)
            else:
                for s in suffixes:
                    p = os.path.join(base, s)
                    if os.path.exists(p): detected_paths.append(p)

    # 2. 探测 Steam 安装目录 (userdata)
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
        steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
        winreg.CloseKey(key)
        userdata = os.path.join(steam_path, "userdata").replace('/', '\\')
        if os.path.exists(userdata):
            for acc in os.listdir(userdata):
                acc_path = os.path.join(userdata, acc, STS2_APPID, "remote")
                if os.path.exists(acc_path):
                    for s in suffixes:
                        p = os.path.join(acc_path, s)
                        if os.path.exists(p): detected_paths.append(p)
    except: pass

    return list(set(detected_paths))

def save_cache(paths):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(paths))

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return None

# ================= 主程序类 =================
class StS2UltimateSync:
    def __init__(self, root):
        self.root = root
        self.root.title("STS2 存档+战绩全能同步工具")
        self.root.geometry("800x720")
        self.setup_ui()

    def log(self, msg):
        """安全写日志"""
        if hasattr(self, 'log_box'):
            now = datetime.now().strftime("%H:%M:%S")
            self.log_box.config(state="normal")
            self.log_box.insert("end", f"[{now}] {msg}\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")

    def setup_ui(self):
        # --- 1. 先创建日志框 (防止后续 log 调用报错) ---
        tk.Label(self.root, text="操作日志：", font=("微软雅黑", 9)).pack(side="bottom", anchor="w", padx=20)
        self.log_box = tk.Text(self.root, height=12, bg="#f8f9fa", font=("Consolas", 9), state="disabled")
        self.log_box.pack(side="bottom", fill="x", padx=20, pady=(0, 20))

        # --- 2. 创建标题和输入框 ---
        tk.Label(self.root, text="杀戮尖塔2 存档 & 战绩同步管理", font=("微软雅黑", 14, "bold"), fg="#c0392b").pack(pady=10)
        tk.Label(self.root, text="存档路径列表 (每行一个 progress.save)：", font=("微软雅黑", 9)).pack(anchor="w", padx=20)
        
        self.path_text = tk.Text(self.root, height=10, font=("Consolas", 9), undo=True)
        self.path_text.pack(fill="x", padx=20, pady=5)

        # --- 3. 按钮布局 ---
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        btn_opt = {"width": 16, "height": 2, "font": ("微软雅黑", 9, "bold")}
        
        tk.Button(btn_frame, text="同步最新进度", bg="#27ae60", fg="white", **btn_opt, command=self.sync_progress).pack(side="left", padx=5)
        tk.Button(btn_frame, text="同步对战记录", bg="#8e44ad", fg="white", **btn_opt, command=self.sync_history).pack(side="left", padx=5)
        tk.Button(btn_frame, text="解锁全成就", bg="#f39c12", fg="white", **btn_opt, command=self.unlock_all).pack(side="left", padx=5)
        tk.Button(btn_frame, text="还原进度备份", bg="#2980b9", fg="white", **btn_opt, command=self.restore).pack(side="left", padx=5)

        # --- 4. 加载数据 ---
        cache = load_cache()
        if cache:
            self.path_text.insert("1.0", "\n".join(cache))
            self.log("已加载本地路径缓存。")
        else:
            auto_paths = find_all_possible_paths()
            if auto_paths:
                self.path_text.insert("1.0", "\n".join(auto_paths))
                self.log("已自动探测并填入本地存档路径。")
            else:
                self.log("未发现存档，请手动粘贴路径。")

    def get_paths(self):
        paths = [p.strip() for p in self.path_text.get("1.0", "end-1c").split('\n') if p.strip()]
        if paths: save_cache(paths)
        return paths

    def sync_progress(self):
        paths = self.get_paths()
        latest_file, latest_mtime = None, 0
        for p in paths:
            if os.path.exists(p) and os.path.getmtime(p) > latest_mtime:
                latest_mtime, latest_file = os.path.getmtime(p), p
        
        if not latest_file: return
        dt = datetime.fromtimestamp(latest_mtime).strftime('%H:%M:%S')
        for target in paths:
            if target != latest_file:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(latest_file, target)
        self.log(f"同步成功！以 {dt} 的存档为准同步了所有版本。")

    def sync_history(self):
        paths = self.get_paths()
        all_runs = {}
        history_dirs = []
        for p in paths:
            h_dir = os.path.join(os.path.dirname(p), "history")
            history_dirs.append(h_dir)
            if os.path.exists(h_dir):
                for f in os.listdir(h_dir):
                    if f.endswith(".run") and f not in all_runs:
                        all_runs[f] = os.path.join(h_dir, f)
        
        count = 0
        for h_dir in history_dirs:
            os.makedirs(h_dir, exist_ok=True)
            for f_name, src in all_runs.items():
                dest = os.path.join(h_dir, f_name)
                if not os.path.exists(dest):
                    shutil.copy2(src, dest)
                    count += 1
        self.log(f"战绩同步完成！共补齐了 {count} 条 .run 记录。")

    def unlock_all(self):
        full_save = os.path.join(os.getcwd(), FULL_SAVE_NAME)
        if not os.path.exists(full_save):
            messagebox.showerror("错误", f"找不到 {FULL_SAVE_NAME}")
            return
        
        paths = self.get_paths()
        # 备份最新
        latest_file, _ = None, 0
        for p in paths:
            if os.path.exists(p) and os.path.getmtime(p) > _:
                _, latest_file = os.path.getmtime(p), p
        if latest_file:
            shutil.copy2(latest_file, os.path.join(os.getcwd(), BACKUP_NAME))
            self.log("已备份当前进度。")

        for target in paths:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(full_save, target)
        self.log("全成就存档已覆盖。")

    def restore(self):
        back = os.path.join(os.getcwd(), BACKUP_NAME)
        if not os.path.exists(back): return
        for target in self.get_paths():
            shutil.copy2(back, target)
        self.log("已还原原始备份。")

if __name__ == "__main__":
    root = tk.Tk()
    app = StS2UltimateSync(root)
    root.mainloop()