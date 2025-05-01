<!-- 这是一个对于整个项目结构及其功能的设计分析 -->

## 项目结构

首先这个项目包括两块

- 数据获取
- 读取数据并根据交易逻辑执行操作

首先解决数据获取的问题，数据获取包括两部分，实时数据获取，历史数据获取。对于实时数据，考虑使用 websocket 获取，对于历史数据，考虑使用 http 请求获取。

先解决 websocket 获取数据部分

### websocket 获取数据

对于 websocket 获取数据，需要考虑，连接、异常断开后重连。考虑使用一个 keepAlive 检查连接状态，其他地方不进行任何的重连操作以免将操作复杂化。目前已将 webSocketOkx 除却数据处理的部分写好，实现持久连接以及断线重连的逻辑。根据不同的需要，通过继承这个类，修改\_msgProcess 方法实现数据处理部分。注意这里使用了协程，运行的时候需要使用 gather 收集任务再运行，否则可能会遇到堵塞。

```text
    project/
        |-- .env
        |-- .getignore
        |-- config.py
        |-- design.md
        |-- README.md
        |-- src/
            |-- main.py
            |-- webSocketOkx.py
            |-- utils/
                |-- __init__.py
                |-- check.py
                |-- logger.py
                |-- login.py

```
