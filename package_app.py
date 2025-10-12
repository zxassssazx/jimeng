import os
import sys
import subprocess
import shutil
from pathlib import Path

# 确保中文显示正常
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# 项目根目录
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# 目标目录
TARGET_DIR = os.path.join(ROOT_DIR, 'new')

# 确保new目录存在
os.makedirs(TARGET_DIR, exist_ok=True)

print("=== 正在准备封装火山AI图像生成器 ===")
print(f"项目根目录: {ROOT_DIR}")
print(f"目标目录: {TARGET_DIR}")

# 检查是否已安装PyInstaller
try:
    import PyInstaller
    print(f"已安装PyInstaller版本: {PyInstaller.__version__}")
except ImportError:
    print("未安装PyInstaller，正在安装...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)
    print("PyInstaller安装成功")

# 安装项目依赖
print("正在安装项目依赖...")
subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', os.path.join(ROOT_DIR, 'requirements.txt')], check=True)

# 创建临时工作目录
TEMP_DIR = os.path.join(TARGET_DIR, 'temp')
os.makedirs(TEMP_DIR, exist_ok=True)

# 创建配置目录结构
CONFIG_DIR = os.path.join(TARGET_DIR, 'config')
os.makedirs(CONFIG_DIR, exist_ok=True)

# 复制配置文件
def copy_config_files():
    # 复制update_check_config.json
    config_source = os.path.join(ROOT_DIR, 'update_check_config.json')
    if os.path.exists(config_source):
        shutil.copy2(config_source, CONFIG_DIR)
        print(f"已复制配置文件: {config_source} -> {CONFIG_DIR}")
    
    # 创建版本信息文件
    version_file = os.path.join(CONFIG_DIR, 'version_info.json')
    version_content = '''{
    "current_version": "1.3",
    "last_update": "2024-01-01"
}
'''
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(version_content)
    print(f"已创建版本信息文件: {version_file}")

# 复制README文件
def copy_readme():
    readme_source = os.path.join(ROOT_DIR, 'README.md')
    if os.path.exists(readme_source):
        shutil.copy2(readme_source, TARGET_DIR)
        print(f"已复制README文件: {readme_source} -> {TARGET_DIR}")

# 使用PyInstaller封装应用
def package_with_pyinstaller():
    print("正在使用PyInstaller封装应用...")
    
    # 准备命令行参数列表
    cmd_args = [
        sys.executable, '-m', 'PyInstaller',
        '--onefile',  # 创建单文件
        '--windowed',  # 窗口模式，不显示控制台
        '--name', 'VolcanoAIImageGenerator',
        '--hidden-import', 'volcenginesdkarkruntime',
        '--hidden-import', 'PIL',
        '--hidden-import', 'tkinter',
        '--distpath', TARGET_DIR,
        '--workpath', TEMP_DIR,
        '--specpath', TEMP_DIR,
    ]
    
    # 添加数据文件
    # update_check_config.json
    config_json_path = os.path.join(ROOT_DIR, 'update_check_config.json')
    if os.path.exists(config_json_path):
        cmd_args.extend(['--add-data', f'{config_json_path};.'])
    
    # update_checker.py
    update_checker_path = os.path.join(ROOT_DIR, 'update_checker.py')
    if os.path.exists(update_checker_path):
        cmd_args.extend(['--add-data', f'{update_checker_path};.'])
    
    # api_key.txt (如果存在)
    api_key_path = os.path.join(ROOT_DIR, 'api_key.txt')
    if os.path.exists(api_key_path):
        cmd_args.extend(['--add-data', f'{api_key_path};.'])
    
    # 添加主脚本文件
    cmd_args.append(os.path.join(ROOT_DIR, 'main.py'))
    
    # 执行PyInstaller命令
    try:
        subprocess.run(cmd_args, check=True)
        
        print("封装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"封装失败: {e}")
        return False

# 创建启动脚本
def create_run_script():
    run_bat_path = os.path.join(TARGET_DIR, 'run_app.bat')
    run_content = '''@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo 正在启动火山AI图像生成器...
echo 版本: 1.3

REM 检查是否存在配置文件夹
if not exist config (mkdir config)

REM 检查是否存在版本信息文件
if not exist config\version_info.json (
    echo 创建版本信息文件...
    echo { > config\version_info.json
    echo     "current_version": "1.3", >> config\version_info.json
    echo     "last_update": "2024-01-01" >> config\version_info.json
    echo } >> config\version_info.json
)

REM 运行主程序
VolcanoAIImageGenerator.exe

if %errorlevel% neq 0 (
    echo 程序运行出错，请检查日志文件。
    pause
)
'''
    
    with open(run_bat_path, 'w', encoding='utf-8') as f:
        f.write(run_content)
    
    print(f"已创建启动脚本: {run_bat_path}")

# 创建说明文件
def create_readme():
    readme_path = os.path.join(TARGET_DIR, 'README.txt')
    readme_content = '''火山AI图像生成器使用说明

版本: 1.3

功能简介:
- 支持DeepSeek API图像生成
- 支持火山AI SDK图像生成
- 自动更新检查功能

使用方法:
1. 双击运行run_app.bat启动程序
2. 在界面中输入API密钥和提示词
3. 点击生成按钮创建图像

配置说明:
- 程序会自动创建config文件夹存储配置
- version_info.json包含版本信息
- update_check_config.json包含更新检查配置

注意事项:
- 确保已安装所有必要的依赖
- 如果遇到问题，请检查程序日志或重新安装
'''
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"已创建说明文件: {readme_path}")

# 清理临时文件
def clean_up():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        print(f"已清理临时文件: {TEMP_DIR}")

# 主函数
def main():
    try:
        # 复制配置文件
        copy_config_files()
        copy_readme()
        
        # 封装应用
        if package_with_pyinstaller():
            # 创建启动脚本和说明文件
            create_run_script()
            create_readme()
            
            print("\n=== 封装完成！===")
            print(f"应用程序已成功封装到: {TARGET_DIR}")
            print("请运行run_app.bat启动程序")
        else:
            print("封装失败，请检查错误信息")
    finally:
        # 清理临时文件
        clean_up()

if __name__ == '__main__':
    main()