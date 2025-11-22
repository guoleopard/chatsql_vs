@echo off
:: 创建虚拟环境
python -m venv venv

:: 激活虚拟环境
call venv\Scripts\activate

:: 安装依赖
pip install -r requirements.txt

echo 虚拟环境创建和依赖安装完成，请使用以下命令激活虚拟环境：
echo venv\Scripts\activate
pause
