# 数据大屏视觉与构图规范

Agent 制作 dataV 时，在 API/字段正确之外，须同时满足本节的**构图、色彩、组件一致性**。字段仍以 [datav.md](datav.md) 与界面保存结构为准；本节约束「怎么排、怎么配色、怎么选图种」。

## 1. 视觉层级（先定重心）

| 层级 | 作用 | 做法 |
|------|------|------|
| 主舞台 | 一眼结论 | `center_v2` 的 `main`：宽中栏 + 高主区；图种要有体量感 |
| 翼/辅 | 解释主结论 | 左右窄槽：占比、趋势、构成细节 |
| 基座 | 托住对比 | 底栏扁槽：对比柱/明细构成，勿抢主视觉 |
| 标题 | 主题指名 | 顶栏富文本居中；可配统一色系外框/动效 |

**宏大 ≠ 单纯放大像素。** 主槽优先面状或纪念碑式图种（见下）；密条、明细表、小指标卡不宜占 `main`。  
`layout: center_v2` 时默认按图种冲击权重提升主视觉（`compose: false` 可关闭）。实现见 `scripts/datav_layouts.py` 的 `HERO_VISUAL_WEIGHT`。

### 主槽图种建议

| 意图 | 优先 | 次选 | 避免放主槽 |
|------|------|------|------------|
| 空间/份额体量 | `treemap`、`map` | 大 `pie-donut`（分类 ≤6） | `table-*`、`indicator` 独占 |
| 类别对比 | `bar` / `bar-group` | `bar-stack` | `bar-stack-horizontal`（细碎） |
| 趋势 | 侧翼 `line` / `area` | — | 主槽堆满多系列折线 |
| 构成细节 | 侧翼或底栏堆叠条 | — | 主舞台密横条 |

均分多图用 `grid_3x4`；要「一张主视觉压住画面」用 `center_v2`。

## 2. 色彩与格调（必须统一）

1. **一套色系贯穿全屏**：边框/`outerImage`、标题光效、图表 `colors` 同属一个冷/暖基调；禁止中间金框、四周蓝框这类混用。  
2. **避免经典深纯色堆砌**（如默认 `#5470c6` / 过饱和单色块）。优先产品色板淡彩：`elegant` / `future` / `simple`，或自拟同明度区间的柔和色。  
3. **柱/条可开渐变**：`extraView.customAttr.basicStyle.gradient = true`（产品柱图能力）；树图/环图用淡色 + `alpha` 约 75–88。  
4. **对比可读**：暗底大屏标签/标题用浅色字；tooltip 保持白底黑字（勿白字）。树图须 `label.show=true` 且开维度/占比（与界面树图默认一致）。  
5. **系列色数量**：环图/树图有效可辨色控制在约 5–9；过多则合并「其他」或换树图/堆叠。

### 推荐淡彩示例（可整屏复用）

```text
elegant: #95a2ff #fa8080 #ffc076 #fae768 #87e885 #3cb9fc #73abf5 #cb9bff #9de0ff
future:  #63b2ee #76da91 #f8cb7f #f89588 #7cd6cf #7898e1 #efa666 #eddd86 #9192ab
```

plan 示例字段：

```json
"extraView": {
  "customAttr": {
    "basicStyle": {
      "colorScheme": "future",
      "alpha": 86,
      "gradient": true,
      "colors": ["#63b2ee", "#76da91", "#f8cb7f", "#f89588", "#7cd6cf", "#7898e1", "#efa666", "#eddd86", "#9192ab"]
    }
  }
}
```

## 3. 组件与美化（产品能力内）

| 手段 | 用法 | 注意 |
|------|------|------|
| 画布底图 | `canvas.background` + `backgroundImageEnable` | 氛围层；内容可收在主舞台，两侧留给底图 |
| 组件外框 | `commonBackground.backgroundType=outerImage` + `outerImage` | **全屏同一资源**；GIF 动效也须同色系 |
| 富文本标题 | `UserView` + `rich-text`，`render=custom` | 居中写入 `propValue.textValue`；勿用 ScrollText 冒充居中 |
| 图片/视频 | `Picture`→`propValue.url`；`DeVideo`→`videoLinks.web.src` | 字段与界面一致，勿臆造 JSON |
| 生成素材 | Python 出 PNG/GIF | 只放**用户工作区** `generated/`，skill 包不落二进制；plan 只写 URL/`/static-resource/...` |

美化优先序：底图 → 统一 outerImage →（可选）Picture/DeVideo → 图表淡彩/渐变。

## 4. 间距与密度

- 默认画布 1920×1080；模板已含边距与槽间距，勿把组件贴死无缝。  
- 数据密时优先 `grid_3x4` 或加过滤/下钻，而不是无层级地堆满主舞台。  
- 高管一页结论：主舞台 1 个宏大图 + 少量 KPI/占比；运维密盘：多槽均分，仍保持外框与色板一致。

## 5. 交付前检查（大屏）

- [ ] 布局模板与主图图种匹配（宏大感 / 均分）  
- [ ] 全屏外框/`outerImage` 色系统一  
- [ ] 图表色板淡彩一致；柱条按需 `gradient`；无过深经典纯色墙  
- [ ] 树图/环图标签可见；tooltip 可读  
- [ ] `render` 正确（rich-text/indicator → `custom`）  
- [ ] 取数 preview 通过后再 publish  
- [ ] 生成图未写入正式 skill 目录  

示范提示词与 plan：[examples/datav_showcase_center_beautify.md](../examples/datav_showcase_center_beautify.md)。
