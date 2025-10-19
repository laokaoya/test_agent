#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
儿童AI对话测试平台启动脚本
"""

import os
import sys
import io
import webbrowser
import time
import threading

# 设置UTF-8编码（Windows系统）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    # 设置环境变量
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 添加父目录到路径，以便导入app模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open('http://localhost:5000')

def main():
    print("🚀 启动儿童AI对话测试平台...")
    print("📱 访问地址: http://localhost:5000")
    print("🔧 配置说明:")
    print("   - 左侧面板: 配置测试角色和评分标准")
    print("   - 右侧面板: 查看测试结果")
    print("   - 点击'测试Dify连接'验证API连接")
    print("   - 点击'开始测试'运行完整测试")
    print("\n按 Ctrl+C 停止服务器")
    print("-" * 50)
    
    # 在新线程中打开浏览器
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")

if __name__ == '__main__':
    main()
