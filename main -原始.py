import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import requests
import json
import threading
from PIL import Image, ImageTk
import os
import base64
from urllib.parse import urlparse
import sys
import re

# 导入升级检查器
from update_checker import UpdateChecker

def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller创建的临时文件夹
        base_path = sys._MEIPASS
    except Exception:
        # 开发环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 火山AI SDK导入
try:
    from volcenginesdkarkruntime import Ark
    from volcenginesdkarkruntime.types.images import SequentialImageGenerationOptions
    # 尝试导入图像生成相关的模块
    HAS_ARK_SDK = True
except ImportError:
    HAS_ARK_SDK = False
    print("警告: 未找到火山AI SDK，请安装 'volcengine-python-sdk[ark]'")

class VolcanoImageGenerator:
    def __init__(self, root):
        self.root = root
        
        # 初始化版本号为默认值
        default_version = "1.3"
        email = "邮箱ozxuu@outlook.com"
        
        # 尝试从版本信息文件读取版本号
        version_info_file = None
        if getattr(sys, 'frozen', False):
            # 封装环境
            app_dir = os.path.dirname(sys.executable)
            config_dir = os.path.join(app_dir, '..', 'config')
            version_info_file = os.path.join(config_dir, 'version_info.json')
        else:
            # 开发环境
            version_info_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'new', 'config', 'version_info.json')
        
        current_version = default_version
        if version_info_file and os.path.exists(version_info_file):
            try:
                with open(version_info_file, 'r', encoding='utf-8') as f:
                    version_info = json.load(f)
                    if 'current_version' in version_info:
                        current_version = version_info['current_version']
            except Exception as e:
                print(f"读取版本信息失败: {str(e)}")
        
        # 设置窗口标题
        self.root.title(f"火山AI图像生成器V{current_version} {email}")
        self.root.geometry("900x700")
        
        # 创建菜单栏
        self.create_menu()
        
        # API配置
        self.api_key = tk.StringVar()
        self.model = tk.StringVar(value="doubao-seedream-4-0-250828")
        
        # DeepSeek API配置
        self.deepseek_api_key = tk.StringVar()
        
        # 图像生成参数
        self.prompt = tk.StringVar()
        self.size = tk.StringVar(value="2K")
        self.watermark = tk.BooleanVar(value=True)
        self.stream = tk.BooleanVar(value=False)
        self.sequential_gen = tk.StringVar(value="Disabled (禁用)")
        self.max_images = tk.IntVar(value=4)
        
        # DeepSeek参数
        self.deepseek_model = tk.StringVar(value="deepseek-chat")
        
        # 图生图参数
        self.image_path = tk.StringVar()
        self.reference_images = []
        
        # 当前显示的图像路径
        self.current_image_path = None
        
        # 初始化升级检查器
        self.update_checker = UpdateChecker(self.root, self)
        
        self.setup_ui()
        
    def create_menu(self):
        """创建菜单栏"""
        self.menu_bar = tk.Menu(self.root)
        self.root.config(menu=self.menu_bar)
        
        # 创建文件菜单
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        self.menu_bar.add_cascade(label="文件", menu=file_menu)
        
        # 创建帮助菜单
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="帮助", menu=help_menu)
        
    def add_context_menu(self, widget):
        """为输入框添加右键复制粘贴菜单"""
        context_menu = tk.Menu(widget, tearoff=0)
        context_menu.add_command(label="复制", command=lambda: self.copy_to_clipboard(widget))
        context_menu.add_command(label="粘贴", command=lambda: self.paste_from_clipboard(widget))
        context_menu.add_command(label="剪切", command=lambda: self.cut_to_clipboard(widget))
        
        # 绑定右键事件
        widget.bind("<Button-3>", lambda event: self.show_context_menu(event, context_menu))
        
    def show_context_menu(self, event, menu):
        """显示右键菜单"""
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            
    def copy_to_clipboard(self, widget):
        """复制选中的文本到剪贴板"""
        try:
            if isinstance(widget, scrolledtext.ScrolledText):
                # 对于ScrolledText组件
                try:
                    selected_text = widget.selection_get()
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
                except tk.TclError:
                    # 没有选中文本
                    pass
            else:
                # 对于Entry组件
                try:
                    selected_text = widget.selection_get()
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
                except tk.TclError:
                    # 没有选中文本
                    pass
        except Exception as e:
            self.update_status(f"复制失败: {str(e)}")
            
    def paste_from_clipboard(self, widget):
        """从剪贴板粘贴文本"""
        try:
            clipboard_text = widget.clipboard_get()
            if isinstance(widget, scrolledtext.ScrolledText):
                # 对于ScrolledText组件，插入到光标位置
                widget.insert(tk.INSERT, clipboard_text)
            else:
                # 对于Entry组件，插入到光标位置
                widget.insert(tk.INSERT, clipboard_text)
        except Exception as e:
            self.update_status(f"粘贴失败: {str(e)}")
            
    def cut_to_clipboard(self, widget):
        """剪切选中的文本到剪贴板"""
        try:
            if isinstance(widget, scrolledtext.ScrolledText):
                # 对于ScrolledText组件
                try:
                    selected_text = widget.selection_get()
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
                    widget.delete("sel.first", "sel.last")
                except tk.TclError:
                    # 没有选中文本
                    pass
            else:
                # 对于Entry组件
                try:
                    selected_text = widget.selection_get()
                    widget.clipboard_clear()
                    widget.clipboard_append(selected_text)
                    widget.delete(0, tk.END)
                except tk.TclError:
                    # 没有选中文本
                    pass
        except Exception as e:
            self.update_status(f"剪切失败: {str(e)}")
        
    def expand_status(self):
        """扩大状态栏"""
        self.status_text_height = min(20, self.status_text_height + 2)  # 最大高度为20
        self.status_text.config(height=self.status_text_height)
        self.update_status(f"[信息] 状态栏已扩大，当前高度: {self.status_text_height}")
        
    def shrink_status(self):
        """缩小状态栏"""
        self.status_text_height = max(4, self.status_text_height - 2)  # 最小高度为4
        self.status_text.config(height=self.status_text_height)
        self.update_status(f"[信息] 状态栏已缩小，当前高度: {self.status_text_height}")
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        # 为各主要区域配置行权重，使图像预览区域能够更好地利用空间
        main_frame.rowconfigure(5, weight=1)  # 图像预览区域权重
        
        # API密钥区域
        api_frame = ttk.LabelFrame(main_frame, text="API配置", padding="10")
        api_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        api_frame.columnconfigure(1, weight=1)
        
        ttk.Label(api_frame, text="火山AI API密钥:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.api_key_entry = ttk.Entry(api_frame, textvariable=self.api_key, width=50)
        self.api_key_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.add_context_menu(self.api_key_entry)
        ttk.Button(api_frame, text="保存密钥", command=self.save_api_key).grid(row=0, column=2, padx=(0, 5))
        ttk.Button(api_frame, text="测试连接", command=self.test_api_connectivity).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(api_frame, text="清除密钥", command=self.clear_saved_api_key).grid(row=0, column=4)
        
        # DeepSeek API密钥区域
        ttk.Label(api_frame, text="DeepSeek API密钥:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.deepseek_api_key_entry = ttk.Entry(api_frame, textvariable=self.deepseek_api_key, width=50)
        self.deepseek_api_key_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(0, 5))
        self.add_context_menu(self.deepseek_api_key_entry)
        ttk.Button(api_frame, text="保存DeepSeek密钥", command=self.save_deepseek_api_key).grid(row=1, column=2, padx=(0, 5))
        ttk.Button(api_frame, text="测试DeepSeek连接", command=self.test_deepseek_connectivity).grid(row=1, column=3, padx=(0, 5))
        ttk.Button(api_frame, text="清除DeepSeek密钥", command=self.clear_deepseek_api_key).grid(row=1, column=4)
        
        # DeepSeek模型选择
        ttk.Label(api_frame, text="DeepSeek模型:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        model_combo = ttk.Combobox(api_frame, textvariable=self.deepseek_model,
                                  values=["deepseek-chat", "deepseek-reasoner"], state="readonly", width=20)
        model_combo.grid(row=2, column=1, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Label(api_frame, text="（API密钥通用）", foreground="gray").grid(
            row=2, column=2, sticky=tk.W, pady=(5, 0))
        
        # 加载已保存的API密钥
        self.load_api_key()
        self.load_deepseek_api_key()
        
        # 模式选择区域
        mode_frame = ttk.LabelFrame(main_frame, text="生成模式", padding="10")
        mode_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        mode_frame.columnconfigure(0, weight=1)
        
        self.mode_var = tk.StringVar(value="txt2img_single")
        modes = [
            ("文本生成单张图", "txt2img_single"),
            ("文本生成组图", "txt2img_multi"),
            ("图生图-单张", "img2img_single"),
            ("图生图-组图", "img2img_multi"),
            ("多图参考生成单张", "multi_img2img_single"),
            ("多图参考生成组图", "multi_img2img_multi")
        ]
        
        mode_row = 0
        mode_col = 0
        for text, mode in modes:
            ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=mode, 
                           command=self.on_mode_change).grid(row=mode_row, column=mode_col, sticky=tk.W, padx=(0, 10))
            mode_col += 1
            if mode_col > 2:
                mode_col = 0
                mode_row += 1
        
        # 参数设置区域
        params_frame = ttk.LabelFrame(main_frame, text="参数设置", padding="10")
        params_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        params_frame.columnconfigure(1, weight=1)
        
        # 提示词
        ttk.Label(params_frame, text="提示词:").grid(row=0, column=0, sticky=tk.NW, padx=(0, 5))
        self.prompt_text = scrolledtext.ScrolledText(params_frame, height=4, wrap=tk.WORD)
        self.prompt_text.grid(row=0, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        self.add_context_menu(self.prompt_text)
        
        # 人格预设
        ttk.Label(params_frame, text="人格预设:").grid(row=1, column=0, sticky=tk.NW, padx=(0, 5), pady=(0, 5))
        self.persona_preset = scrolledtext.ScrolledText(params_frame, height=3, wrap=tk.WORD)
        self.persona_preset.grid(row=1, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        self.add_context_menu(self.persona_preset)
        ttk.Label(params_frame, text="（例如：摄影风格、生成参数等）", foreground="gray").grid(
            row=2, column=1, sticky=tk.W, pady=(0, 5))
        
        # 添加优化提示词按钮
        ttk.Button(params_frame, text="使用AI优化提示词", command=self.optimize_prompt_with_ai).grid(
            row=3, column=0, sticky=tk.W, padx=(0, 5), pady=(0, 10))
        
        # 尺寸选择
        ttk.Label(params_frame, text="尺寸:").grid(row=4, column=0, sticky=tk.W, padx=(0, 5))
        size_combo = ttk.Combobox(params_frame, textvariable=self.size, 
                                 values=["1K", "2K", "4K"], state="readonly", width=10)
        size_combo.grid(row=4, column=1, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        
        # 水印选项
        ttk.Checkbutton(params_frame, text="添加水印", variable=self.watermark).grid(
            row=4, column=2, sticky=tk.W, padx=(0, 10), pady=(0, 5))
        
        # 流式输出选项
        ttk.Checkbutton(params_frame, text="流式输出", variable=self.stream).grid(
            row=4, column=3, sticky=tk.W, pady=(0, 5))
        
        # 连续生成选项
        ttk.Label(params_frame, text="连续生成:").grid(row=5, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        seq_combo = ttk.Combobox(params_frame, textvariable=self.sequential_gen,
                                values=["Disabled (禁用)", "Auto (自动)"], state="readonly", width=15)
        seq_combo.grid(row=5, column=1, sticky=tk.W, padx=(0, 10), pady=(5, 0))
        
        # 最大图像数
        ttk.Label(params_frame, text="最大图像数:").grid(row=5, column=2, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        ttk.Spinbox(params_frame, from_=1, to=10, textvariable=self.max_images, width=10).grid(
            row=5, column=3, sticky=tk.W, pady=(5, 0))
        
        # 图像选择区域（仅在图生图模式下显示）
        self.image_frame = ttk.LabelFrame(params_frame, text="参考图像", padding="5")
        self.image_frame.grid(row=6, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        self.image_frame.columnconfigure(1, weight=1)
        self.image_frame.grid_remove()  # 默认隐藏
        
        # 单图像选择区域
        single_image_frame = ttk.Frame(self.image_frame)
        single_image_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Button(single_image_frame, text="选择图像", command=self.select_image).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.image_path_label = ttk.Label(single_image_frame, text="未选择图像")
        self.image_path_label.grid(row=0, column=1, sticky=tk.W)
        # 添加清除按钮
        ttk.Button(single_image_frame, text="清除", command=self.clear_single_image).grid(
            row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # 多图像选择区域标题
        ttk.Label(self.image_frame, text="多图参考上传区域:", font=('Arial', 9, 'bold')).grid(
            row=1, column=0, sticky=tk.W, pady=(10, 5))
        
        # 多图像选择区域
        self.multi_image_frame = ttk.LabelFrame(self.image_frame, text="参考图像选择", padding="5")
        self.multi_image_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        self.multi_image_frame.columnconfigure(1, weight=1)
        # self.multi_image_frame.grid_remove()  # 默认隐藏
        
        # 上传通道说明
        ttk.Label(self.multi_image_frame, text="上传通道说明: 启用后将上传所有参考图像，否则仅使用第一张", 
                 font=('Arial', 8)).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 5))
        
        # 添加上传通道复选框
        self.upload_channel = tk.BooleanVar(value=False)
        ttk.Checkbutton(self.multi_image_frame, text="启用上传通道", variable=self.upload_channel).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 10))
        
        # 参考图像选择按钮
        self.ref_image_labels = []
        for i in range(3):
            ttk.Button(self.multi_image_frame, text=f"选择图像{i+1}", 
                      command=lambda idx=i: self.select_reference_image(idx)).grid(
                row=i+2, column=0, sticky=tk.W, padx=(0, 10), pady=(0, 5))
            label = ttk.Label(self.multi_image_frame, text="未选择图像")
            label.grid(row=i+2, column=1, sticky=tk.W, pady=(0, 5))
            self.ref_image_labels.append(label)
            # 添加清除按钮
            ttk.Button(self.multi_image_frame, text="清除", 
                      command=lambda idx=i: self.clear_reference_image(idx)).grid(
                row=i+2, column=2, sticky=tk.W, padx=(10, 0), pady=(0, 5))
        
        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(button_frame, text="生成图像", command=self.generate_image).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="保存图像", command=self.save_image).pack(side=tk.LEFT)
        
        # 状态区域
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding="10")
        status_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        # 减小状态区域的权重，让图像预览区域获得更多空间
        status_frame.rowconfigure(0, weight=0)
        
        # 创建一个框架来容纳状态文本和调整大小的控件
        status_content_frame = ttk.Frame(status_frame)
        status_content_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        status_content_frame.columnconfigure(0, weight=1)
        status_content_frame.rowconfigure(0, weight=1)
        
        self.status_text = scrolledtext.ScrolledText(status_content_frame, height=8, wrap=tk.WORD)
        self.status_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 添加调整大小的控件
        resize_frame = ttk.Frame(status_content_frame)
        resize_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(resize_frame, text="↑ 扩大", command=self.expand_status).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(resize_frame, text="↓ 缩小", command=self.shrink_status).pack(side=tk.LEFT)
        
        # 初始化状态文本高度
        self.status_text_height = 8
        
        # 图像预览区域
        preview_frame = ttk.LabelFrame(main_frame, text="图像预览", padding="15")
        preview_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        self.image_label = ttk.Label(preview_frame)
        self.image_label.grid(row=0, column=0)
        # 绑定双击事件
        self.image_label.bind("<Double-Button-1>", self.zoom_image)
        
        # 初始模式设置
        self.on_mode_change()
        
    def save_api_key(self):
        """保存API密钥到本地文件（简单加密）"""
        try:
            api_key = self.api_key.get()
            if api_key:
                # 简单的加密处理（异或加密）
                encrypted_key = self.simple_encrypt(api_key, "volcano_key")
                # 使用resource_path函数获取正确的文件路径
                api_key_path = resource_path("api_key.txt")
                with open(api_key_path, "w") as f:
                    f.write(encrypted_key)
                self.update_status("API密钥已加密保存")
            else:
                # 如果API密钥为空，删除保存的文件
                api_key_path = resource_path("api_key.txt")
                if os.path.exists(api_key_path):
                    os.remove(api_key_path)
                self.update_status("API密钥已清除")
        except Exception as e:
            self.update_status(f"保存API密钥失败: {str(e)}")
    
    def clear_saved_api_key(self):
        """清除已保存的API密钥"""
        try:
            # 删除保存的API密钥文件
            # 使用resource_path函数获取正确的文件路径
            api_key_path = resource_path("api_key.txt")
            if os.path.exists(api_key_path):
                os.remove(api_key_path)
                self.update_status("已清除保存的API密钥")
                # 清空输入框中的API密钥
                self.api_key.set("")
                messagebox.showinfo("成功", "已清除保存的API密钥")
            else:
                self.update_status("没有找到保存的API密钥")
                messagebox.showinfo("信息", "没有找到保存的API密钥")
        except Exception as e:
            self.update_status(f"清除API密钥失败: {str(e)}")
            messagebox.showerror("错误", f"清除API密钥失败: {str(e)}")
            
    def load_api_key(self):
        """从本地文件加载API密钥（解密）"""
        try:
            # 使用resource_path函数获取正确的文件路径
            api_key_path = resource_path("api_key.txt")
            if os.path.exists(api_key_path):
                # 使用UTF-8编码读取文件，避免Windows系统上的编码问题
                with open(api_key_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # 检查是否包含占位符或注释
                    if not content or "your_api_key_here" in content or content.startswith("#"):
                        # 文件为空、包含占位符或注释，这是正常情况，不需要报错
                        return
                    
                    # 解密处理
                    decrypted_key = self.simple_decrypt(content, "volcano_key")
                    self.api_key.set(decrypted_key)
        except FileNotFoundError:
            # 文件不存在是正常情况，不需要报错
            pass
        except Exception as e:
            # 只有在文件存在但读取失败时才更新状态
            if hasattr(self, 'status_text'):
                self.update_status(f"加载API密钥失败: {str(e)}")
            else:
                print(f"加载API密钥失败: {str(e)}")
    
    def save_deepseek_api_key(self):
        """保存DeepSeek API密钥到本地文件（简单加密）"""
        try:
            api_key = self.deepseek_api_key.get()
            if api_key:
                # 简单的加密处理（异或加密）
                encrypted_key = self.simple_encrypt(api_key, "deepseek_key")
                # 使用resource_path函数获取正确的文件路径
                deepseek_api_key_path = resource_path("deepseek_api_key.txt")
                with open(deepseek_api_key_path, "w") as f:
                    f.write(encrypted_key)
                self.update_status("DeepSeek API密钥已加密保存")
            else:
                # 如果API密钥为空，删除保存的文件
                deepseek_api_key_path = resource_path("deepseek_api_key.txt")
                if os.path.exists(deepseek_api_key_path):
                    os.remove(deepseek_api_key_path)
                self.update_status("DeepSeek API密钥已清除")
        except Exception as e:
            self.update_status(f"保存DeepSeek API密钥失败: {str(e)}")
    
    def clear_deepseek_api_key(self):
        """清除已保存的DeepSeek API密钥"""
        try:
            # 删除保存的API密钥文件
            # 使用resource_path函数获取正确的文件路径
            deepseek_api_key_path = resource_path("deepseek_api_key.txt")
            if os.path.exists(deepseek_api_key_path):
                os.remove(deepseek_api_key_path)
                self.update_status("已清除保存的DeepSeek API密钥")
                # 清空输入框中的API密钥
                self.deepseek_api_key.set("")
                messagebox.showinfo("成功", "已清除保存的DeepSeek API密钥")
            else:
                self.update_status("没有找到保存的DeepSeek API密钥")
                messagebox.showinfo("信息", "没有找到保存的DeepSeek API密钥")
        except Exception as e:
            self.update_status(f"清除DeepSeek API密钥失败: {str(e)}")
            messagebox.showerror("错误", f"清除DeepSeek API密钥失败: {str(e)}")
            
    def load_deepseek_api_key(self):
        """从本地文件加载DeepSeek API密钥（解密）"""
        try:
            # 使用resource_path函数获取正确的文件路径
            deepseek_api_key_path = resource_path("deepseek_api_key.txt")
            if os.path.exists(deepseek_api_key_path):
                # 使用UTF-8编码读取文件，避免Windows系统上的编码问题
                with open(deepseek_api_key_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    # 检查是否包含占位符或注释
                    if not content or "your_api_key_here" in content or content.startswith("#"):
                        # 文件为空、包含占位符或注释，这是正常情况，不需要报错
                        return
                    
                    # 解密处理
                    decrypted_key = self.simple_decrypt(content, "deepseek_key")
                    self.deepseek_api_key.set(decrypted_key)
        except FileNotFoundError:
            # 文件不存在是正常情况，不需要报错
            pass
        except Exception as e:
            # 只有在文件存在但读取失败时才更新状态
            if hasattr(self, 'status_text'):
                self.update_status(f"加载DeepSeek API密钥失败: {str(e)}")
            else:
                print(f"加载DeepSeek API密钥失败: {str(e)}")
    
    def simple_encrypt(self, text, key):
        """简单的异或加密"""
        # 将文本和密钥转换为字节
        text_bytes = text.encode('utf-8')
        key_bytes = key.encode('utf-8')
        
        # 执行异或加密
        encrypted_bytes = bytearray()
        for i in range(len(text_bytes)):
            encrypted_bytes.append(text_bytes[i] ^ key_bytes[i % len(key_bytes)])
        
        # 返回十六进制表示的字符串
        return encrypted_bytes.hex()
    
    def simple_decrypt(self, hex_text, key):
        """简单的异或解密"""
        try:
            # 将十六进制字符串转换为字节
            encrypted_bytes = bytes.fromhex(hex_text)
            key_bytes = key.encode('utf-8')
            
            # 执行异或解密
            decrypted_bytes = bytearray()
            for i in range(len(encrypted_bytes)):
                decrypted_bytes.append(encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)])
            
            # 返回解密后的字符串
            return decrypted_bytes.decode('utf-8')
        except:
            # 如果解密失败，返回原始文本
            return hex_text
    
    def on_mode_change(self):
        """当生成模式改变时调用"""
        mode = self.mode_var.get()
        
        # 根据模式显示/隐藏图像选择区域
        # 始终显示图像选择区域，不再根据模式隐藏
        # 控制单图像和多图像选择区域的显示
        self.image_frame.grid()  # 始终显示图像选择区域
        if mode.startswith("multi_img2img"):
            self.multi_image_frame.grid()
            self.image_path_label.master.grid_remove()  # 隐藏单图像选择
        else:
            self.multi_image_frame.grid()  # 始终显示多图像选择区域
            self.image_path_label.master.grid()  # 显示单图像选择
    
    def select_image(self):
        """选择单个图像文件"""
        file_path = filedialog.askopenfilename(
            title="选择图像文件",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if file_path:
            self.image_path.set(file_path)
            self.image_path_label.config(text=os.path.basename(file_path))
            # 显示图像预览
            self.preview_selected_image(file_path)
    
    def clear_single_image(self):
        """清除单图像选择"""
        # 清除图像路径
        self.image_path.set("")
        # 重置标签文本
        self.image_path_label.config(text="未选择图像")
        # 移除预览图像
        if hasattr(self, 'image_preview_label'):
            self.image_preview_label.config(image='')  # 清除图像
            if hasattr(self.image_preview_label, 'image'):
                del self.image_preview_label.image
        self.update_status("[信息] 已清除单张参考图像")
    
    def preview_selected_image(self, image_path):
        """预览选中的图像"""
        try:
            # 打开并调整图像大小用于预览
            image = Image.open(image_path)
            # 调整图像大小以适应预览区域
            max_width, max_height = 100, 100
            image.thumbnail((max_width, max_height), Image.LANCZOS)
            
            # 转换为Tkinter兼容的格式
            photo = ImageTk.PhotoImage(image)
            
            # 创建或更新预览标签
            if not hasattr(self, 'image_preview_label'):
                self.image_preview_label = ttk.Label(self.image_frame)
                self.image_preview_label.grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
            
            self.image_preview_label.config(image=photo)
            self.image_preview_label.image = photo  # 保持引用防止被垃圾回收
            self.update_status(f"[信息] 已选择图像: {os.path.basename(image_path)}")
        except Exception as e:
            self.update_status(f"[错误] 无法预览图像: {str(e)}")
    
    def select_reference_image(self, index):
        """选择参考图像文件"""
        file_path = filedialog.askopenfilename(
            title=f"选择参考图像 {index+1}",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")]
        )
        if file_path:
            # 扩展参考图像列表到所需大小
            while len(self.reference_images) <= index:
                self.reference_images.append("")
                
            self.reference_images[index] = file_path
            self.ref_image_labels[index].config(text=os.path.basename(file_path))
            # 显示图像预览
            self.preview_reference_image(file_path, index)
    
    def clear_reference_image(self, index):
        """清除指定索引的参考图像"""
        # 确保索引在有效范围内
        if 0 <= index < len(self.reference_images) and self.reference_images[index]:
            # 清除图像路径
            self.reference_images[index] = ""
            # 重置标签文本
            self.ref_image_labels[index].config(text="未选择图像")
            # 移除预览图像
            preview_attr_name = f'ref_image_preview_{index}'
            if hasattr(self, preview_attr_name):
                preview_label = getattr(self, preview_attr_name)
                preview_label.config(image='')  # 清除图像
                if hasattr(preview_label, 'image'):
                    del preview_label.image
            self.update_status(f"[信息] 已清除参考图像 {index+1}")
    
    def preview_reference_image(self, image_path, index):
        """预览选中的参考图像"""
        try:
            # 打开并调整图像大小用于预览
            image = Image.open(image_path)
            # 调整图像大小以适应预览区域
            max_width, max_height = 50, 50
            image.thumbnail((max_width, max_height), Image.LANCZOS)
            
            # 转换为Tkinter兼容的格式
            photo = ImageTk.PhotoImage(image)
            
            # 创建或更新预览标签
            preview_attr_name = f'ref_image_preview_{index}'
            if not hasattr(self, preview_attr_name):
                preview_label = ttk.Label(self.multi_image_frame)
                preview_label.grid(row=index+2, column=2, sticky=tk.W, padx=(10, 0))
                setattr(self, preview_attr_name, preview_label)
            
            preview_label = getattr(self, preview_attr_name)
            preview_label.config(image=photo)
            preview_label.image = photo  # 保持引用防止被垃圾回收
            self.update_status(f"[信息] 已选择参考图像 {index+1}: {os.path.basename(image_path)}")
        except Exception as e:
            self.update_status(f"[错误] 无法预览参考图像 {index+1}: {str(e)}")
    
    def encode_image_to_base64(self, image_path):
        """将图像编码为base64字符串"""
        try:
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode('utf-8')
                # 添加MIME类型前缀，以符合火山AI SDK的要求
                return f"data:image/jpeg;base64,{encoded}"
        except Exception as e:
            self.update_status(f"图像编码失败: {str(e)}")
            return None
    
    def update_status(self, message):
        """更新状态信息"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update_idletasks()
    
    def generate_image(self):
        """在新线程中生成图像"""
        thread = threading.Thread(target=self._generate_image_thread)
        thread.daemon = True
        thread.start()
    
    def _generate_image_thread(self):
        """实际的图像生成过程"""
        try:
            self.update_status("=" * 50)
            self.update_status("开始图像生成流程...")
            self.update_status("=" * 50)
            
            # 检查是否安装了火山AI SDK
            if not HAS_ARK_SDK:
                self.update_status("[错误] 未安装火山AI SDK，请安装 'volcengine-python-sdk[ark]'")
                return
            
            # 获取参数
            api_key = self.api_key.get()
            if not api_key:
                self.update_status("[错误] 请提供API密钥 | Error: API key is required")
                return
                
            prompt = self.prompt_text.get("1.0", tk.END).strip()
            if not prompt:
                self.update_status("[错误] 请提供提示词 | Error: Prompt is required")
                return
            
            self.update_status(f"[参数] 提示词: {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
            self.update_status(f"[参数] 模型: {self.model.get()}")
            self.update_status(f"[参数] 尺寸: {self.size.get()}")
            self.update_status(f"[参数] 水印: {'开启' if self.watermark.get() else '关闭'}")
            self.update_status(f"[参数] 流式输出: {'开启' if self.stream.get() else '关闭'}")
            
            # 初始化Ark客户端
            self.update_status("[处理] 正在初始化火山AI客户端...")
            client = Ark(
                base_url="https://ark.cn-beijing.volces.com/api/v3",
                api_key=api_key,
            )
            
            # 构建请求参数
            request_params = {
                "model": self.model.get(),
                "prompt": prompt,
                "size": self.size.get(),
                "watermark": self.watermark.get(),
                "response_format": "url"
            }
            
            # 流式输出参数
            if self.stream.get():
                request_params["stream"] = True
            
            # 连续生成参数
            sequential_value = self.sequential_gen.get()
            if sequential_value == "Auto (自动)":
                request_params["sequential_image_generation"] = "auto"
                request_params["sequential_image_generation_options"] = SequentialImageGenerationOptions(
                    max_images=self.max_images.get()
                )
                self.update_status(f"[参数] Sequential Generation: Enabled (开启), Max Images: {self.max_images.get()}")
            else:
                request_params["sequential_image_generation"] = "disabled"
                self.update_status("[参数] Sequential Generation: Disabled (禁用)")
            
            # 根据模式添加图像参数
            mode = self.mode_var.get()
            self.update_status(f"[模式] 当前生成模式: {mode}")
            
            if mode == "img2img_single":
                if not self.image_path.get():
                    self.update_status("[错误] 请选择参考图像 | Error: Please select a reference image")
                    return
                self.update_status("[处理] 正在编码参考图像...")
                encoded_image = self.encode_image_to_base64(self.image_path.get())
                if encoded_image:
                    request_params["image"] = encoded_image
                    self.update_status("[处理] 参考图像编码完成")
                else:
                    self.update_status("[错误] 参考图像编码失败 | Error: Failed to encode reference image")
                    return
            elif mode == "img2img_multi":
                if not self.image_path.get():
                    self.update_status("[错误] 请选择参考图像 | Error: Please select a reference image")
                    return
                self.update_status("[处理] 正在编码参考图像...")
                encoded_image = self.encode_image_to_base64(self.image_path.get())
                if encoded_image:
                    request_params["image"] = encoded_image
                    self.update_status("[处理] 参考图像编码完成")
                else:
                    self.update_status("[错误] 参考图像编码失败 | Error: Failed to encode reference image")
                    return
            elif mode == "multi_img2img_single" or mode == "multi_img2img_multi":
                if not self.reference_images or not any(self.reference_images):
                    self.update_status("[错误] 请选择至少一张参考图像 | Error: Please select at least one reference image")
                    return
                # 过滤掉空的图像路径
                valid_images = [img for img in self.reference_images if img]
                self.update_status(f"[处理] 正在编码 {len(valid_images)} 张参考图像...")
                encoded_images = []
                for i, img_path in enumerate(valid_images):
                    self.update_status(f"[处理] 正在编码图像 {i+1}/{len(valid_images)}...")
                    encoded_img = self.encode_image_to_base64(img_path)
                    if encoded_img:
                        encoded_images.append(encoded_img)
                    else:
                        self.update_status(f"[错误] 图像 {i+1} 编码失败 | Error: Failed to encode image {i+1}")
                        return
                
                # 根据模式设置sequential_image_generation参数
                if mode == "multi_img2img_single":
                    # 多图参考生成单张图模式
                    request_params["sequential_image_generation"] = "disabled"
                    # 传递所有参考图像
                    request_params["image"] = encoded_images
                    self.update_status("[处理] 多图参考生成单张图模式")
                elif mode == "multi_img2img_multi":
                    # 多图参考生成组图模式
                    request_params["sequential_image_generation"] = "auto"
                    request_params["sequential_image_generation_options"] = SequentialImageGenerationOptions(
                        max_images=self.max_images.get()
                    )
                    # 传递所有参考图像
                    request_params["image"] = encoded_images
                    self.update_status("[处理] 多图参考生成组图模式")
                
                self.update_status(f"[处理] 所有 {len(encoded_images)} 张图像编码完成")
            
            # 发送请求
            self.update_status("[网络] 正在发送请求到火山AI服务...")
            if self.stream.get():
                # 流式输出模式
                self.update_status("[流式] 启用流式输出模式...")
                stream = client.images.generate(**request_params)
                self.handle_stream_response(stream)
            else:
                # 普通模式
                imagesResponse = client.images.generate(**request_params)
                self.handle_regular_response(imagesResponse)
                    
        except Exception as e:
            self.update_status(f"[异常] 发生未预期的错误: {str(e)} | [Exception] Unexpected error occurred: {str(e)}")
            import traceback
            self.update_status("[异常详情] 详细错误信息:")
            self.update_status(traceback.format_exc())
    
    def handle_regular_response(self, imagesResponse):
        """处理普通响应"""
        try:
            self.update_status("[成功] 请求成功发送到火山AI服务!")
            
            # 处理响应结果
            if hasattr(imagesResponse, 'data') and imagesResponse.data:
                images = imagesResponse.data
                self.update_status(f"[结果] 成功生成 {len(images)} 张图像")
                
                # 下载并显示第一张图像
                if images:
                    first_image = images[0]
                    if hasattr(first_image, 'url') and first_image.url:
                        first_image_url = first_image.url
                        self.update_status("[下载] 正在下载第一张生成的图像...")
                        self.download_and_display_image(first_image_url)
                        
                        # 显示所有图像URL
                        self.update_status("[结果] 生成的图像URL列表:")
                        for i, img in enumerate(images):
                            if hasattr(img, 'url') and img.url:
                                self.update_status(f"  图像 {i+1}: {img.url}")
                            else:
                                self.update_status(f"  图像 {i+1}: {str(img)}")
                
                self.update_status("=" * 50)
                self.update_status("图像生成流程完成!")
                self.update_status("=" * 50)
            else:
                self.update_status("[错误] 响应中没有图像数据")
                self.update_status(str(imagesResponse))
        except Exception as e:
            self.update_status(f"[异常] 处理响应时发生错误: {str(e)}")
            import traceback
            self.update_status("[异常详情] 详细错误信息:")
            self.update_status(traceback.format_exc())
    
    def handle_stream_response(self, stream):
        """处理流式响应"""
        try:
            self.update_status("[流式] 开始处理流式响应...")
            image_urls = []
            
            for event in stream:
                if event is None:
                    continue
                    
                if event.type == "image_generation.partial_failed":
                    self.update_status(f"[流式] 图像生成部分失败: {event.error}")
                    if event.error is not None and hasattr(event.error, 'code') and event.error.code == "InternalServiceError":
                        break
                        
                elif event.type == "image_generation.partial_succeeded":
                    if event.error is None and event.url:
                        self.update_status(f"[流式] 接收到图像: Size: {event.size}, URL: {event.url}")
                        image_urls.append(event.url)
                        # 下载并显示第一张图像
                        if len(image_urls) == 1:
                            self.update_status("[下载] 正在下载第一张生成的图像...")
                            self.download_and_display_image(event.url)
                            
                elif event.type == "image_generation.completed":
                    if event.error is None:
                        self.update_status("[流式] 图像生成完成")
                        self.update_status(f"[流式] 最终使用情况: {event.usage}")
                        
                elif event.type == "image_generation.partial_image":
                    self.update_status(f"[流式] 部分图像数据: index={event.partial_image_index}, size={len(event.b64_json) if event.b64_json else 0}")
            
            # 显示所有图像URL
            if image_urls:
                self.update_status("[结果] 生成的图像URL列表:")
                for i, url in enumerate(image_urls):
                    self.update_status(f"  图像 {i+1}: {url}")
            
            self.update_status("=" * 50)
            self.update_status("图像生成流程完成!")
            self.update_status("=" * 50)
            
        except Exception as e:
            self.update_status(f"[异常] 处理流式响应时发生错误: {str(e)}")
            import traceback
            self.update_status("[异常详情] 详细错误信息:")
            self.update_status(traceback.format_exc())
    
    def download_and_display_image(self, image_url):
        """下载并显示图像"""
        try:
            self.update_status("正在下载图像...")
            response = requests.get(image_url)
            
            if response.status_code == 200:
                # 保存临时文件
                temp_filename = "temp_image.jpg"
                with open(temp_filename, "wb") as f:
                    f.write(response.content)
                
                # 显示图像
                self.display_image(temp_filename)
                self.current_image_path = temp_filename
                self.update_status("图像显示完成")
            else:
                self.update_status(f"下载图像失败: {response.status_code}")
                
        except Exception as e:
            self.update_status(f"下载或显示图像时出错: {str(e)}")
    
    def display_image(self, image_path):
        """在GUI中显示图像"""
        try:
            # 打开并调整图像大小
            image = Image.open(image_path)
            # 调整图像大小以适应显示区域
            max_width, max_height = 400, 300
            image.thumbnail((max_width, max_height), Image.LANCZOS)
            
            # 转换为Tkinter兼容的格式
            photo = ImageTk.PhotoImage(image)
            
            # 更新标签
            self.image_label.config(image=photo)
            self.image_label.image = photo  # 保持引用防止被垃圾回收
        except Exception as e:
            self.update_status(f"显示图像时出错: {str(e)}")
    
    def save_image(self):
        """保存当前显示的图像"""
        if not self.current_image_path:
            self.update_status("没有可保存的图像")
            return
            
        try:
            # 询问保存位置
            file_path = filedialog.asksaveasfilename(
                defaultextension=".jpg",
                filetypes=[("JPEG files", "*.jpg"), ("PNG files", "*.png"), ("All files", "*.*")]
            )
            
            if file_path:
                # 复制临时文件到新位置
                with open(self.current_image_path, "rb") as src:
                    with open(file_path, "wb") as dst:
                        dst.write(src.read())
                self.update_status(f"图像已保存到: {file_path}")
        except Exception as e:
            self.update_status(f"保存图像时出错: {str(e)}")
    
    def zoom_image(self, event=None):
        """双击放大图像"""
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            self.update_status("没有可放大的图像")
            return
            
        try:
            # 创建新的弹窗显示放大图像
            zoom_window = tk.Toplevel(self.root)
            zoom_window.title("图像放大预览")
            zoom_window.geometry("800x600")
            
            # 创建画布和滚动条
            canvas_frame = ttk.Frame(zoom_window)
            canvas_frame.pack(fill=tk.BOTH, expand=True)
            
            # 创建画布
            canvas = tk.Canvas(canvas_frame, bg="white")
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            h_scrollbar = ttk.Scrollbar(zoom_window, orient=tk.HORIZONTAL, command=canvas.xview)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
            
            canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            # 打开放大图像
            image = Image.open(self.current_image_path)
            
            # 转换为Tkinter兼容的格式
            photo = ImageTk.PhotoImage(image)
            
            # 在画布上显示图像
            canvas_image = canvas.create_image(0, 0, anchor=tk.NW, image=photo)
            
            # 设置滚动区域
            canvas.config(scrollregion=canvas.bbox(tk.ALL))
            
            # 保持引用防止被垃圾回收
            zoom_window.photo = photo
            
            # 添加缩放功能
            def zoom_wheel(event):
                # 获取当前缩放比例
                scale = 1.0
                if hasattr(zoom_window, 'scale'):
                    scale = zoom_window.scale
                    
                # 根据滚轮方向调整缩放比例
                if event.delta > 0:
                    scale *= 1.1  # 放大
                else:
                    scale *= 0.9  # 缩小
                    
                # 限制缩放范围
                scale = max(0.1, min(scale, 5.0))
                zoom_window.scale = scale
                
                # 重新加载图像并应用缩放
                image = Image.open(self.current_image_path)
                new_width = int(image.width * scale)
                new_height = int(image.height * scale)
                resized_image = image.resize((new_width, new_height), Image.LANCZOS)
                
                # 转换为Tkinter兼容的格式
                photo = ImageTk.PhotoImage(resized_image)
                
                # 更新画布上的图像
                canvas.itemconfig(canvas_image, image=photo)
                canvas.config(scrollregion=canvas.bbox(tk.ALL))
                
                # 保持引用防止被垃圾回收
                zoom_window.photo = photo
            
            # 绑定鼠标滚轮事件
            canvas.bind("<MouseWheel>", zoom_wheel)
            canvas.bind("<Button-4>", zoom_wheel)  # Linux支持
            canvas.bind("<Button-5>", zoom_wheel)  # Linux支持
            
            # 添加说明文本
            self.update_status("双击放大图像窗口已打开，使用鼠标滚轮可以缩放图像")
            
        except Exception as e:
            self.update_status(f"放大图像时出错: {str(e)}")
    
    def test_api_connectivity(self):
        """测试API连通性"""
        self.update_status("=" * 50)
        self.update_status("开始API连接测试...")
        self.update_status("=" * 50)
        
        # 检查是否安装了火山AI SDK
        if not HAS_ARK_SDK:
            self.update_status("[错误] 未安装火山AI SDK，请安装 'volcengine-python-sdk[ark]'")
            messagebox.showerror("错误", "未安装火山AI SDK，请安装 'volcengine-python-sdk[ark]'")
            return
        
        api_key = self.api_key.get()
        if not api_key:
            self.update_status("[错误] 请先输入API密钥 | Error: Please enter API key first")
            messagebox.showerror("错误", "请先输入API密钥")
            return
            
        self.update_status("[处理] 正在测试API连通性...")
        
        try:
            # 初始化Ark客户端
            self.update_status("[处理] 正在初始化火山AI客户端...")
            client = Ark(
                base_url="https://ark.cn-beijing.volces.com/api/v3",
                api_key=api_key,
            )
            
            self.update_status("[网络] 正在连接到火山AI服务...")
            # 使用一个简单的图像生成请求来测试API密钥
            # 我们发送一个带有简单参数的请求，如果API密钥有效，会返回具体的错误而不是认证错误
            try:
                # 创建一个简单的测试请求，使用支持的参数
                test_params = {
                    "model": "test-model",  # 使用一个不存在但格式正确的模型名
                    "prompt": "test",
                    "size": "512x512"
                }
                
                # 尝试发送请求
                response = client.images.generate(**test_params)
                # 如果能到达这里，说明API密钥有效
                self.update_status("[成功] API连接测试成功!")
                self.update_status("[信息] API密钥有效，可以正常连接到火山AI服务")
                messagebox.showinfo("成功", "API密钥有效，可以正常连接到火山AI服务")
            except Exception as e:
                # 检查异常类型来判断API密钥是否有效
                error_str = str(e).lower()
                if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
                    self.update_status("[错误] API连接测试失败: API密钥无效")
                    self.update_status("[解决方案] 请检查您的API密钥是否正确")
                    messagebox.showerror("错误", "API密钥无效，请检查您的API密钥")
                elif "403" in error_str or "forbidden" in error_str:
                    self.update_status("[错误] API连接测试失败: 访问被拒绝")
                    self.update_status("[解决方案] 请检查您的API密钥和权限设置")
                    messagebox.showerror("错误", "访问被拒绝，请检查您的API密钥和权限")
                elif "400" in error_str or "bad request" in error_str or "404" in error_str:
                    # 400/404错误表示API端点是可访问的，API密钥有效
                    self.update_status("[成功] API连接测试成功!")
                    self.update_status("[信息] API密钥有效，可以正常连接到火山AI服务")
                    messagebox.showinfo("成功", "API密钥有效，可以正常连接到火山AI服务")
                else:
                    self.update_status(f"[错误] API连接测试失败: {str(e)}")
                    self.update_status("[解决方案] 请检查网络连接和API密钥")
                    messagebox.showerror("错误", f"连接失败: {str(e)}")
                
        except Exception as e:
            self.update_status(f"[异常] API连接测试失败: {str(e)}")
            self.update_status("[解决方案] 请检查网络连接和API密钥")
            messagebox.showerror("错误", f"测试过程中发生错误: {str(e)}")
        
        self.update_status("=" * 50)
        self.update_status("API连接测试完成!")
        self.update_status("=" * 50)

    def test_deepseek_connectivity(self):
        """测试DeepSeek API连通性"""
        self.update_status("=" * 50)
        self.update_status("开始DeepSeek API连接测试...")
        self.update_status("=" * 50)
        
        # 导入openai库
        try:
            from openai_compat import OpenAI
        except ImportError:
            self.update_status("[错误] 未安装openai库，请运行 'pip install openai'")
            messagebox.showerror("错误", "未安装openai库，请运行 'pip install openai'")
            return
        
        api_key = self.deepseek_api_key.get()
        if not api_key:
            self.update_status("[错误] 请先输入DeepSeek API密钥 | Error: Please enter DeepSeek API key first")
            messagebox.showerror("错误", "请先输入DeepSeek API密钥")
            return
            
        self.update_status("[处理] 正在测试DeepSeek API连通性...")
        
        try:
            # 初始化OpenAI客户端（确保只使用官方支持的参数）
            self.update_status("[处理] 正在初始化DeepSeek客户端...")
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
            )
            
            self.update_status("[网络] 正在连接到DeepSeek服务...")
            # 使用一个简单的聊天完成请求来测试API密钥
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "user", "content": "Hello, this is a test message."}
                    ],
                    max_tokens=10,
                    temperature=0.1
                )
                
                # 如果能到达这里，说明API密钥有效
                self.update_status("[成功] DeepSeek API连接测试成功!")
                self.update_status("[信息] API密钥有效，可以正常连接到DeepSeek服务")
                messagebox.showinfo("成功", "DeepSeek API密钥有效，可以正常连接到DeepSeek服务")
                
            except Exception as e:
                # 检查异常类型来判断API密钥是否有效
                error_str = str(e).lower()
                if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
                    self.update_status("[错误] DeepSeek API连接测试失败: API密钥无效")
                    self.update_status("[解决方案] 请检查您的DeepSeek API密钥是否正确")
                    messagebox.showerror("错误", "DeepSeek API密钥无效，请检查您的API密钥")
                elif "403" in error_str or "forbidden" in error_str:
                    self.update_status("[错误] DeepSeek API连接测试失败: 访问被拒绝")
                    self.update_status("[解决方案] 请检查您的DeepSeek API密钥和权限设置")
                    messagebox.showerror("错误", "访问被拒绝，请检查您的API密钥和权限")
                else:
                    self.update_status(f"[错误] DeepSeek API连接测试失败: {str(e)}")
                    self.update_status("[解决方案] 请检查网络连接和API密钥")
                    messagebox.showerror("错误", f"连接失败: {str(e)}")
                
        except Exception as e:
            self.update_status(f"[异常] DeepSeek API连接测试失败: {str(e)}")
            self.update_status("[解决方案] 请检查网络连接和API密钥")
            messagebox.showerror("错误", f"测试过程中发生错误: {str(e)}")
        
        self.update_status("=" * 50)
        self.update_status("DeepSeek API连接测试完成!")
        self.update_status("=" * 50)
    
    def optimize_prompt_with_ai(self):
        """使用DeepSeek AI优化提示词"""
        self.update_status("=" * 50)
        self.update_status("开始使用AI优化提示词...")
        self.update_status("=" * 50)
        
        # 导入openai库
        try:
            from openai_compat import OpenAI
        except ImportError:
            self.update_status("[错误] 未安装openai库，请运行 'pip install openai'")
            messagebox.showerror("错误", "未安装openai库，请运行 'pip install openai'")
            return
        
        # 检查DeepSeek API密钥
        api_key = self.deepseek_api_key.get()
        if not api_key:
            self.update_status("[错误] 请先输入DeepSeek API密钥")
            messagebox.showerror("错误", "请先输入DeepSeek API密钥")
            return
        
        # 获取当前提示词
        current_prompt = self.prompt_text.get("1.0", tk.END).strip()
        if not current_prompt:
            self.update_status("[错误] 请先输入提示词")
            messagebox.showerror("错误", "请先输入提示词")
            return
            
        # 获取人格预设
        persona_preset = self.persona_preset.get("1.0", tk.END).strip()
        
        self.update_status("[处理] 正在使用DeepSeek AI优化提示词...")
        
        try:
            # 初始化OpenAI客户端（确保只使用官方支持的参数）
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com",
            )
            
            # 构造提示词优化的系统消息
            system_message = """你是一个专业的AI图像生成提示词优化助手。你的任务是帮助用户优化他们的图像生成提示词，使其更加详细、具体和富有表现力。
            
优化提示词时请遵循以下原则：
1. 保持用户原始意图不变
2. 增加细节描述，如具体的物体、颜色、材质、光照、风格等
3. 添加艺术风格描述，如"油画"、"水彩"、"科幻风格"、"写实风格"等
4. 添加质量增强词，如"高清"、"4K"、"细节丰富"、"高质量"等
5. 保持语言简洁明了
6. 不要添加与原意相悖的内容"""

            # 如果有人格预设，则添加到系统消息中
            if persona_preset:
                system_message += f"\n\n用户还提供了以下人格预设，请在优化时考虑这些要求：\n{persona_preset}"

            system_message += "\n\n请直接返回优化后的提示词，不要添加任何解释或其他内容。"
            
            # 构造用户消息
            user_message = f"请优化以下图像生成提示词：\n\n{current_prompt}"
            
            # 获取选择的模型
            selected_model = self.deepseek_model.get()
            
            # 发送请求到DeepSeek API
            response = client.chat.completions.create(
                model=selected_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            # 获取优化后的提示词
            optimized_prompt = response.choices[0].message.content.strip()
            
            # 将优化后的提示词更新到输入框
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", optimized_prompt)
            
            self.update_status("[成功] 提示词优化完成!")
            self.update_status(f"[信息] 使用模型: {selected_model}")
            self.update_status(f"[信息] 原始提示词长度: {len(current_prompt)} 字符")
            self.update_status(f"[信息] 优化后提示词长度: {len(optimized_prompt)} 字符")
            messagebox.showinfo("成功", "提示词已优化并更新到输入框中")
            
        except Exception as e:
            error_str = str(e).lower()
            if "401" in error_str or "unauthorized" in error_str or "invalid api key" in error_str:
                self.update_status("[错误] DeepSeek API调用失败: API密钥无效")
                self.update_status("[解决方案] 请检查您的DeepSeek API密钥是否正确")
                messagebox.showerror("错误", "DeepSeek API密钥无效，请检查您的API密钥")
            elif "403" in error_str or "forbidden" in error_str:
                self.update_status("[错误] DeepSeek API调用失败: 访问被拒绝")
                self.update_status("[解决方案] 请检查您的DeepSeek API密钥和权限设置")
                messagebox.showerror("错误", "访问被拒绝，请检查您的API密钥和权限")
            else:
                self.update_status(f"[错误] DeepSeek API调用失败: {str(e)}")
                self.update_status("[解决方案] 请检查网络连接和API密钥")
                messagebox.showerror("错误", f"API调用失败: {str(e)}")
        
        self.update_status("=" * 50)
        self.update_status("AI提示词优化完成!")
        self.update_status("=" * 50)

def main():
    root = tk.Tk()
    app = VolcanoImageGenerator(root)
    root.mainloop()

if __name__ == "__main__":
    main()