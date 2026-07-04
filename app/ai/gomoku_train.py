"""五子棋神经网络自我对弈训练脚本

使用 PyTorch 训练 AlphaZero 风格的策略-价值网络。
训练完成后导出 ONNX 模型供推理使用。

用法:
    pip install torch onnxruntime
    python -m app.ai.gomoku_train --iterations 50 --games-per-iter 100

架构 (v2):
    - 6 ResNet blocks × 128 channels (~1.2M 参数)
    - 4 输入特征平面 (己方/对方/玩家标记/合法位置)
    - Policy head: 225 维走法概率
    - Value head: [-1,1] 局面评估

训练流程:
    1. 初始化随机模型
    2. 自我对弈生成训练数据 (MCTS 200 模拟, 温度前15步1.0/之后0.5)
    3. 用训练数据优化模型 (5 epochs, Adam + StepLR)
    4. 重复 2-3 直到收敛
    5. 导出 ONNX 模型到 data/gomoku_model.onnx

预期训练时间与棋力:
    - 500 games (5 iter):  入门级, ~Elo 800  (约 1-2 小时)
    - 2000 games (20 iter): 业余级, ~Elo 1200 (约 4-8 小时)
    - 5000 games (50 iter): 中级,   ~Elo 1500 (约 12-24 小时)
    推理时使用 400 MCTS 模拟, 比训练时的 200 更强。
    参考: junxiaosong/AlphaZero_Gomoku (6×6 board, 500-1000 games 收敛)
"""

import os
import sys
import time
import math
import random
import argparse
import numpy as np
from collections import deque
from typing import List, Tuple

# ── 常量 ──
N = 15
EMPTY = 0
PLAYER = 1
AI = 2
DIRECTIONS = [(1, 0), (0, 1), (1, 1), (1, -1)]

# ── 设备检测 ──
def _get_device():
    try:
        import torch
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    except ImportError:
        return 'cpu'

DEVICE = _get_device()

# 模型路径（兼容 PyInstaller 打包和开发模式）
def _get_paths():
    try:
        from app.utils.paths import get_data_dir
        data_dir = str(get_data_dir())
    except Exception:
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
    return data_dir

_DATA_DIR = _get_paths()
MODEL_PATH = os.path.join(_DATA_DIR, 'gomoku_model.onnx')
CHECKPOINT_DIR = os.path.join(_DATA_DIR, 'gomoku_checkpoints')

# ── PyTorch 模型定义 ──

def get_model():
    """获取 PyTorch 模型"""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class ResBlock(nn.Module):
        """残差块"""
        def __init__(self, channels=64):
            super().__init__()
            self.conv1 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
            self.bn1 = nn.BatchNorm2d(channels)
            self.conv2 = nn.Conv2d(channels, channels, 3, padding=1, bias=False)
            self.bn2 = nn.BatchNorm2d(channels)

        def forward(self, x):
            residual = x
            out = F.relu(self.bn1(self.conv1(x)))
            out = self.bn2(self.conv2(out))
            out += residual
            return F.relu(out)

    class GomokuNet(nn.Module):
        """策略-价值网络

        输入: (batch, 4, 15, 15) 特征平面
        输出: policy (batch, 225) + value (batch, 1)

        架构: 6 ResNet blocks × 128 channels (~1.2M 参数)
        参考: junxiaosong/AlphaZero_Gomoku (3 blocks × 64 ch),
              initial-h/AlphaZero_Gomoku_MPI (19 blocks, Gomocup top 30)
        """
        def __init__(self, num_res_blocks=6, channels=128):
            super().__init__()
            # 初始卷积
            self.conv_input = nn.Conv2d(4, channels, 3, padding=1, bias=False)
            self.bn_input = nn.BatchNorm2d(channels)
            # 残差层
            self.res_blocks = nn.ModuleList([ResBlock(channels) for _ in range(num_res_blocks)])
            # Policy head
            self.policy_conv = nn.Conv2d(channels, 4, 1, bias=False)
            self.policy_bn = nn.BatchNorm2d(4)
            self.policy_fc = nn.Linear(4 * N * N, N * N)
            # Value head
            self.value_conv = nn.Conv2d(channels, 2, 1, bias=False)
            self.value_bn = nn.BatchNorm2d(2)
            self.value_fc1 = nn.Linear(2 * N * N, 128)
            self.value_fc2 = nn.Linear(128, 1)

        def forward(self, x):
            # 初始层
            x = F.relu(self.bn_input(self.conv_input(x)))
            # 残差层
            for block in self.res_blocks:
                x = block(x)
            # Policy head
            p = F.relu(self.policy_bn(self.policy_conv(x)))
            p = p.view(p.size(0), -1)
            p = self.policy_fc(p)
            p = F.log_softmax(p, dim=1)
            # Value head
            v = F.relu(self.value_bn(self.value_conv(x)))
            v = v.view(v.size(0), -1)
            v = F.relu(self.value_fc1(v))
            v = torch.tanh(self.value_fc2(v))
            return p, v

    return GomokuNet()


# ── 棋盘工具函数 ──

def check_win(board, player):
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


def is_terminal(board):
    """检查终局, 返回 (is_over, winner)"""
    if check_win(board, AI):
        return True, AI
    if check_win(board, PLAYER):
        return True, PLAYER
    for y in range(N):
        for x in range(N):
            if board[y][x] == EMPTY:
                return False, 0
    return True, 0  # 平局


def board_to_tensor(board, player=AI):
    """将棋盘转为 PyTorch tensor"""
    import torch
    features = np.zeros((4, N, N), dtype=np.float32)
    for y in range(N):
        for x in range(N):
            if board[y][x] == AI:
                features[0][y][x] = 1.0
            elif board[y][x] == PLAYER:
                features[1][y][x] = 1.0
            if board[y][x] == EMPTY:
                features[3][y][x] = 1.0
    features[2][:, :] = 1.0 if player == AI else 0.0
    return torch.FloatTensor(features).unsqueeze(0).to(DEVICE)


# ── MCTS (训练用, 简化版) ──

class MCTSNode:
    __slots__ = ['parent', 'move', 'children', 'N', 'W', 'Q', 'P', 'is_expanded', 'player']

    def __init__(self, parent=None, move=None, prior=0.0, player=AI):
        self.parent = parent
        self.move = move
        self.children = {}
        self.N = 0
        self.W = 0.0
        self.Q = 0.0
        self.P = prior
        self.is_expanded = False
        self.player = player

    def select_child(self):
        best_score = float('-inf')
        best_child = None
        sqrt_parent = math.sqrt(max(self.N, 1))
        for move, child in self.children.items():
            u = child.Q + 1.5 * child.P * sqrt_parent / (1 + child.N)
            if u > best_score:
                best_score = u
                best_child = child
        return best_child

    def expand(self, policy, player):
        self.is_expanded = True
        self.player = player
        next_player = 3 - player
        for i in range(N * N):
            if policy[i] > 0.001:
                move = (i % N, i // N)
                self.children[move] = MCTSNode(
                    parent=self, move=move,
                    prior=policy[i], player=next_player
                )

    def backup(self, value):
        self.N += 1
        self.W += value
        self.Q = self.W / self.N
        if self.parent:
            self.parent.backup(-value)


def mcts_self_play(model, board, num_sims=200, temperature=1.0):
    """MCTS 搜索, 返回 (move, policy)"""
    import torch

    root = MCTSNode(player=AI)

    # 根节点扩展
    with torch.no_grad():
        tensor = board_to_tensor(board)
        log_policy, value = model(tensor)
        policy = torch.exp(log_policy).squeeze().cpu().numpy()

    # 合法位置 mask
    for y in range(N):
        for x in range(N):
            if board[y][x] != EMPTY:
                policy[y * N + x] = 0.0
    total = policy.sum()
    if total > 0:
        policy /= total

    # Dirichlet 噪声
    legal_moves = [(x, y) for y in range(N) for x in range(N) if board[y][x] == EMPTY]
    if legal_moves:
        noise = np.random.dirichlet([0.3] * len(legal_moves))
        for i, (x, y) in enumerate(legal_moves):
            idx = y * N + x
            policy[idx] = 0.75 * policy[idx] + 0.25 * noise[i]
        total = policy.sum()
        if total > 0:
            policy /= total

    root.expand(policy, AI)

    for _ in range(num_sims):
        node = root
        sim_board = [row[:] for row in board]

        while node.is_expanded and node.children:
            node = node.select_child()
            if node.move:
                sim_board[node.move[1]][node.move[0]] = node.parent.player

        over, winner = is_terminal(sim_board)
        if over:
            if winner == AI:
                value = 1.0
            elif winner == PLAYER:
                value = -1.0
            else:
                value = 0.0
        else:
            with torch.no_grad():
                tensor = board_to_tensor(sim_board, node.player)
                log_policy, value = model(tensor)
                policy = torch.exp(log_policy).squeeze().cpu().numpy()
                value = value.item()
                for y in range(N):
                    for x in range(N):
                        if sim_board[y][x] != EMPTY:
                            policy[y * N + x] = 0.0
                total = policy.sum()
                if total > 0:
                    policy /= total
                node.expand(policy, node.player)

        node.backup(value)

    # 访问分布
    visit_counts = np.zeros(N * N, dtype=np.float32)
    for move, child in root.children.items():
        visit_counts[move[1] * N + move[0]] = child.N

    total = visit_counts.sum()
    if total > 0:
        if temperature < 0.01:
            # 贪心: 选择访问最多的
            policy = np.zeros(N * N, dtype=np.float32)
            best_idx = np.argmax(visit_counts)
            policy[best_idx] = 1.0
        else:
            # 温度采样
            policy = visit_counts ** (1.0 / temperature)
            policy /= policy.sum()
    else:
        policy = np.ones(N * N, dtype=np.float32) / (N * N)

    # 按概率采样走法
    legal_indices = [y * N + x for y in range(N) for x in range(N) if board[y][x] == EMPTY]
    legal_probs = np.array([policy[i] for i in legal_indices])
    total = legal_probs.sum()
    if total > 0:
        legal_probs /= total
    else:
        legal_probs = np.ones(len(legal_indices)) / len(legal_indices)

    chosen_idx = np.random.choice(len(legal_indices), p=legal_probs)
    move_x = legal_indices[chosen_idx] % N
    move_y = legal_indices[chosen_idx] // N

    return (move_x, move_y), policy


# ── 自我对弈 ──

def self_play_game(model, num_sims=200, temperature=1.0):
    """一局自我对弈, 返回训练数据 [(board_state, policy, value)]"""
    board = [[EMPTY] * N for _ in range(N)]
    data = []  # (features, policy, winner)
    move_count = 0
    current_player = PLAYER  # 玩家先手

    while True:
        # 温度: 前 15 步用 1.0 (探索), 之后用 0.5 (利用)
        temp = 1.0 if move_count < 15 else 0.5
        # MCTS 搜索
        move, policy = mcts_self_play(model, board, num_sims, temp)

        # 保存训练数据 (从当前玩家视角)
        features = np.zeros((4, N, N), dtype=np.float32)
        for y in range(N):
            for x in range(N):
                if board[y][x] == AI:
                    features[0][y][x] = 1.0
                elif board[y][x] == PLAYER:
                    features[1][y][x] = 1.0
                if board[y][x] == EMPTY:
                    features[3][y][x] = 1.0
        features[2][:, :] = 1.0 if current_player == AI else 0.0

        data.append((features, policy, current_player))

        # 落子
        board[move[1]][move[0]] = current_player
        move_count += 1

        # 检查终局
        over, winner = is_terminal(board)
        if over:
            # 计算每个状态的价值
            training_data = []
            for features, policy, player in data:
                if winner == 0:
                    value = 0.0
                elif player == winner:
                    value = 1.0
                else:
                    value = -1.0
                training_data.append((features, policy, value))
            return training_data

        current_player = 3 - current_player


# ── 训练 ──

def train_model(model, training_data, optimizer, batch_size=64):
    """用训练数据优化模型"""
    import torch
    import torch.nn.functional as F

    if len(training_data) < batch_size:
        return 0.0

    random.shuffle(training_data)
    total_loss = 0.0
    num_batches = 0

    for i in range(0, len(training_data), batch_size):
        batch = training_data[i:i + batch_size]
        if len(batch) < 2:
            continue

        features = torch.FloatTensor(np.stack([d[0] for d in batch])).to(DEVICE)
        target_policies = torch.FloatTensor(np.stack([d[1] for d in batch])).to(DEVICE)
        target_values = torch.FloatTensor(np.array([d[2] for d in batch])).unsqueeze(1).to(DEVICE)

        log_policies, values = model(features)

        # Policy loss: KL 散度
        policy_loss = -torch.sum(target_policies * log_policies) / len(batch)
        # Value loss: MSE
        value_loss = F.mse_loss(values, target_values)
        # L2 正则化
        l2_reg = sum(p.pow(2).sum() for p in model.parameters()) * 1e-4

        loss = policy_loss + value_loss + l2_reg

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        num_batches += 1

    return total_loss / max(num_batches, 1)


def export_onnx(model, path):
    """导出 ONNX 模型"""
    import torch

    model.eval()
    model_cpu = model.cpu()
    dummy = torch.randn(1, 4, N, N)
    torch.onnx.export(
        model_cpu, dummy, path,
        input_names=['input'],
        output_names=['policy', 'value'],
        dynamic_axes={'input': {0: 'batch'}, 'policy': {0: 'batch'}, 'value': {0: 'batch'}},
        opset_version=18,
        dynamo=False
    )
    model.to(DEVICE)  # 移回 GPU
    print(f"[train] ONNX 模型已导出: {path}")


# ── 主函数 ──

def main():
    parser = argparse.ArgumentParser(description='五子棋神经网络自我对弈训练')
    parser.add_argument('--iterations', type=int, default=50, help='训练迭代次数')
    parser.add_argument('--games-per-iter', type=int, default=100, help='每次迭代的自我对弈局数')
    parser.add_argument('--sims', type=int, default=200, help='MCTS 模拟次数')
    parser.add_argument('--lr', type=float, default=0.001, help='学习率')
    parser.add_argument('--resume', type=str, default=None, help='从检查点恢复')
    args = parser.parse_args()

    try:
        import torch
    except ImportError:
        print("[train] 请先安装 PyTorch: pip install torch")
        sys.exit(1)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    # 初始化模型
    model = get_model().to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=20, gamma=0.5)

    start_iter = 0
    if args.resume and os.path.exists(args.resume):
        checkpoint = torch.load(args.resume, weights_only=False, map_location=DEVICE)
        model.load_state_dict(checkpoint['model'])
        optimizer.load_state_dict(checkpoint['optimizer'])
        if 'scheduler' in checkpoint:
            scheduler.load_state_dict(checkpoint['scheduler'])
        start_iter = checkpoint.get('iteration', 0)
        print(f"[train] 从检查点恢复: iteration {start_iter}")

    # 训练数据缓冲区
    replay_buffer = deque(maxlen=50000)

    print(f"[train] 设备: {DEVICE}" + (f" ({torch.cuda.get_device_name(0)})" if DEVICE.type == 'cuda' else ""))
    print(f"[train] 开始训练: {args.iterations} 迭代, 每次 {args.games_per_iter} 局")
    print(f"[train] MCTS 模拟次数: {args.sims}")

    for iteration in range(start_iter, args.iterations):
        iter_start = time.time()

        # 阶段 1: 自我对弈生成数据
        print(f"\n[iter {iteration+1}/{args.iterations}] 自我对弈中...")
        game_count = 0
        for g in range(args.games_per_iter):
            data = self_play_game(model, args.sims)
            replay_buffer.extend(data)
            game_count += 1
            if (g + 1) % 10 == 0:
                print(f"  对弈 {g+1}/{args.games_per_iter} 局完成, "
                      f"缓冲区: {len(replay_buffer)} 条数据")

        # 阶段 2: 训练模型
        print(f"[iter {iteration+1}/{args.iterations}] 训练模型中...")
        train_data = list(replay_buffer)
        epochs = 5
        for epoch in range(epochs):
            loss = train_model(model, train_data, optimizer)
            print(f"  epoch {epoch+1}/{epochs}: loss = {loss:.4f}")

        # 学习率调度
        scheduler.step()

        # 保存检查点
        checkpoint_path = os.path.join(CHECKPOINT_DIR, f'checkpoint_{iteration+1}.pth')
        torch.save({
            'iteration': iteration + 1,
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'scheduler': scheduler.state_dict(),
        }, checkpoint_path)

        # 每 10 个迭代导出 ONNX
        if (iteration + 1) % 10 == 0 or iteration == args.iterations - 1:
            export_onnx(model, MODEL_PATH)

        elapsed = time.time() - iter_start
        print(f"[iter {iteration+1}/{args.iterations}] 完成, 耗时 {elapsed:.1f}s, "
              f"缓冲区: {len(replay_buffer)} 条")

    # 最终导出
    export_onnx(model, MODEL_PATH)
    print(f"\n[train] 训练完成! 模型: {MODEL_PATH}")


if __name__ == '__main__':
    main()
