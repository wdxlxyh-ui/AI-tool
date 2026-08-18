# Azure Blob SAS 令牌获取教程

## 步骤详解

### 1. 登录 Azure Portal

1. 打开浏览器访问：https://portal.azure.com
2. 使用你的 Azure 账号登录

### 2. 查找存储账户

1. 在右上角搜索框输入：`Storage Account`
2. 选择你对应的存储账户
3. 点进第一个结果（edgeadls2 通常是最新的）

### 3. 进入容器页面

1. 在左侧菜单中找到并点击 **"Containers"**
2. 在容器列表中找到名为 `edge` 的容器
3. 点击进入该容器

### 4. 生成 SAS 令牌

#### 方法一：在容器页面

1. 点击容器上方的 **"Settings"** 按钮
2. 选择 **"Shared access signature"**
3. 在 "New SAS" 部分，勾选权限：
   - ✅ **Read**（读取）
   - ✅ **List**（列出文件）
4. 选择过期时间：
   - 推荐：1 年（从现在开始的 365 天）
5. 点击 **"Generate SAS token and connection string"**

#### 方法二：在存储账户总览页面

1. 点击左侧菜单的 **"Security + networking"**
2. 找到 **"Access keys"**
3. 点击第一组密钥下方的 **"Azure Storage Explorer"** 链接
4. 在 Azure Storage Explorer 中选择：`edge` → `blob`
5. 右键点击任意文件 → **"Get SAS URL"**

### 5. 复制 SAS 令牌

在生成页面中，你会看到两个部分：

#### 重要部分：SAS Token

```
sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=YYYY-MM-DD...etc...
```

**复制这个部分，格式类似于：**

```
sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=2027-06-08T12:00:00Z&st=2026-06-09T04:00:00Z&spr=https&sig=xxxxxxx...xxxx
```

不要复制整个 URL，只需要 SAS Token 后缀！

#### Header 部分示例

如果你想构造完整 URL，可以这样组合：

**Blob URL 基础：**
```
https://edgeadls2.blob.core.chinacloudapi.cn/edge
```

**SAS Token：**
```
sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=2027-06-08T12:00:00Z&st=2026-06-09T04:00:00Z&spr=https&sig=xxxxxxx...xxxx
```

**完整 Blob 下载 URL：**
```
https://edgeadls2.blob.core.chinacloudapi.cn/edge/edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz?sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=2027-06-08T12:00:00Z&st=2026-06-09T04:00:00Z&spr=https&sig=xxxxxxx...xxxx
```

### 6. 配置到 .env 文件

#### 复制示例配置文件

```bash
cp .env.example .env
```

#### 编辑 .env 文件

```bash
vim .env
```

#### 填写 SAS 令牌

```bash
# 格式：不要在前面加 "sv=" 或 "?"，直接复制完整的查询参数
AZURE_BLOB_SAS_TOKEN=sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=2027-06-08T12:00:00Z&st=2026-06-09T04:00:00Z&spr=https&sig=xxxxxxx...xxxx
```

#### 保存文件

```bash
:wq
```

### 7. 验证 SAS 令牌

```bash
# 测试 Azure Blob 连接
python blob_tool.py \
    --check "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz" \
    --list "edgeftpfile/edge-ems/"
```

如果看到 "✅ 文件存在"，说明 SAS 令牌配置正确。

## 常见问题

### Q1: SAS 令牌过期怎么办？

**回答：** SAS 令牌有过期时间，过期后需要：
1. 重新进入 Azure Portal
2. 重新生成 SAS 令牌
3. 更新 .env 文件中的 SAS 令牌值

### Q2: SAS 令牌权限不够？

**回答：** 确保勾选以下权限：
- ✅ Read（读取）
- ✅ List（列出）

如果缺少权限，下载或列出文件时会出现错误。

### Q3: 如何测试 SAS 令牌是否有效？

**回答：**
```bash
# 使用项目提供的 Blob 工具
python blob_tool.py \
    --check "edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz"
```

或使用 curl：

```bash
export SAS_TOKEN="sv=2021-06-08&ss=b&srt=sco&sp=rwl&se=2027-06-08T12:00:00Z&st=2026-06-09T04:00:00Z&spr=https&sig=xxxxxxx...xxxx"

curl -I \
  "https://edgeadls2.blob.core.chinacloudapi.cn/edge/edgeftpfile/edge-ems/develop_2605/HPUY/edge-ems.tar.gz?$SAS_TOKEN"
```

返回 200 OK 说明凭证有效。

### Q4: 生产环境和测试环境用不同的 SAS 令牌？

**回答：** 当然可以！这样可以：
- 生产环境使用安全完整的 SAS 令牌
- 开发测试环境使用更短有效期的测试 SAS 令牌
- 便于管理和监控不同的访问权限

## 安全提示

### ⚠️ 一定要注意

1. **不要分享你的 .env 文件**
   - .env 文件包含敏感信息（SAS 令牌、服务器密码）
   - 绝对不要提交到 Git 仓库
   - 安全存储在本地

2. **定期更换 SAS 令牌**
   - SAS 令牌有有效期
   - 长期使用的 SAS 令牌可能需要更新
   - 服务器密码也建议定期更换

3. **最小权限原则**
   - 只勾选必要的权限（Read + List）
   - 不要勾选 Write、Delete 等高危权限
   - 定期检查 Azure Portal 中的令牌列表

## 详细文档

- [Azure Blob Storage 官方文档](https://learn.microsoft.com/zh-cn/azure/storage/blobs/storage-blobs-introduction)
- [SAS 令牌详解](https://learn.microsoft.com/zh-cn/azure/storage/common/storage-sas-overview)
- [Blob 服务快速入门](https://learn.microsoft.com/zh-cn/azure/storage/blobs/storage-quickstart-blobs-python)
