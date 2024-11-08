# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import TheSeedCore as TSC

if TYPE_CHECKING:
    pass
task_total_count = 0
execution_count = 10


async def shutdown_system():
    for i in range(10):
        await asyncio.sleep(1)
        print("System shutdown countdown:", 10 - i)
    print("System shutdown")
    TSC.LinkStop()


async def example_function(start_time: float):
    current_time = time.time()
    await asyncio.sleep(2)
    execution_time = time.time() - current_time
    return start_time, current_time - start_time, execution_time


async def example_function_callback(result: tuple[float, float, float]):
    callback_time = time.time() - result[0]
    arrival_time = result[1]
    execution_time = result[2]
    global task_total_count, execution_count
    task_total_count += 1
    print(f"Task{task_total_count}. Callback time: {callback_time:.3f}, Arrival time: {arrival_time:.3f}, Execution time: {execution_time:.3f}")
    if task_total_count == execution_count:
        print("All example functions have been completed.")
        await shutdown_system()


async def countdown():
    for i in range(2):
        await asyncio.sleep(1)
        print(f"The example will complete in {2 - i} seconds.")
    print("Example completed")


async def main_function():
    global execution_count
    start_time = time.time()
    print("Start example function")
    for i in range(execution_count):
        TSC.submitThreadTask(example_function, callback=example_function_callback, start_time=start_time)


if __name__ == "__main__":
    TSC.ConnectTheSeedCore(check_env=False, MainPriority=TSC.Priority.HIGH, CoreProcessCount=4, ExpandPolicy=TSC.ExpandPolicy.AutoExpand, ShrinkagePolicy=TSC.ShrinkagePolicy.AutoShrink, PerformanceReport=True)
    TSC.MainEventLoop().create_task(main_function())
    TSC.MainEventLoop().create_task(countdown())
    TSC.LinkStart()
