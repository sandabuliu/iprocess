#  IProcess

### 说明
提供可交互式的多进程接口


### 安装
-----------
```shell
pip install git+https://github.com/sandabuliu/iprocess.git
```
or

```shell
git clone https://github.com/sandabuliu/iprocess.git
cd iprocess
python setup.py install
```


### QuickStart
---------------
#####  查看进程状态
```python
import time
from iprocess import IProcess

class Test(IProcess):
    def run(self):
        time.sleep(5)
        raise Exception('error')

test = Test()
test.start()

while Test:
    keepalive = test.keepalive
    print keepalive
    if not keepalive['alive']:
        break
    time.sleep(1)
```

输出结果:

    {'alive': True}
    {'alive': True}
    {'alive': True}
    {'alive': True}
    {'alive': True}
    {'alive': False, 'error': Exception('error',), 'exitcode': 0, 'traceback': 'Traceback (most recent call last):\n  File "/Users/home/iprocess/iprocess/iprocess.py", line 135, in _func\n    ret = run()\n  File "test.py", line 13, in run\n    raise Exception(\'error\')\nException: error\n'}

##### 查看进程变量
```python
import time
from iprocess import IProcess


class Increaser(IProcess):
    """Increaser 进程将列表中的数据均实现自加效果"""

    def __init__(self, data, *args, **kwargs):
        super(Increaser, self).__init__(*args, **kwargs)
        self._data = data
        self.index = 0

    def run(self):
        for i, item in enumerate(self._data):
            time.sleep(0.2)
            self._data[i] += 1
            self.index = i+1

    @IProcess.property
    def data(self):
        return self._data
```

输出结果：

    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    [1, 2, 3, 3, 4, 5, 6, 7, 8, 9]
    [1, 2, 3, 4, 5, 6, 6, 7, 8, 9]
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 9]
    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    
##### 查看计算进度
```python
import time
from iprocess import IProcess

class Increaser(IProcess):
    """Increaser 进程将列表中的数据均实现自加效果"""

    def __init__(self, data, *args, **kwargs):
        super(Increaser, self).__init__(*args, **kwargs)
        self._data = data
        self.index = 0

    def run(self):
        for i, item in enumerate(self._data):
            time.sleep(0.2)
            self._data[i] += 1
            self.index = i+1

    @IProcess.property
    def data(self):
        return self._data

    @IProcess.property
    def progress(self):
        return 100.0 * self.index / len(self._data)


a = Increaser(range(10))
a.start()

while a.is_alive():
    print a.progress, a.data
    time.sleep(0.6)

print a.progress, a.data
```

输出结果：

    0.0 [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    30.0 [1, 2, 3, 3, 4, 5, 6, 7, 8, 9]
    60.0 [1, 2, 3, 4, 5, 6, 6, 7, 8, 9]
    90.0 [1, 2, 3, 4, 5, 6, 7, 8, 9, 9]
    100.0 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

#####  添加任务
```python
import time
from iprocess import IProcess


class Increaser(IProcess):
    """Increaser 进程将列表中的数据均实现自加效果"""

    def __init__(self, data, *args, **kwargs):
        super(Increaser, self).__init__(*args, **kwargs)
        self._data = data
        self.index = 0

    def run(self):
        for i, item in enumerate(self._data):
            time.sleep(0.2)
            self._data[i] += 1
            self.index = i+1

    @IProcess.property
    def data(self):
        return self._data

    @IProcess.property
    def progress(self):
        return 100.0 * self.index / len(self._data)

    @IProcess.child
    def append(self, x):
        self._data.append(x)


a = Increaser(range(10))
a.start()

print a.progress, a.data
a.append(1)

while a.is_alive():
    print a.progress, a.data
    time.sleep(0.6)

print a.progress, a.data
```

输出结果:

    10.0 [1, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    9.09090909091 [1, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1]
    36.3636363636 [1, 2, 3, 4, 4, 5, 6, 7, 8, 9, 1]
    63.6363636364 [1, 2, 3, 4, 5, 6, 7, 7, 8, 9, 1]
    90.9090909091 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 1]
    100.0 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 2]

详细内容, 见: [http://t.navan.cc](http://t.navan.cc)

Copyright © 2017 [g_tongbin@foxmail.com](mailto:g_tongbin@foxmail.com)
