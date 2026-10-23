# 数学表达式网页绘图器

支持一维曲线、二维曲面、三维点云，以及极坐标曲线。

## 极坐标示例

在网页的绘图类型中选择“极坐标曲线”，输入：

```text
表达式：1+cos(theta)
定义域：theta=0,2*pi
```

表达式表示 `r=f(theta)`，角度按弧度输入；定义域支持 `pi` 和 `e` 常量。

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
