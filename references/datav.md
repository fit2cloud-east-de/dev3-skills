# 数据大屏（dataV）

通过 API 创建/更新 **数据大屏**（`type=dataV`）。仪表板见 [dashboard.md](dashboard.md)（独立资源树与矩阵布局，勿混用）。

## Agent 强制流程（数据集）

1. **先列数据集**：`datav.py datasets --flat`（或 `dataset.py tree`），对照用户需求选型。  
2. **优先用本次会话为该大屏新建的数据集**；没有合适的再评估是否新建。  
3. **禁止擅自删改已有数据集**。若确需改字段/计算逻辑：  
   - 说明风险：其它看板/大屏可能引用该集，修改会导致其数据变化；  
   - 自查是否冲突；有冲突则 **自己新建数据集**，不得改共用集；  
   - 须用户明确同意后才改已有集。  
4. **禁止擅自复用「非本次创建」的已有数据集**。用户明确确认「可以用某某数据集」后方可绑定。  
5. 图表保存前必须 **取数预览成功**（`preview-chart` / `apply` 内置预览）；失败则中止并修正轴/过滤/聚合。

## 工作流

1. `catalog` / `layouts` — 图表类型、装饰与**排版模板**  
2. `resolve-folder` — 在 **数据大屏树** 上定位文件夹（组织根 id 与数据源/数据集树通常不同）  
3. `datasets` + `fields --simplify` — 选型与字段  
4. 按需求拆解：选布局模板 → 选图类型、轴字段、聚合、过滤 → 填入各内容槽；需要时补 `config`（图表样式）、`canvas`（全局设置）  
5. `plan-example` → 写 plan → **`lint-plan` 自检** → `apply`（内置取数预览与二次自检）  
6. 联动/跳转：随 plan 的 `linkage` / `jump` 一起提交，或用 `linkage` / `jump` 子命令在图表保存后单独维护  
7. `get --resource-table snapshot`（默认）核对；`publish --i-confirm-publish` 发布  

不确定某项默认值就先查：`python datav.py defaults --key <配置项>`（离线，不需要连接）。

## 排版模板（优先使用）

默认画布 1920×1080。plan 中设 `layout`（或 `layoutTemplate`）后，未手写像素的图表按槽位自动排版；内容槽可放**任意图表 / 表格 / 指标卡**等。

| id | 名称 | 结构 |
|----|------|------|
| `grid_3x4` | 平均分布 3×4 | 顶栏大标题 + **3 行 × 4 列** 共 12 个等大内容格（`c0`…`c11`） |
| `center_v2` | 居中结构-形式二 | 顶栏 + **宽主舞台** `main`（约 68% 宽 × 72% 高）+ 左右窄翼 + 底栏扁基座；主槽宜宏大图种 |

- `title` / `name`：自动生成标题槽 **富文本**（与界面一致：`render=custom`、`propValue.textValue` 含居中 HTML、`verticalAlign=center-align`）；可用 `decorations` 里 `slot:"title"` 覆盖  
- 图表 `render` 必须与界面 `getViewConfig` 一致：`rich-text` / `indicator` / `picture-group` → `custom`，其余常见图 → `antv`（错误 render 会导致组件不挂载、不可见且无法双击编辑）
- 勿用滚动文字做大标题居中：产品把对齐存在 `style.textAlign`，但滚动文字渲染不按该字段水平居中  
- `charts[].slot`：指定落入哪一格；省略则按模板 `contentSlots` 顺序填充  
- 仍可手写 `layout:{left,top,width,height}` 覆盖单格  
- 图表 **提示（tooltip）** 默认白底黑字（`color:#000000`），勿改成白字  
- 查看像素：`python datav.py layouts --id grid_3x4`

## 视觉与构图（必读）

排版模板只解决槽位；**层级、淡彩/渐变、外框统一、主图图种**见 [datav_visual.md](datav_visual.md)。做美化大屏时与本节交叉遵守。

## 示范案例（居中美化）

「公有云费用看板」类大屏：整屏底图 + 组件 `commonBackground.outerImage`（含 GIF）做边框/动效，图种以环图/树图/折线/横向堆叠条 + 富文本 KPI 为主，并对 `customAttr.basicStyle.colors` 微调。  
**提示词与 plan 示意：** [examples/datav_showcase_center_beautify.md](../examples/datav_showcase_center_beautify.md)。  
**资产规则：** AI 用 Python 生成的美化图只落在**用户工作区**（如会话 `./generated/`），禁止放进正式 `dev3-skills/`；plan 只引用 URL 或 `/static-resource/...`。

## 画布与组件

| 概念 | 说明 |
|------|------|
| 画布 | 默认 1920×1080 暗色；`canvasStyleData` 为 JSON **字符串**；氛围图用 `background` + `backgroundImageEnable` |
| `componentData` | 组件数组的 JSON **字符串**；大屏位置用 `style.left/top/width/height`（像素） |
| `canvasViewInfo` | **对象**：仅 `UserView` / `VQuery` 需要；key = 组件 `id` |
| 组件美化 | `commonBackground.outerImage` + `backgroundType=outerImage`（边框/光效/动态图，比堆 Picture 更贴产品） |
| 装饰 | `ScrollText` / `Picture` / `DeVideo` / `RectShape` / `CanvasBoard` 等，**不**进 `canvasViewInfo` |
| 图片 `Picture` | 界面媒体栏；地址写入 `propValue.url`（plan 可写 `url`）；可选 `adaptation`: `adaptation`/`original`/`equiratio`；`propValue.flip` |
| 视频 `DeVideo` | 界面媒体栏；地址写入 **`videoLinks.web.src`**（plan 可写 `url`/`src`）；可选 `autoplay`/`loop`/`muted`；**不要**把视频地址写进 `propValue` |
| 配色微调 | plan 传 `extraView.customAttr.basicStyle`：`colors` / `colorScheme`（如 `elegant`/`future`）/ `gradient`（柱条渐变）/ `alpha`（淡化）；避免经典深纯色堆砌 |

## 全局默认配置（面板级）

整块大屏的公共设置存在 `canvasStyleData`（JSON **字符串**）。plan 里写 `canvas`，键名与之一一对应；**支持点号路径**写嵌套项。

```json
{
  "canvas": {
    "backgroundColor": "#020408",
    "width": 1920,
    "height": 1080,
    "screenAdaptor": "widthFirst",
    "refreshBrowserEnable": true,
    "refreshBrowserTime": 10,
    "dashboard.gapSize": 8,
    "component.chartTitle.show": false,
    "component.chartTitle.color": "#ffffff",
    "component.chartCommonStyle.backgroundImageEnable": true,
    "component.chartCommonStyle.backgroundType": "outerImage",
    "component.chartCommonStyle.outerImage": "https://example.com/frame.png"
  }
}
```

常用项（全量 100+ 项见 [panel_defaults.md](panel_defaults.md)，或 `defaults --group canvas`）：

| 配置项 | 大屏默认 | 说明 |
|--------|----------|------|
| `width` / `height` | 1920 / 1080 | 画布尺寸；组件坐标按此像素摆放 |
| `screenAdaptor` | `widthFirst` | 屏幕适配：`widthFirst` / `heightFirst` / `full` / `keepSize` |
| `dashboardAdaptor` | `keepHeightAndWidth` | 预览适配；另可 `withWidth` |
| `refreshBrowserEnable` + `refreshBrowserTime` + `refreshBrowserUnit` | false / 5 / minute | 整页定时刷新 |
| `refreshViewEnable` + `refreshTime` + `refreshUnit` | false / 5 / minute | 图表定时刷新 |
| `backgroundColor` | `#020408` | 画布底色 |
| `backgroundImageEnable` + `background` | false / "" | 画布底图 |
| `dashboard.gapSize` | 5 | 组件间隙（`dashboard.gap`=`yes` 时生效） |
| `dashboard.resultCount` | 1000 | 面板级结果集条数（`resultMode`=`all` 时） |
| `component.chartTitle.*` | show=true / 16px / `#ffffff` / 左对齐·顶部 | 统一组件标题风格 |
| `component.chartCommonStyle.*` | 内置边框 `board/board_1.svg` | 统一组件背景：底色、边框图、内边距、圆角、毛玻璃 |
| `component.seniorStyleSetting.linkageIconColor` | `#ffffff` | 联动角标颜色 |

**规则**

- 画布级「统一风格」只在 `openCommonStyle=true` 时生效；组件自身的 `commonBackground` 会覆盖它
- `backgroundType` / `opacity` 是历史字段（⛔ 界面无入口），不要依赖
- 改 `component.chartTitle.*` 会同时影响所有图表标题；只想改一张图，用 `charts[].config.text.*` 或 `extraView.customStyle.text`

## 图表配置（单张）

图表样式写在 `canvasViewInfo[组件id]`，分三个容器：

| 容器 | 管什么 | 典型项 |
|------|--------|--------|
| `customAttr` | 图形本身：配色、标签、提示框、指标卡、表格 | `basicStyle.colors`、`label.show`、`tooltip.trigger`、`tableHeader.*` |
| `customStyle` | 图表外框：标题、图例、坐标轴 | `text.*`、`legend.*`、`xAxis.color`、`yAxis.fontSize` |
| `senior` | 高级：空值、缩放、辅助线、阈值、滚动 | `functionCfg.emptyDataStrategy`、`sliderShow`、`threshold` |

plan 里用 `charts[].config` 写**友好键**，键名必须在清单内（写错会立刻报错并给出近似项，不会静默丢配置）：

```json
{
  "type": "bar",
  "title": "各省销量",
  "xAxis": ["省份"],
  "yAxis": [{ "name": "销售量", "summary": "sum" }],
  "config": {
    "label.show": true,
    "label.color": "#8ab4f8",
    "legend.show": false,
    "xAxis.color": "#8ab4f8",
    "tooltip.backgroundColor": "#0b1a33",
    "basicStyle.gradient": true,
    "senior.emptyDataStrategy": "breakLine"
  }
}
```

- 友好键前缀决定落点：`label.` / `tooltip.` / `indicator.` / `tableHeader.` → `customAttr`；`text.` / `legend.` / `xAxis.` / `yAxis.` → `customStyle`；`senior.` → `senior`
- 也可直接写全路径：`customAttr.basicStyle.colors`、`customStyle.legend.vPosition`
- 顶层可写：`title` / `resultCount` / `resultMode` / `refreshViewEnable` / `refreshTime` / `refreshUnit` / `customFilter` / `linkageActive` / `jumpActive`
- 需要原样透传产品字段时用 `charts[].extraView`（深合并 `customAttr` / `customStyle` / `senior` 一层）
- 项目含义与默认值：`python datav.py defaults --group chart`，单项 `--key label.show`

**易踩坑**

- 提示框默认**白底黑字**；把 `tooltip.color` 改成白字在大屏上会看不见
- `label.show` 默认关；饼图与矩形树图在建图时会被脚本打开（产品 setupDefaultOptions 行为）
- 大屏默认配色走图表自身 `customAttr.basicStyle.colors`；面板级 `component.chartColor` 只对仪表板生效

## 图表轴与聚合（不得出错）

| 图类型 | 轴规则 |
|--------|--------|
| bar / line / area 等 | `xAxis`=维度 `d`；`yAxis`=指标 `q` |
| pie / 环形 | `xAxis`=维度；`yAxis`=**仅 1 个**指标 |
| indicator | **仅** `yAxis`（1 个数值指标）；`xAxis` 空 |
| table-info | 列放 `xAxis`（d/q 均可）；无 yAxis |
| bar-stack 等 | 另配 `extStack` 堆叠维 |
| bar-group / line 分组 | 另配 `xAxisExt` |

- **聚合 `summary`**：写在 **指标字段** 上：`sum` / `avg` / `max` / `min` / `count` / `count_distinct` 等。  
- 文本/时间类指标默认倾向 `count`；数值默认 `sum`。用户指定优先。  
- **图表内过滤** `customFilter`：`{ "logic":"and", "items":[ { "type":"item", "fieldId", "term", "value", ... } ] }`。`term`：`eq/not_eq/lt/le/gt/ge/in/like/null/not_null/between` 等。无过滤用 `{}`。  
- **查询组件 VQuery**：条件在组件 `propValue`，运行时注入图表；结构复杂，须按产品配置核对 `checkedFields` / `checkedFieldsMap`，勿与 `customFilter` 混用错位。

## 图表联动

界面路径：选中图表 → 高级 → 联动设置 → 勾选目标图表 → 配关联字段 → 保存。

**运行时生效要同时满足三条**（少一条就"配了但点了没反应"）：

1. 源图表 `linkageActive=true`（图表 · 高级 · 联动 开关）
2. 联动关系自身 `linkage_active=true`（保存时 `active` 不为 false）
3. 关联字段有成对的 `sourceField` / `targetField`（数据集字段 id）

plan 写法（`apply` 会在图表落库后自动写入）：

```json
{
  "charts": [
    { "type": "bar", "title": "各省销量", "xAxis": ["省份"], "yAxis": [{"name": "销售量", "summary": "sum"}] },
    { "type": "pie", "title": "销量占比", "xAxis": ["省份"], "yAxis": [{"name": "销售量", "summary": "sum"}] }
  ],
  "linkage": [
    {
      "source": "各省销量",
      "targets": ["销量占比"],
      "fields": [{ "source": "省份", "target": "省份" }]
    }
  ]
}
```

- `source` / `targets` 写**图表标题或组件 id**；标题重名会报错并要求改用 id（`lint-plan` 会提前警告重名）
- `fields` 可省略：源图与目标图同数据集时字段 id 天然一致，跨数据集按**同名字段**配对；一条都配不上会报错而不是静默成功
- `active: false`：只保留关系不启用
- 点击行为由画布级 `actionSelection.linkageActive` 决定：`custom`（默认，弹浮框让用户选联动或下钻）/ `auto`（点击同时触发联动和下钻）

单独维护（图表须已保存）：

```bash
python datav.py linkage list   --id <DV_ID>
python datav.py linkage set    --id <DV_ID> --source "各省销量" --target "销量占比" --field 省份=省份
python datav.py linkage set    --id <DV_ID> --file linkage.json          # 复杂配置走文件
python datav.py linkage set    --id <DV_ID> --source "各省销量" --target "销量占比" --replace
python datav.py linkage active --id <DV_ID> --source "各省销量" [--off]
python datav.py linkage remove --id <DV_ID> --source "各省销量"
```

- `set` 默认**合并**：只覆盖本次提到的目标，其它目标保持原样；`--replace` 才清空该源图表全部联动
- 只删关系不会关图表总开关；反过来关总开关也不会删关系

## 图表跳转

界面路径：选中图表 → 高级 → 跳转设置 → 勾选触发字段 → 选跳转类型 → 填内容/选目标面板 → 保存。

**运行时生效要同时满足两条**：源图表 `jumpActive=true`，且该字段 `checked=true`（内部跳转还需目标面板 id）。

| 项 | 取值 | 说明 |
|----|------|------|
| `linkType` | `outer`（默认）/ `inner` | 外部链接 / 面板内跳转 |
| `jumpType` | `_self` / `_blank`（默认）/ `newPop` | 当前页面 / 新开页面 / 弹窗页面 |
| `windowSize` | `large` / `middle`（默认）/ `small` | 仅 `jumpType=newPop` 生效 |
| `content` | ≤4000 字符 | `linkType=outer` 必填 |
| `attachParams` | false（默认） | 把当前过滤条件作为外部参数带给目标（内部跳转） |
| `targetDvId` | 面板 id | `linkType=inner` 必填 |
| `targets[].type` | `view` / `filter` / `outParams` | 目标：图表 / 过滤组件 / 外部参数 |

**触发字段必须在图表已用字段里**（`xAxis` / `xAxisExt` / `extStack` / `yAxis` / `yAxisExt` / `drillFields`）。不在其中的字段，界面里根本不会出现，写了也会被脚本拒绝。先用 `jump fields --id <DV_ID> --source "图表名"` 确认。

**链接占位符**：界面里写 `[字段名]`，保存时会转成 `[字段id]`，点击时替换成该行实际值。直接写 `[省份]` 即可，脚本负责换算：

```json
{
  "jump": [
    {
      "source": "各省销量",
      "field": "省份",
      "linkType": "outer",
      "jumpType": "_blank",
      "content": "https://bi.example.com/detail?prov=[省份]&y=[年份]"
    },
    {
      "source": "各省销量",
      "field": "省份",
      "linkType": "inner",
      "jumpType": "newPop",
      "windowSize": "large",
      "targetDvId": "<目标大屏ID>",
      "targets": [{ "view": "明细表", "fields": [{ "source": "省份", "target": "省份" }] }]
    }
  ]
}
```

单独维护：

```bash
python datav.py jump list   --id <DV_ID>
python datav.py jump fields --id <DV_ID> --source "各省销量"
python datav.py jump set    --id <DV_ID> --source "各省销量" --field 省份 \
       --link-type outer --jump-type _blank --content "https://x/detail?prov=[省份]"
python datav.py jump set    --id <DV_ID> --file jump.json     # 内部跳转/多字段建议走文件
python datav.py jump active --id <DV_ID> --source "各省销量" [--off]
python datav.py jump remove --id <DV_ID> --source "各省销量"
```

- `set` 默认**合并**：只覆盖本次提到的字段，其它字段已有跳转保留；`--replace` 才整体重建
- 内部跳转的目标图表、过滤组件、外部参数名都能被自动识别；配不上会列出目标面板里的全部候选
- 发布后跳转随快照一起生效；只改跳转不重新发布会停留在编辑稿

## plan JSON 要点

```json
{
  "name": "销售运营大屏",
  "title": "大标题文案",
  "folderName": "目标文件夹",
  "layout": "grid_3x4",
  "datasetId": "可选默认数据集",
  "canvas": { "backgroundColor": "#020408" },
  "charts": [
    {
      "slot": "c0",
      "type": "bar",
      "title": "各省销量",
      "xAxis": ["省份"],
      "yAxis": [{ "name": "销售量", "summary": "sum" }]
    },
    {
      "slot": "main",
      "type": "map",
      "title": "主视觉（居中结构时用）"
    }
  ]
}
```

`layout: "center_v2"` 时内容槽为 `main`、`secondary_left_top` 等（见 `layouts`）。`apply` 默认整页替换；`--append` 追加。

### 图片 / 视频（decorations）

```json
{
  "decorations": [
    {
      "kind": "Picture",
      "url": "https://example.com/logo.png",
      "adaptation": "adaptation",
      "layout": { "left": 40, "top": 900, "width": 320, "height": 120 }
    },
    {
      "kind": "DeVideo",
      "url": "https://example.com/demo.mp4",
      "autoplay": true,
      "loop": true,
      "muted": true,
      "layout": { "left": 1400, "top": 800, "width": 480, "height": 270 }
    }
  ]
}
```

也可用中文别名 `kind: "图片"` / `"视频"`。完整 `propValue` / `videoLinks`（从界面导出）可原样传入。

## 保存前自检（推荐）

`apply` 内置离线自检，**有 error 直接阻止写入**，不会留下半成品大屏。也可单独跑：

```bash
python datav.py lint-plan --file plan.json
```

拦得住的问题：图种不在清单、缺 `datasetId`、指标卡/明细表轴放错、单指标图种给了多个指标、`config` 键名写错、联动缺 `targets`、跳转缺字段或 `content`、内部跳转缺 `targetDvId`。
只警告不阻断的：坐标越界、标题重名、堆叠图没给 `extStack`、把 `jump`/`linkage` 写在了 `charts[]` 里面（**这类不会生效**，必须写 plan 顶层并给 `source`）。

`config` 的简写键必须命中注册表，`label.shw` 这种笔误会被当成未知项拦下并给出近似项；确有必要写注册表之外的字段时，改用完整路径（`customAttr.` / `customStyle.` / `senior.` 开头）跳过校验。

确认要强行写入时加 `--allow-lint-errors`（不推荐）。

## 主要 API

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | /de2api/dataVisualization/tree | `{ busiFlag:"dataV" }` |
| POST | /de2api/dataVisualization/saveCanvas | 新建 |
| POST | /de2api/dataVisualization/updateCanvas | 更新画布（组件 + canvasViewInfo） |
| POST | /de2api/dataVisualization/findById | 详情（**编辑稿**用 `resourceTable:snapshot`；未发布时 `core` 可能为空） |
| POST | /de2api/dataVisualization/updatePublishStatus | 发布 `status=1` / 取消 `0`（需 `activeViewIds`） |
| POST | /de2api/chart/listByDQ/{datasetId}/{chartId} | 维度/指标字段 |
| POST | /de2api/chartData/getData | 图表取数预览 |
| POST | /de2api/linkage/getViewLinkageGatherArray | 联动候选（目标图表 + 其字段 + 已有配置） |
| POST | /de2api/linkage/saveLinkage | 保存联动 `{dvId, sourceViewId, linkageInfo[]}` |
| POST | /de2api/linkage/updateLinkageActive | 源图表联动总开关 |
| POST | /de2api/linkage/removeLinkage | 删除某图表的全部联动 |
| GET | /de2api/linkage/getVisualizationAllLinkageInfo/{dvId}/{resourceTable} | 面板联动全貌 |
| POST | /de2api/linkJump/updateJumpSet | 保存跳转（整表覆盖，需回传未改动字段） |
| POST | /de2api/linkJump/updateJumpSetActive | 源图表跳转总开关 |
| POST | /de2api/linkJump/removeJumpSet | 删除某图表全部跳转 |
| GET | /de2api/linkJump/queryWithViewId/{dvId}/{viewId} | 单图表跳转明细（含全部候选字段） |
| GET | /de2api/linkJump/queryVisualizationJumpInfo/{dvId}/{resourceTable} | 面板跳转全貌 |
| GET | /de2api/linkJump/viewTableDetailList/{dvId} | 目标面板可跳转项（图表/过滤组件/外部参数） |

联动与跳转都写**编辑稿（snapshot）**；发布后才同步到 `core`。文件夹定位须在 **dataV 树**；写入范围受 `DE_ALLOWED_WRITE_SCOPE` 约束（须含大屏侧允许节点）。
