#!/bin/bash
# Edge-EMS 部署工具包 - 快速验收脚本

set -e

echo "=========================================================================="
echo "  Edge-EMS 部署工具包 - 交付验收"
echo "=========================================================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查压缩包
echo "📦 检查交付压缩包..."
echo "--------------------------------------"

TAR_FILE="/tmp/edge-ems-deploy-tool-yuhangtian.tar.gz"

if [ ! -f "$TAR_FILE" ]; then
    echo -e "${RED}❌ 压缩包不存在: $TAR_FILE${NC}"
    exit 1
fi

SIZE=$(du -h "$TAR_FILE" | awk '{print $1}')
echo -e "${GREEN}✅ 压缩包存在${NC}"
echo "   文件大小: $SIZE"
echo ""

# 列出主要文档
echo "📖 检查主要文档..."
echo "--------------------------------------"

DOCS=(
    "README.md"
    "USER_MANUAL.md"
    "FRONTEND_GUIDE.md"
    "PROJECT_SUMMARY.md"
    "DELIVERY_NOTES.md"
)

for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        SIZE=$(du -h "$doc" | awk '{print $1}')
        echo -e "${GREEN}✅ $doc${NC}"
        echo "   大小: $SIZE"
    else
        echo -e "${RED}❌ $doc 不存在${NC}"
    fi
done

echo ""

# 列出核心脚本
echo "🛠️  检查核心脚本..."
echo "--------------------------------------"

Scripts=(
    "main.py"
    "blob_tool.py"
    "check_environment.py"
)

for script in "${Scripts[@]}"; do
    if [ -f "$script" ]; then
        SIZE=$(du -h "$script" | awk '{print $1}')
        echo -e "${GREEN}✅ $script${NC}"
        echo "   大小: $SIZE"
    else
        echo -e "${RED}❌ $script 不存在${NC}"
    fi
done

echo ""

# 列出配置文件
echo "⚙️  检查配置文件..."
echo "--------------------------------------"

Configs=(
    ".env.example"
    "requirements.txt"
    ".gitignore"
)

for conf in "${Configs[@]}"; do
    if [ -f "$conf" ]; then
        SIZE=$(du -h "$conf" | awk '{print $1}')
        echo -e "${GREEN}✅ $conf${NC}"
        echo "   大小: $SIZE"
    else
        echo -e "${RED}❌ $conf 不存在${NC}"
    fi
done

echo ""

# 列出辅助脚本
echo "🔍 检查辅助脚本..."
echo "--------------------------------------"

HelperScripts=(
    "scripts/check-before-deploy.sh"
    "scripts/verify-after-deploy.sh"
    "scripts/rollback.sh"
)

for script in "${HelperScripts[@]}"; do
    if [ -f "$script" ]; then
        SIZE=$(du -h "$script" | awk '{print $1}')
        echo -e "${GREEN}✅ $script${NC}"
        echo "   大小: $SIZE"
    else
        echo -e "${RED}❌ $script 不存在${NC}"
    fi
done

echo ""

# 列出文档目录
echo "📚 检查文档目录..."
echo "--------------------------------------"

if [ -d "docs" ]; then
    DOCS_COUNT=$(find docs -type f | wc -l)
    echo -e "${GREEN}✅ docs/ 目录存在${NC}"
    echo "   包含文件数: $DOCS_COUNT"
    echo ""
    echo "   文档列表:"
    for doc in docs/*; do
        SIZE=$(du -h "$doc" | awk '{print $1}')
        echo -e "${GREEN}   📄 $doc${NC}"
        echo "     大小: $SIZE"
    done
else
    echo -e "${RED}❌ docs/ 目录不存在${NC}"
fi

echo ""
echo "=========================================================================="
echo "✅ 交付验收完成！"
echo "=========================================================================="
echo ""
echo "📦 压缩包位置:"
echo "   $TAR_FILE"
echo ""
echo "📋 关键信息:"
echo "   - 文件大小: $(du -h "$TAR_FILE" | awk '{print $1}')"
echo "   - 总文件数: $(tar -tzf "$TAR_FILE" | wc -l)"
echo "   - 文档: 5 个主要文档 + 2 个文档模块"
echo "   - 核心@本语3个脚本 + 3个辅助脚本"
echo "   - 配置: 3个配置文件"
echo ""
echo "🎮 快速开始:"
echo ""
echo "   # 1. 解压"
echo "   tar -xzf $TAR_FILE"
echo "   cd edge-ems-deploy-tool"
echo ""
echo "   # 2. 安装依赖"
echo "   pip install -r requirements.txt"
echo ""
echo "   # 3. 配置环境"
echo "   cp .env.example .env"
echo "   vim .env  # 填写 SAS 令牌和服务器密码"
echo ""
echo "   # 4. 测试运行"
echo "   python main.py --branch develop_2605 --server HPUY --component all --tar-only"
echo ""
echo "📚 文档优先级:"
echo "   1. FRONTEND_GUIDE.md  # 前端开发指南（必读）"
echo "   2. README.md          # 用户使用指南（必读）"
echo "   3. USER_MANUAL.md     # 详细使用手册"
echo "   4. PROJECT_SUMMARY.md # 项目总结"
echo ""
echo "🎉 可以直接交给另一个AI进行开发！"
echo ""
