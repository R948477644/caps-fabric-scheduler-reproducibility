# Fabric 热点账户交易性能优化实验阶段性整理

记录日期：2026-06-15  
实验阶段：Native Fabric 基线实验、Traditional Lock 调度器实验  
实验目标：在真实 Hyperledger Fabric + Caliper/自定义负载发生器环境下，构建热点账户转账工作负载，观察原生 Fabric 在热点冲突下的性能退化，并验证基于锁调度的冲突控制机制是否能够消除 MVCC 冲突。

## 1. 实验环境与公共配置

本阶段实验在本机 WSL2 + Docker Desktop 环境中完成，用于预实验和方案可行性验证。Fabric 网络采用 4 个 peer 节点、1 个 Raft orderer 节点，通道名为 `vllchannel`，链码名为 `hotkey`。

Fabric 网络配置：

| 配置项 | 设置 |
|---|---|
| Peer 数量 | 4 个：Org1/Org2 各 2 个 peer |
| Orderer | 1 个 Raft orderer |
| Channel | `vllchannel` |
| Chaincode | `hotkey` |
| 链码语言 | Go |
| 账户数量 | 1000 |
| 热点账户数量 | 100 |
| 交易函数 | `Transfer(from, to, amount)` |
| 客户端数 | 100 |

`hotkey` 链码以账户余额转账为核心逻辑。每笔交易读取并写入两个账户状态，即 `from` 和 `to` 两个 key。因此，当大量交易集中访问有限数量的热点账户时，Fabric 原生 MVCC 校验阶段容易出现读写集版本冲突。

## 2. 实验一：Native Fabric 基线实验

### 2.1 实验目的

Native Fabric 实验用于作为后续 Traditional Lock、VLL-only、VLL+SCD 的基线。该实验不引入任何额外调度器，客户端直接通过 Caliper Fabric Gateway 向 Fabric 提交交易，由 Fabric 自身的背书、排序、验证和提交流程处理并发冲突。

该实验主要观察：

- 原生 Fabric 在热点账户转账负载下的成功交易数量；
- 随发送速率升高，失败交易数量如何变化；
- Fabric 原生 MVCC 冲突对有效吞吐和延迟的影响；
- 后续调度优化方法是否能够减少无效交易和冲突浪费。

### 2.2 工作负载设计

Native 实验使用 Caliper 的 fixed-rate 控制器。每个 worker 根据自身编号和本地交易序号生成 `from/to` 账户，账户范围限制在 100 个热点账户内。

核心交易模式如下：

```text
from = acct{hot index}
to   = acct{another hot index}
amount = 1
```

该模式能够稳定产生热点 key 冲突，并适合观察 Fabric MVCC 校验带来的失败交易。

### 2.3 实验参数

| 参数 | 设置 |
|---|---|
| 工具 | Hyperledger Caliper |
| 客户端/worker 数 | 100 |
| 每轮持续时间 | 60 s |
| 发送速率 | 50、100、200、300、500 TPS |
| 链码函数 | `Transfer` |
| 热点账户数 | 100 |

### 2.4 Native Fabric 实验结果

| Offered TPS | Succ | Fail | Send Rate TPS | Max Latency s | Min Latency s | Avg Latency s | Throughput TPS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 50 | 2749 | 351 | 48.7 | 2.37 | -0.99 | 0.17 | 47.4 |
| 100 | 5047 | 1018 | 98.8 | 2.06 | -1.10 | 0.11 | 95.6 |
| 200 | 7292 | 4808 | 193.3 | 1.99 | -1.06 | 0.16 | 192.8 |
| 300 | 4965 | 13135 | 292.7 | 2.86 | -1.82 | 0.31 | 283.2 |
| 500 | 112 | 29988 | 485.3 | 44.15 | 0.30 | 10.50 | 253.7 |

结果来源：

- `/home/rd/fabric-exp/caliper-vll/native-100clients-.log`
- `/home/rd/fabric-exp/caliper-vll/report.html`
- `/home/rd/fabric-exp/caliper-vll/benchmark-native-100clients.yaml`

### 2.5 结果分析

Native Fabric 在低速率下能够维持较高发送吞吐，但失败交易随压力上升明显增加。特别是在 300 TPS 和 500 TPS 下，失败交易数量远高于成功交易数量，说明热点账户访问导致的并发冲突已经成为主要性能瓶颈。

500 TPS 下虽然 Caliper 统计的 Throughput 为 253.7 TPS，但成功交易只有 112 笔，失败交易达到 29988 笔。该现象表明，系统处理了大量最终无效的交易请求，背书、排序和验证资源被冲突交易消耗，导致有效提交能力急剧下降。

Caliper 表中出现负的最小延迟值，属于本地 WSL2/Docker Desktop/Caliper 计时环境下的统计异常，论文中不宜将该指标作为关键结论。后续分析应主要采用成功数、失败数、平均延迟、吞吐趋势和冲突比例。

## 3. 实验二：Traditional Lock 调度器实验

### 3.1 实验目的

Traditional Lock 实验用于构建一个保守并发控制基线。其核心思想是在交易进入 Fabric 前增加一个外部调度器，根据交易访问的 key 提前进行加锁，避免互相冲突的交易同时进入 Fabric 背书和提交流程。

该实验验证：

- 基于锁的调度器是否能够消除热点账户交易中的 MVCC 冲突；
- 保守锁机制在高冲突场景下的性能代价；
- 与 Native Fabric 相比，是否能够减少无效交易对 Fabric 资源的浪费；
- 为后续 VLL-only 和 VLL+SCD 提供对比基线。

### 3.2 实现方案

Traditional Lock 未直接修改 Fabric 内核，而是在 Fabric 客户端提交路径前实现外部调度器。客户端先将交易提交给调度器，调度器根据 `from/to` 两个账户 key 判断是否存在锁冲突。

调度逻辑如下：

1. 接收客户端交易请求；
2. 从交易参数中提取访问 key 集合：`{from, to}`；
3. 若 key 未被占用，则加锁并提交 Fabric；
4. 若 key 被占用，则进入等待队列；
5. Fabric 提交完成后释放锁；
6. 若等待队列达到上限，则返回 `429 backpressure`。

Traditional Lock 调度器参数：

| 参数 | 设置 |
|---|---|
| 提交模式 | Fabric SDK submitter |
| 最大并行非冲突交易数 | `TRAD_LOCK_MAX_ACTIVE=16` |
| 最大等待队列长度 | `TRAD_LOCK_MAX_QUEUE=500` |
| 背书节点 | `peer0.org1.example.com:7051`、`peer0.org2.example.com:9051` |
| 负载发生器 | 自定义 HTTP fixed-rate load generator |
| 客户端数 | 100 |
| 每轮持续时间 | 20 s |

### 3.3 为什么 Traditional Lock 使用自定义负载发生器

最初尝试使用 Caliper custom workload 直接压测调度器，但发现 Caliper 对非标准 Fabric adapter 的 HTTP workload 统计口径不合适：Caliper 报告中 Submitted 可能为 0，且速率控制未能准确反映调度器实际接收的请求。因此 Traditional Lock 阶段改用自定义 fixed-rate HTTP load generator。

该负载发生器保留了与 Native 实验一致的热点账户访问模式，但由调度器负责提交 Fabric。这样可以更准确地区分：

- 客户端发送数量；
- 调度器接受数量；
- 调度器拒绝数量；
- Fabric 提交成功数量；
- MVCC 冲突数量；
- 排队等待时间和 Fabric 提交时间。

需要注意的是，Native 实验使用 Caliper，Traditional Lock 实验使用自定义负载发生器，两者在工具统计口径上并不完全相同。论文中若进行直接对比，应强调二者共享相同 Fabric 网络、链码和热点工作负载，但客户端驱动实现不同。

### 3.4 Traditional Lock 实验结果

| Offered TPS | Sent | 200 OK | 429 Backpressure | MVCC Failures | Client Completion TPS | Client Avg Latency ms | Dispatcher Avg Queue ms | Dispatcher Avg Fabric ms | Dispatcher Avg Total ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 100 | 100 | 0 | 0 | 4.56 | 1889.68 | 459.42 | 1427.87 | 1887.29 |
| 10 | 200 | 200 | 0 | 0 | 8.65 | 1068.18 | 443.14 | 622.00 | 1065.14 |
| 20 | 400 | 400 | 0 | 0 | 16.81 | 562.34 | 190.13 | 368.75 | 558.88 |
| 30 | 600 | 600 | 0 | 0 | 24.90 | 404.17 | 131.47 | 267.24 | 398.71 |
| 50 | 1000 | 1000 | 0 | 0 | 49.97 | 288.80 | 126.09 | 157.33 | 283.42 |
| 100 | 2000 | 2000 | 0 | 0 | 99.90 | 361.40 | 247.01 | 102.82 | 349.83 |
| 200 | 4000 | 3391 | 609 | 0 | 160.41 | 1954.07 | 2174.01 | 102.76 | 2276.76 |
| 300 | 6000 | 3957 | 2043 | 0 | 241.16 | 1692.95 | 2470.22 | 90.17 | 2560.39 |
| 500 | 10000 | 3916 | 6084 | 0 | 367.51 | 1127.81 | 2768.09 | 99.99 | 2868.08 |

结果来源：

- `/home/rd/fabric-exp/caliper-vll/results/traditional-lock-sdk-100clients-<rate>tps-client.json`
- `/home/rd/fabric-exp/caliper-vll/results/traditional-lock-sdk-100clients-<rate>tps-metrics.json`
- `/home/rd/fabric-exp/caliper-vll/EXPERIMENT_1_TRADITIONAL_LOCK_RESULTS.md`

### 3.5 结果分析

Traditional Lock 的最重要结果是所有有效实验点中 `MVCC Failures = 0`。这说明在本实验的热点账户转账模型下，调度器能够通过提前锁定读写 key，避免冲突交易同时进入 Fabric，从而消除 Fabric 提交阶段的 MVCC 冲突。

在 100 TPS 及以下，Traditional Lock 基本能够接受并成功提交全部请求，没有触发队列拒绝。200 TPS 开始，等待队列达到容量上限，调度器开始返回 `429 backpressure`。该现象表明 Traditional Lock 是一种保守冲突控制策略：它可以保证冲突安全，但在热点冲突密集时会牺牲并行度，并将压力表现为排队等待或队列拒绝。

与 Native Fabric 相比，Traditional Lock 将原本可能进入 Fabric 并最终失败的冲突交易提前挡在调度层，从而减少 Fabric 内部无效交易消耗。但其缺点是调度器成为新的瓶颈，尤其在高并发热点访问下，队列长度和排队延迟迅速上升。

## 4. 实验过程中遇到的问题与可写入论文的工作

### 4.1 热点交易链码构造

为了研究 Fabric 在热点冲突场景下的交易性能，本阶段构造了 `hotkey` 链码。该链码不同于普通 asset-transfer 示例，而是围绕账户余额转账设计，每笔交易明确读写两个账户 key。该设计使冲突关系可控、可复现，便于后续 VLL 和 SCD 调度策略对比。

论文中可表述为：

> 为了模拟高冲突区块链交易场景，本文设计并实现了热点账户转账链码，通过控制热点账户集合大小，使交易读写集之间产生可调节的冲突关系，为排序与锁调度优化提供可重复的实验负载。

### 4.2 Native Fabric 冲突基线建立

Native Fabric 实验验证了在热点账户负载下，Fabric 原生执行-排序-验证流程会产生大量无效交易。该实验为后续优化算法提供了基线数据。

论文中可表述为：

> 本文首先在未引入额外调度机制的 Fabric 网络上进行基线测试，发现随着热点交易发送速率升高，交易失败数显著增加，说明 Fabric 原生 MVCC 机制在热点写冲突场景下存在资源浪费问题。

### 4.3 Traditional Lock 调度器实现

本阶段实现了一个外部 Traditional Lock 调度器，将冲突控制前移到 Fabric 提交之前。该调度器不修改 Fabric 内核，通过 SDK 提交交易，具有较好的可部署性和实验隔离性。

论文中可表述为：

> 本文实现了一种基于传统排他锁的交易预调度机制，在客户端与 Fabric 网络之间增加调度层，根据交易声明或解析得到的访问 key 集合进行冲突检测。对于访问集合相交的交易，调度器采用等待队列进行串行化处理；对于非冲突交易，则允许并行提交。

### 4.4 Caliper 与外部调度器适配问题

实验中发现 Caliper 对 Fabric 原生工作负载支持较好，但对外部 HTTP 调度器模式的统计口径并不完全适配。因此实现了自定义负载发生器，用于记录调度器接收、拒绝、成功、失败、排队延迟和 Fabric 提交延迟。

论文中可表述为：

> 由于优化方案引入了 Fabric 外部调度层，传统 Caliper 指标无法完整反映调度层内部队列状态。本文进一步实现了轻量级固定速率负载发生器，并在调度器端采集队列长度、锁等待时间、Fabric 提交时间和拒绝请求数等指标，以更准确评估调度机制本身的性能特征。

### 4.5 链码运行时稳定性问题

实验过程中，Go 链码容器曾出现 gRPC `too_many_pings` 导致链码容器退出的问题。该问题与当前 Docker Desktop/Fabric/Go chaincode shim 组合下的 keepalive 策略有关。实验中将 vendored `fabric-chaincode-go/v2` 的 keepalive 间隔由 1 分钟调整为 10 分钟，并将 `hotkey` 链码升级至 version `1.1`、sequence `2`，之后链码容器稳定运行。

论文中不宜过度展开具体工程错误，但可以作为实验环境可靠性处理说明：

> 为保证长时间压力测试稳定性，本文对链码运行时连接保持参数进行了调整，避免链码容器在高频测试过程中因 gRPC keepalive 策略触发异常断连，从而保证实验结果来自交易冲突控制机制本身，而非运行时连接不稳定。

### 4.6 Peer 区块同步滞后问题

链码升级过程中，`peer0.org2.example.com` 曾落后 Org1 约 251 个区块，导致 lifecycle approval 状态在不同组织视角下不一致。通过重启该 peer，使其重新连接 orderer 并追块后，链码定义成功提交。

论文中可抽象为：

> 在多 peer 实验网络中，本文对各 peer 的区块高度和链码生命周期状态进行一致性检查，确保实验开始前所有背书节点处于相同链码版本和通道高度，避免节点状态不一致影响交易背书与验证结果。

### 4.7 负载发生器本身的瓶颈修正

Traditional Lock 高速率测试中曾发现 HTTP agent socket 上限过小会造成客户端本地排队，从而放大端到端延迟。随后将 `maxSockets` 与 `maxOutstanding` 参数化并提高上限，使压力真正进入调度器，由调度器队列产生 backpressure。

论文中可表述为：

> 为避免客户端负载发生器成为瓶颈，本文对并发连接数与未完成请求数进行参数化控制，确保高负载下观测到的排队和拒绝主要来自调度器本身，而非客户端 HTTP 连接池限制。

## 5. 阶段性结论

Native Fabric 实验表明，在热点账户转账场景中，原生 Fabric 会随着发送速率升高产生大量失败交易，尤其在 300 TPS 和 500 TPS 下冲突问题非常明显。该结果证明热点 key 访问下的 MVCC 冲突是 Fabric 交易性能下降的重要来源。

Traditional Lock 实验表明，基于 key 的外部锁调度可以将 MVCC 冲突降低到 0，从而验证了“在 Fabric 提交前进行冲突控制”的可行性。但 Traditional Lock 的保守排他锁策略会限制并行度，在高负载下表现为队列排队和 backpressure，说明仅依赖传统锁机制无法充分释放非冲突交易的并行潜力。

因此，后续 VLL-only 和 VLL+SCD 实验应重点验证：

1. 是否同样能够保持 `MVCC Failures = 0`；
2. 是否能够在热点冲突下比 Traditional Lock 接受更多请求；
3. 是否能够降低队列等待时间；
4. 是否能够减少高负载下的 `429 backpressure`；
5. 是否能够在保证冲突安全的同时提升有效提交吞吐。

## 6. 后续论文写作建议

这两个实验可以放在第五章实验部分的前半段，作为“实验环境与基线结果”。建议结构如下：

```text
5.1 实验环境与工作负载设计
5.2 Native Fabric 热点交易基线实验
5.3 Traditional Lock 保守调度实验
5.4 VLL-only 调度优化实验
5.5 VLL+SCD 综合优化实验
5.6 对比分析与讨论
```

其中 Native Fabric 用于说明问题存在，Traditional Lock 用于说明简单保守调度虽然能消除冲突，但会引入排队和并行度损失。后续 VLL/VLL+SCD 的论文贡献点可以围绕“在保持冲突安全的前提下提高可并行提交能力”展开。

## 7. VLL-only 调度器阶段性进展

在 Traditional Lock 实验之后，进一步实现了 VLL-only 前置调度器。该调度器同样部署在 Fabric 客户端提交路径之前，但调度依据从传统锁集合扩展为交易预声明的读写集。对于当前 `Transfer(from, to, amount)` 链码而言，`from` 和 `to` 两个账户均会被读取和更新，因此二者都被视为写集合中的 key。

VLL-only 调度器最终采用 active write-counter 模型：等待队列中的交易不会提前占有 key；只有当交易被调度执行时，其写集合对应的 active writer 计数才会增加。交易提交完成后释放这些计数，再唤醒后续等待交易。该设计可以避免冲突交易同时进入 Fabric，同时允许与当前活跃交易不冲突的后续交易提前执行。

实现过程中曾尝试严格 per-key FIFO 队列模型。该模型虽然能够保证 MVCC 冲突为 0，但在热点转账负载下出现明显 head-of-line blocking。例如连续交易可能形成 `acct000000 -> acct000001`、`acct000001 -> acct000002`、`acct000002 -> acct000003` 的链式关系，严格 per-key FIFO 会使后续非直接冲突交易也被等待交易阻塞，导致 1 TPS 下也出现较长排队时间。因此最终版本改为 active conflict counter，不让尚未执行的等待交易提前占位。该过程可以作为论文中“VLL 调度器设计细节与工程修正”的一项工作。

VLL-only 实验参数：

| 参数 | 设置 |
|---|---|
| Dispatcher | `gateway/vll-only-dispatcher.js` |
| 端口 | 8083 |
| 提交模式 | Fabric SDK |
| 最大活跃交易数 | `VLL_ONLY_MAX_ACTIVE=16` |
| 最大等待队列长度 | `VLL_ONLY_MAX_QUEUE=500` |
| 负载发生器 | 自定义 fixed-rate HTTP load generator |
| 客户端数 | 100 |
| 每轮持续时间 | 20 s |

VLL-only 实验结果：

| Offered TPS | Sent | 200 OK | 429 Backpressure | MVCC Failures | Client Completion TPS | Client Avg Latency ms | Dispatcher Avg Queue ms | Dispatcher Avg Fabric ms | Dispatcher Avg Total ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 100 | 100 | 0 | 0 | 4.26 | 1887.33 | 478.53 | 1405.95 | 1884.48 |
| 10 | 200 | 200 | 0 | 0 | 10.02 | 863.15 | 366.73 | 493.41 | 860.13 |
| 20 | 400 | 400 | 0 | 0 | 16.85 | 590.25 | 225.60 | 360.14 | 585.73 |
| 30 | 600 | 600 | 0 | 0 | 25.10 | 372.47 | 121.92 | 246.40 | 368.32 |
| 50 | 1000 | 1000 | 0 | 0 | 49.97 | 259.85 | 100.50 | 154.37 | 254.87 |
| 100 | 2000 | 2000 | 0 | 0 | 99.91 | 325.49 | 223.49 | 94.63 | 318.12 |
| 200 | 4000 | 3801 | 199 | 0 | 162.88 | 1675.93 | 1662.14 | 88.51 | 1750.65 |
| 300 | 6000 | 3786 | 2214 | 0 | 243.63 | 1678.17 | 2543.11 | 92.93 | 2636.04 |
| 500 | 10000 | 4176 | 5824 | 0 | 374.77 | 1065.64 | 2452.04 | 88.72 | 2540.76 |

阶段性结论是：VLL-only 与 Traditional Lock 一样能够将 MVCC 冲突控制为 0，说明基于预声明读写集的 Fabric 前置调度机制是有效的。在 200 TPS 下，VLL-only 的 429 拒绝数少于 Traditional Lock；在 500 TPS 下，VLL-only 的成功提交数略高于 Traditional Lock。但在 300 TPS 及以上，队列等待仍然明显，说明 VLL-only 主要解决冲突安全问题，并未完全解决热点交易调度效率问题。这为下一步 VLL+SCD 提供了实验动机：在保持 MVCC 冲突为 0 的前提下，进一步降低排队等待和 backpressure。

## 8. VLL+SCD 批量匹配调度器阶段性结果

在 VLL-only 实验之后，进一步实现了 VLL+SCD 前置调度器。该调度器仍然保持 VLL 的 active write-counter 冲突控制机制，即只有当前正在提交 Fabric 的交易会占用写 key，等待队列中的交易不会提前占位。在此基础上，SCD 层负责从等待窗口中选择一组更适合并行提交的交易。

针对本实验中的账户转账 workload，每笔 `Transfer(from, to, amount)` 都会读写两个账户 key，因此可以将一笔交易抽象为账户图中的一条边，两个账户是边的端点。如果两笔交易共享任意账户端点，则二者不能同时提交；如果一组交易两两不共享端点，则该组交易构成一个 matching，可以作为安全并行批次提交给 Fabric。

当前实现采用在线贪心近似，而不是在调度路径中求解完整最大匹配。调度器每轮从等待队列前部取 `VLL_SCD_WINDOW=256` 个候选交易，过滤掉与当前活跃写 key 冲突的交易，然后统计候选窗口中的 key 频率。对于每笔交易，使用两个写 key 的频率估算冲突代价，并结合等待时间老化项形成调度分数：

```text
score(T) = ageWeight * ageScore(T)
           - conflictWeight * conflictCost(T)
           - positionWeight * queuePosition(T)
```

其中 `conflictCost(T)` 表示该交易两个账户在当前窗口中的热点程度，`ageScore(T)` 用于防止高冲突交易长期饥饿。排序后，调度器按分数从高到低贪心选择一批互不共享账户 key 的交易，直到达到最大活跃交易数或没有可选交易为止。

VLL+SCD 实验参数：

| 参数 | 设置 |
|---|---|
| Dispatcher | `gateway/vll-scd-dispatcher.js` |
| 端口 | 8084 |
| 提交模式 | Fabric SDK |
| 最大活跃交易数 | `VLL_SCD_MAX_ACTIVE=32` |
| 最大等待队列长度 | `VLL_SCD_MAX_QUEUE=500` |
| 调度窗口 | `VLL_SCD_WINDOW=256` |
| 老化间隔 | `VLL_SCD_AGE_BOOST_MS=100` |
| 老化权重 | `VLL_SCD_AGE_WEIGHT=10` |
| 冲突代价权重 | `VLL_SCD_CONFLICT_WEIGHT=1` |
| 客户端数 | 100 |
| 每轮持续时间 | 20 s |

VLL+SCD 批量匹配实验结果：

| Offered TPS | Sent | 200 OK | 429 Backpressure | MVCC Failures | Client Completion TPS | Client Avg Latency ms | Dispatcher Avg Queue ms | Dispatcher Avg Fabric ms | Dispatcher Avg Total ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 100 | 100 | 0 | 0 | 3.82 | 1921.91 | 463.30 | 1456.71 | 1920.01 |
| 10 | 200 | 200 | 0 | 0 | 8.53 | 1015.57 | 357.10 | 652.22 | 1009.32 |
| 20 | 400 | 400 | 0 | 0 | 16.69 | 552.89 | 204.99 | 345.86 | 550.85 |
| 30 | 600 | 600 | 0 | 0 | 25.15 | 396.78 | 114.48 | 276.17 | 390.65 |
| 50 | 1000 | 1000 | 0 | 0 | 41.73 | 241.96 | 72.00 | 168.43 | 240.44 |
| 100 | 2000 | 2000 | 0 | 0 | 99.91 | 112.11 | 28.62 | 81.17 | 109.79 |
| 200 | 4000 | 3716 | 284 | 0 | 137.45 | 1533.48 | 1534.41 | 101.13 | 1635.53 |
| 300 | 6000 | 3621 | 2379 | 0 | 224.29 | 1682.78 | 2656.43 | 98.51 | 2754.94 |
| 500 | 10000 | 3626 | 6374 | 0 | 375.56 | 1020.24 | 2632.39 | 92.48 | 2724.87 |

阶段性结论是：VLL+SCD 在所有测试速率下均保持 `MVCC Failures = 0`，说明批量匹配调度没有破坏冲突安全性。与此前泛化的“低冲突优先”版本相比，当前面向转账 workload 的 matching 调度在 100 TPS 档表现明显改善，2000 个请求全部成功，客户端平均延迟降至 112.11 ms，调度器平均总耗时降至 109.79 ms。这说明 SCD 在中等负载下能够通过选择互不共享账户的交易批次提高调度质量。

在 200 TPS 及以上，系统开始出现明显 `429 backpressure`，主要原因是热点账户转账 workload 的可并行度受到写集合冲突的硬约束。调度器可以避免冲突交易进入 Fabric，也可以在等待窗口内选择更好的非冲突批次，但当大量请求集中访问同一批热点账户时，它无法凭空创造安全并行度。因此，高负载区间可以作为论文中的限制分析：VLL+SCD 提升的是冲突安全前提下的批次选择效率，而不是消除热点写冲突本身。

从论文写作角度看，这组实验可以支撑三点：第一，VLL+SCD 与 VLL-only 一样能够将 Fabric MVCC 冲突控制为 0；第二，转账依赖图/批量匹配思想比简单队列顺序更贴合账户转账场景；第三，在极端热点负载下仍需要进一步结合热点账户准入控制、加权匹配或更大的调度窗口来降低队列背压。
