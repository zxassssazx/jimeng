# 火山AI图像生成器

这是一个基于火山AI SDK的图像生成工具，支持多种生成模式：
- 文本生成单张图
- 文本生成组图
- 图生图-单张
- 图生图-组图
- 多图参考生成单张
- 多图参考生成组图

## 更新说明

本版本已适配火山AI SDK 4.0版本，主要更新内容：
1. 更新了SDK导入方式，使用`volcenginesdkarkruntime`模块
2. 更新了`SequentialImageGenerationOptions`的导入路径
3. 更新了requirements.txt中的依赖版本
4. 添加了SDK升级检查功能

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 方法一：使用图形界面（推荐）

1. 运行程序：
   ```bash
   python main.py
   ```

2. 在界面中输入火山AI API密钥
3. 选择生成模式和参数
4. 点击"生成图像"按钮

### 方法二：使用API密钥文件

1. 获取火山AI API密钥：
   - 登录火山引擎控制台 (https://console.volcengine.com/)
   - 进入AI服务相关页面（如文生图、图生图等服务）
   - 在API密钥管理页面创建或获取API密钥
   - 复制API密钥

2. 将API密钥填入`api_key.txt`文件中：
   ```
   your_actual_api_key_here
   ```
   将`your_actual_api_key_here`替换为您从火山引擎控制台获取的实际API密钥

## 升级功能说明

本工具包含自动SDK版本检查功能，可以帮助您及时了解火山AI SDK的更新情况。

### 功能特点

- 自动检查更新：程序启动后会自动检查火山AI SDK的最新版本（每天检查一次）
- 手动检查：您可以通过菜单栏的"帮助" -> "检查更新"随时手动检查
- 版本比较：显示当前安装的版本和PyPI上的最新版本
- 一键更新：支持通过弹出的对话框直接启动SDK更新

### 使用方式

1. 自动更新检查：程序会在启动后自动检查，如果有新版本会弹出提示
2. 手动检查更新：
   - 点击菜单栏中的"帮助" -> "检查更新"
   - 系统会显示当前版本和最新版本的对比信息
   - 如需更新，请点击"立即更新"按钮

### 注意事项

- 更新SDK需要网络连接
- 更新完成后请重启应用程序以使用新版本的SDK
- 如果您希望保持当前版本，可以选择"稍后提醒"

3. 运行程序：
   ```bash
   python main.py
   ```

### 方法三：使用环境变量

设置环境变量：
```bash
export VOLCENGINE_API_KEY=your_actual_api_key_here
python main.py
```

## 测试脚本

项目包含两个测试脚本：
- `test_sdk.py` - 测试SDK导入和基本功能
- `test_image_generation.py` - 测试图像生成功能（需要设置API密钥环境变量）

## 注意事项

1. 请确保已安装支持ark扩展的SDK版本：
   ```bash
   pip install 'volcengine-python-sdk[ark]'
   ```

2. API密钥需要在火山AI平台获取

3. 生成的图像将保存为临时文件，可以使用界面中的"保存图像"按钮保存到指定位置

*****
https://xwean.com/2049.html 这里有百度网盘的下载链接

也不知道为什么封装会这么大...

有python 用开发版本 挺不错的~

版本 1

通过网盘分享的文件：即梦 4.0 封装

链接: https://pan.baidu.com/s/1RTU8udP4eCN1WIRSQzhjMQ?pwd=f8f9 提取码: f8f9

版本 2

通过网盘分享的文件：即梦 4.0 散装

链接: https://pan.baidu.com/s/19QqlFa3f_ygXdjJXjjWgYA?pwd=cwmk 提取码: cwmk
