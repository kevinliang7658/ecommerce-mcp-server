# 01 - 把"电商工具箱" MCP Server 接入 Claude Desktop 与 Kimi Code

> 前置：已完成 `pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`，并能跑通 `python mcp_server/server.py --self-test`。
> 本文档教两件事：把 MCP Server 挂到 Claude Desktop 上、挂到 Kimi Code CLI 上，然后在对话里让大模型真的调用你的工具。

## 先理解接入原理（30 秒）

```
 Claude Desktop / Kimi Code  ──(启动子进程, 走标准输入输出 stdio)──▶  python mcp_server/server.py
        │                                                                      │
        │  对话中模型判断"该用工具了"                                            │  @mcp.tool() 登记的
        └──────────────────  发工具调用请求 ────────────────────────────────────▶  三个函数
```

- 客户端（Claude / Kimi Code）根据配置**启动**你的 server.py 作为子进程，两者通过标准输入输出讲 MCP 协议（JSON-RPC）；
- 所以配置的核心就是告诉客户端：**用什么命令、在哪个目录、带什么环境变量**启动它；
- 工具的"说明书"是 docstring——模型靠它判断何时调用、怎么传参，docstring 写不好，模型就不会用。

## 一、接入 Claude Desktop

### 1. 找到配置文件

Windows 下 Claude Desktop 的配置文件在：

```
%APPDATA%\Claude\claude_desktop_config.json
```

（在资源管理器地址栏直接粘贴 `%APPDATA%\Claude` 回车即到。没有该文件就新建一个。）

### 2. 写入配置

```json
{
  "mcpServers": {
    "ecommerce-toolbox": {
      "command": "python",
      "args": [
        "C:/path/to/ecommerce-mcp-server/mcp_server/server.py"
      ],
      "env": {
        "DEEPSEEK_API_KEY": "sk-你的key"
      }
    }
  }
}
```

注意四个坑（全是新手高频事故）：

1. **路径分隔符**：JSON 里 `\` 要写成 `\\`，或者像上面一样直接用 `/`（Python 都认）；
2. **command 用 python 还是全路径**：如果 `python` 不在系统 PATH（比如装在虚拟环境），就写全路径，如 `"command": "C:/Users/你的用户名/AppData/Local/Programs/Python/Python312/python.exe"`；
3. **env 的作用**：子进程不继承你终端里的环境变量，key 要么写进这里的 `env`，要么确认它已设在"系统环境变量"里；
4. **改完配置要彻底退出 Claude Desktop 再开**（托盘图标右键 Quit），仅关窗口不生效。

### 3. 验证

- 重开 Claude Desktop，对话框下方出现 🔨（工具）图标，点开能看到 `exchange_rate_convert`、`logistics_track`、`marketing_copy_generate` 三个工具；
- 发一句："帮我查一下单号 YT10001 的包裹到哪了"；
- Claude 会弹出"是否允许调用 logistics_track"，点允许，就能看到它拿着工具返回的轨迹组织回答。

## 二、接入 Kimi Code（CLI）

Kimi Code 的 MCP 配置文件是 `mcp.json`，有两个级别：

| 级别 | 路径 | 生效范围 |
| --- | --- | --- |
| 用户级 | `C:\Users\你的用户名\.kimi-code\mcp.json` | 所有项目共享 |
| 项目级 | 项目目录下 `.kimi-code\mcp.json` | 仅当前项目，同名覆盖用户级 |

### 1. 写配置（用户级示例）

```json
{
  "mcpServers": {
    "ecommerce-toolbox": {
      "command": "python",
      "args": [
        "C:/path/to/ecommerce-mcp-server/mcp_server/server.py"
      ],
      "env": {
        "DEEPSEEK_API_KEY": "sk-你的key"
      }
    }
  }
}
```

带 `command` 字段的是 stdio 型 Server（本地子进程）；如果是远程 HTTP 型 Server，用 `"url": "https://..."` 字段。可选字段还有 `cwd`（子进程工作目录）、`enabled`（临时禁用）、`enabledTools`/`disabledTools`（工具黑白名单）等。

### 2. 验证

1. 启动 `kimi`，输入 `/mcp` 查看所有 Server 的连接状态，`ecommerce-toolbox` 应为已连接；
2. 也可以在 TUI 里用 `/mcp-config` 交互式增删改 Server，不用手编 JSON；
3. 直接对它说："29.99 美元按现在汇率是多少人民币？" —— Kimi Code 会调用 `mcp__ecommerce-toolbox__exchange_rate_convert`（MCP 工具的命名规则是 `mcp__<服务名>__<工具名>`）；
4. 首次调用会弹权限确认，选"本次会话内允许"后续就不再打断；想永久放行可在 `config.toml` 里加权限规则：

```toml
[[permission.rules]]
decision = "allow"
pattern = "mcp__ecommerce-toolbox__*"
```

## 三、两个客户端的对照小结

| | Claude Desktop | Kimi Code |
| --- | --- | --- |
| 配置文件 | `%APPDATA%\Claude\claude_desktop_config.json` | `~/.kimi-code/mcp.json`（用户级）/ `.kimi-code/mcp.json`（项目级） |
| 配置结构 | `mcpServers` → command/args/env | 完全相同的 `mcpServers` 结构（可以互相抄） |
| 查看工具 | 对话框 🔨 图标 | `/mcp` 命令 |
| 工具授权 | 每次询问 / 允许 | 每次询问 / 会话内允许 / config.toml 永久规则 |

看到没：**配置结构是一样的**——这就是 MCP 作为开放协议的价值：Server 写一次，所有支持 MCP 的客户端都能用。

## 四、排错清单

| 症状 | 排查 |
| --- | --- |
| 客户端里看不到工具 | 配置文件 JSON 语法错（多了逗号/路径单反斜杠没转义）；改完没彻底重启客户端 |
| Server 进程秒退 | 手动 `python mcp_server/server.py` 看报错；多半是 mcp 包没装或 Python 版本不对 |
| 工具调用报 401 | `env` 里的 DEEPSEEK_API_KEY 没配或失效（只影响文案工具，汇率/物流不受影响） |
| 模型"想不到"用工具 | docstring 描述不清。把"当用户询问……时使用"这类触发场景写进 docstring |
| 中文参数乱码 | 确认 Python 文件是 UTF-8 保存，且系统区域/终端编码为 UTF-8 |

## 五、从演示到生产

- 本地 stdio 适合"个人助理"场景；团队共用应把 Server 部署成 HTTP 型（FastMCP 支持），客户端配 `url` 接入；
- 危险操作（写库、发邮件）要么别做成工具，要么在函数里二次确认 + 记录审计日志；
- 工具返回内容会进入模型上下文，注意截断超长返回，别把整张表塞回去。
