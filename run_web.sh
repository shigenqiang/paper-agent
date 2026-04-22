#!/bin/bash

# 论文Agent Web界面启动脚本

echo "====================================="
echo "    论文Agent Web界面启动中..."
echo "====================================="

# 检查Python环境
if ! command -v python &> /dev/null; then
    echo "错误: 未找到Python，请先安装Python"
    exit 1
fi

# 安装依赖
echo "正在检查依赖..."
pip install -q -r requirements.txt

# 启动Streamlit应用
echo "启动Web界面..."
streamlit run app.py
