# 服装门店陈列检查助手

可现场试用的陈列检查 Agent：上传门店照片，按**题目给定规则库**逐条核验，输出结构化报告。信息不充分时明确给出「无法判断」，不凭大模型常识推测整店。

---

## 1. Agent 访问入口

**在线试用（可直接打开）：** https://trio-told-boxes-boots.trycloudflare.com

打开后即可上传门店照片，或点击「模糊过暗样例」（秒出「无法判断」）。挂装/叠装样例在未配置云端视觉模型时约 1–3 分钟。

本地启动：

**http://127.0.0.1:8080**

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r display_inspector/requirements.txt

# 推荐：配置 OpenAI 兼容的视觉模型（智谱 GLM-4V / 通义千问 VL / GPT-4o）
export VISION_API_KEY="your-key"
export VISION_BASE_URL="https://open.bigmodel.cn/api/paas/v4"   # 按供应商修改
export VISION_MODEL="glm-4v-flash"                               # 按供应商修改

PYTHONPATH=. python -m display_inspector
```

无云端 Key 时，可安装本地视觉依赖（首次会下载约 2.2B 模型，CPU 上单张约 1–3 分钟）：

```bash
pip install -r display_inspector/requirements-local.txt
PYTHONPATH=. python -m display_inspector
```

页面内「视觉接口」栏也可临时填写 API Key / Base URL / 模型名，无需改环境变量。

---

## 2. 使用说明

| 输入 | 说明 |
|------|------|
| 门店照片 | 必填，jpg/png/webp，可多张 |
| 拍摄区域 | 可选：全景 / 挂装 / 叠装 / 模特 / 鞋包配件 / 价签 |
| 补充文字 | 可选，如「主通道右侧挂装区，补货未结束」 |
| 视觉接口 | 可选，OpenAI 兼容的多模态模型 |

操作：打开页面 → 上传照片或点击内置样例 → 开始检查 → 查看结构化报告。

---

## 3. 规则使用说明

判断**只引用** `display_inspector/rules.yaml`，该文件由题目表格固化，每条有稳定 `rule_id`（H01、F04、S02…）。

处理流程：

1. **照片有效性闸门（OpenCV，非模型常识）**  
   模糊、过暗、过曝、分辨率过低 → 全部检查项输出「无法判断」，不推测整店。
2. **视觉观察**  
   云端模型按观察字段填 true/false/null；本地模型用短问答。模型**不打规则分、不定严重程度**。
3. **规则引擎（Python）**  
   把观察结果映射到题目规则：true→合规，false→不合规，null→无法判断，对象未入镜→不适用。  
   严重程度用规则库写死的高/中/低，商品触地、疏散占用等不得被模型改成低。
4. **特殊规则**  
   价签文字看不清 → 只输出「内容无法判断」（T03），不编造价格。

不允许模型另立「看起来不整齐」之类标准。页面底部会展示完整规则库。

---

## 4. 输出格式说明

| 题目要求 | 字段 |
|----------|------|
| 是否合规 | `overall_status`：合规 / 不合规 / 无法判断；`overall_compliant`：true / false / null |
| 具体问题 | `issues[].problem` |
| 对应检查标准 | `rule_id` + `rule_text` |
| 问题所在区域 | `area` |
| 严重程度 | `severity`：高 / 中 / 低 |
| 整改建议 | `suggestion` |
| 无法确定 | `undetermined_items[]`，`undetermined_reason` 明确写「无法判断」原因 |

页面同时提供表格与可复制/下载的 JSON。

---

## 5. 自测样例（已实际跑通）

样例图在 `display_inspector/samples/`，完整 JSON 在同目录 `selftest_*.json`。页面上也可一键复现。

### 样例 A：模糊过暗 → 整单无法判断

输入：`sample_blurry_dark.png`（由清晰挂装图压暗并高斯模糊）

输出摘要：

```json
{
  "overall_status": "无法判断",
  "overall_compliant": null,
  "photo_validity": {
    "usable": false,
    "issues": ["照片模糊", "照片过暗"]
  },
  "summary": "照片有效性不足：照片模糊、照片过暗。相关检查项输出「无法判断」，不推测整店情况。",
  "model_used": "photo-quality-gate"
}
```

全部 25 条规则均为「无法判断」，原因：照片模糊；照片过暗。**没有**给出整店合规结论。

### 样例 B：挂装混用衣架 → 不合规

输入：`sample_hanging_messy.png`（挂装杆、空衣架、黑塑与金属衣架混用、颜色穿插）

输出摘要（本地 VQA 实地跑通）：

```json
{
  "overall_status": "不合规",
  "overall_compliant": false,
  "issues": [
    {
      "rule_id": "H01",
      "rule_text": "同一组衣架方向、材质、颜色须一致",
      "problem": "同一组衣架方向、材质或颜色不一致",
      "area": "挂装区域",
      "severity": "低",
      "suggestion": "统一同组衣架的挂钩朝向、材质与颜色，撤换混用衣架"
    }
  ],
  "summary": "按题目规则核验为不合规：高 0 项、中 0 项、低 1 项；另有 17 项无法判断。"
}
```

间距、色序、空架面积等未形成足够证据的项保持「无法判断」，叠装/模特等未入镜项不按合规放行。价签字迹输出「内容无法判断」。

配置云端视觉模型后，同一张图可覆盖更多规则条目，但字段结构不变。

### 样例 C：叠装探出 + 通道杂物 → 不合规（含高风险）

输入：`sample_folded_safety.png`

输出摘要（本地 VQA 实地跑通）：

- 是否合规：不合规
- F04 商品不得触地（高）
- F05 商品不得探出层板（中）
- S01 无垃圾、污渍、纸箱、补货袋等杂物（中）
- S02 通道、疏散区域、消防设施不得占用（高）
- 摘要：高 2 项、中 2 项；其余可见信息不足的条目保持无法判断

完整 JSON：`display_inspector/samples/selftest_folded.json`

---

## 项目结构

```
display_inspector/
  rules.yaml          # 题目规则库（唯一判定依据）
  photo_quality.py    # 模糊/过暗等有效性闸门
  engine.py           # 观察结果 → 规则判定
  vision.py           # 云端 JSON 观察 / 本地短问答
  inspector.py        # 编排
  app.py              # FastAPI
  static/             # 上传与报告页
  samples/            # 自测图片与 JSON
```

```bash
PYTHONPATH=. pytest display_inspector/tests -q
```
