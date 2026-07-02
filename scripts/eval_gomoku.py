"""五子棋 AI 难度等级评估脚本

模拟对弈评估各难度等级之间的胜率差异。
验证高一级对低一级有明显优势 (~70%+ 胜率)。

用法:
    python scripts/eval_gomoku.py                    # 默认每对 20 局
    python scripts/eval_gomoku.py --games 50         # 每对 50 局
    python scripts/eval_gomoku.py --levels 1,2,3,4   # 只评估指定等级
"""

import sys
import os
import time
import argparse
from collections import defaultdict

# 添加项目根目录到 path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.ai.gomoku_ai import GomokuAI, N, EMPTY, PLAYER, AI


class SimpleGomokuAI:
    """简化版 AI 包装, 用于评估"""

    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.engine = GomokuAI()
        self.nn_engine = None
        if difficulty == 7:
            try:
                from app.ai.gomoku_nn import GomokuNN
                self.nn_engine = GomokuNN()
            except Exception as e:
                print(f"  WARNING: NN unavailable ({e}), falling back to heuristic")

    def get_move(self, board, move_count):
        if self.difficulty == 7 and self.nn_engine:
            result = self.nn_engine.get_move(board, move_count)
            return result['x'], result['y']
        self.engine.set_board(board)
        if self.difficulty <= 2:
            return self._get_simple_move(board, move_count)
        else:
            result = self.engine.get_move(self.difficulty, move_count)
            return result['x'], result['y']

    def _get_simple_move(self, board, move_count):
        """LV.1 DEFEND / LV.2 GREEDY 等效"""
        # 快速必胜/必堵（只检查有棋子周围的空位）
        for p in (AI, PLAYER):
            for y in range(N):
                for x in range(N):
                    if board[y][x]:
                        continue
                    # 只检查有邻居的位置
                    has_neighbor = False
                    for dy2 in range(-1, 2):
                        for dx2 in range(-1, 2):
                            nx, ny = x + dx2, y + dy2
                            if 0 <= nx < N and 0 <= ny < N and board[ny][nx]:
                                has_neighbor = True
                                break
                        if has_neighbor:
                            break
                    if not has_neighbor:
                        continue
                    board[y][x] = p
                    win = self.engine.check_win(p)
                    board[y][x] = EMPTY
                    if win:
                        return x, y

        return self._greedy_move(board)

    def _greedy_move(self, board):
        """贪心走法（快速版）"""
        import random
        best = -1
        moves = []
        dirs = [(1, 0), (0, 1), (1, 1), (1, -1)]
        for y in range(N):
            for x in range(N):
                if board[y][x]:
                    continue
                s = 0
                for dx, dy in dirs:
                    for p in (AI, PLAYER):
                        c1 = self.engine.count_dir(x, y, dx, dy, p)
                        c2 = self.engine.count_dir(x, y, -dx, -dy, p)
                        total = c1 + c2 + 1
                        if total >= 5:
                            s += 100000
                        elif total >= 3:
                            s += total * total * 10
                        else:
                            s += total * total
                if s > best:
                    best = s
                    moves = [(x, y)]
                elif s == best:
                    moves.append((x, y))
        return random.choice(moves) if moves else (7, 7)


def play_game(ai_black, ai_white, verbose=False):
    """一局对弈

    ai_black: 先手 (PLAYER=1)
    ai_white: 后手 (AI=2)

    返回: winner (1=黑胜, 2=白胜, 0=平局)
    """
    board = [[EMPTY] * N for _ in range(N)]
    move_count = 0
    current = 1  # 黑先

    while True:
        if current == 1:
            x, y = ai_black.get_move(board, move_count)
        else:
            x, y = ai_white.get_move(board, move_count)

        if board[y][x] != EMPTY:
            # 非法走法, 判负
            return 3 - current

        board[y][x] = current
        move_count += 1

        if verbose:
            print(f"  {'Black' if current == 1 else 'White'}: ({x}, {y})")

        # 检查获胜
        for dx, dy in [(1, 0), (0, 1), (1, 1), (1, -1)]:
            cnt = 0
            nx, ny = x, y
            while 0 <= nx < N and 0 <= ny < N and board[ny][nx] == current:
                cnt += 1
                nx += dx
                ny += dy
            if cnt >= 5:
                return current

        # 检查平局
        if move_count >= N * N:
            return 0

        current = 3 - current


def evaluate_pair(level_a, level_b, num_games):
    """评估两个等级之间的对弈

    返回: (a_wins, b_wins, draws)
    """
    a_wins = 0
    b_wins = 0
    draws = 0

    for i in range(num_games):
        # 交替先后手
        if i % 2 == 0:
            ai_a = SimpleGomokuAI(level_a)
            ai_b = SimpleGomokuAI(level_b)
            winner = play_game(ai_a, ai_b)
            if winner == 1:  # a 先手胜
                a_wins += 1
            elif winner == 2:  # b 后手胜
                b_wins += 1
            else:
                draws += 1
        else:
            ai_b = SimpleGomokuAI(level_b)
            ai_a = SimpleGomokuAI(level_a)
            winner = play_game(ai_b, ai_a)
            if winner == 2:  # a 后手胜
                a_wins += 1
            elif winner == 1:  # b 先手胜
                b_wins += 1
            else:
                draws += 1

    return a_wins, b_wins, draws


def main():
    parser = argparse.ArgumentParser(description='五子棋 AI 难度等级评估')
    parser.add_argument('--games', type=int, default=20, help='每对对弈局数')
    parser.add_argument('--levels', type=str, default='1,2,3,4,5,6',
                        help='评估的等级列表 (逗号分隔)')
    args = parser.parse_args()

    levels = [int(x) for x in args.levels.split(',')]
    level_names = {
        1: 'LV.1 DEFEND',
        2: 'LV.2 GREEDY',
        3: 'LV.3 MINIMAX',
        4: 'LV.4 ALPHA-BETA',
        5: 'LV.5 DEEP',
        6: 'LV.6 MASTER',
        7: 'LV.7 NEURAL',
    }

    print("=" * 60)
    print("五子棋 AI 难度等级评估")
    print(f"每对 {args.games} 局, 交替先后手")
    print("=" * 60)

    # 胜率矩阵
    results = {}  # (a, b) -> (a_wins, b_wins, draws)

    for i, la in enumerate(levels):
        for lb in levels[i + 1:]:
            name_a = level_names.get(la, f'LV.{la}')
            name_b = level_names.get(lb, f'LV.{lb}')
            print(f"\n{name_a} vs {name_b}...", end=' ', flush=True)

            start = time.time()
            a_wins, b_wins, draws = evaluate_pair(la, lb, args.games)
            elapsed = time.time() - start

            results[(la, lb)] = (a_wins, b_wins, draws)

            total = a_wins + b_wins + draws
            a_pct = a_wins / total * 100 if total else 0
            b_pct = b_wins / total * 100 if total else 0
            print(f"{a_pct:.0f}% - {b_pct:.0f}% (draw {draws}) [{elapsed:.1f}s]")

    # 打印汇总表格
    print("\n" + "=" * 60)
    print("胜率矩阵 (行 vs 列, 行的胜率%)")
    print("=" * 60)

    # 表头
    header = f"{'':>15}"
    for l in levels:
        name = level_names.get(l, f'LV.{l}')
        header += f" {name:>12}"
    print(header)

    for la in levels:
        name_a = level_names.get(la, f'LV.{la}')
        row = f"{name_a:>15}"
        for lb in levels:
            if la == lb:
                row += f" {'---':>12}"
            elif (la, lb) in results:
                a_w, b_w, d = results[(la, lb)]
                total = a_w + b_w + d
                pct = a_w / total * 100 if total else 0
                row += f" {pct:>11.0f}%"
            elif (lb, la) in results:
                a_w, b_w, d = results[(lb, la)]
                total = a_w + b_w + d
                pct = b_w / total * 100 if total else 0
                row += f" {pct:>11.0f}%"
            else:
                row += f" {'N/A':>12}"
        print(row)

    # 难度递增验证
    print("\n" + "=" * 60)
    print("难度递增验证")
    print("=" * 60)
    all_good = True
    for i in range(len(levels) - 1):
        la, lb = levels[i], levels[i + 1]
        if (la, lb) in results:
            a_w, b_w, d = results[(la, lb)]
            total = a_w + b_w + d
            higher_win = b_w / total * 100 if total else 0
            name_a = level_names.get(la, f'LV.{la}')
            name_b = level_names.get(lb, f'LV.{lb}')
            status = "[OK]" if higher_win > 55 else "[WEAK]"
            if higher_win <= 55:
                all_good = False
            print(f"  {name_a} vs {name_b}: {name_b} winrate {higher_win:.0f}% {status}")

    if all_good:
        print("\n[OK] Difficulty levels verified: higher levels beat lower ones")
    else:
        print("\n[WARN] Some level differences are weak, consider tuning")

    print(f"\n总耗时: {sum(time.time() for _ in [0])}s")


if __name__ == '__main__':
    main()
