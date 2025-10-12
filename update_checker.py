import requests
import re
import json
import threading
import tkinter as tk
from tkinter import messagebox, ttk
import os
import subprocess
import sys
from datetime import datetime, timedelta

# 添加resource_path函数，用于正确获取资源文件路径
def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class UpdateChecker:
    def __init__(self, parent, app=None):
        """初始化升级检查器"""
        self.parent = parent
        self.app = app  # 主应用程序实例，用于显示状态信息
        self.last_check_time = None
        self.check_interval = timedelta(days=1)  # 每天检查一次
        
        # 根据当前运行环境确定配置文件路径
        if getattr(sys, 'frozen', False):
            # 如果是封装后的环境
            self.app_dir = os.path.dirname(sys.executable)
            # 直接使用app目录作为根目录
            self.root_dir = self.app_dir
            
            # 配置文件路径
            self.config_dir = os.path.join(self.root_dir, '..', 'config')
            self.config_file = os.path.join(self.config_dir, 'update_check_config.json')
            # 版本信息文件
            self.version_info_file = resource_path(os.path.join('config', 'version_info.json'))
            # 更新器路径
            self.updater_dir = os.path.join(self.root_dir, '..', 'updater')
            
            # 尝试从版本信息文件读取版本，如果失败则使用默认值
            self.app_version = "1.3"  # 默认版本号
            try:
                if os.path.exists(self.version_info_file):
                    with open(self.version_info_file, 'r', encoding='utf-8') as f:
                        version_info = json.load(f)
                        if 'current_version' in version_info:
                            self.app_version = version_info['current_version']
                            # 更新主应用程序的标题
                            if self.app and hasattr(self.app.root, 'title'):
                                current_title = self.app.root.title()
                                # 替换标题中的版本号
                                new_title = re.sub(r'V[\d.]+', f'V{self.app_version}', current_title)
                                self.app.root.title(new_title)
            except Exception as e:
                if self.app:
                    self.app.update_status(f"[警告] 读取版本信息失败: {str(e)}")
        else:
            # 开发环境
            self.app_dir = os.path.dirname(os.path.abspath(__file__))
            self.config_file = os.path.join(self.app_dir, 'update_check_config.json')
            self.app_version = "1.3"
        
        self.load_config()
        
        # 创建菜单项
        self.create_menu_item()
        
        # 启动后台检查
        self.start_background_check()
    
    def log(self, message):
        """记录日志信息"""
        # 在开发环境中，打印日志到控制台
        print(f"[更新检查器] {message}")
        
        # 在封装环境中，尝试记录日志到文件
        if getattr(sys, 'frozen', False):
            try:
                log_file = os.path.join(self.config_dir, 'update_checker.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"[{timestamp}] {message}\n")
            except Exception as e:
                # 如果记录日志失败，静默忽略
                pass
    
    def load_config(self):
        """加载配置文件"""
        try:
            # 在封装环境中，确保配置目录存在
            if getattr(sys, 'frozen', False) and not os.path.exists(self.config_dir):
                try:
                    os.makedirs(self.config_dir)
                    self.log(f"创建配置目录: {self.config_dir}")
                except Exception as e:
                    self.log(f"创建配置目录失败: {str(e)}")
            
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'last_check_time' in config:
                        self.last_check_time = datetime.fromisoformat(config['last_check_time'])
        except Exception as e:
            if self.app:
                self.app.update_status(f"[警告] 加载升级配置失败: {str(e)}")
    
    def save_config(self):
        """保存配置文件"""
        try:
            config = {
                'last_check_time': self.last_check_time.isoformat() if self.last_check_time else None
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            if self.app:
                self.app.update_status(f"[警告] 保存升级配置失败: {str(e)}")
    
    def create_menu_item(self):
        """在主菜单中创建检查更新菜单项"""
        # 尝试获取menu_bar，首先从app对象（主应用程序）中获取，然后从parent（root窗口）中获取
        menu_bar = None
        if hasattr(self.app, 'menu_bar'):
            menu_bar = self.app.menu_bar
        elif hasattr(self.parent, 'menu_bar'):
            menu_bar = self.parent.menu_bar
        
        if menu_bar:
            # 直接获取帮助菜单，如果不存在则创建
            # 先检查是否已有帮助菜单
            help_menu = None
            try:
                for i in range(menu_bar.index('end') + 1):
                    try:
                        menu_label = menu_bar.entrycget(i, 'label')
                        if menu_label == '帮助':
                            help_menu = menu_bar.nametowidget(menu_bar.entrycget(i, 'menu'))
                            break
                    except:
                        continue
            except:
                # 如果获取菜单索引失败，说明菜单可能为空
                pass
            
            if not help_menu:
                help_menu = tk.Menu(menu_bar, tearoff=0)
                menu_bar.add_cascade(label="帮助", menu=help_menu)
            
            # 直接添加检查更新菜单项
            # 先检查是否已存在该菜单项
            check_exists = False
            try:
                # 检查help_menu是否为空
                end_index = help_menu.index('end')
                if end_index is not None:
                    for i in range(end_index + 1):
                        try:
                            if help_menu.entrycget(i, 'label') == '检查更新':
                                check_exists = True
                                break
                        except:
                            continue
            except:
                # 如果菜单为空或出现其他错误，直接跳过检查
                pass
            
            if not check_exists:
                # 添加分隔符（如果菜单不为空）
                try:
                    end_index = help_menu.index('end')
                    if end_index is not None:
                        help_menu.add_separator()
                except:
                    # 如果菜单为空，不需要添加分隔符
                    pass
                help_menu.add_command(label="检查更新", command=self.check_for_updates)
    
    def start_background_check(self):
        """启动后台自动检查"""
        # 检查是否需要进行自动检查
        should_check = True
        if self.last_check_time:
            should_check = (datetime.now() - self.last_check_time) > self.check_interval
        
        if should_check:
            # 在后台线程中检查更新
            thread = threading.Thread(target=self.check_for_updates, args=(True,), daemon=True)
            thread.start()
    
    def get_current_version(self):
        """获取当前应用和SDK版本信息"""
        try:
            # 首先尝试从版本信息文件获取版本
            if getattr(sys, 'frozen', False) and hasattr(self, 'version_info_file') and os.path.exists(self.version_info_file):
                try:
                    with open(self.version_info_file, 'r', encoding='utf-8') as f:
                        version_info = json.load(f)
                        if 'current_version' in version_info:
                            return version_info['current_version']
                except Exception as e:
                    self.log(f"从版本信息文件读取失败: {str(e)}")
            
            # 在封装环境中
            if getattr(sys, 'frozen', False):
                # 尝试导入SDK获取版本
                try:
                    import volcenginesdkarkruntime
                    if hasattr(volcenginesdkarkruntime, '__version__'):
                        sdk_version = volcenginesdkarkruntime.__version__
                        self.log(f"从SDK获取版本: {sdk_version}")
                        return sdk_version
                except ImportError:
                    self.log("无法导入SDK，使用硬编码版本")
                    
                return self.app_version
            else:
                # 开发环境：从requirements.txt获取SDK版本
                requirements_path = os.path.join(self.app_dir, 'requirements.txt')
                if os.path.exists(requirements_path):
                    try:
                        with open(requirements_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 查找volcengine-python-sdk[ark]的版本
                            match = re.search(r'volcengine-python-sdk\[ark\]==([\d\.]+)', content)
                            if match:
                                sdk_version = match.group(1)
                                self.log(f"从requirements.txt获取版本: {sdk_version}")
                                return sdk_version
                    except Exception as e:
                        self.log(f"读取requirements.txt失败: {str(e)}")
                        
        except Exception as e:
            error_msg = f"[错误] 获取版本信息失败: {str(e)}"
            self.log(error_msg)
            if self.app:
                self.app.update_status(error_msg)
        
        self.log(f"返回默认版本: {self.app_version}")
        return self.app_version
    
    def get_latest_version(self):
        """从PyPI获取最新SDK版本"""
        try:
            # 查询PyPI API获取最新版本
            response = requests.get('https://pypi.org/pypi/volcengine-python-sdk/json', timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data['info']['version']
        except Exception as e:
            if self.app:
                self.app.update_status(f"[错误] 检查SDK更新失败: {str(e)}")
        return None
    
    def check_for_updates(self, automatic=False):
        """检查是否有可用更新"""
        # 更新最后检查时间
        self.last_check_time = datetime.now()
        self.save_config()
        
        if self.app:
            self.app.update_status("[信息] 正在检查更新...")
        
        try:
            current_version = self.get_current_version()
            if not current_version:
                if not automatic:
                    messagebox.showinfo("检查更新", "无法获取当前SDK版本。请检查requirements.txt文件。")
                return
            
            latest_version = self.get_latest_version()
            if not latest_version:
                if not automatic:
                    messagebox.showinfo("检查更新", "无法连接到PyPI服务器。请稍后再试。")
                return
            
            # 比较版本号
            if self.compare_versions(current_version, latest_version) < 0:
                # 有新版本可用
                self.parent.after(0, lambda: self.show_update_dialog(current_version, latest_version))
            else:
                if not automatic:
                    self.parent.after(0, lambda: messagebox.showinfo("检查更新", f"您正在使用最新版本的SDK: {current_version}"))
            
        finally:
            if self.app:
                self.app.update_status("[信息] 更新检查完成")
    
    def compare_versions(self, version1, version2):
        """比较两个版本号"""
        v1_parts = list(map(int, version1.split('.')))
        v2_parts = list(map(int, version2.split('.')))
        
        # 补齐版本号长度
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts += [0] * (max_len - len(v1_parts))
        v2_parts += [0] * (max_len - len(v2_parts))
        
        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        return 0
    
    def show_update_dialog(self, current_version, latest_version):
        """显示更新对话框"""
        # 创建一个新窗口
        dialog = tk.Toplevel(self.parent)
        dialog.title("发现新版本")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.parent)  # 设置为主窗口的子窗口
        dialog.grab_set()  # 模态窗口
        
        # 窗口居中
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.parent.winfo_width() // 2) - (width // 2) + self.parent.winfo_x()
        y = (self.parent.winfo_height() // 2) - (height // 2) + self.parent.winfo_y()
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # 添加信息标签
        ttk.Label(dialog, text="发现新的SDK版本!").grid(row=0, column=0, columnspan=2, pady=10)
        ttk.Label(dialog, text=f"当前版本: {current_version}").grid(row=1, column=0, sticky=tk.W, padx=20, pady=5)
        ttk.Label(dialog, text=f"最新版本: {latest_version}").grid(row=2, column=0, sticky=tk.W, padx=20, pady=5)
        
        # 添加按钮
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="立即更新", command=lambda: self.perform_update(dialog)).grid(row=0, column=0, padx=10)
        ttk.Button(button_frame, text="稍后提醒", command=dialog.destroy).grid(row=0, column=1, padx=10)
        
    def perform_update(self, dialog):
        """执行更新操作"""
        dialog.destroy()
        
        if self.app:
            self.app.update_status("[信息] 正在准备更新...")
        
        try:
            if getattr(sys, 'frozen', False):
                # 封装环境：启动外部更新器
                # 首先检查更新器目录是否存在
                if not os.path.exists(self.updater_dir):
                    self.log(f"更新器目录不存在: {self.updater_dir}")
                    # 尝试使用绝对路径
                    alt_updater_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'updater')
                    if os.path.exists(alt_updater_dir):
                        self.log(f"使用替代更新器目录: {alt_updater_dir}")
                        self.updater_dir = alt_updater_dir
                    else:
                        raise Exception(f"更新器目录不存在: {self.updater_dir} 和 {alt_updater_dir}")
                
                if os.name == 'nt':  # Windows
                    # 检查是否有预编译的更新器可执行文件
                    updater_exe = os.path.join(self.updater_dir, 'updater.exe')
                    self.log(f"检查更新器可执行文件: {updater_exe}")
                    
                    if os.path.exists(updater_exe):
                        # 运行预编译的更新器
                        self.log(f"启动预编译的更新器: {updater_exe}")
                        cmd = f'start "应用更新器" "{updater_exe}"'
                        self.log(f"执行命令: {cmd}")
                        os.system(cmd)
                    else:
                        # 尝试运行Python脚本形式的更新器
                        updater_script = os.path.join(self.updater_dir, 'updater.py')
                        self.log(f"检查更新器脚本: {updater_script}")
                        
                        if os.path.exists(updater_script):
                            # 使用系统安装的Python
                            self.log(f"使用系统Python运行更新器脚本: {updater_script}")
                            cmd = f'start "应用更新器" python "{updater_script}"'
                            self.log(f"执行命令: {cmd}")
                            os.system(cmd)
                        else:
                            raise Exception(f"未找到更新器文件: {updater_exe} 或 {updater_script}")
                
                if self.app:
                    self.app.update_status("[信息] 外部更新器已启动，请按照提示完成更新")
                    messagebox.showinfo("应用更新", "外部更新器已启动，请按照提示完成更新。\n更新完成后应用程序将自动重启。")
            else:
                # 开发环境：直接更新SDK
                if os.name == 'nt':  # Windows
                    cmd = f'cmd /c "pip install --upgrade volcengine-python-sdk[ark] && pause"'
                    os.system(f'start "更新SDK" {cmd}')
                else:  # macOS/Linux
                    cmd = f'pip install --upgrade volcengine-python-sdk[ark] && read -p "按Enter键继续..."'
                    os.system(f'xterm -e "{cmd}"')
                
                if self.app:
                    self.app.update_status("[信息] SDK更新已开始，请在弹出的终端窗口中完成更新")
                    messagebox.showinfo("更新SDK", "SDK更新已开始，请在弹出的终端窗口中完成更新。\n更新完成后请重启应用程序。")
        except Exception as e:
            if self.app:
                self.app.update_status(f"[错误] 启动更新失败: {str(e)}")
            messagebox.showerror("更新失败", f"无法启动更新: {str(e)}")

# 如果直接运行此脚本，用于测试
if __name__ == "__main__":
    root = tk.Tk()
    root.title("更新检查器测试")
    root.geometry("300x200")
    
    # 创建菜单
    menu_bar = tk.Menu(root)
    root.config(menu=menu_bar)
    
    # 保存菜单引用
    root.menu_bar = menu_bar
    
    # 模拟主应用程序
    class MockApp:
        def update_status(self, message):
            print(message)
    
    # 创建更新检查器
    update_checker = UpdateChecker(root, MockApp())
    
    # 测试按钮
    ttk.Button(root, text="检查更新", command=update_checker.check_for_updates).pack(pady=50)
    
    root.mainloop()