"""五子棋 AI 引擎 — Minimax + Alpha-Beta 剪枝

参考实现:
- lihongxun945/gobang (JS, alpha-beta + evaluation patterns)
- kevin2014123/gomoku-ai (JS, minimax)
- Kali-Hac/Gomoku-AI (Python, threat-space search)

难度等级:
- LV.3: Minimax depth 2 + alpha-beta (速度优先)
- LV.4: Alpha-beta depth 4 + transposition table
- LV.5: Iterative deepening 2s
- LV.6: VCF + iterative deepening 3s
"""

import time
import hashlib
from typing import Optional
from dataclasses import dataclass, field

# ── 常量 ──
N = 15  # 棋盘大小
EMPTY = 0
PLAYER = 1  # 人类玩家（黑棋）
AI = 2      # AI（白棋）

# ── 模式评分 ──
SCORES = {
    'FIVE': 10_000_000,
    'OPEN_FOUR': 1_000_000,
    'BLOCK_FOUR': 80_000,
    'OPEN_THREE': 50_000,
    'BLOCK_THREE': 5_000,
    'OPEN_TWO': 500,
    'BLOCK_TWO': 50,
}

DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]


@dataclass
class TTEntry:
    """置换表条目"""
    depth: int
    score: float
    flag: int  # 0=exact, 1=lower, -1=upper
    best_move: Optional[tuple] = None


@dataclass
class GomokuAI:
    """五子棋 AI 引擎"""
    board: list = field(default_factory=lambda: [[EMPTY] * N for _ in range(N)])
    zobrist_table: list = field(default_factory=list)
    zobrist_hash: int = 0
    tt: dict = field(default_factory=dict)
    history_table: list = field(default_factory=lambda: [0] * (N * N))
    killers: list = field(default_factory=lambda: [[None, None] for _ in range(64)])
    nodes_searched: int = 0
    start_time: float = 0
    time_limit: float = 0

    def __post_init__(self):
        if not self.zobrist_table:
            self._init_zobrist()

    def _init_zobrist(self):
        """初始化 Zobrist 哈希表"""
        import random
        random.seed(42)  # 可复现
        self.zobrist_table = [
            [[0, random.getrandbits(64), random.getrandbits(64)]
             for _ in range(N)]
            for _ in range(N)
        ]
        self._rebuild_hash()

    def _rebuild_hash(self):
        """重建当前棋盘的 Zobrist 哈希"""
        h = 0
        for y in range(N):
            for x in range(N):
                if self.board[y][x]:
                    h ^= self.zobrist_table[y][x][self.board[y][x]]
        self.zobrist_hash = h

    def _toggle(self, x: int, y: int, p: int):
        """翻转 (x,y) 位置 p 玩家的 Zobrist 位"""
        self.zobrist_hash ^= self.zobrist_table[y][x][p]

    def set_board(self, board: list):
        """设置棋盘状态"""
        self.board = [row[:] for row in board]
        self._rebuild_hash()

    def check_win(self, player: int) -> bool:
        """检查 player 是否获胜（五连）"""
        for y in range(N):
            for x in range(N):
                if self.board[y][x] != player:
                    continue
                for dx, dy in DIRECTIONS:
                    count = 0
                    nx, ny = x, y
                    while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == player:
                        count += 1
                        nx += dx
                        ny += dy
                    if count >= 5:
                        return True
        return False

    def count_dir(self, x: int, y: int, dx: int, dy: int, player: int) -> int:
        """从 (x,y) 沿 (dx,dy) 方向数连续同色棋子"""
        count = 0
        nx, ny = x + dx, y + dy
        while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == player:
            count += 1
            nx += dx
            ny += dy
        return count

    def scan_line(self, x: int, y: int, dx: int, dy: int, player: int) -> tuple:
        """扫描 (x,y) 沿 (dx,dy) 方向，返回 (count, open_ends)"""
        count = 1
        open_ends = 0
        # 正向
        nx, ny = x + dx, y + dy
        while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == player:
            count += 1
            nx += dx
            ny += dy
        if 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == EMPTY:
            open_ends += 1
        # 反向
        nx, ny = x - dx, y - dy
        while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == player:
            count += 1
            nx -= dx
            ny -= dy
        if 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == EMPTY:
            open_ends += 1
        return count, open_ends

    def score_cell(self, x: int, y: int, player: int) -> dict:
        """评估空位 (x,y) 对 player 的模式分数"""
        five = open_four = block_four = open_three = block_three = 0
        self.board[y][x] = player
        for dx, dy in DIRECTIONS:
            cnt, opn = self.scan_line(x, y, dx, dy, player)
            if cnt >= 5:
                five += 1
            elif cnt == 4:
                if opn == 2:
                    open_four += 1
                elif opn == 1:
                    block_four += 1
            elif cnt == 3:
                if opn == 2:
                    open_three += 1
                elif opn == 1:
                    block_three += 1
            elif cnt == 2:
                pass  # open_two 通过组合检测处理
        # 跳棋模式: X_XXX, XX_XX
        for dx, dy in DIRECTIONS:
            for sign in (1, -1):
                gx = x + dx * sign
                gy = y + dy * sign
                if not (0 <= gx < N and 0 <= gy < N) or self.board[gy][gx] != EMPTY:
                    continue
                self.board[gy][gx] = player
                cnt, opn = self.scan_line(gx, gy, dx, dy, player)
                self.board[gy][gx] = 0
                if cnt >= 5:
                    five += 1
                elif cnt == 4 and opn == 2:
                    open_four += 1
                elif cnt == 4 and opn == 1:
                    block_four += 1
                elif cnt == 3 and opn == 2:
                    open_three += 1
        self.board[y][x] = EMPTY
        return {
            'five': five, 'open_four': open_four, 'block_four': block_four,
            'open_three': open_three, 'block_three': block_three
        }

    def evaluate_board(self) -> float:
        """快速全棋盘评估 — 按行扫描连续棋子段

        对每行/列/对角线做一次扫描，统计连续段的长度和开放端。
        """
        ai_p = [0] * 7  # [open2, block2, open3, block3, block4, open4, five]
        pl_p = [0] * 7

        def process_line(line):
            i = 0
            llen = len(line)
            while i < llen:
                x, y = line[i]
                p = self.board[y][x]
                if p == EMPTY:
                    i += 1
                    continue
                j = i + 1
                while j < llen:
                    nx, ny = line[j]
                    if self.board[ny][nx] != p:
                        break
                    j += 1
                length = j - i
                open_ends = 0
                if i > 0:
                    bx, by = line[i - 1]
                    if self.board[by][bx] == EMPTY:
                        open_ends += 1
                if j < llen:
                    fx, fy = line[j]
                    if self.board[fy][fx] == EMPTY:
                        open_ends += 1
                pp = ai_p if p == AI else pl_p
                if length >= 5:
                    pp[6] += 1
                elif length == 4:
                    pp[5 if open_ends == 2 else 4] += 1
                elif length == 3:
                    pp[2 if open_ends == 2 else 3] += 1
                elif length == 2:
                    pp[0 if open_ends == 2 else 1] += 1
                i = j

        # 行
        for y in range(N):
            process_line([(x, y) for x in range(N)])
        # 列
        for x in range(N):
            process_line([(x, y) for y in range(N)])
        # 对角线 (左上到右下)
        for d in range(-N + 1, N):
            line = [(d + i, i) for i in range(N) if 0 <= d + i < N]
            if len(line) >= 5:
                process_line(line)
        # 对角线 (右上到左下)
        for d in range(0, 2 * N - 1):
            line = [(d - i, i) for i in range(N) if 0 <= d - i < N]
            if len(line) >= 5:
                process_line(line)

        # 组合威胁评分 (限制 open_three 奖励避免过度膨胀)
        def combo_score(p):
            if p[6] > 0:
                return SCORES['FIVE']
            if p[5] > 0:
                return SCORES['OPEN_FOUR']
            if p[4] >= 2:
                return SCORES['OPEN_FOUR']
            if p[4] >= 1 and p[2] >= 1:
                return SCORES['OPEN_FOUR'] * 0.9
            # 最多奖励2个 open_three 作为组合威胁
            ot_bonus = min(p[2], 2) * SCORES['OPEN_THREE']
            if p[2] >= 2:
                ot_bonus = max(ot_bonus, SCORES['OPEN_FOUR'] * 0.8)
            return (p[5] * SCORES['OPEN_FOUR'] + p[4] * SCORES['BLOCK_FOUR'] +
                    ot_bonus + p[3] * SCORES['BLOCK_THREE'] +
                    p[0] * SCORES['OPEN_TWO'] + p[1] * SCORES['BLOCK_TWO'])

        return combo_score(ai_p) - combo_score(pl_p) * 1.1

    def find_critical_move(self, player: int) -> Optional[tuple]:
        """快速找必胜/必堵点"""
        opp = 3 - player
        # 先检查游戏是否已结束
        if self.check_win(player) or self.check_win(opp):
            return None
        # 先找自己能赢的
        for y in range(N):
            for x in range(N):
                if self.board[y][x]:
                    continue
                self.board[y][x] = player
                win = self.check_win(player)
                self.board[y][x] = EMPTY
                if win:
                    return (x, y)
        # 再找必须堵的
        for y in range(N):
            for x in range(N):
                if self.board[y][x]:
                    continue
                self.board[y][x] = opp
                win = self.check_win(opp)
                self.board[y][x] = EMPTY
                if win:
                    return (x, y)
        return None

    def get_candidates(self, radius: int = 2) -> list:
        """获取候选走法（已有棋子周围 radius 格内的空位）"""
        s = set()
        for y in range(N):
            for x in range(N):
                if not self.board[y][x]:
                    continue
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < N and 0 <= ny < N and not self.board[ny][nx]:
                            s.add(ny * N + nx)
        return [(v % N, v // N) for v in s]

    def _quick_score(self, x: int, y: int) -> float:
        """快速评估走法分数（用于排序）"""
        score = 0
        for dx, dy in DIRECTIONS:
            for p in (AI, PLAYER):
                c1 = self.count_dir(x, y, dx, dy, p)
                c2 = self.count_dir(x, y, -dx, -dy, p)
                total = c1 + c2 + 1
                if total >= 5:
                    score += 100000
                else:
                    score += (3 ** (total * 2)) * (1.1 if p == AI else 1.0)
        return score

    # ── VCF/VCT 威胁搜索 ──

    def _count_patterns_fast(self, x: int, y: int, player: int) -> tuple:
        """快速统计 (x,y) 处的模式: (open3, block4, open4)"""
        open3 = block4 = open4 = 0
        for dx, dy in DIRECTIONS:
            count = 1
            open_ends = 0
            nx, ny = x + dx, y + dy
            while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == player:
                count += 1
                nx += dx
                ny += dy
            if 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == EMPTY:
                open_ends += 1
            nx, ny = x - dx, y - dy
            while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == player:
                count += 1
                nx -= dx
                ny -= dy
            if 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == EMPTY:
                open_ends += 1
            if count >= 5:
                open4 += 1
            elif count == 4:
                if open_ends == 2:
                    open4 += 1
                elif open_ends == 1:
                    block4 += 1
            elif count == 3 and open_ends == 2:
                open3 += 1
        return open3, block4, open4

    def _find_threat_moves(self, player: int, threat_type: str) -> list:
        """找到所有能制造指定类型威胁的走法"""
        moves = []
        seen = set()
        for y in range(N):
            for x in range(N):
                if self.board[y][x] != player:
                    continue
                for dx, dy in DIRECTIONS:
                    for sign in (1, -1):
                        nx = x + dx * sign
                        ny = y + dy * sign
                        while 0 <= nx < N and 0 <= ny < N and self.board[ny][nx] == player:
                            nx += dx * sign
                            ny += dy * sign
                        if not (0 <= nx < N and 0 <= ny < N) or self.board[ny][nx] != EMPTY:
                            continue
                        key = ny * N + nx
                        if key in seen:
                            continue
                        self.board[ny][nx] = player
                        o3, b4, o4 = self._count_patterns_fast(nx, ny, player)
                        self.board[ny][nx] = EMPTY
                        is_threat = False
                        if threat_type == 'four' and (o4 > 0 or b4 > 0):
                            is_threat = True
                        elif threat_type == 'three' and o3 > 0 and o4 == 0 and b4 == 0:
                            is_threat = True
                        if is_threat:
                            seen.add(key)
                            moves.append((nx, ny))
        return moves

    def _find_forced_block(self, player: int) -> Optional[tuple]:
        """找对手的必堵点（用于 VCF 强制序列）"""
        opp = 3 - player
        for y in range(N):
            for x in range(N):
                if self.board[y][x]:
                    continue
                self.board[y][x] = opp
                win = self.check_win(opp)
                self.board[y][x] = EMPTY
                if win:
                    return (x, y)
        return None

    def vcf_search(self, player: int, depth: int) -> Optional[tuple]:
        """VCF: Victory by Continuous Four"""
        if depth <= 0:
            return None
        opp = 3 - player
        # 能直接赢？
        for y in range(N):
            for x in range(N):
                if self.board[y][x]:
                    continue
                self.board[y][x] = player
                if self.check_win(player):
                    self.board[y][x] = EMPTY
                    return (x, y)
                self.board[y][x] = EMPTY
        # 找冲四威胁
        fours = self._find_threat_moves(player, 'four')
        for move in fours:
            mx, my = move
            self.board[my][mx] = player
            self._toggle(mx, my, player)
            must_block = self._find_forced_block(opp)
            if must_block:
                bx, by = must_block
                self.board[by][bx] = opp
                self._toggle(bx, by, opp)
                result = self.vcf_search(player, depth - 1)
                self.board[by][bx] = EMPTY
                self._toggle(bx, by, opp)
                self.board[my][mx] = EMPTY
                self._toggle(mx, my, player)
                if result:
                    return move
            else:
                self.board[my][mx] = EMPTY
                self._toggle(mx, my, player)
                return move  # 无堵 = 赢
            self.board[my][mx] = EMPTY
            self._toggle(mx, my, player)
        return None

    def vct_search(self, player: int, depth: int) -> Optional[tuple]:
        """VCT: Victory by Continuous Three+Four"""
        if depth <= 0:
            return None
        # 先试 VCF
        vcf = self.vcf_search(player, depth * 2)
        if vcf:
            return vcf
        # 找活三威胁
        threes = self._find_threat_moves(player, 'three')
        for move in threes:
            mx, my = move
            self.board[my][mx] = player
            self._toggle(mx, my, player)
            result = self.vcf_search(player, depth * 2)
            self.board[my][mx] = EMPTY
            self._toggle(mx, my, player)
            if result:
                return move
        return None

    # ── Minimax + Alpha-Beta ──

    def minimax(self, depth: int, alpha: float, beta: float, is_max: bool) -> float:
        """带置换表的 alpha-beta 剪枝"""
        self.nodes_searched += 1

        # 时间检查 (每256节点检查一次，更灵敏)
        if self.nodes_searched % 256 == 0:
            if self.time_limit > 0 and (time.time() - self.start_time) > self.time_limit:
                return self.evaluate_board()

        # 置换表查询
        tt_key = self.zobrist_hash
        tt_entry = self.tt.get(tt_key)
        if tt_entry and tt_entry.depth >= depth:
            if tt_entry.flag == 0:
                return tt_entry.score
            if tt_entry.flag == 1 and tt_entry.score >= beta:
                return tt_entry.score
            if tt_entry.flag == -1 and tt_entry.score <= alpha:
                return tt_entry.score

        # 终局判断
        if self.check_win(AI):
            return SCORES['FIVE'] + depth
        if self.check_win(PLAYER):
            return -SCORES['FIVE'] - depth
        if depth == 0:
            return self.evaluate_board()

        cands = self.get_candidates(2)
        if not cands:
            return 0

        # 走法排序: TT move > killer > history
        tt_move = tt_entry.best_move if tt_entry else None
        k1 = self.killers[depth][0] if depth < len(self.killers) else None
        k2 = self.killers[depth][1] if depth < len(self.killers) else None

        def sort_key(m):
            mx, my = m
            s = self.history_table[my * N + mx]
            if tt_move and m == tt_move:
                s += 10_000_000
            if k1 and m == k1:
                s += 5_000_000
            if k2 and m == k2:
                s += 4_000_000
            return s

        cands.sort(key=sort_key, reverse=True)
        limit = min(len(cands), 20)
        orig_alpha = alpha
        best_move = None

        if is_max:
            val = float('-inf')
            for i in range(limit):
                mx, my = cands[i]
                self.board[my][mx] = AI
                self._toggle(mx, my, AI)
                s = self.minimax(depth - 1, alpha, beta, False)
                self.board[my][mx] = EMPTY
                self._toggle(mx, my, AI)
                if s > val:
                    val = s
                    best_move = (mx, my)
                alpha = max(alpha, s)
                if beta <= alpha:
                    self.history_table[my * N + mx] += depth * depth
                    if depth < len(self.killers):
                        if self.killers[depth][0] != (mx, my):
                            self.killers[depth][1] = self.killers[depth][0]
                            self.killers[depth][0] = (mx, my)
                    break
            flag = 1 if val >= beta else (-1 if val <= orig_alpha else 0)
            self.tt[tt_key] = TTEntry(depth, val, flag, best_move)
            return val
        else:
            val = float('inf')
            for i in range(limit):
                mx, my = cands[i]
                self.board[my][mx] = PLAYER
                self._toggle(mx, my, PLAYER)
                s = self.minimax(depth - 1, alpha, beta, True)
                self.board[my][mx] = EMPTY
                self._toggle(mx, my, PLAYER)
                if s < val:
                    val = s
                    best_move = (mx, my)
                beta = min(beta, s)
                if beta <= alpha:
                    self.history_table[my * N + mx] += depth * depth
                    if depth < len(self.killers):
                        if self.killers[depth][0] != (mx, my):
                            self.killers[depth][1] = self.killers[depth][0]
                            self.killers[depth][0] = (mx, my)
                    break
            flag = -1 if val <= orig_alpha else (1 if val >= beta else 0)
            self.tt[tt_key] = TTEntry(depth, val, flag, best_move)
            return val

    # ── 迭代加深 ──

    def iterative_deepening(self, time_limit: float) -> tuple:
        """迭代加深搜索，在时间限制内尽可能搜索更深

        关键: 只有当整层搜索全部完成时才更新 best_move，
        超时层的结果丢弃，使用上一层的完成结果。
        """
        cands = self.get_candidates(2)
        if not cands:
            return self._get_center_move()

        # 快速必胜/必堵
        win = self.find_critical_move(AI)
        if win:
            return win
        block = self.find_critical_move(PLAYER)
        if block:
            return block

        # 按快速评分排序
        cands.sort(key=lambda m: self._quick_score(m[0], m[1]), reverse=True)
        limit = min(len(cands), 15)
        best_move = cands[0]  # 默认: 快速评分最高的候选
        self.start_time = time.time()
        self.time_limit = time_limit

        for d in range(1, 30):
            # 深度开始前检查时间 (留 20% 余量)
            if time.time() - self.start_time > time_limit * 0.8:
                break
            best = float('-inf')
            dm = None
            completed = True
            for i in range(limit):
                # 每个候选前检查时间 (留 10% 余量)
                if time.time() - self.start_time > time_limit * 0.9:
                    completed = False
                    break
                mx, my = cands[i]
                self.board[my][mx] = AI
                self._toggle(mx, my, AI)
                s = self.minimax(d, float('-inf'), float('inf'), False)
                self.board[my][mx] = EMPTY
                self._toggle(mx, my, AI)
                if s > best:
                    best = s
                    dm = (mx, my)
            # 只有整层完成才更新结果
            if completed and dm is not None:
                best_move = dm
            if best >= SCORES['FIVE']:
                break
        return best_move

    def _get_center_move(self) -> tuple:
        """中心点开局"""
        if self.board[7][7] == EMPTY:
            return (7, 7)
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = 7 + dx, 7 + dy
                if 0 <= nx < N and 0 <= ny < N and not self.board[ny][nx]:
                    return (nx, ny)
        return (7, 7)

    # ── 开局策略 ──

    def get_opening_move(self, move_count: int) -> Optional[tuple]:
        """开局走法（前 3 步）"""
        center = 7
        if move_count == 0:
            return (center, center)
        if move_count == 1:
            if self.board[center][center] == EMPTY:
                return (center, center)
            for dx, dy in [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]:
                nx, ny = center + dx, center + dy
                if 0 <= nx < N and 0 <= ny < N and not self.board[ny][nx]:
                    return (nx, ny)
        if move_count == 2:
            around = [(0, 1), (1, 0), (1, 1), (-1, 1), (0, -1), (-1, 0), (-1, -1), (1, -1)]
            best, best_score = None, -1
            for dx, dy in around:
                nx, ny = center + dx, center + dy
                if 0 <= nx < N and 0 <= ny < N and not self.board[ny][nx]:
                    s = 0
                    for ddx, ddy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
                        cnt, opn = self.scan_line(nx, ny, ddx, ddy, AI)
                        s += cnt * 2 + opn
                    if s > best_score:
                        best_score = s
                        best = (nx, ny)
            if best:
                return best
        return None

    # ── AI 走法调度 ──

    def get_move(self, difficulty: int, move_count: int = 0) -> dict:
        """根据难度返回 AI 走法

        difficulty: 3-6
        返回: {'x': int, 'y': int, 'score': float, 'thinking_time': float, 'nodes': int}
        """
        self.nodes_searched = 0
        self.tt.clear()
        self.history_table = [0] * (N * N)
        self.killers = [[None, None] for _ in range(64)]
        start = time.time()

        # 开局
        if move_count <= 2:
            opening = self.get_opening_move(move_count)
            if opening:
                elapsed = time.time() - start
                return {
                    'x': opening[0], 'y': opening[1],
                    'score': 0, 'thinking_time': elapsed,
                    'nodes': 0, 'depth': 0
                }

        # 快速必胜/必堵
        critical = self.find_critical_move(AI)
        if critical:
            elapsed = time.time() - start
            return {
                'x': critical[0], 'y': critical[1],
                'score': SCORES['FIVE'],
                'thinking_time': elapsed, 'nodes': 0, 'depth': 0
            }
        critical = self.find_critical_move(PLAYER)
        if critical:
            elapsed = time.time() - start
            return {
                'x': critical[0], 'y': critical[1],
                'score': -SCORES['FIVE'],
                'thinking_time': elapsed, 'nodes': 0, 'depth': 0
            }

        move = None
        search_depth = 0

        if difficulty == 3:
            # LV.3: Minimax depth 2 (速度优先, depth 3 在 Python 中太慢)
            search_depth = 2
            cands = self.get_candidates(2)
            if cands:
                cands.sort(key=lambda m: self._quick_score(m[0], m[1]), reverse=True)
                limit = min(len(cands), 20)
                best = float('-inf')
                for i in range(limit):
                    mx, my = cands[i]
                    self.board[my][mx] = AI
                    self._toggle(mx, my, AI)
                    s = self.minimax(2, float('-inf'), float('inf'), False)
                    self.board[my][mx] = EMPTY
                    self._toggle(mx, my, AI)
                    if s > best:
                        best = s
                        move = (mx, my)

        elif difficulty == 4:
            # LV.4: Alpha-beta depth 4
            search_depth = 4
            cands = self.get_candidates(2)
            if cands:
                cands.sort(key=lambda m: self._quick_score(m[0], m[1]), reverse=True)
                limit = min(len(cands), 15)
                best = float('-inf')
                for i in range(limit):
                    mx, my = cands[i]
                    self.board[my][mx] = AI
                    self._toggle(mx, my, AI)
                    s = self.minimax(4, float('-inf'), float('inf'), False)
                    self.board[my][mx] = EMPTY
                    self._toggle(mx, my, AI)
                    if s > best:
                        best = s
                        move = (mx, my)

        elif difficulty == 5:
            # LV.5: Iterative deepening 2s
            search_depth = 5
            move = self.iterative_deepening(2.0)

        elif difficulty == 6:
            # LV.6: VCF + iterative deepening 3s
            search_depth = 6
            vcf = self.vcf_search(AI, 30)
            if vcf:
                move = vcf
            else:
                move = self.iterative_deepening(3.0)

        if not move:
            move = self._get_center_move()

        elapsed = time.time() - start
        return {
            'x': move[0], 'y': move[1],
            'score': 0,
            'thinking_time': round(elapsed, 3),
            'nodes': self.nodes_searched,
            'depth': search_depth
        }


def get_gomoku_move(board: list, difficulty: int, move_count: int = 0) -> dict:
    """便捷函数：获取 AI 走法"""
    ai = GomokuAI()
    ai.set_board(board)
    return ai.get_move(difficulty, move_count)
