# -*- coding: utf-8 -*-
from __future__ import annotations

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
    matrix_power_result = [[1, 0], [0, 1]]  # Identity matrix
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


def syncCpuBoundTaskExample():
    time.sleep(1)  # 减少等待时间以平衡计算时间
    task_result = fib(30000)  # 使用矩阵快速幂计算 Fibonacci 数值
    return task_result


def syncIoBoundTaskExample():
    # 模拟IO密集型任务，例如读写文件
    # 这里用sleep来模拟等待IO操作
    time.sleep(0.1)  # 模拟IO延迟
    return "IO task completed"


async def asyncCpuBoundTaskExample():
    await asyncio.sleep(0.1)  # 减少等待时间以平衡计算时间
    task_result = fib(10000)  # 使用矩阵快速幂计算 Fibonacci 数值
    return task_result


async def asyncIoBoundTaskExample():
    # 模拟IO密集型任务，例如读写文件
    # 这里用sleep来模拟等待IO操作
    await asyncio.sleep(0.1)  # 模拟IO延迟
    return "IO task completed"


def callback(r):
    print(r)


class Test:
    def __init__(self):
        TheSeed.submitProcessTask(asyncCpuBoundTaskExample, Callback=callback)


if __name__ == "__main__":
    linkStart(Test, debug_mode=False)
