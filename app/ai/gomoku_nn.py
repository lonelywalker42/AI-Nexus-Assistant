"""五子棋神经网络 + MCTS (LV.7)

AlphaZero 风格的神经网络蒙特卡洛树搜索。
- 神经网络: 输入棋盘状态, 输出 policy (走法概率) + value (局面评估)
- MCTS: 使用神经网络引导搜索, PUCT 选择公式
- 推理: 使用 ONNX Runtime (轻量级, 无需 PyTorch)

模型文件: data/gomoku_model.onnx
"""

import os
import math
import time
import numpy as np
from typing import Optional, Tuple

# ── 常量 ──
N = 15
EMPTY = 0
PLAYER = 1
AI = 2
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

# MCTS 参数
C_PUCT = 1.5          # 探索常数
NUM_SIMULATIONS = 400  # 每次走法的模拟次数
DIRICHLET_ALPHA = 0.3  # 根节点噪声参数
DIRICHLET_EPS = 0.25   # 噪声权重
TEMPERATURE = 1.0      # 温度参数 (训练时高, 对弈时低)

# 模型路径（兼容 PyInstaller 打包和开发模式）
def _get_model_path():
    try:
        from app.utils.paths import get_data_dir
        return str(get_data_dir() / 'gomoku_model.onnx')
    except Exception:
        return os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'gomoku_model.onnx')

MODEL_PATH = _get_model_path()


class MCTSNode:
    """MCTS 节点"""
    __slots__ = ['parent', 'move', 'children', 'N', 'W', 'Q', 'P', 'is_expanded',
                 'player', 'board_hash']

    def __init__(self, parent=None, move=None, prior=0.0, player=AI):
        self.parent = parent
        self.move = move  # (x, y) 走法
        self.children = {}  # move -> MCTSNode
        self.N = 0  # 访问次数
        self.W = 0.0  # 总价值
        self.Q = 0.0  # 平均价值 (W/N)
        self.P = prior  # 先验概率
        self.is_expanded = False
        self.player = player
        self.board_hash = None

    def select_child(self) -> Tuple['MCTSNode', tuple]:
        """PUCT 选择: 选择 UCB 最大的子节点"""
        best_score = float('-inf')
        best_child = None
        sqrt_parent = math.sqrt(max(self.N, 1))

        for move, child in self.children.items():
            # PUCT 公式: Q + c_puct * P * sqrt(N_parent) / (1 + N_child)
            u = child.Q + C_PUCT * child.P * sqrt_parent / (1 + child.N)
            if u > best_score:
                best_score = u
                best_child = child

        return best_child, best_child.move if best_child else None

    def expand(self, policy: np.ndarray, player: int):
        """扩展节点, 用神经网络的 policy 作为先验概率"""
        self.is_expanded = True
        self.player = player
        next_player = 3 - player

        for y in range(N):
            for x in range(N):
                idx = y * N + x
                if policy[idx] > 0.001:  # 只扩展有意义的走法
                    move = (x, y)
                    self.children[move] = MCTSNode(
                        parent=self, move=move,
                        prior=policy[idx], player=next_player
                    )

    def backup(self, value: float):
        """回传价值"""
        self.N += 1
        self.W += value
        self.Q = self.W / self.N

        if self.parent:
            # 对手的价值取反
            self.parent.backup(-value)


class GomokuNN:
    """五子棋神经网络 + MCTS"""

    def __init__(self):
        self.model = None
        self.model_loaded = False
        self._try_load_model()

    def _try_load_model(self):
        """尝试加载 ONNX 模型"""
        try:
            import onnxruntime as ort
            if os.path.exists(MODEL_PATH):
                self.model = ort.InferenceSession(MODEL_PATH)
                self.model_loaded = True
                print(f"[gomoku_nn] 模型加载成功: {MODEL_PATH}")
            else:
                print(f"[gomoku_nn] 模型文件不存在: {MODEL_PATH}, 使用启发式评估")
        except ImportError:
            print("[gomoku_nn] onnxruntime 未安装, 使用启发式评估")
        except Exception as e:
            print(f"[gomoku_nn] 模型加载失败: {e}, 使用启发式评估")

    def board_to_features(self, board: list) -> np.ndarray:
        """将棋盘转换为 4×15×15 特征平面

        平面 0: 当前玩家的棋子
        平面 1: 对手的棋子
        平面 2: 当前玩家标记 (全 1 或全 0)
        平面 3: 合法位置标记
        """
        features = np.zeros((4, N, N), dtype=np.float32)
        for y in range(N):
            for x in range(N):
                if board[y][x] == AI:
                    features[0][y][x] = 1.0
                elif board[y][x] == PLAYER:
                    features[1][y][x] = 1.0
                if board[y][x] == EMPTY:
                    features[3][y][x] = 1.0
        # AI 视角: 当前玩家总是 AI
        features[2][:, :] = 1.0
        return features

    def predict(self, board: list) -> Tuple[np.ndarray, float]:
        """神经网络推理: 返回 (policy, value)

        policy: 15×15=225 维概率向量
        value: [-1, 1] 局面评估
        """
        if not self.model_loaded:
            return self._heuristic_predict(board)

        features = self.board_to_features(board)
        features = features.reshape(1, 4, N, N)  # batch dim

        try:
            inputs = {self.model.get_inputs()[0].name: features}
            policy_out, value_out = self.model.run(None, inputs)
            policy = policy_out[0]  # (225,)
            value = float(value_out[0][0])  # scalar

            # 将已落子位置的概率置零
            for y in range(N):
                for x in range(N):
                    if board[y][x] != EMPTY:
                        policy[y * N + x] = 0.0

            # 归一化
            total = policy.sum()
            if total > 0:
                policy /= total
            else:
                # 所有合法位置等概率
                for y in range(N):
                    for x in range(N):
                        if board[y][x] == EMPTY:
                            policy[y * N + x] = 1.0
                policy /= policy.sum()

            return policy, value
        except Exception as e:
            print(f"[gomoku_nn] 推理失败: {e}")
            return self._heuristic_predict(board)

    def _heuristic_predict(self, board: list) -> Tuple[np.ndarray, float]:
        """启发式评估 (无模型时的 fallback)"""
        policy = np.zeros(N * N, dtype=np.float32)
        value = 0.0

        # 简单的威胁评估
        for y in range(N):
            for x in range(N):
                if board[y][x] != EMPTY:
                    continue
                score = 0
                for dx, dy in DIRECTIONS:
                    for p in (AI, PLAYER):
                        cnt = 1
                        nx, ny = x + dx, y + dy
                        while 0 <= nx < N and 0 <= ny < N and board[ny][nx] == p:
                            cnt += 1
                            nx += dx
                            ny += dy
                        nx, ny = x - dx, y - dy
                        while 0 <= nx < N and 0 <= ny < N and board[ny][nx] == p:
                            cnt += 1
                            nx -= dx
                            ny -= dy
                        if cnt >= 5:
                            score += 100000 if p == AI else 80000
                        else:
                            score += (3 ** cnt) * (1.1 if p == AI else 1.0)
                policy[y * N + x] = score

        total = policy.sum()
        if total > 0:
            policy /= total
        else:
            for y in range(N):
                for x in range(N):
                    if board[y][x] == EMPTY:
                        policy[y * N + x] = 1.0
            policy /= policy.sum()

        return policy, value

    def check_win(self, board: list, player: int) -> bool:
        """检查是否获胜"""
        for y in range(N):
            for x in range(N):
                if board[y][x] != player:
                    continue
                for dx, dy in DIRECTIONS:
                    cnt = 0
                    nx, ny = x, y
                    while 0 <= nx < N and 0 <= ny < N and board[ny][nx] == player:
                        cnt += 1
                        nx += dx
                        ny += dy
                    if cnt >= 5:
                        return True
        return False

    def is_terminal(self, board: list) -> Tuple[bool, float]:
        """检查是否终局, 返回 (is_terminal, value)"""
        if self.check_win(board, AI):
            return True, 1.0
        if self.check_win(board, PLAYER):
            return True, -1.0
        # 检查是否平局
        for y in range(N):
            for x in range(N):
                if board[y][x] == EMPTY:
                    return False, 0.0
        return True, 0.0

    def mcts_search(self, board: list, num_simulations: int = NUM_SIMULATIONS) -> Tuple[tuple, np.ndarray]:
        """MCTS 搜索

        返回: (best_move, policy)
        - best_move: 最佳走法 (x, y)
        - policy: 225 维访问概率向量
        """
        root = MCTSNode(player=AI)

        # 根节点扩展
        policy, value = self.predict(board)
        # 添加 Dirichlet 噪声 (探索)
        legal_mask = np.array([1.0 if board[y][x] == EMPTY else 0.0
                               for y in range(N) for x in range(N)])
        noise = np.random.dirichlet([DIRICHLET_ALPHA] * int(legal_mask.sum()))
        noise_idx = 0
        noisy_policy = policy.copy()
        for y in range(N):
            for x in range(N):
                if board[y][x] == EMPTY:
                    noisy_policy[y * N + x] = (
                        (1 - DIRICHLET_EPS) * policy[y * N + x] +
                        DIRICHLET_EPS * noise[noise_idx]
                    )
                    noise_idx += 1
        root.expand(noisy_policy, AI)

        for _ in range(num_simulations):
            node = root
            sim_board = [row[:] for row in board]
            path = [node]

            # 选择: 从根到叶
            while node.is_expanded and node.children:
                node, move = node.select_child()
                if move:
                    sim_board[move[1]][move[0]] = node.parent.player
                path.append(node)

            # 评估
            terminal, value = self.is_terminal(sim_board)
            if not terminal:
                # 神经网络评估
                policy, value = self.predict(sim_board)
                node.expand(policy, node.player)

            # 回传
            for n in reversed(path):
                n.backup(value)
                value = -value

        # 返回访问次数最多的走法和访问分布
        visit_counts = np.zeros(N * N, dtype=np.float32)
        for move, child in root.children.items():
            visit_counts[move[1] * N + move[0]] = child.N

        total_visits = visit_counts.sum()
        if total_visits > 0:
            policy = visit_counts / total_visits
        else:
            policy = np.zeros(N * N, dtype=np.float32)

        # 最佳走法: 访问次数最多
        best_idx = np.argmax(visit_counts)
        best_move = (best_idx % N, best_idx // N)

        return best_move, policy

    def get_move(self, board: list, move_count: int = 0) -> dict:
        """获取 MCTS 走法

        返回: {'x': int, 'y': int, 'score': float, 'thinking_time': float,
               'nodes': int, 'simulations': int}
        """
        start = time.time()

        # 开局
        if move_count == 0:
            return {'x': 7, 'y': 7, 'score': 0, 'thinking_time': 0,
                    'nodes': 0, 'simulations': 0, 'model_loaded': self.model_loaded}
        if move_count == 1:
            if board[7][7] == EMPTY:
                return {'x': 7, 'y': 7, 'score': 0, 'thinking_time': 0,
                        'nodes': 0, 'simulations': 0, 'model_loaded': self.model_loaded}
            # 靠近中心
            for dx, dy in [(1, 1), (1, 0), (0, 1), (-1, 1)]:
                nx, ny = 7 + dx, 7 + dy
                if 0 <= nx < N and 0 <= ny < N and board[ny][nx] == EMPTY:
                    return {'x': nx, 'y': ny, 'score': 0, 'thinking_time': 0,
                            'nodes': 0, 'simulations': 0, 'model_loaded': self.model_loaded}

        # 快速必胜/必堵
        for p in (AI, PLAYER):
            for y in range(N):
                for x in range(N):
                    if board[y][x]:
                        continue
                    board[y][x] = p
                    win = self.check_win(board, p)
                    board[y][x] = EMPTY
                    if win:
                        elapsed = time.time() - start
                        return {'x': x, 'y': y, 'score': 10000000 if p == AI else -10000000,
                                'thinking_time': elapsed, 'nodes': 0, 'simulations': 0,
                                'model_loaded': self.model_loaded}

        # MCTS 搜索
        # 根据模型是否加载调整模拟次数
        sims = NUM_SIMULATIONS if self.model_loaded else 200
        best_move, policy = self.mcts_search(board, sims)

        elapsed = time.time() - start
        return {
            'x': best_move[0], 'y': best_move[1],
            'score': 0,
            'thinking_time': round(elapsed, 3),
            'nodes': 0,
            'simulations': sims,
            'model_loaded': self.model_loaded
        }


# ── 单例 ──
_nn_instance = None


def get_nn_move(board: list, move_count: int = 0) -> dict:
    """便捷函数: 获取神经网络 + MCTS 走法"""
    global _nn_instance
    if _nn_instance is None:
        _nn_instance = GomokuNN()
    return _nn_instance.get_move(board, move_count)
