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

环境变量
--------
- DEEPSEEK_API_KEY   必填
- DEEPSEEK_BASE_URL  默认 https://api.deepseek.com
- DEEPSEEK_MODEL     默认 deepseek-flash（原生多模态）

检查类别
--------
照片有效性、挂装、叠装、模特、鞋包配件、价签、清洁与安全。

照片模糊、过暗、遮挡或局部未入镜时，相关项输出「无法判断」。
"""
