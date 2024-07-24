# -*- coding: utf-8 -*-
from __future__ import annotations

from torch import nn

from TheSeedCore import *

if TYPE_CHECKING:
    pass


def memoryUsagePsutil():
    # 返回以MB为单位的内存使用
    process = psutil.Process()
    mem = process.memory_info().rss / float(2 ** 20)
    return mem


# 矩阵乘法
def matrixMultiply(F, M):
    x = F[0][0] * M[0][0] + F[0][1] * M[1][0]
    y = F[0][0] * M[0][1] + F[0][1] * M[1][1]
    z = F[1][0] * M[0][0] + F[1][1] * M[1][0]
    w = F[1][0] * M[0][1] + F[1][1] * M[1][1]
    return [[x, y], [z, w]]


# 矩阵快速幂
def matrixPower(F, n):
    matrix_power_result = [[1, 0], [0, 1]]
    while n > 0:
        if n % 2 == 1:
            matrix_power_result = matrixMultiply(matrix_power_result, F)
        F = matrixMultiply(F, F)
        n //= 2
    return matrix_power_result


# 使用矩阵快速幂计算 Fibonacci 数值
def fib(n):
    if n == 0:
        return 0
    F = [[1, 1], [1, 0]]
    F = matrixPower(F, n - 1)
    return F[0][0]


class SimpleNN(nn.Module):
    def __init__(self):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(20000, 500)
        self.fc2 = nn.Linear(500, 10)

    def forward(self, x):
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)
        return x


# 示例同步GPU加速任务
def syncTensorGpuBoostExample():
    """同步GPU加速任务，处理已经迁移到GPU的张量并返回加倍后的结果。"""
    tensor = torch.rand(10000, 10000).cuda()
    start_time = time.time()
    processed_tensors = [tensor * 2 for tensor in tensor]  # 在GPU上进行计算
    end_time = time.time()
    time.sleep(1)  # 模拟同步处理延迟
    pid = os.getpid()
    return f'{pid} - {float(f"{end_time - start_time:.2f}")}'


# 示例同步GPU加速任务
def syncNNGpuBoostExample():
    """同步GPU加速任务，处理已经迁移到GPU的张量并返回神经网络的输出。"""
    module = SimpleNN().cuda()
    tensor = torch.rand(100, 20000).cuda()
    start_time = time.time()
    with torch.no_grad():
        output = module.forward(tensor)
    end_time = time.time()
    time.sleep(1)  # 模拟同步处理延迟
    return float(f"{end_time - start_time:.4f}")


# 示例异步GPU加速任务
async def asyncTensorGpuBoostExample():
    """异步GPU加速任务，处理已经迁移到GPU的张量并返回加倍后的结果。"""
    tensor = torch.rand(1000, 1000).cuda()
    start_time = time.time()
    processed_tensors = [tensor * 2 for tensor in tensor]  # 在GPU上进行计算
    end_time = time.time()
    await asyncio.sleep(1)  # 模拟异步处理延迟
    return float(f"{end_time - start_time:.4f}")


# 示例异步GPU加速任务
async def asyncNNGpuBoostExample():
    """异步GPU加速任务，处理已经迁移到GPU的张量并返回加倍后的结果。"""
    module = SimpleNN().cuda()
    tensor = torch.rand(100, 20000).cuda()
    start_time = time.time()
    with torch.no_grad():
        output = module.forward(tensor)
    end_time = time.time()
    await asyncio.sleep(1)  # 模拟异步处理延迟
    return float(f"{end_time - start_time:.4f}")


# 示例同步CPU密集型任务
def syncCpuBoundTaskExample():
    start_time = time.time()
    task_result1 = fib(2500000)  # 使用矩阵快速幂计算 Fibonacci 数值
    end_time = time.time()
    return float(f"{end_time - start_time:.2f}")


# 示例同步IO密集型任务
def syncIoBoundTaskExample():
    # 模拟IO密集型任务，例如读写文件
    time.sleep(0.1)  # 这里用sleep来模拟等待IO操作
    return "IO task completed"


# 示例异步CPU密集型任务
async def asyncCpuBoundTaskExample():
    start_time = time.time()
    task_result = fib(2500000)  # 使用矩阵快速幂计算 Fibonacci 数值
    end_time = time.time()
    return float(f"{end_time - start_time:.2f}")


# 示例异步IO密集型任务
async def asyncIoBoundTaskExample():
    # 模拟IO密集型任务，例如读写文件
    await asyncio.sleep(0.1)  # 这里用sleep来模拟等待IO操作
    return "IO task completed"


def callback(r):
    pid = os.getpid()
    print(f"{pid} - {r}")


class Test:
    def __init__(self):
        for i in range(8):
            TheSeed.submitProcessTask(syncCpuBoundTaskExample, Callback=callback, GpuBoost=False)


if __name__ == "__main__":
    config = ConcurrencySystemConfig(False, 8, 6, 8, 12, 30, 120, "Abandonment", 3, "NoExpand", "NoShrink", 3)
    linkStart(Test, concurrency_system_config=config, debug_mode=False)
