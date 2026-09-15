"""
门店陈列合规检查 Agent
====================

服装连锁总部可用本系统上传门店照片，由视觉 Agent 对照统一陈列标准自动巡检。

输出字段
--------
1. 是否合规（合规 / 不合规 / 无法判断）
2. 具体问题
3. 对应检查标准
4. 问题所在区域
5. 严重程度（高 / 中 / 低 / 无法判断）
6. 整改建议
7. 证据不足时明确写「无法判断」，不推测整店情况

启动
----
1. 安装依赖（仅检查 Agent，无需 Elasticsearch / GPU）：

       pip install -r requirements-inspect.txt

2. 配置 DeepSeek 密钥（不要把密钥写进代码或提交到 Git）：

       cp .env.example .env
       # 编辑 .env，填入 DEEPSEEK_API_KEY

3. 启动后端：

       python -m display_inspect

4. 启动前端（另开终端）：

       cd frontend && npm install && npm run dev

浏览器打开 http://localhost:5173

给别人用的公网链接
----------------
`localhost` 只有你自己电脑能打开。要让别人用浏览器访问，需要一个公网地址。推荐两种做法。

### 1. 长期链接：部署到 Render（免费档即可）

1. 把代码推到 GitHub（当前分支即可）。
2. 打开 https://dashboard.render.com ，用 GitHub 登录，New → Web Service，选这个仓库。
3. 运行时选 Docker（本仓库已有 `Dockerfile` 和 `render.yaml`）。
4. 环境变量填：
   - `DEEPSEEK_API_KEY` = 你的密钥（不要写进代码）
   - `DEEPSEEK_MODEL` = `deepseek-flash`
5. 部署完成后，Render 会给出类似 `https://xxx.onrender.com` 的链接，发给别人即可。

同一套镜像也可以放到 Railway、Fly.io。它们都会读取 `PORT` 环境变量。

生产模式是「先构建前端，再由后端同一个端口提供页面和 API」：

    cd frontend && npm install && npm run build
    python -m display_inspect
    # 然后打开 http://localhost:8000

### 2. 临时演示：Cloudflare Tunnel / ngrok

本机或服务器先按上面的生产模式启动 8000 端口，再开一条隧道：

    cloudflared tunnel --url http://localhost:8000

终端里会出现 `https://xxxx.trycloudflare.com`。这个链接别人马上能打开，但关掉电脑或隧道后就会失效。

环境变量
--------
- DEEPSEEK_API_KEY   必填
- DEEPSEEK_BASE_URL  默认 https://api.deepseek.com
- DEEPSEEK_MODEL     默认 deepseek-flash（原生多模态）
- PORT               服务端口，默认 8000（Render / Railway 会自动注入）

检查类别
--------
照片有效性、挂装、叠装、模特、鞋包配件、价签、清洁与安全。

照片模糊、过暗、遮挡或局部未入镜时，相关项输出「无法判断」。
"""
