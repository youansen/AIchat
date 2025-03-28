import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import requests
import threading
import json
import hashlib
import os
import platform
from datetime import datetime

# API配置
API_KEY = 'sk-dpfnluvscykqowvqieqnkqlmidluthutergmlartjyrzjdbo'
API_URL = 'https://api.siliconflow.cn/v1/chat/completions'

def get_appdata_path():
    """获取系统应用数据存储路径"""
    system = platform.system()
    app_name = "DeepSeekChat"
    
    if system == "Windows":
        base_path = os.environ.get('APPDATA', os.path.expanduser('~'))
    elif system == "Darwin":  # macOS
        base_path = os.path.expanduser('~/Library/Application Support')
    else:  # Linux/Unix
        base_path = os.path.expanduser('~/.config')
    
    full_path = os.path.join(base_path, app_name)
    os.makedirs(full_path, exist_ok=True)
    return full_path

class AuthSystem:
    USER_DATA_FILE = os.path.join(get_appdata_path(), "users.json")

    @staticmethod
    def hash_password(password):
        return hashlib.sha256(password.encode()).hexdigest()

    @classmethod
    def load_users(cls):
        try:
            if os.path.exists(cls.USER_DATA_FILE):
                with open(cls.USER_DATA_FILE, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"加载用户数据失败: {str(e)}")
            return {}

    @classmethod
    def save_users(cls, users):
        try:
            with open(cls.USER_DATA_FILE, "w") as f:
                json.dump(users, f, indent=2)
        except Exception as e:
            print(f"保存用户数据失败: {str(e)}")

    @classmethod
    def register_user(cls, username, password):
        users = cls.load_users()
        if username in users:
            return False, "用户名已存在"
        users[username] = cls.hash_password(password)
        cls.save_users(users)
        return True, "注册成功"

    @classmethod
    def verify_user(cls, username, password):
        users = cls.load_users()
        if username not in users:
            return False, "用户不存在"
        if users[username] != cls.hash_password(password):
            return False, "密码错误"
        return True, "登录成功"

class LoginWindow:
    def __init__(self, master, on_login_success):
        self.master = master
        self.on_login_success = on_login_success
        self.master.title("登录 - DeepSeek AI")
        self.master.geometry("400x300")
        self.master.configure(bg="#2d2d2d")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._setup_styles()
        self.create_widgets()

    def _setup_styles(self):
        self.style.configure("TFrame", background="#2d2d2d")
        self.style.configure("TLabel", background="#2d2d2d", foreground="white")
        self.style.configure("TEntry", fieldbackground="#404040", foreground="white")
        self.style.configure("TButton", 
                            background="#404040",
                            foreground="white",
                            padding=8,
                            font=("微软雅黑", 10))
        self.style.map("TButton",
                      background=[('active', '#505050'), ('disabled', '#353535')])

    def create_widgets(self):
        main_frame = ttk.Frame(self.master)
        main_frame.pack(pady=40, padx=20, fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="用户名:").pack(anchor=tk.W)
        self.username_entry = ttk.Entry(main_frame)
        self.username_entry.pack(fill=tk.X, pady=5)

        ttk.Label(main_frame, text="密码:").pack(anchor=tk.W)
        self.password_entry = ttk.Entry(main_frame, show="*")
        self.password_entry.pack(fill=tk.X, pady=5)

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)

        ttk.Button(btn_frame, text="登录", command=self.login).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="注册", command=self.register).pack(side=tk.RIGHT, padx=10)

    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("错误", "用户名和密码不能为空")
            return

        success, msg = AuthSystem.verify_user(username, password)
        if success:
            self.master.destroy()
            self.on_login_success(username)
        else:
            messagebox.showerror("登录失败", msg)

    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("错误", "用户名和密码不能为空")
            return

        success, msg = AuthSystem.register_user(username, password)
        if success:
            messagebox.showinfo("注册成功", "账户已创建，请登录")
        else:
            messagebox.showerror("注册失败", msg)

class HistoryManager:
    def __init__(self, username):
        self.username = username
        self.base_dir = os.path.join(get_appdata_path(), "Users", username, "History")
        os.makedirs(self.base_dir, exist_ok=True)
        
    def get_current_file(self):
        return os.path.join(self.base_dir, f"{datetime.now().strftime('%Y-%m')}.json")
    
    def save_history(self, user_msg, ai_msg):
        history = {
            "timestamp": datetime.now().isoformat(),
            "user": user_msg,
            "ai": ai_msg
        }
        
        file_path = self.get_current_file()
        try:
            data = []
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            data.append(history)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史记录失败: {str(e)}")

    def load_history(self, year_month=None):
        if year_month:
            file_path = os.path.join(self.base_dir, f"{year_month}.json")
        else:
            file_path = self.get_current_file()
        
        if not os.path.exists(file_path):
            return []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []

class DarkChatApplication:
    def __init__(self, master, username):
        self.master = master
        self.username = username
        self.setup_window()
        self.history_manager = HistoryManager(username)
        self.create_widgets()
        self.setup_layout()
        self.create_history_menu()

    def setup_window(self):
        self.master.title(f"DeepSeek AI Chat - 当前用户：{self.username}")
        self.master.geometry("800x600")
        self.master.minsize(600, 400)
        self.master.configure(bg="#2d2d2d")
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._setup_styles()

    def _setup_styles(self):
        self.style.configure(".", background="#2d2d2d", foreground="white")
        self.style.configure("TFrame", background="#2d2d2d")
        self.style.configure("TButton", 
                            background="#404040",
                            foreground="white",
                            bordercolor="#606060",
                            relief="flat",
                            padding=6)
        self.style.map("TButton",
                      background=[('active', '#505050'), ('disabled', '#353535')],
                      bordercolor=[('active', '#707070')])

    def create_widgets(self):
        self.chat_area = scrolledtext.ScrolledText(
            self.master,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("微软雅黑", 11),
            bg="#1a1a1a",
            fg="#e0e0e0",
            insertbackground="white",
            padx=10,
            pady=10,
            highlightthickness=0
        )
        
        self.input_frame = ttk.Frame(self.master)
        self.input_box = tk.Text(
            self.input_frame,
            height=4,
            font=("微软雅黑", 11),
            relief="flat",
            bg="#404040",
            fg="white",
            insertbackground="white",
            padx=10,
            pady=10,
            highlightthickness=0
        )
        self.input_box.bind("<Control-Return>", self.send_message)
        self.input_box.bind("<KeyRelease>", self.auto_resize)
        
        self.send_btn = ttk.Button(
            self.input_frame,
            text="发送 (Ctrl+Enter)",
            command=self.send_message,
            style="TButton"
        )
        
        self.status_bar = ttk.Label(
            self.master,
            text="就绪",
            relief=tk.SUNKEN,
            anchor=tk.W,
            background="#404040",
            foreground="white"
        )

    def setup_layout(self):
        self.chat_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self.input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        self.input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.send_btn.pack(side=tk.RIGHT, padx=(10, 0))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.chat_area.tag_config("user", foreground="#6ab0f3", lmargin1=20, lmargin2=20)
        self.chat_area.tag_config("bot", foreground="#e0e0e0", lmargin1=20, lmargin2=20, spacing3=10)
        self.chat_area.tag_config("error", foreground="#ff4444")

    def create_history_menu(self):
        menubar = tk.Menu(self.master)
        history_menu = tk.Menu(menubar, tearoff=0)
        history_menu.add_command(label="查看历史记录", command=self.show_history)
        menubar.add_cascade(label="历史", menu=history_menu)
        self.master.config(menu=menubar)

    def show_history(self):
        history_win = tk.Toplevel(self.master)
        history_win.title("聊天历史记录")
        history_win.geometry("800x600")
        
        time_frame = ttk.Frame(history_win)
        time_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(time_frame, text="选择月份:").pack(side=tk.LEFT)
        self.month_var = tk.StringVar()
        month_combobox = ttk.Combobox(
            time_frame, 
            textvariable=self.month_var,
            values=self.get_available_months(),
            state="readonly"
        )
        month_combobox.pack(side=tk.LEFT, padx=10)
        month_combobox.bind("<<ComboboxSelected>>", lambda e: self.load_selected_history(history_text))
        
        history_text = scrolledtext.ScrolledText(
            history_win,
            wrap=tk.WORD,
            font=("微软雅黑", 10),
            padx=10,
            pady=10
        )
        history_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.display_history(history_text)

    def get_available_months(self):
        files = os.listdir(self.history_manager.base_dir)
        return [f.replace(".json", "") for f in files if f.endswith(".json")]

    def load_selected_history(self, text_widget):
        selected_month = self.month_var.get()
        history = self.history_manager.load_history(selected_month)
        self.display_history(text_widget, history)

    def display_history(self, text_widget, history=None):
        history = history or self.history_manager.load_history()
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        
        for record in history:
            text_widget.insert(tk.END, 
                f"[{record['timestamp']}]\n"
                f"你：{record['user']}\n"
                f"DeepSeek：{record['ai']}\n\n",
                "history")
        text_widget.config(state=tk.DISABLED)

    def auto_resize(self, event=None):
        lines = self.input_box.get("1.0", "end-1c").count("\n") + 1
        self.input_box.config(height=min(max(lines, 2), 6))

    def send_message(self, event=None):
        user_input = self.input_box.get("1.0", tk.END).strip()
        if not user_input:
            return
        
        self.input_box.delete("1.0", tk.END)
        self.update_ui_state(False)
        self.master.after(0, self.display_message, f"{self.username}：{user_input}\n", "user")
        
        threading.Thread(
            target=self.process_request,
            args=(user_input,),
            daemon=True
        ).start()

    def process_request(self, user_input):
        try:
            headers = {
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json'
            }

            data = {
                'model': 'deepseek-ai/DeepSeek-R1-Distill-Qwen-7B',
                'messages': [{'role': 'user', 'content': user_input}],
                'max_tokens': 10000,
            }

            response = requests.post(API_URL, headers=headers, json=data)
            
            if response.status_code == 200:
                reply = response.json()['choices'][0]['message']['content']
                self.master.after(0, self.display_message, f"DeepSeek：{reply}\n\n", "bot")
                self.history_manager.save_history(user_input, reply)
            else:
                error_msg = f"错误: {response.status_code} - {response.text[:200]}"
                self.master.after(0, self.display_message, error_msg + "\n\n", "error")
        except Exception as e:
            error_msg = f"连接错误：{str(e)}\n\n"
            self.master.after(0, self.display_message, error_msg, "error")
        finally:
            self.master.after(0, self.update_ui_state, True)

    def display_message(self, message, tag):
        self.chat_area.config(state=tk.NORMAL)
        self.chat_area.insert(tk.END, message, tag)
        self.chat_area.config(state=tk.DISABLED)
        self.chat_area.yview(tk.END)
        self.status_bar.config(text="就绪")

    def update_ui_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.send_btn.config(state=state)
        self.input_box.config(state=state)
        self.status_bar.config(text="正在生成回复..." if not enabled else "就绪")

def start_chat(username):
    chat_root = tk.Tk()
    DarkChatApplication(chat_root, username)
    chat_root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    login_root = tk.Toplevel()
    LoginWindow(login_root, lambda username: (login_root.destroy(), start_chat(username)))
    root.mainloop()