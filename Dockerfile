# 使用官方 Python 运行时作为父镜像
FROM python:3.8

# 设置工作目录
WORKDIR /usr/src/app

# 复制当前目录内容到容器中的工作目录
COPY . .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 使端口 8080 可供此容器外的环境使用
EXPOSE 8080

# 定义环境变量
ENV NAME World

# 在容器启动时运行 app.py
CMD ["python", "./sample.py"]