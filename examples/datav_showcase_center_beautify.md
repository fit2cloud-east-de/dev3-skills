# 示范案例：居中结构 + 美化底图（提示词配方）

本例从「公有云费用看板」类大屏抽象而来：用**画布底图 + 组件外框图（含动态 GIF）**做氛围，图表落在居中分区，并对单图 `colors` 做微调。  
构图/配色/外框统一的完整规则见 [references/datav_visual.md](../references/datav_visual.md)。  
**不要**把生产图片/GIF 放进本 skill 仓库；生成物只落在用户 AI 运行工作区，再经 URL / 静态资源引用进 plan。

## Agent 须遵守

1. **资产落点**（强制）  
   - 生成的 PNG/GIF/SVG 等 → 用户默认工作区（本仓库联调时用仓库外的 `分析区/工作区/generated/`，或会话当前项目的 `./generated/`）。  
   - **禁止**写入 `dev3-skills/`（含 `examples/`、`scripts/`、`references/`）。  
   - plan / JSON 里只保留 **可访问 URL** 或 DataEase 已上传的 `/static-resource/...` 路径，不提交二进制。

2. **美化手段优先序**（与产品一致）  
   1. 画布：`canvas.backgroundImageEnable` + `canvas.background`（整屏氛围）  
   2. 组件：`commonBackground.backgroundType = "outerImage"` + `outerImage`（卡片边框/光效/动态装饰）  
   3. 可选：独立 `Picture` / `DeVideo`（Logo、宣传片）——本示范主路径**不依赖**它们  
   4. 标题/KPI：`rich-text`（`render=custom`，`propValue.textValue` 含 `text-align:center`）

3. **布局骨架**：居中结构 `center_v2`（中栏更宽、主舞台更高；左右为窄翼，底栏为扁基座）  

```text
[================ 顶栏标题 =================]
[ 翼：环图 ] [######## 主舞台：宏大图种 ########] [ 翼：环图 ]
[ 翼：折线 ] [######## treemap/map/柱体 #######] [ 翼：占比 ]
[          ] [==== 底栏基座：构成/对比辅图 ====] [          ]
```

**宏大感原则（勿只放大像素）：**
- 主槽优先 `map` / `treemap` / `bar` 等面状或纪念碑式图种；  
- 忌把 `bar-stack-horizontal`、明细表、小指标卡放主舞台（细碎、无体量感）；  
- `apply` 默认会按图种冲击权重把更合适的图提升到 `main`（`compose: false` 可关闭）。

## 提示词模板（给用户需求 → Agent 展开）

复制后按业务替换括号内容：

```text
做一个暗色数据大屏，风格参考「居中结构 + 美化底图」示范：
- 主题：（如 公有云费用 / 销售运营）
- 画布 1920×1080，深色底；先在工作区用 Python 生成一张科技感底图 PNG，上传或给出可访问 URL，写入 canvas.background，并开启 backgroundImageEnable
- 顶栏一条居中富文本大标题；（可选）为标题组件配 outerImage 动态边框 GIF（同样先生成再引用 URL，勿入库）
- 左右为占比类（pie-donut / treemap），中栏放 KPI 富文本 + 横向堆叠条（bar-stack-horizontal）对比两组对象
- 中下与两侧放年度/趋势折线（line）
- 图表外框统一用 outerImage 边框图；同类图可共用同一边框资源
- 配色：避免默认/经典深纯色；优先产品色板 `elegant` / `future` / `simple` 等淡彩；柱/条开启 `basicStyle.gradient=true`；树图/环图用淡色 + 适当降低 `alpha`（约 75–88）
- tooltip 保持可读（勿白字白底）；图表 render 按类型正确（indicator/rich-text → custom）
- 数据集按 skill 纪律选型；保存前 preview；确认后 publish
- 所有生成图片只写在用户工作区 generated/，skill 目录不落二进制
```

## plan 片段示意（字段级，无二进制）

```json
{
  "name": "费用运营大屏",
  "title": "2023年公有云费用看板",
  "layout": "center_v2",
  "canvas": {
    "width": 1920,
    "height": 1080,
    "backgroundColor": "rgba(2,4,8,1)",
    "backgroundImageEnable": true,
    "background": "<用户工作区生成并上传后的 URL 或 /static-resource/...>"
  },
  "charts": [
    {
      "slot": "main",
      "type": "bar-stack-horizontal",
      "title": "预算使用-A",
      "xAxis": ["<维度>"],
      "yAxis": [{ "name": "<指标>", "summary": "sum" }],
      "extraView": {
        "customAttr": {
          "basicStyle": {
            "colors": ["#E7A62D", "#999999", "#FAC858", "#E2BD84", "#7A90E0", "#3BA272", "#2BE7FF", "#0A8ADA", "#FFD700"]
          }
        }
      },
      "commonBackground": {
        "backgroundType": "outerImage",
        "backgroundImageEnable": true,
        "backgroundColorSelect": false,
        "outerImage": "<边框图 URL>"
      }
    },
    {
      "slot": "secondary_left_top",
      "type": "pie-donut",
      "title": "云平台占比",
      "xAxis": ["<维度>"],
      "yAxis": [{ "name": "<指标>", "summary": "sum" }],
      "extraView": {
        "customAttr": {
          "basicStyle": {
            "colors": ["#39C4FF", "#999999", "#FAC858", "#E2BD84", "#7A90E0", "#3BA272", "#2BE7FF", "#0A8ADA", "#FFD700"]
          }
        }
      }
    }
  ],
  "decorations": [
    {
      "slot": "title",
      "kind": "rich-text",
      "role": "title",
      "text": "2023年公有云费用看板"
    }
  ]
}
```

说明：

- `apply` 已透传：`canvas.*`（含 `background` / `backgroundImageEnable`）、图表与标题的 `commonBackground`、`extraView`（或 `view`）配色合并。字段须与界面保存一致，**禁止臆造 JSON**。  
- 主色板与金色强调仅作示范；业务色可改，但保持「主色一组 + 强调一组」的微调方式。

## 工作区生成资产（示例命令，勿写入 skill）

在用户工作区执行（路径自定）：

```bash
mkdir -p generated/datav_beautify
# 用 Python（Pillow/matplotlib 等）生成 canvas_bg.png、frame.png、title_glow.gif
# 上传到 DataEase 静态资源或对象存储后，把 URL 填回 plan
```

## 相关

- 命令与通用流程：[datav.md](datav.md)  
- 字段说明：[../references/datav.md](../references/datav.md)  
- 原始拆解（含测试环境 id，仅分析区）：仓库 `分析区/工作区/公有云费用看板_案例分析.md`
