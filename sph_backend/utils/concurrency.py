from asyncio import Semaphore, Task, TaskGroup
from collections.abc import Iterable, Awaitable, Callable


async def run_in_parallel[T](jobs: Iterable[Callable[[], Awaitable[T]]], max_parallel: int) -> list[T]:
    if max_parallel < 1:
        raise ValueError("max_parallel must be >= 1")

    semaphore = Semaphore(max_parallel)

    async def run(job_: Callable[[], Awaitable[T]]) -> T:
        async with semaphore:
            return await job_()

    tasks: list[Task[T]] = []
    try:
        async with TaskGroup() as tg:
            for job in jobs:
                tasks.append(
                    tg.create_task(run(job))
                )
    except ExceptionGroup as eg:
        raise eg.exceptions[0] from eg

    res: list[T] = []
    for task in tasks:
        res.append(task.result())
    return res
