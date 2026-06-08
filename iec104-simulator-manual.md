# IEC 60870-5-104 模拟器 — 使用手册

> 版本: 2.5.2 | 更新日期: 2026-05-21

---

## 目录

1. [概述](#1-概述)
2. [系统要求](#2-系统要求)
3. [快速安装](#3-快速安装)
4. [运行模式](#4-运行模式)
5. [点表配置](#5-点表配置)
6. [Web 管理界面](#6-web-管理界面)
7. [HTTP API](#7-http-api)
8. [自动变化策略](#8-自动变化策略)
9. [置数操作](#9-置数操作)
10. [运行管理](#10-运行管理)
11. [跨平台编译与打包](#11-跨平台编译与打包)
12. [防火墙配置](#12-防火墙配置)
13. [常见问题](#13-常见问题)

---

## 1. 概述

IEC 104 从站模拟器用于变电站自动化测试，支持多实例并行运行，模拟 RTU 及间隔层设备。适用于 SCADA 系统开发、集成测试和自动化测试场景。

### 核心能力

- 模拟 IEC 60870-5-104 从站（Server），接受客户端连接
- 支持 Modbus TCP 协议，与 IEC104 并行运行（v2.4.0+）
- 支持遥测(AI)、遥信(DI)、遥脉(PI)、遥控(DO)、遥调(AO) 五种测点类型
- 总召唤、电度召唤、变化上送、品质描述 QDS
- 双运行模式：传统单实例模式 + 服务多实例模式
- Vue 3 Web 管理界面（配置管理/运行监控/实例详情/实时趋势）
- RESTful HTTP API
- MCP 协议支持（AI Agent 程序化控制）
- 自动变化引擎（11 种策略：递增/随机/CSV回放/MAX/MIN/SOC/电量/AO关联/接口更新/手动/自定义公式）
- CSV 多测点同步回放（多列 CSV 映射到不同测点，共享时间基准）
- 实例上限 1000，独立端口分配，自动防火墙管理
- 跨平台编译（Linux amd64/arm64、Windows amd64）、`.deb` 打包

### 应用场景

| 场景 | 说明 |
|------|------|
| SCADA 系统联调 | 模拟真实变电站设备，验证主站系统功能 |
| 自动化测试 | 通过 API 批量写入测点，配合 EGC 测试框架 |
| 储能系统仿真 | SOC 计算策略模拟电池储能系统行为 |
| Modbus 设备仿真 | 模拟 Modbus TCP 从站设备，支持功能码 1/3/4/5/6/16 |
| 培训演示 | 搭建虚拟变电站环境用于操作培训 |

---

## 2. 系统要求

### 运行环境

| 平台 | 支持 | 架构 |
|------|------|------|
| Linux | ✅ | amd64 / arm64 |
| Windows | ✅ | amd64 |
| macOS | 需源码编译 | amd64 / arm64 |

### 端口需求

| 端口 | 用途 | 说明 |
|------|------|------|
| 8989 (默认) | HTTP 管理 | Web UI + REST API |
| 2404 (默认) | IEC104 数据 | 传统模式数据端口 |
| 502 (默认) | Modbus TCP 数据 | Modbus 模式数据端口 |
| 动态分配 | 实例端口 | 服务模式每个实例独立分配 |

> 防火墙会自动放行已使用的端口（需 `iptables` 权限）。

---

## 3. 快速安装

### 3.1 下载压缩包（推荐）

从发行页面下载对应平台的压缩包：

```bash
# Linux amd64
tar xzf gridsim-v2.5.2-linux-amd64.tar.gz
cd gridsim-v2.5.2-linux-amd64

# 启动服务
./bin/start.sh
# 浏览器访问 http://localhost:8989
```

### 3.2 停止服务

```bash
./bin/stop.sh
```

### 3.3 重启服务

```bash
./bin/restart.sh
```

### 3.4 从源码构建

```bash
# 克隆仓库
git clone <repo-url>
cd iec104-sim-master

# 构建前端（需要 Node.js 18+）
cd web && npm install && npm run build && cd ..

# 构建后端
go build -o bin/gridsim ./cmd/gridsim/

# 启动
./bin/gridsim serve --http :8989 --config-dir ./config --log-dir ./logs
```

### 3.5 发行包目录结构

```
gridsim-v2.5.2-linux-amd64/
├── bin/
│   ├── gridsim            ← 主程序
│   ├── gridsim-mcp        ← MCP 服务器（可选）
│   ├── start.sh           ← 启动脚本
│   ├── stop.sh            ← 停止脚本
│   └── restart.sh         ← 重启脚本
├── config/
│   ├── instances.json     ← 实例配置文件（初始为空）
│   └── *.xlsx             ← 点表文件（通过 Web UI 上传）
├── logs/
│   └── output.log         ← 运行日志
├── manuals/               ← 使用手册（PDF/Markdown）
├── resources/             ← 资源目录
└── web/dist/              ← Web 前端静态文件
```

---

## 4. 运行模式

### 4.1 服务模式（推荐）

多实例管理模式，通过 Web UI 管理多个 IEC104 实例：

```bash
./gridsim serve \
  --http :8989 \
  --config-dir ./config \
  --log-dir ./logs \
  --log info
```

### 4.2 传统模式（单实例）

单进程单端口模式，适用于简单场景：

```bash
./gridsim -p 2404 -c samples/point.xlsx -H :8080 -l info
```

### 4.3 命令行参数

| 参数 | 缩写 | 默认值 | 适用模式 | 说明 |
|------|------|--------|----------|------|
| `--port` | `-p` | 2404 | 传统 | IEC104 服务端 TCP 端口 |
| `--config` | `-c` | 必填 | 传统 | `.xlsx` 配置文件路径 |
| `--http` | `-H` | `:8989` | 全部 | HTTP API 监听地址 |
| `--log` | `-l` | `info` | 全部 | 日志级别: debug/info/warn/error |
| `--config-dir` |  | `./config` | 服务 | 配置文件目录 |
| `--log-dir` | `-L` | `./logs` | 服务 | 日志文件目录 |
| `--protocol` |  | `iec104` | 传统 | 协议类型: `iec104` / `modbus_tcp` |
| `--modbus-port` |  | `502` | 传统 | Modbus TCP 端口 |
| `--modbus-byte-order` |  | `ABCD` | 传统 | Modbus 字节序: `ABCD` / `BADC` / `CDAB` / `DCBA` |
| `--modbus-slave-id` |  | `1` | 传统 | Modbus 从站 ID |

### 4.4 Modbus TCP 模式

从 v2.4.0 起支持与 IEC104 并行运行 Modbus TCP 协议。在服务模式下，创建实例时通过 `protocol` 字段选择协议类型。

**传统模式启动 Modbus TCP：**
```bash
./gridsim -p 502 -c samples/ModbusTCP-ESS.xlsx --protocol modbus_tcp -H :8989
```

**服务模式创建 Modbus 实例（API）：**
```bash
curl -X POST http://localhost:8989/api/v1/instances \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Modbus储能",
    "iec104_port": 502,
    "xlsx_file": "ModbusTCP-ESS.xlsx",
    "protocol": "modbus_tcp",
    "modbus_config": {
      "byte_order": "ABCD",
      "slave_id": 1
    }
  }'
```

**支持的 Modbus 功能码：**

| 功能码 | 操作 | 说明 |
|--------|------|------|
| 1 | Read Coils | 读取 DI 测点 |
| 3 | Read Holding Registers | 读取 AI 测点（FLOAT/DOUBLE） |
| 4 | Read Input Registers | 读取 AI 测点（FLOAT/DOUBLE） |
| 5 | Write Single Coil | 写入 DI 测点 |
| 6 | Write Single Register | 写入 AI 测点 |
| 16 | Write Multiple Registers | 批量写入 AI 测点 |

---

## 5. 点表配置

### 5.1 Excel 点表格式

点表使用 `.xlsx` 文件，工作表名称必须为 `point`。

| 列 | 表头 | 类型 | 必填 | 说明 | 示例 |
|----|------|------|------|------|------|
| A | point-name | string | 是 | 测点名称 | 母线电压 |
| B | point-number | uint32 | 是 | IOA，同类型测点唯一 | 16385 |
| C | value-type | string | 是 | 数据类型 | FLOAT |
| D | point-type | string | 是 | 测点类型 | AI |
| E | efficient | float64 | 是 | 系数 | 1.0 |
| F | base-value | float64 | 是 | 初始值 | 100.5 |
| G | alias | string | 否 | 别名或描述 | 220kV母线 |

### 5.2 测点类型说明

| 类型 | 中文 | IEC 104 类型 | 数据 | 说明 |
|------|------|-------------|------|------|
| AI | 遥测 YC | M_ME_NC_1 (13) | float32 | 模拟量监视，value = base × efficient |
| DI | 遥信 YX | M_SP_NA_1 (1) | bool 0/1 | 数字量监视（开关状态） |
| PI | 遥脉 YM | M_IT_NA_1 (15) | int32 | 脉冲计数 |
| DO | 遥控 | C_SC_NA_1 (45) | - | 接收外部控制，更新 DI 点 |
| AO | 遥调 | C_SE_NC_1 (48) | - | 接收外部控制，更新 AI 点 |

### 5.3 数据值类型

| 值类型 | 说明 |
|--------|------|
| FLOAT | 32 位浮点数（AI推荐） |
| DOUBLE | 64 位浮点数 |
| INT | 32 位整数 |
| BIT | 布尔值（DI/DO） |

### 5.4 上传点表

通过 Web UI **配置管理** → 上传点表文件（.xlsx），或使用 API：

```bash
curl -X POST http://localhost:8989/api/v1/upload \
  -F "file=@samples/point.xlsx"
```

上传后的文件存储在 `config/` 目录下，创建实例时在"点表文件"下拉框中选择。

### 5.5 示例点表

可在 `config/` 或 `samples/` 目录下找到示例点表文件：
- `固定验证-关口表.xlsx`
- `固定验证-储能.xlsx`
- `固定验证-光伏.xlsx`
- `固定验证-FCR.xlsx`
- `ModbusTCP-ESS.xlsx` — Modbus TCP 储能示例

### 5.6 Modbus 扩展格式

从 v2.4.0 起，点表支持 Modbus TCP 扩展列。标准格式 A~G 列不变，额外列被自动忽略，Modbus 客户端导出的点表可直接复用：

| 列 | 表头 | 说明 |
|----|------|------|
| A-G | 同标准格式 | 基础测点定义（point-name, point-number, value-type, point-type, efficient, base-value, alias） |
| H | register-address | Modbus 寄存器地址 |
| I | function-code | Modbus 功能码（1/3/4/5/6/16） |
| J | value-type | Modbus 数据类型（BIT/FLOAT/DOUBLE） |
| K | group-number | 客户端分组（忽略） |
| L | call-interval | 客户端轮询间隔（忽略） |
| M | user-defined-rule | 自定义规则（忽略） |

> Modbus 客户端工具导出的点表可直接使用，模拟器自动忽略多余列。

---

## 6. Web 管理界面

浏览器访问 `http://localhost:8989`。默认管理员账号：

| 用户名 | 密码 |
|--------|------|
| admin | admin |

> 用户配置在 `config/users.json` 中，支持密码哈希（bcrypt）。

### 6.1 配置管理（/config）

实例的增删改查：

- **实例容量显示（v2.5.1+）**：页面顶部显示全局状态 — 已配置 X / 1000 | 运行中 N 个 | 已停止 N 个
- **添加实例**：填写名称、IEC104 端口、选择点表文件、选择协议类型
- **启动/停止**：控制实例运行状态
- **编辑/删除**：修改配置或移除实例
- **HTTP 端口**：可选开启独立 HTTP 端口（默认自动分配）

**创建实例参数：**

| 字段 | 必填 | 说明 |
|------|------|------|
| 名称 | 是 | 实例名称，如"关口表" |
| 协议类型 | 否 | `iec104`（默认）或 `modbus_tcp`（v2.4.0+） |
| IEC104 端口 | 是 | IEC104/Modbus TCP 协议监听端口（1-65535） |
| 点表文件 | 是 | 选择已上传的 .xlsx 点表 |
| 启用 HTTP 接口 | 否 | 是否开启独立的测点 HTTP API |
| HTTP 端口 | 否 | 独立 HTTP API 端口 |

### 6.2 运行监控（/monitor）

以卡片视图展示所有实例的运行状态：

- 运行时长、IEC104 端口、客户端连接状态
- 总召次数、遥控次数、变化上送次数
- 实例状态标签（运行中/已停止/错误）
- 点击实例名称进入详情页

### 6.3 实例详情（/detail/:id）

单个实例的详细监控和操作页面：

**测点实时值表格：**
- 高频轮询（100ms~1000ms 可调）
- 实时显示所有测点的当前值、类型、更新时间
- AI 显示浮点值，DI 显示开关状态，PI 显示整数值

**置数操作：**
- AI（遥测）：输入浮点数值
- DI（遥信）：开关 ON/OFF 切换
- PI（遥脉）：输入整数值
- 置数成功绿色提示

**自动变化配置：**
- 每个测点可独立配置自动变化策略
- 批量配置：勾选多个测点，批量应用策略
- 导出/导入：JSON 格式批量导出导入配置

**CSV 功能：**
- 导出测点实时数据为 CSV
- **CSV 多测点同步回放（v2.5.0+）**：详情页新增独立"CSV 多测点回放"卡片
  - 上传多列 CSV 文件（time,value1,value2...），每列映射到不同测点
  - 支持相对时间（ms/s）和绝对时间（hh:mm:ss）两种回放模式
  - 多个测点共享同一时间基准，严格同步回放
  - **自动映射（v2.5.2+）**：上传后自动按列名匹配测点，未匹配的按顺序分配到 AI 测点，可手动修改
  - 状态持久化：退出详情页再打开自动恢复运行状态
  - 向后兼容：单测点 CSV 模式完全不变

### 6.4 实时趋势（/trend）

多线 SVG 趋势对比图：

- 最多 8 条测点曲线同图对比
- 轮询间隔：100ms / 200ms / 500ms / 1s / 5s
- 时间范围：5m / 15m / 30m / 1h
- 鼠标悬停查看数值
- 支持隐藏/显示单条曲线
- 配置自动保存到 localStorage

---

## 7. HTTP API

基础地址：`http://localhost:8989/api/v1`

### 7.1 实例管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/instances` | 列出所有实例 |
| POST | `/api/v1/instances` | 创建实例 |
| GET | `/api/v1/instances/{id}` | 获取实例详情 |
| PUT | `/api/v1/instances/{id}` | 更新实例配置 |
| DELETE | `/api/v1/instances/{id}` | 删除实例 |
| POST | `/api/v1/instances/{id}/start` | 启动实例 |
| POST | `/api/v1/instances/{id}/stop` | 停止实例 |
| POST | `/api/v1/instances/{id}/restart` | 重启实例 |
| GET | `/api/v1/status` | 全局服务状态（含 max_instances） |
| POST | `/api/v1/upload` | 上传点表文件 |
| GET | `/api/v1/files` | 列出已上传文件 |
| GET | `/api/v1/protocols` | 查询支持的协议类型 |

**实例配置模型（v2.4.0+）：**
```json
{
  "id": "a1b2c3d4e5f6",
  "name": "Modbus储能",
  "iec104_port": 502,
  "xlsx_file": "ModbusTCP-ESS.xlsx",
  "enabled": false,
  "http_enabled": true,
  "http_port": 2405,
  "protocol": "modbus_tcp",
  "modbus_config": {
    "port": 502,
    "byte_order": "ABCD",
    "slave_id": 1
  }
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 实例名称 |
| iec104_port | int | 是 | IEC104/Modbus 端口 |
| xlsx_file | string | 是 | 点表文件名 |
| enabled | bool | 否 | 是否启用（默认 false） |
| http_enabled | bool | 否 | 是否开启独立 HTTP 端口 |
| http_port | int | 否 | HTTP 端口 |
| protocol | string | 否 | 协议类型: `iec104` / `modbus_tcp`（默认 iec104）|
| modbus_config | object | 否 | Modbus TCP 额外配置 |

### 7.2 测点操作

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/instances/{id}/points` | 获取所有测点 |
| GET | `/api/v1/instances/{id}/points/{ioa}` | 获取单个测点 |
| PUT | `/api/v1/instances/{id}/points/{ioa}` | 置数 |
| POST | `/api/v1/instances/{id}/points/batch` | 批量置数 ⭐ |

### 7.3 自动变化配置

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/instances/{id}/points/auto-change/{ioa}` | 获取配置 |
| PUT | `/api/v1/instances/{id}/points/auto-change/{ioa}` | 配置自动变化 |
| DELETE | `/api/v1/instances/{id}/points/auto-change/{ioa}` | 删除配置 |
| PUT | `/api/v1/instances/{id}/points/auto-change/batch` | 批量配置 |
| GET | `/api/v1/instances/{id}/points/auto-change/export` | 导出配置 |
| POST | `/api/v1/instances/{id}/points/auto-change/import` | 导入配置 |

### 7.4 CSV 功能

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/instances/{id}/points/export` | 导出测点 CSV |
| POST | `/api/v1/instances/{id}/upload-csv` | 上传 CSV 回放文件 |
| GET | `/api/v1/instances/{id}/csv-files` | 列出可用 CSV 回放文件 |
| POST | `/api/v1/instances/{id}/csv-replay` | 配置 CSV 多测点同步回放 |

> CSV 文件存储位置：`{configDir}/csv/{instanceID}/`（实例私有）和 `{configDir}/csv/`（共享）。引擎查找时实例目录优先，共享目录作为 fallback。

### 7.5 调用示例

```bash
# 置数 AI 遥测
curl -X PUT http://localhost:8989/api/v1/instances/{id}/points/16385 \
  -H 'Content-Type: application/json' \
  -d '{"value": 235.5}'

# 置数 DI 遥信
curl -X PUT http://localhost:8989/api/v1/instances/{id}/points/5 \
  -H 'Content-Type: application/json' \
  -d '{"bool_value": true}'

# 批量置数（自动化测试核心接口）
curl -X POST http://localhost:8989/api/v1/instances/{id}/points/batch \
  -H 'Content-Type: application/json' \
  -d '{"points": [
    {"ioa": 16385, "value": 235.5},
    {"ioa": 16386, "value": 236.0},
    {"ioa": 5, "bool_value": true}
  ]}'

# 配置自动变化（递增策略）
curl -X PUT http://localhost:8989/api/v1/instances/{id}/points/auto-change/16385 \
  -H 'Content-Type: application/json' \
  -d '{
    "strategy": "increment",
    "enabled": true,
    "params": {
      "start_value": 0,
      "step": 1,
      "period_ms": 1000,
      "max_value": 100
    }
  }'

# CSV 多测点同步回放（一键配置所有映射）
curl -X POST http://localhost:8989/api/v1/instances/{id}/csv-replay \
  -H 'Content-Type: application/json' \
  -d '{
    "csv_file": "replay_data.csv",
    "time_format": "relative",
    "time_unit": "ms",
    "mappings": [
      {"column": 1, "ioa": 16385},
      {"column": 2, "ioa": 16386}
    ]
  }'
```

---

## 8. 自动变化策略

自动变化引擎是模拟器的核心功能，可让测点值按照预设策略自动变化，模拟真实设备行为。

### 8.1 策略一览

| # | 策略 | 英文标识 | 适用测点 | 说明 |
|---|------|----------|----------|------|
| 1 | 递增 | `increment` | AI | 每周期 += 步长，达最大值后回起始值 |
| 2 | 随机 | `random` | AI | 在 [min, max] 范围内随机取值 |
| 3 | CSV 回放 | `csv` | AI | 按 CSV 文件定义的时间序列播放 |
| 4 | 取大 | `max` | AI | 取多个关联 IOA 的最大值 |
| 5 | 取小 | `min` | AI | 取多个关联 IOA 的最小值 |
| 6 | SOC 计算 | `soc` | AI | 基于功率积分计算电池荷电状态 |
| 7 | 电量统计 | `energy` | AI | 基于功率积分计算累计电量 |
| 8 | AO 关联 | `aofollow` | AI | 跟随指定 AO 点的遥控值变化 |
| 9 | 接口更新 | `apiupdate` | AI | 仅允许 HTTP API 写入，引擎不做计算 |
| 10 | 手动 | `manual` | AI | 不自动计算，完全由用户 API 置数 |
| 11 | 自定义公式 | `custom` | AI | 按钮式编辑器构造四则运算公式 |

### 8.2 递增策略参数

```json
{
  "start_value": 0,
  "step": 1,
  "period_ms": 1000,
  "max_value": 100
}
```

| 参数 | 必填 | 说明 |
|------|------|------|
| start_value | 是 | 起始值 |
| step | 是 | 每周期增加值 |
| period_ms | 是 | 周期（毫秒，≥100） |
| max_value | 是 | 最大值，达此值后回到 start_value |

### 8.3 随机策略参数

```json
{
  "min_value": 0,
  "max_value_r": 100,
  "period_ms": 1000,
  "decimal_places": 2
}
```

| 参数 | 必填 | 说明 |
|------|------|------|
| min_value | 是 | 最小值 |
| max_value_r | 是 | 最大值 |
| period_ms | 是 | 周期（毫秒，≥100） |
| decimal_places | 是 | 小数位数 |

### 8.4 CSV 回放策略

按 CSV 文件定义的时间序列逐行播放。CSV 文件需先通过 API 或 Web UI 上传。

**文件存储位置：** 上传的 CSV 存储在 `config/csv/{instanceID}/`（实例私有目录），也可手动放入 `config/csv/`（共享目录，所有实例可见）。引擎查找时实例目录优先。

**单测点 CSV 格式（原始模式）：**
```csv
时间戳,值
2026-05-16 10:00:00,100.0
2026-05-16 10:00:01,101.5
2026-05-16 10:00:02,102.3
```

**多测点 CSV 格式（v2.5.0+，多列同步回放）：**
```csv
time,母线电压,线路电流,有功功率
0,100.0,5.2,520.0
1000,101.5,5.3,537.9
2000,102.3,5.1,521.7
```

多列 CSV 支持：
- **相对时间**：time 列为毫秒(ms)或秒(s)偏移量
- **绝对时间**：time 列为 hh:mm:ss 格式
- 每列映射到不同测点 IOA，共享同一时间基准，严格同步回放
- **自动映射**（v2.5.2+）：上传 CSV 后自动匹配列名到测点名，未匹配的按顺序分配到 AI 测点（IOA 升序），用户可手动修改
- 单测点 CSV 模式完全不变，向后兼容

**参数：**

| 参数 | 必填 | 说明 |
|------|------|------|
| csv_file | 是 | CSV 文件名 |
| time_format | 否 | 时间格式: `auto`（默认） |
| time_unit | 否 | 时间单位: `ms` / `s`（相对时间模式） |
| csv_column_map | 否 | 多列映射 JSON，如 `{"母线电压":16385,"线路电流":16386}` |

### 8.5 MAX/MIN 策略参数

```json
{
  "para_a": "16385,16386,16387",
  "para_b": ""
}
```

| 参数 | 必填 | 说明 |
|------|------|------|
| para_a | 是 | 关联 IOA 列表（逗号分隔） |
| para_b | 否 | 备用参数 |

### 8.6 SOC 计算策略

基于功率积分计算电池荷电状态（State of Charge），适用于储能系统仿真。

```json
{
  "init_soc": 50,
  "rated_cap": 1000,
  "power_ioa": 16385,
  "integral_ms": 1000
}
```

| 参数 | 必填 | 说明 |
|------|------|------|
| init_soc | 是 | 初始 SOC (%) |
| rated_cap | 是 | 额定容量 (kWh) |
| power_ioa | 是 | 功率 AI 点号 |
| integral_ms | 是 | 积分周期 (ms) |

### 8.7 电量统计策略

基于功率积分计算累计电量：

```json
{
  "init_energy": 0,
  "stat_type": 0,
  "energy_power_ioa": 16385,
  "energy_period_ms": 1000
}
```

| 参数 | 必填 | 说明 |
|------|------|------|
| init_energy | 是 | 初始电量 (kWh) |
| stat_type | 是 | 统计类型（0=充电, 1=放电） |
| energy_power_ioa | 是 | 功率 AI 点号 |
| energy_period_ms | 是 | 积分周期 (ms) |

### 8.8 AO 关联策略

当指定 AO 点被遥控时，自动同步更新本 AI 点值。

```json
{
  "follow_ao_ioa": 16390
}
```

| 参数 | 必填 | 说明 |
|------|------|------|
| follow_ao_ioa | 是 | 关联的 AO 点号 |

### 8.9 接口更新策略

```json
{
  "api_init_value": 0
}
```

仅允许通过 HTTP API 写入值，引擎不做任何自动计算。适用于外部系统联调。

### 8.10 手动策略

引擎不自动计算，值完全由用户通过 API 置数。适用于外部系统联调场景。

### 8.11 自定义公式策略（v2.2.0）

支持通过按钮式编辑器构造四则运算公式：

```json
{
  "custom_ioas": "16385,16386,16387",
  "custom_formula": "({0} + {1}) * {2} / 2",
  "period_ms": 1000
}
```

- 支持运算符：`+`、`-`、`*`、`/`、`(`、`)`
- 支持 2~50 个关联测点，使用 `{0}`、`{1}`... 作为占位符
- 递归下降表达式解析器，支持括号优先级和除零保护

---

## 9. 置数操作

### 9.1 置数与自动变化的关系

- **置数**：手动写入测点值，触发变化上送（COT=3）
- **自动变化**：引擎按策略自动修改值
- **两者独立**：置数不覆盖自动变化，自动变化不覆盖置数值
- 置数值独立存储，不随实时数据刷新覆盖

### 9.2 置数 REST API

```bash
# AI 遥测置数
curl -X PUT http://localhost:8989/api/v1/instances/{id}/points/16385 \
  -H 'Content-Type: application/json' \
  -d '{"value": 235.5}'

# DI 遥信置数
curl -X PUT http://localhost:8989/api/v1/instances/{id}/points/5 \
  -H 'Content-Type: application/json' \
  -d '{"bool_value": true}'

# PI 遥脉置数
curl -X PUT http://localhost:8989/api/v1/instances/{id}/points/10 \
  -H 'Content-Type: application/json' \
  -d '{"int_value": 42}'
```

### 9.3 批量置数（自动化测试核心）

```bash
curl -X POST http://localhost:8989/api/v1/instances/{id}/points/batch \
  -H 'Content-Type: application/json' \
  -d '{
    "points": [
      {"ioa": 16385, "value": 999.99},
      {"ioa": 5, "bool_value": false},
      {"ioa": 10, "int_value": 100}
    ]
  }'
```

### 9.4 品质描述 QDS

更新测点的品质描述信息：

```bash
curl -X PUT http://localhost:8989/api/points/{ioa}/qds \
  -H 'Content-Type: application/json' \
  -d '{"invalid": true, "blocked": true}'
```

QDS 字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| invalid | bool | 无效 |
| not_topical | bool | 非当前 |
| substituted | bool | 取代 |
| overflow | bool | 溢出 |
| blocked | bool | 闭锁 |

---

## 10. 运行管理

### 10.1 日志查看

```bash
# 查看实时日志
tail -f logs/output.log

# 查看最后 100 行
tail -100 logs/output.log
```

### 10.2 日志级别

| 级别 | 说明 |
|------|------|
| debug | 详细调试信息 |
| info | 常规运行信息（默认） |
| warn | 警告信息 |
| error | 错误信息 |

### 10.3 实例限制

- 最大实例数：**1000 个**（v2.4.0+ 从 10 提升至 1000）
- 每个实例只接受一个客户端连接
- 端口自动检测冲突

### 10.4 配置持久化

实例配置存储在 `config/instances.json` 中，格式：

```json
[
  {
    "id": "a1b2c3d4e5f6",
    "name": "变电站A",
    "iec104_port": 2404,
    "xlsx_file": "samples/point.xlsx",
    "enabled": false,
    "http_enabled": true,
    "http_port": 2405
  }
]
```

---

## 11. 跨平台编译与打包

### 11.1 Makefile 目标

```bash
make build-linux-amd64     # Linux amd64
make build-linux-arm64     # Linux arm64
make build-windows         # Windows amd64
make build-all             # 全平台二进制
make build-full            # 完整构建（含前端）
make dist                  # 三平台发行包
```

### 11.2 完整构建流程

```bash
# 1. 构建前端
cd web && npm install && npm run build && cd ..

# 2. 构建二进制（当前平台）
go build -ldflags="-s -w -X main.version=2.5.2" -o bin/gridsim ./cmd/gridsim/

# 3. 全平台一键打包
make dist
```

### 11.3 发行包

构建产物在 `dist/` 目录：
- `gridsim-v2.5.2-linux-amd64.tar.gz`
- `gridsim-v2.5.2-linux-arm64.tar.gz`
- `gridsim-v2.5.2-windows-amd64.zip`

---

## 12. 防火墙配置

模拟器在服务模式下自动管理 `iptables` 防火墙规则：

- 启动实例时自动放行对应 IEC104 和 HTTP 端口
- 停止实例时自动移除规则
- 规则注释：`gridsim-instance` / `gridsim-http`

> 需要 `iptables` 执行权限。如无法使用，启动日志会提示，不影响模拟器运行。

---

## 13. 常见问题

### 13.1 实例启动失败

**现象**：实例状态显示"错误"

**检查项**：
1. 点表文件是否已上传且格式正确
2. IEC104 端口是否被占用
3. 查看日志 `logs/output.log` 中的错误信息

### 13.2 客户端无法连接

**现象**：IEC104 客户端连接被拒绝

**检查项**：
1. 实例是否已启动（状态应为"运行中"）
2. IEC104 端口是否正确
3. 防火墙是否阻止了端口（检查 `iptables -L`）
4. 是否有其他客户端已连接（每个实例只接受一个客户端）

### 13.3 测点值不更新

**现象**：Web 界面显示的值不变

**检查项**：
1. 自动变化策略是否已启用（enabled=true）
2. 策略参数是否正确（如 period_ms 是否 ≥ 100）
3. CSV 回放文件是否已上传
4. 测点类型是否支持自动变化（仅 AI/DI/PI 支持）

### 13.4 Web 界面无法访问

**现象**：浏览器无法打开 `http://localhost:8989`

**检查项**：
1. 模拟器是否已启动
2. `--http` 参数指定的地址是否正确
3. 防火墙是否阻止了 8989 端口
4. 前端构建目录 `web/dist/` 是否存在

### 13.5 CSV 回放不工作

**现象**：配置了 CSV 回放策略但值不变

**检查项**：
1. CSV 文件是否已通过 Web UI 或 API 上传
2. CSV 格式是否正确（时间戳, 值）
3. 文件名是否与策略配置的 csv_file 一致
4. CSV 上传路径与引擎查找路径是否匹配（v2.2.0 已修复路径问题）

### 13.6 打包路径问题

**现象**：发行版中 Web UI 无法加载（空白页）

**原因**：Go 代码通过 `filepath.Dir(exePath)` 定位二进制所在目录，前端路径为相对 `../web/dist/`。打包时必须保持 `web/dist/` 目录层级。

**解决方法**：
```bash
# ✅ 正确
mkdir -p package/web/dist && cp -r web/dist/* package/web/dist/

# ❌ 错误
cp -r web/dist package/web/  # 会导致路径变成 web/index.html 而非 web/dist/index.html
```

### 13.7 Modbus 客户端连接失败

**现象**：Modbus TCP 客户端无法连接

**检查项**：
1. 实例协议类型是否设置为 `modbus_tcp`
2. 点表文件是否包含 Modbus 扩展列（register-address, function-code）
3. Modbus 端口是否正确（默认 502）
4. 防火墙是否阻止了 Modbus 端口
5. 字节序配置是否匹配客户端（ABCD/BADC/CDAB/DCBA）

### 13.8 CSV 多测点回放不工作

**现象**：配置了多列 CSV 回放但测点值不变

**检查项**：
1. CSV 第一列是否为 time 列（相对 ms/s 或绝对 hh:mm:ss）
2. 列名是否与 `csv_column_map` 中的映射一致
3. 每个映射的 IOA 是否存在于点表中
4. 单测点 CSV 模式完全不变，如只需单测点请使用原始格式
