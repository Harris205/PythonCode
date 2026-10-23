# 数学表达式网页绘图器

支持一维曲线、二维曲面和三维点云。

## 本地运行

```powershell
python app.py
```

访问 `http://127.0.0.1:5000`。

## Render 部署

在 Render 中将此仓库作为 Python Web Service 部署，并使用仓库中的 `render.yaml`。

生产启动命令：

```text
gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

健康检查地址：`/health`。
