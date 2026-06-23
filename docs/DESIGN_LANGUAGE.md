# AI Nexus Assistant 设计语言规范 v1.0

## 一、设计哲学

**关键词**: 简洁、克制、专业、专注、安静的高级感

七项核心原则：
1. **内容优先，元素退隐** — 内容始终是唯一焦点，其他元素主动退隐
2. **无情绪化装饰** — 安静、专注、轻量
3. **克制优于表达** — hover 仅展示微妙的背景变化，无突出边框、无夸张动画
4. **即时保存** — 所有修改即时保存，无全局保存按钮
5. **错误不打断** — AI 服务不可用时展示低干扰错误，永不崩溃 UI
6. **MVP 优先** — 先实现可运行的 MVP，再逐步打磨
7. **一致性** — 同类元素在所有页面保持相同样式

设计参考: Apple Dashboard、Vercel Analytics、Linear Design、OpenAI Design Language

---

## 二、色彩系统

### 核心色板（近单色灰度）

| 角色 | 色值 | 用途 |
|------|------|------|
| 页面背景 | `#FCFCFC` / `#F8FAFC` | 页面骨架背景 |
| 侧边栏背景 | `#FCFCFD` | 左侧导航区域 |
| 卡片表面 | `#FFFFFF` | 卡片、面板、对话框 |
| 柔和表面 | `#EDEDED` / `#F5F5F5` | 次级背景、输入填充、hover 基底 |
| 选中背景 | `#E2E2E2` | 侧边栏/列表选中项 |
| 分割线/边框 | `#E5E5E5` / `#EEEEEE` | 边框、分割线 |
| 主文本 | `#171717` / `#0F172A` | 标题、关键数字 |
| 次文本 | `#4F4F4F` / `#64748B` | 描述、辅助信息 |
| 弱文本 | `#666666` / `#94A3B8` | 占位符、提示 |

### 语义色彩（谨慎使用）

| 语义 | 色值 | 用途 |
|------|------|------|
| 成功/活跃 | `#10B981` / `#059669` | 成功状态 |
| 成功背景 | `#ECFDF5` | 成功状态标签背景 |
| 错误/问题 | `#F87171` | 错误标题强调 |
| 警告 | `#D97706` | 警告状态 |

### 禁止使用的色彩
- 高饱和度颜色
- Material 默认紫色
- 彩虹渐变
- 蓝色主色调（整体色板保持中性灰）

---

## 三、排版系统

### 字体栈
- **主字体**: Inter, SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, PingFang SC
- **等宽字体**: JetBrains Mono（编辑器/代码/数字显示）

### 字号规范

| 角色 | 字号 | 字重 | 行高 | 字间距 |
|------|------|------|------|--------|
| 页面标题 | 16-18px | w600 | 1.2-1.35 | -0.2 |
| 分组标题 | 13-15px | w600 | 1.4 | — |
| 正文/设置文本 | 13-14px | w400-w500 | 1.55-1.7 | — |
| 描述文本 | 12-13px | w400 | — | — |
| 小标签 | 10-12px | w500-w600 | — | 0.8-1 |
| 代码块 | 13px | w400 | 1.4 | — |

### 关键排版规则
- 标题统一使用 `w600`（SemiBold）；正文使用 `w400`（Regular）
- 数字显示使用等宽数字（`font-variant-numeric: tabular-nums`）
- 负字间距仅用于大号展示数字（-1.5px 到 -3.2px）

---

## 四、圆角系统

| 元素 | 圆角 | Tailwind 类 | 用途 |
|------|------|-------------|------|
| 主容器/卡片 | 16px | `rounded-2xl` | SoftCard、对话框、面板 |
| 次级容器 | 12px | `rounded-xl` | 设置卡片、统计卡片、列表项 |
| 输入框 | 10-12px | `rounded-xl` | 搜索框、文本输入 |
| 图标按钮 | 10px | `rounded-lg` | 侧边栏按钮、操作按钮 |
| 胶囊按钮 | 999px | `rounded-full` | 完全圆角"药丸"形状 |
| 代码块 | 8px | `rounded-lg` | 代码区域 |
| 标签/徽章 | 6px | `rounded-md` | 小型标签 |

### 圆角规则
- 同类型元素必须使用相同圆角
- 卡片统一使用 `rounded-2xl`（16px）
- 按钮统一使用 `rounded-lg`（10px）或 `rounded-full`（胶囊）
- 暗色主题不改变圆角值

---

## 五、间距系统

| 场景 | 值 |
|------|-----|
| 页面水平内边距 | 24-32px |
| 页面垂直内边距 | 20-24px |
| 卡片内边距 | 20px（默认）/ 24px（大卡片） |
| 段落间距 | 20-24px |
| 元素间距 | 12-16px |
| 紧凑间距 | 6-8px |
| 最大内容宽度 | 1200px（居中） |

---

## 六、阴影系统

**核心规则**: 持久内容块不使用阴影。仅弹出层、工具提示、浮动层可使用阴影。

| 场景 | 值 |
|------|-----|
| 卡片（持久） | `0 1px 3px rgba(0,0,0,0.04)` |
| 卡片 hover | `0 4px 12px rgba(0,0,0,0.06)` |
| 弹出层 | `0 8px 30px rgba(0,0,0,0.08)` |
| 弹出层遮罩 | `rgba(15, 23, 42, 0.12)` |
| 工具提示 | `0 4px 12px rgba(0,0,0,0.08)` |

---

## 七、动画与交互规范

### 动画时长

| 场景 | 时长 | 缓动曲线 |
|------|------|----------|
| 微交互 | 120ms | ease-out-cubic |
| 小过渡 | 140-160ms | ease-out-cubic |
| 大过渡 | 240-280ms | ease-out-cubic |
| 展开/折叠 | 280ms | ease-in-out-cubic |

### 动画原则
- 无夸张动画，无浮动效果
- 无 FAB 脉冲
- Apple 风格缓动曲线（`ease-out-cubic` 为主曲线）

### 交互模式

**Hover**: 极度克制。仅微妙的背景色变化（`#F5F5F5` → `#E2E2E2`）。无突出边框。无颜色变化。无缩放变换。120ms ease-out-cubic。

**输入框**: 无边框 + 浅色背景。聚焦时：显示边框 + 加深背景。占位符颜色 `#94A3B8`。圆角 10-12px。

**对话框/模态框**: 白色背景，圆角 16px。背景遮罩 `rgba(15, 23, 42, 0.12)`。左上标题，右上关闭按钮。底部固定操作按钮。

---

## 八、图标规范

### 核心规则
- **禁止使用 emoji 作为 UI 图标** — 所有图标必须使用 SVG 图标组件
- 图标组件位于 `src/components/Icons.tsx`
- 统一使用 stroke 样式，`stroke-width: 1.5`
- 默认尺寸 18px，按钮内图标 14-16px
- 图标颜色继承父元素 `currentColor`

### 图标映射（替代 emoji）

| 原 emoji | SVG 图标组件 | 用途 |
|----------|-------------|------|
| 📊 | `IconChart` | 统计、图表 |
| 📋 | `IconClipboard` | 剪贴板、计划 |
| 📚 | `IconBook` | 文献、书籍 |
| 🧪 | `IconFlask` | 实验 |
| 🧠 | `IconBrain` | AI、智能 |
| 💬 | `IconChat` | 对话 |
| 🔍 | `IconSearch` | 搜索 |
| ✨ | `IconSparkle` | AI 功能 |
| 📝 | `IconEdit` | 编辑、写作 |
| 📄 | `IconFile` | 文件、PDF |
| 📥 | `IconUpload` | 导入（旋转180°） |
| 🔗 | `IconGlobe` | 链接、在线 |
| 📁 | `IconFolder` | 文件夹 |
| ❌ | `IconX` | 关闭、错误 |
| ✅ | `IconCheck` | 完成、成功 |
| ⚠️ | `IconLightbulb` | 警告、提示 |
| 💡 | `IconLightbulb` | 提示、想法 |
| 🔄 | `IconRepeat` | 刷新、重试 |
| ⏳ | `IconClock` | 等待 |
| 🌸 | `IconSun` | 主题 |
| 🤖 | `IconBrain` | Agent |
| 🆕 | `IconSparkle` | 新版本 |

### 状态指示
- 成功: 绿色 `#10B981` + `IconCheck`
- 错误: 红色 `#F87171` + `IconX`
- 警告: 琥珀色 `#D97706` + `IconLightbulb`
- 加载: `IconClock` 或 spinner 动画

---

## 九、组件规范

### SoftCard（主卡片模式）
```
padding: 20px
borderRadius: 16px (rounded-2xl)
background: #FFFFFF
border: 1px solid rgba(229, 229, 229, 0.6)
shadow: 0 1px 3px rgba(0,0,0,0.04)
```

### 图标按钮
```
size: 34x34px
icon: 18px, color: #666666
hover: #EDEDED background
borderRadius: 10px
```

### 胶囊按钮（主要操作）
```
height: 32px
padding: 16px horizontal, 6px vertical
borderRadius: 999px (rounded-full)
background: #171717 (近黑)
hover: #262626
color: white
fontSize: 13px, fontWeight: w500
```

### 页面布局
```
maxWidth: 1200px (居中)
水平内边距: 24-32px
垂直内边距: 20-24px
```
