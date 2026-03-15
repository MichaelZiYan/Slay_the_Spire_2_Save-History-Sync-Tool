import os
import winreg
import shutil
import tkinter as tk
from tkinter import messagebox
from datetime import datetime

# ================= 配置 =================
CACHE_FILE = "paths_config.txt"
FULL_SAVE_NAME = "全存档.save"
BACKUP_NAME = "我的原始存档路径备份.save" # 会存放在脚本目录下
STS2_APPID = "2868840"
FILES_TO_SYNC = ["progress.save", "current_run.save"]

# ================= 工具函数 =================
def find_all_possible_paths():
    """全自动脱敏探测 saves 目录位置"""
    detected_dirs = []
    appdata = os.environ.get('APPDATA')
    
    # 探测后缀 (现在只定位到 saves 文件夹)
    suffixes = [
        os.path.join("modded", "profile1", "saves"),
        os.path.join("profile1", "saves")
    ]

    # 1. 探测 AppData 目录
    if appdata:
        search_bases = [
            os.path.join(appdata, "GSE Saves", STS2_APPID, "remote"),
            os.path.join(appdata, "SlayTheSpire2", "steam")
        ]
        for base in search_bases:
            if not os.path.exists(base): continue
            if "SlayTheSpire2" in base: # Steam 路径下有 SteamID 文件夹
                for sid in os.listdir(base):
                    sid_path = os.path.join(base, sid)
                    if os.path.isdir(sid_path):
                        for s in suffixes:
                            d = os.path.join(sid_path, s)
                            if os.path.exists(d): detected_dirs.append(d + os.sep)
            else:
                for s in suffixes:
                    d = os.path.join(base, s)
                    if os.path.exists(d): detected_dirs.append(d + os.sep)

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
                        d = os.path.join(acc_path, s)
                        if os.path.exists(d): detected_dirs.append(d + os.sep)
    except: pass

    return list(set(detected_dirs))

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
        self.root.title("STS2 存档+战绩全能同步工具 (目录版)")
        self.root.geometry("800x720")
        self.setup_ui()

    def log(self, msg):
        if hasattr(self, 'log_box'):
            now = datetime.now().strftime("%H:%M:%S")
            self.log_box.config(state="normal")
            self.log_box.insert("end", f"[{now}] {msg}\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")

    def setup_ui(self):
        # 1. 先创建日志框
        tk.Label(self.root, text="操作日志：", font=("微软雅黑", 9)).pack(side="bottom", anchor="w", padx=20)
        self.log_box = tk.Text(self.root, height=12, bg="#f8f9fa", font=("Consolas", 9), state="disabled")
        self.log_box.pack(side="bottom", fill="x", padx=20, pady=(0, 20))

        # 2. 创建标题和输入框
        tk.Label(self.root, text="杀戮尖塔2 存档 & 战绩同步管理", font=("微软雅黑", 14, "bold"), fg="#c0392b").pack(pady=10)
        tk.Label(self.root, text="存档目录列表 (每行一个 ...\\saves\\)：", font=("微软雅黑", 9)).pack(anchor="w", padx=20)
        
        self.path_text = tk.Text(self.root, height=10, font=("Consolas", 9), undo=True)
        self.path_text.pack(fill="x", padx=20, pady=5)

        # 3. 按钮布局
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        btn_opt = {"width": 16, "height": 2, "font": ("微软雅黑", 9, "bold")}
        
        tk.Button(btn_frame, text="同步最新进度", bg="#27ae60", fg="white", **btn_opt, command=self.sync_progress).pack(side="left", padx=5)
        tk.Button(btn_frame, text="同步对战记录", bg="#8e44ad", fg="white", **btn_opt, command=self.sync_history).pack(side="left", padx=5)
        tk.Button(btn_frame, text="解锁全成就", bg="#f39c12", fg="white", **btn_opt, command=self.unlock_all).pack(side="left", padx=5)
        tk.Button(btn_frame, text="还原进度备份", bg="#2980b9", fg="white", **btn_opt, command=self.restore).pack(side="left", padx=5)

        # 4. 加载数据
        cache = load_cache()
        if cache:
            self.path_text.insert("1.0", "\n".join(cache))
            self.log("已加载本地路径缓存。")
        else:
            auto_paths = find_all_possible_paths()
            if auto_paths:
                self.path_text.insert("1.0", "\n".join(auto_paths))
                self.log("已自动探测并填入本地 saves 目录。")
            else:
                self.log("未发现存档，请手动粘贴目录路径。")

    def get_paths(self):
        paths = [p.strip() for p in self.path_text.get("1.0", "end-1c").split('\n') if p.strip()]
        # 确保路径以斜杠结尾
        paths = [p if p.endswith(os.sep) else p + os.sep for p in paths]
        if paths: save_cache(paths)
        return paths

    def sync_progress(self):
        paths = self.get_paths()
        source_dir, latest_mtime = None, 0
        
        # 寻找包含最新文件的目录
        for d in paths:
            if not os.path.exists(d): continue
            for f in FILES_TO_SYNC:
                f_path = os.path.join(d, f)
                if os.path.exists(f_path):
                    mtime = os.path.getmtime(f_path)
                    if mtime > latest_mtime:
                        latest_mtime, source_dir = mtime, d
        
        if not source_dir:
            self.log("未在任何目录发现进度文件。")
            return
            
        dt = datetime.fromtimestamp(latest_mtime).strftime('%H:%M:%S')
        for target_dir in paths:
            if target_dir == source_dir: continue
            os.makedirs(target_dir, exist_ok=True)
            for f in FILES_TO_SYNC:
                src_f = os.path.join(source_dir, f)
                if os.path.exists(src_f):
                    shutil.copy2(src_f, os.path.join(target_dir, f))
        
        self.log(f"同步成功！源目录: {source_dir} (更新时间 {dt})")

    def sync_history(self):
        paths = self.get_paths()
        all_runs = {}
        history_dirs = []
        for d in paths:
            # history 通常与 saves 同级，即在 saves 的上一层目录下
            # 路径示例: .../profile1/saves/ -> .../profile1/history/
            h_dir = os.path.abspath(os.path.join(d, "..", "history"))
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
        self.log(f"战绩同步完成！共补全了 {count} 条记录。")

    def unlock_all(self):
        full_save = os.path.join(os.getcwd(), FULL_SAVE_NAME)
        if not os.path.exists(full_save):
            messagebox.showerror("错误", f"找不到 {FULL_SAVE_NAME}")
            return
        
        paths = self.get_paths()
        # 备份第一个有效目录中的原有进度
        for d in paths:
            prog = os.path.join(d, "progress.save")
            if os.path.exists(prog):
                shutil.copy2(prog, os.path.join(os.getcwd(), BACKUP_NAME))
                self.log(f"已备份原始进度至脚本目录。")
                break

        for target_dir in paths:
            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(full_save, os.path.join(target_dir, "progress.save"))
        self.log("全成就存档已覆盖至所有目录。")

    def restore(self):
        back = os.path.join(os.getcwd(), BACKUP_NAME)
        if not os.path.exists(back):
            self.log("未发现备份文件。")
            return
        for target_dir in self.get_paths():
            if os.path.exists(target_dir):
                shutil.copy2(back, os.path.join(target_dir, "progress.save"))
        self.log("已还原原始备份进度。")

if __name__ == "__main__":
    root = tk.Tk()
    app = StS2UltimateSync(root)
    root.mainloop()
