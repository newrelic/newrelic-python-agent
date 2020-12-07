from celery import Celery


app = Celery('tasks')

@app.task
def add(x, y):
    return x + y

@app.task
def tsum(nums):
    return sum(nums)
