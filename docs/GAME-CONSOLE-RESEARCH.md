# 轻量像素小游戏调研报告 — 游戏机模式集成方案

> 调研时间：2026-06-23 | 调研方法：5路并行搜索 + 对抗验证 + 综合排名

## 1. 调研概述

### 1.1 调研目标

为 AI Nexus Assistant（Tauri 2 + React 19 + TypeScript + Tailwind CSS v4 桌面应用）设计"游戏机模式"——一套可玩性高、像素风格的轻量级 HTML5 小游戏集合，便于在 WebView2 中运行，无需后端支持。

### 1.2 筛选标准

| 维度 | 要求 |
|------|------|
| 视觉风格 | 像素风（pixel art），复古街机感 |
| 可玩性 | 上手快、重玩价值高、非 Demo 级别 |
| 许可证 | MIT / Apache-2.0 / Unlicense（宽松许可，可嵌入闭源项目） |
| 轻量级 | 游戏仓库 <5MB，单文件或少依赖为佳 |
| 集成性 | 可在 React/Tauri WebView2 中运行，无需后端 |
| 渲染方式 | HTML5 Canvas 或 WebGL，纯前端 |

### 1.3 调研方法

从五个角度进行全网搜索：(1) 浏览器/WebView 可运行的 HTML5 像素游戏开源项目；(2) 与 React/TypeScript 技术栈匹配的 Canvas 像素游戏；(3) 经典复古街机风格的 JS/TS 像素小游戏；(4) Tauri/WebView2 中嵌入游戏的可行方案与最佳实践；(5) 轻量级像素游戏引擎/库便于自研。共筛选 140 余个 GitHub 仓库，经许可证、体积、像素风格、可玩性、集成难度五维验证后，形成最终推荐列表。

---

## 2. 推荐游戏项目（按推荐度排序）

### 2.1 第一梯队：强烈推荐（可直接集成，质量最高）

---

**A1. mumuy/pacman — 经典吃豆人**

- **GitHub**: https://github.com/mumuy/pacman
- **Stars**: 1,636 | **语言**: JavaScript | **仓库体积**: 124KB
- **许可证**: MIT
- **游戏类型**: 迷宫追逐 | **玩法**: 操控吃豆人吃掉所有豆子，躲避幽灵，利用能量豆反杀
- **像素风格**: ★★★★★（忠实还原经典街机像素画风）
- **可玩性**: ★★★★★（经典玩法，零学习成本，无限重玩）
- **集成难度**: ★★★★★（单 HTML 入口，零依赖，iframe 即用）
- **集成方案**: 将 `index.html` 及资源复制到 `public/games/pacman/`，通过 `<iframe>` 加载
- **Demo**: https://github.com/mumuy/pacman 提供在线演示
- **备注**: 活跃维护，中国开发者项目，文档为中文

---

**A2. susam/invaders — 太空侵略者**

- **GitHub**: https://github.com/susam/invaders
- **Stars**: 183 | **语言**: HTML/JavaScript | **仓库体积**: 131KB
- **许可证**: MIT
- **游戏类型**: 固定射击 | **玩法**: 操控底部炮台左右移动射击，消灭上方排列的外星侵略者
- **像素风格**: ★★★★★（1980 年代街机风格，原汁原味）
- **可玩性**: ★★★★☆（经典玩法，难度递增，波次设计合理）
- **集成难度**: ★★★★★（单 HTML 文件，Canvas + Web Audio，零依赖）
- **集成方案**: 单文件直接 iframe，支持键盘控制
- **备注**: 附带复古音效，Web Audio API 实现

---

**A3. tetr.js — 俄罗斯方块**

- **GitHub**: https://github.com/simonlc/tetr.js
- **Stars**: 106 | **语言**: JavaScript | **仓库体积**: 145KB
- **许可证**: MIT
- **游戏类型**: 方块消除 | **玩法**: 经典俄罗斯方块，旋转、移动、消除完整行
- **像素风格**: ★★★☆☆（简洁像素风，非浓重复古）
- **可玩性**: ★★★★★（永恒经典，全球公认最佳休闲游戏之一）
- **集成难度**: ★★★★★（HTML + JS，零依赖，多个小文件）
- **集成方案**: 复制项目文件到 `public/games/tetris/`，iframe 加载

---

**A4. radius-raid-js13k — 太空射击**

- **GitHub**: https://github.com/jackrugile/radius-raid-js13k
- **Stars**: 271 | **语言**: JavaScript | **仓库体积**: 61KB
- **许可证**: MIT
- **游戏类型**: 弹幕射击 | **玩法**: 太空主题射击游戏，13 种敌人类型，5 种道具升级，视差滚动背景
- **像素风格**: ★★★★★（精致复古像素美术，粒子特效）
- **可玩性**: ★★★★☆（敌人多样、道具系统增加深度，波次生存模式）
- **集成难度**: ★★★★★（61KB 单文件，零依赖，js13k 竞赛作品）
- **集成方案**: 单 HTML 文件，iframe 加载即可
- **备注**: js13kGames 竞赛获奖作品，代码精炼

---

**A5. q1k3 — 复古第一人称射击**

- **GitHub**: https://github.com/phoboslab/q1k3
- **Stars**: 1,958 | **语言**: JavaScript | **仓库体积**: 207KB
- **许可证**: MIT
- **游戏类型**: FPS | **玩法**: 复古风格第一人称射击，在迷宫中消灭敌人
- **像素风格**: ★★★★★（经典 Doom 式低分辨率像素渲染）
- **可玩性**: ★★★★☆（技术成就惊人，FPS 操控略有门槛）
- **集成难度**: ★★★★☆（多文件但无依赖，鼠标指针锁定在 WebView 中需测试）
- **集成方案**: 复制到 `public/games/q1k3/`，iframe 加载
- **备注**: 由 phoboslab（Impact.js 引擎作者）制作，13KB 极限压缩

---

### 2.2 第二梯队：推荐（有小瑕疵但值得集成）

---

**B1. Hextris — 六边形方块**

- **GitHub**: https://github.com/Hextris/hextris
- **Stars**: 2,419 | **语言**: JavaScript | **仓库体积**: 27MB（含图片资源，游戏本体约 200KB）
- **许可证**: NOASSERTION（非标准许可证，需确认合法性）
- **游戏类型**: 益智方块 | **玩法**: 旋转六边形，接住从各方向掉落的色块，三个同色消除
- **像素风格**: ★★★☆☆（几何/扁平设计，非传统像素风）
- **可玩性**: ★★★★★（极度上瘾，上手极快）
- **集成难度**: ★★★★★（单 HTML 文件，零依赖）
- **集成方案**: 仅需 `index.html` 和内联 JS/CSS，iframe 加载
- **风险提示**: 许可证字段为 NOASSERTION，集成前需联系作者确认授权

---

**B2. skifree.js — 滑雪大冒险**

- **GitHub**: https://github.com/basicallydan/skifree.js
- **Stars**: 554 | **语言**: JavaScript | **仓库体积**: 812KB
- **许可证**: MIT
- **游戏类型**: 无尽跑酷 | **玩法**: 经典 SkiFree 复刻，从山顶滑下，躲避树木、石头、雪怪
- **像素风格**: ★★★★☆（复古 PC 游戏像素风格）
- **可玩性**: ★★★★☆（即时上手，随机生成地形，雪怪追逐增加紧张感）
- **集成难度**: ★★★★☆（多文件但无依赖，Canvas 渲染，最近仍在更新）
- **集成方案**: 复制到 `public/games/skifree/`，iframe 加载

---

**B3. iamkun/tower_game — 叠塔游戏**

- **GitHub**: https://github.com/iamkun/tower_game
- **Stars**: 1,596 | **语言**: JavaScript | **仓库体积**: 1.88MB
- **许可证**: MIT
- **游戏类型**: 休闲堆叠 | **玩法**: 点击/按键让方块落下，堆叠越高分数越高，偏差部分会被切掉
- **像素风格**: ★★★☆☆（简约像素风格，色彩鲜明）
- **可玩性**: ★★★★☆（极简操作，逐渐紧张，有挑战性）
- **集成难度**: ★★★★☆（有 Webpack 构建流程，但 `dist/` 目录已提供预构建单文件）
- **集成方案**: 使用 `dist/` 目录的预构建文件，iframe 加载
- **备注**: 中国开发者作品，有中文文档

---

**B4. js13k-2018 — 2D 像素平台跳跃**

- **GitHub**: https://github.com/starzonmyarmz/js13k-2018
- **Stars**: 212 | **语言**: JavaScript | **仓库体积**: 1.9MB
- **许可证**: MIT
- **游戏类型**: 平台跳跃 | **玩法**: 2D 横版跳跃，躲避障碍，收集物品
- **像素风格**: ★★★★★（精致像素美术，js13k 竞赛水准）
- **可玩性**: ★★★☆☆（关卡有限但手感不错）
- **集成难度**: ★★★★★（单文件，零依赖）
- **集成方案**: iframe 加载单 HTML 文件

---

**B5. Pseudo-3d-Racer — 伪 3D 赛车**

- **GitHub**: https://github.com/ssusnic/Pseudo-3d-Racer
- **Stars**: 66 | **语言**: JavaScript | **仓库体积**: 399KB
- **许可证**: MIT
- **游戏类型**: 竞速 | **玩法**: Outrun 风格伪 3D 赛车，方向键控制，无限赛道
- **像素风格**: ★★★★☆（复古街机赛车视觉，分段渲染路面）
- **可玩性**: ★★★☆☆（操作简单，重复性略高）
- **集成难度**: ★★★★☆（单文件，零依赖，仅方向键操控）
- **集成方案**: iframe 加载

---

**B6. norman-the-necromancer — 死灵法师**

- **GitHub**: https://github.com/danprince/norman-the-necromancer
- **Stars**: 200 | **语言**: TypeScript | **仓库体积**: 269KB
- **许可证**: Unlicense（完全公共领域）
- **游戏类型**: 动作冒险 | **玩法**: 死灵法师主题，召唤亡灵战斗，探索关卡
- **像素风格**: ★★★★★（精致像素美术，暗黑风格）
- **可玩性**: ★★★★☆（完整游戏体验，有探索和战斗）
- **集成难度**: ★★★★★（TypeScript 编写，单文件输出，零依赖）
- **集成方案**: iframe 加载

---

### 2.3 第三梯队：备选方案

---

**C1. phaser-catch-the-cat — 捉猫游戏**

- **GitHub**: https://github.com/ganlvtech/phaser-catch-the-cat
- **Stars**: 751 | **语言**: JavaScript | **仓库体积**: 850KB
- **许可证**: MIT
- **游戏类型**: 益智策略 | **玩法**: 在网格中围堵一只猫，点击格子缩小猫的活动范围
- **像素风格**: ★★★☆☆（简洁网格设计）
- **可玩性**: ★★★★☆（AI 猫有策略性，重复可玩）
- **集成难度**: ★★★☆☆（依赖 Phaser 3，需通过 CDN 加载或打包）
- **集成方案**: iframe 加载，确保 Phaser CDN 在 WebView2 中可达；或下载 Phaser 本地化

---

**C2. SC_Js — 星际争霸风格 RTS**

- **GitHub**: https://github.com/gloomyson/SC_Js
- **Stars**: 591 | **语言**: JavaScript | **仓库体积**: 1.4MB
- **许可证**: MIT
- **游戏类型**: 即时战略 | **玩法**: 多单位操控、资源采集、建筑建造，类星际争霸
- **像素风格**: ★★★★☆（类 RTS 游戏的精灵图风格）
- **可玩性**: ★★★☆☆（操控复杂，不适合休闲模式）
- **集成难度**: ★★★☆☆（多文件，无依赖，Canvas 渲染，单位多时性能需关注）
- **集成方案**: 复制到 `public/games/sc/`，iframe 加载

---

**C3. canvas-tank-battle — 坦克大战**

- **GitHub**: https://github.com/Baatusi/canvas-tank-battle
- **Stars**: 1 | **语言**: JavaScript | **仓库体积**: 50KB
- **许可证**: MIT
- **游戏类型**: 动作射击 | **玩法**: 经典坦克大战，8 方向移动，子弹反弹，10 个关卡
- **像素风格**: ★★★★☆（复古 FC 坦克大战风格）
- **可玩性**: ★★★★☆（经典玩法，10 个关卡，触屏支持）
- **集成难度**: ★★★★★（单 HTML 文件，50KB，MIT，零依赖）
- **集成方案**: iframe 加载
- **备注**: 虽仅 1 star，但代码完整、体积极小、中文注释，适合作为低风险集成选项

---

**C4. nova-rift — 8-bit 太空射击**

- **GitHub**: https://github.com/evelinvee/nova-rift
- **Stars**: 0 | **语言**: JavaScript | **仓库体积**: 9KB
- **许可证**: MIT
- **游戏类型**: 弹幕射击 | **玩法**: 8-bit 像素太空射击，单 HTML 文件，原生 JS，零依赖
- **像素风格**: ★★★★☆（精致 8-bit 太空像素美术）
- **可玩性**: ★★★☆☆（轻量级射击，适合快速游玩）
- **集成难度**: ★★★★★（9KB 单文件，iframe 即用）
- **备注**: 0 stars 项目，建议上线前先人工验证可玩性

---

**C5. js13k-2019 — xx142-b2.exe 潜行游戏**

- **GitHub**: https://github.com/bencoder/js13k-2019
- **Stars**: 216 | **语言**: JavaScript | **仓库体积**: 2.6MB
- **许可证**: MIT
- **游戏类型**: 潜行动作 | **玩法**: 科幻主题潜行游戏，躲避敌人视线，完成任务
- **像素风格**: ★★★★☆（赛博朋克像素风）
- **可玩性**: ★★★★☆（有策略深度，关卡设计精良）
- **集成难度**: ★★★★★（单文件输出，零依赖）
- **集成方案**: iframe 加载

---

## 3. 自研方案建议

若现有开源项目无法完全满足需求，建议基于以下轻量引擎自研小游戏。

### 3.1 引擎选型对比

| 引擎 | Stars | 体积 | 语言 | 许可证 | TypeScript | 特点 | 推荐度 |
|------|-------|------|------|--------|------------|------|--------|
| **LittleJS** | 4,128 | ~50KB（核心） | JS | MIT | 有 `.d.ts` | 零依赖，内置渲染/物理/音频，像素优化 | ★★★★★ |
| **Kontra.js** | 1,065 | ~5KB | JS | MIT | 有 `.d.ts` | 超微型，js13k 优化，适合极简游戏 | ★★★★☆ |
| **litecanvas** | 69 | ~4KB | JS | MIT | 有 `.d.ts` | Pico-8 风格 API，极简，创意编程 | ★★★★☆ |
| **Kaplay** | 1,729 | ~200KB | TS | MIT | 原生 TS | Kaboom.js 继任者，90+ 示例，活跃社区 | ★★★★☆ |
| **melonJS** | 6,322 | ~150KB | JS | MIT | 有 TS 支持 | 瓦片地图支持好，适合平台跳跃/RPG | ★★★☆☆ |

### 3.2 推荐方案：LittleJS + 自研小游戏

**选择理由**：
1. **零依赖**，npm 包体积小（`littlejsengine` 约 50KB）
2. **内置全套功能**：WebGL 渲染、物理引擎、音频系统、输入管理、粒子系统
3. **像素艺术优化**：原生支持像素完美渲染（`pixelPerfect` 选项）
4. **TypeScript 类型支持**：提供 `.d.ts` 声明文件
5. **MIT 许可证**：可自由嵌入闭源项目
6. **附带示例游戏**：可作为自研参考

**自研游戏建议清单**（按开发难度递增）：

| 游戏 | 类型 | 预估工时 | 说明 |
|------|------|----------|------|
| 贪吃蛇 | 经典 | 2-3 天 | 方向键控制，吃食物增长，撞墙/撞身死亡 |
| 打砖块 | 弹球 | 3-4 天 | 挡板接球，消除上方砖块 |
| 躲避球 | 动作 | 2-3 天 | 操控角色躲避四面八方飞来的障碍物 |
| 像素地牢 | Roguelike | 1-2 周 | 随机生成地牢，回合制移动，收集宝箱 |
| 像素弹幕 | 射击 | 1 周 | 自机射击 + 敌方弹幕，Boss 战 |

### 3.3 React + LittleJS 集成示例

```tsx
// src/components/GameCanvas.tsx
import { useEffect, useRef } from 'react';

interface GameCanvasProps {
  gameModule: () => Promise<{ default: () => void }>;
  width?: number;
  height?: number;
}

export function GameCanvas({ gameModule, width = 800, height = 600 }: GameCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    // 动态加载游戏模块
    gameModule().then(mod => mod.default());

    return () => {
      // 游戏退出清理
      if (typeof (window as any).engineDestroy === 'function') {
        (window as any).engineDestroy();
      }
    };
  }, [gameModule]);

  return <canvas ref={canvasRef} width={width} height={height} />;
}
```

---

## 4. 集成架构方案

### 4.1 整体架构设计

```
src/
├── pages/
│   └── GameConsolePage.tsx        # 游戏机模式主页面
├── components/
│   ├── GameConsole/
│   │   ├── ConsoleLayout.tsx      # 游戏机布局（游戏列表 + 游戏区域）
│   │   ├── GameCard.tsx           # 游戏卡片（封面、名称、评分）
│   │   ├── GamePlayer.tsx         # 游戏播放器（iframe 容器）
│   │   ├── GameOverlay.tsx        # 游戏覆盖层（暂停/退出/设置）
│   │   └── ScoreBoard.tsx         # 排行榜组件
│   └── GameCanvas.tsx             # 自研游戏 Canvas 组件
├── games/                         # 游戏元数据
│   ├── registry.ts                # 游戏注册表
│   └── types.ts                   # 类型定义
└── public/
    └── games/                     # iframe 游戏静态资源
        ├── pacman/
        ├── invaders/
        ├── tetris/
        └── ...
```

### 4.2 路由设计

```tsx
// 在路由配置中添加
{
  path: '/games',
  element: <GameConsolePage />,
  children: [
    { index: true, element: <GameList /> },
    { path: ':gameId', element: <GamePlayer /> },
  ]
}
```

### 4.3 游戏注册表

```typescript
// src/games/types.ts
export interface GameInfo {
  id: string;
  name: string;
  nameCN: string;
  description: string;
  cover: string;              // 封面图路径
  type: 'iframe' | 'canvas';  // 加载方式
  src?: string;               // iframe: 游戏 HTML 路径
  module?: () => Promise<any>; // canvas: 动态导入的游戏模块
  controls: ('keyboard' | 'mouse' | 'touch')[];
  category: 'action' | 'puzzle' | 'shooter' | 'racing' | 'rpg';
  difficulty: 1 | 2 | 3 | 4 | 5;
  pixelRating: 1 | 2 | 3 | 4 | 5;
  license: string;
  source: string;             // GitHub URL
}

// src/games/registry.ts
export const GAMES: GameInfo[] = [
  {
    id: 'pacman',
    name: 'Pac-Man',
    nameCN: '吃豆人',
    description: '经典街机游戏，吃掉所有豆子并躲避幽灵',
    cover: '/games/pacman/cover.png',
    type: 'iframe',
    src: '/games/pacman/index.html',
    controls: ['keyboard'],
    category: 'action',
    difficulty: 2,
    pixelRating: 5,
    license: 'MIT',
    source: 'https://github.com/mumuy/pacman'
  },
  // ... 其他游戏
];
```

### 4.4 游戏加载方式

**方案一：iframe 加载（推荐用于集成现有开源游戏）**

```tsx
// src/components/GameConsole/GamePlayer.tsx
import { useParams } from 'react-router-dom';
import { GAMES } from '../../games/registry';

export function GamePlayer() {
  const { gameId } = useParams();
  const game = GAMES.find(g => g.id === gameId);

  if (!game) return <div>游戏未找到</div>;

  if (game.type === 'iframe') {
    return (
      <div className="game-player">
        <iframe
          src={game.src}
          className="w-full h-full border-0"
          allow="autoplay; gamepad"
          sandbox="allow-scripts allow-same-origin"
        />
        <GameOverlay gameId={game.id} />
      </div>
    );
  }

  // Canvas 类型游戏使用动态导入
  return <GameCanvas gameModule={game.module!} />;
}
```

**方案二：Canvas 组件（用于自研游戏）**

```tsx
// 使用 React 的 useEffect + useRef 管理游戏生命周期
export function GameCanvas({ gameModule }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const cleanup = gameModule(canvasRef.current!);
    return cleanup;
  }, [gameModule]);

  return <canvas ref={canvasRef} />;
}
```

### 4.5 存档与排行榜方案

```typescript
// src/games/saveManager.ts
const SAVE_KEY = 'nexus-game-saves';
const SCORE_KEY = 'nexus-game-scores';

export interface GameSave {
  gameId: string;
  timestamp: number;
  data: Record<string, any>;
}

export interface GameScore {
  gameId: string;
  score: number;
  timestamp: number;
}

// 使用 localStorage 持久化（无后端依赖）
export function saveGame(gameId: string, data: Record<string, any>) {
  const saves = JSON.parse(localStorage.getItem(SAVE_KEY) || '{}');
  saves[gameId] = { gameId, timestamp: Date.now(), data };
  localStorage.setItem(SAVE_KEY, JSON.stringify(saves));
}

export function loadGame(gameId: string): GameSave | null {
  const saves = JSON.parse(localStorage.getItem(SAVE_KEY) || '{}');
  return saves[gameId] || null;
}

export function submitScore(gameId: string, score: number) {
  const scores: GameScore[] = JSON.parse(localStorage.getItem(SCORE_KEY) || '[]');
  scores.push({ gameId, score, timestamp: Date.now() });
  scores.sort((a, b) => b.score - a.score);
  // 仅保留每个游戏前 10 名
  const topScores = scores
    .filter((_, i) => i < 10 || scores[i].gameId !== gameId);
  localStorage.setItem(SCORE_KEY, JSON.stringify(topScores));
}

export function getTopScores(gameId: string, limit = 10): GameScore[] {
  const scores: GameScore[] = JSON.parse(localStorage.getItem(SCORE_KEY) || '[]');
  return scores.filter(s => s.gameId === gameId).slice(0, limit);
}
```

**iframe 游戏与宿主通信**（用于存档和排行榜）：

```typescript
// 在 GamePlayer.tsx 中监听 iframe 消息
useEffect(() => {
  const handler = (event: MessageEvent) => {
    if (event.data?.type === 'GAME_SCORE') {
      submitScore(gameId, event.data.score);
    }
    if (event.data?.type === 'GAME_SAVE') {
      saveGame(gameId, event.data.data);
    }
  };
  window.addEventListener('message', handler);
  return () => window.removeEventListener('message', handler);
}, [gameId]);
```

### 4.6 全屏与手柄支持

```typescript
// src/games/gamepadManager.ts
export function useGamepad(onInput: (buttons: number[], axes: number[]) => void) {
  useEffect(() => {
    let animId: number;
    const poll = () => {
      const gamepads = navigator.getGamepads();
      for (const gp of gamepads) {
        if (gp) {
          onInput(
            gp.buttons.map(b => b.pressed ? 1 : 0),
            gp.axes
          );
        }
      }
      animId = requestAnimationFrame(poll);
    };
    animId = requestAnimationFrame(poll);
    return () => cancelAnimationFrame(animId);
  }, [onInput]);
}

// 全屏切换
export function toggleFullscreen(element: HTMLElement) {
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    element.requestFullscreen();
  }
}
```

### 4.7 UI 设计建议

游戏机模式主页面采用复古游戏厅风格：

- **顶部**: 像素字体标题"游戏机模式"，复古 CRT 扫描线效果（CSS 实现）
- **中部**: 横向滚动的游戏卡片列表，每张卡片显示游戏封面、名称、类型标签
- **底部**: 全局排行榜（Top 10），支持按游戏筛选
- **游戏页**: 全屏游戏区域 + 浮动工具栏（暂停/退出/全屏/音量）
- **配色**: 深色背景 + 霓虹色高亮（与深色主题统一）

---

## 5. 实施优先级建议

### Phase 1：基础框架（1-2 周）

| 任务 | 工时 | 说明 |
|------|------|------|
| 创建 `GameConsolePage.tsx` 页面框架 | 1 天 | 路由、布局、游戏列表 |
| 实现 `GamePlayer.tsx` iframe 加载器 | 1 天 | 沙盒化 iframe、全屏支持 |
| 实现游戏注册表 `registry.ts` | 0.5 天 | 类型定义、游戏元数据 |
| 集成第一批游戏（3-4 个） | 2 天 | mumuy/pacman、susam/invaders、tetr.js、radius-raid |
| 存档/排行榜系统 | 1 天 | localStorage 持久化 |

### Phase 2：扩展游戏库（1 周）

| 任务 | 工时 | 说明 |
|------|------|------|
| 集成第二批游戏（4-5 个） | 3 天 | q1k3、skifree.js、tower_game、js13k-2018、Pseudo-3d-Racer |
| 游戏手柄支持 | 1 天 | Gamepad API 集成 |
| CRT 扫描线视觉效果 | 0.5 天 | CSS filter 实现 |
| 游戏搜索/筛选 | 0.5 天 | 按类型、难度、评分筛选 |

### Phase 3：自研游戏（2-3 周，可选）

| 任务 | 工时 | 说明 |
|------|------|------|
| 引入 LittleJS 引擎 | 1 天 | npm 安装、React 封装 |
| 自研贪吃蛇 | 2 天 | 入门级自研游戏 |
| 自研打砖块 | 3 天 | 中等复杂度 |
| 自研像素弹幕 | 5 天 | 进阶自研游戏 |

### 总体时间估算

| 方案 | 时间 | 游戏数量 |
|------|------|----------|
| 最小可行版本（Phase 1） | 1-2 周 | 4 个游戏 |
| 完整版本（Phase 1 + 2） | 2-3 周 | 9-10 个游戏 |
| 含自研（Phase 1 + 2 + 3） | 4-6 周 | 12-13 个游戏 |

---

## 6. 参考来源

### 6.1 推荐游戏项目

| 项目 | GitHub URL | Stars | 许可证 |
|------|-----------|-------|--------|
| mumuy/pacman | https://github.com/mumuy/pacman | 1,636 | MIT |
| susam/invaders | https://github.com/susam/invaders | 183 | MIT |
| simonlc/tetr.js | https://github.com/simonlc/tetr.js | 106 | MIT |
| jackrugile/radius-raid-js13k | https://github.com/jackrugile/radius-raid-js13k | 271 | MIT |
| phoboslab/q1k3 | https://github.com/phoboslab/q1k3 | 1,958 | MIT |
| Hextris/hextris | https://github.com/Hextris/hextris | 2,419 | NOASSERTION |
| basicallydan/skifree.js | https://github.com/basicallydan/skifree.js | 554 | MIT |
| iamkun/tower_game | https://github.com/iamkun/tower_game | 1,596 | MIT |
| starzonmyarmz/js13k-2018 | https://github.com/starzonmyarmz/js13k-2018 | 212 | MIT |
| ssusnic/Pseudo-3d-Racer | https://github.com/ssusnic/Pseudo-3d-Racer | 66 | MIT |
| danprince/norman-the-necromancer | https://github.com/danprince/norman-the-necromancer | 200 | Unlicense |
| ganlvtech/phaser-catch-the-cat | https://github.com/ganlvtech/phaser-catch-the-cat | 751 | MIT |
| gloomyson/SC_Js | https://github.com/gloomyson/SC_Js | 591 | MIT |
| Baatusi/canvas-tank-battle | https://github.com/Baatusi/canvas-tank-battle | 1 | MIT |
| evelinvee/nova-rift | https://github.com/evelinvee/nova-rift | 0 | MIT |
| bencoder/js13k-2019 | https://github.com/bencoder/js13k-2019 | 216 | MIT |

### 6.2 轻量游戏引擎

| 引擎 | GitHub URL | Stars | 许可证 |
|------|-----------|-------|--------|
| LittleJS | https://github.com/KilledByAPixel/LittleJS | 4,128 | MIT |
| Kontra.js | https://github.com/straker/kontra | 1,065 | MIT |
| litecanvas | https://github.com/litecanvas/game-engine | 69 | MIT |
| Kaplay | https://github.com/kaplayjs/kaplay | 1,729 | MIT |
| melonJS | https://github.com/melonjs/melonJS | 6,322 | MIT |
| crisp-game-lib | https://github.com/abagames/crisp-game-lib | 641 | MIT |
| ZzFX | https://github.com/KilledByAPixel/ZzFX | 740 | MIT |

### 6.3 Tauri/WebView2 相关

| 资源 | URL | 说明 |
|------|-----|------|
| Tauri v2 文档 | https://v2.tauri.app | 官方文档 |
| tauri-apps/wry | https://github.com/tauri-apps/wry | WebView 渲染库 |
| tauri-plugin-multiwebview | https://github.com/nicedrop/tauri-plugin-multiwebview | 多 Webview 插件 |
| WebView2 Samples | https://github.com/MicrosoftEdge/WebView2Samples | 微软官方示例 |

### 6.4 参考列表

| 列表 | URL | 说明 |
|------|-----|------|
| awesome-jsgames | https://github.com/proyecto26/awesome-jsgames | JS 游戏精选列表，948 stars |
| one-html-page-challenge | https://github.com/Metroxe/one-html-page-challenge | 单 HTML 页面游戏挑战，1,350 stars |
| js13kGames | https://js13kgames.com/ | 13KB 极限游戏竞赛官网 |

---

**免责声明**：以上 Star 数、仓库体积、许可证信息基于调研时（2026 年 6 月）的 GitHub 数据，实际使用前建议重新验证。特别是许可证为 NOASSERTION 或未标注的项目，集成前务必联系原作者确认授权。
