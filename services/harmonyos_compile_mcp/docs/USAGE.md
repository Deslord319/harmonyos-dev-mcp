# HarmonyOS Compile MCP 使用指南

## 概述

HarmonyOS Compile MCP 提供 **编译结果验证** 功能，采用 **AI 生成脚本 + 本地执行 + MCP 验证** 的工作流。

## 设计理念

### 为什么只保留验证工具？

编译流程（克隆 → 分析 → 配置 → 编译）具有高度灵活性：
- 不同项目的构建系统差异大（CMake/Makefile/GN/Meson）
- 编译参数需要根据具体项目调整
- 环境配置因用户而异

**大模型擅长**：分析构建文件、生成定制化脚本
**MCP 工具擅长**：执行本地无法完成的操作（如验证 .so 文件格式）

因此，我们将编译流程交给 AI 生成脚本，MCP 只负责验证结果。

---

## 工作流

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  1. AI 分析阶段   │ ──→ │  2. 本地执行阶段  │ ──→ │  3. MCP 验证阶段  │
│                 │     │                 │     │                 │
│ - 用户提供构建   │     │ - 用户执行脚本   │     │ - AI 调用 verify  │
│   文件内容      │     │ - 完成编译      │     │   工具          │
│ - AI 生成编译   │     │ - 输出 .so 文件   │     │ - 验证文件格式  │
│   脚本          │     │                 │     │ - 返回验证结果  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 使用步骤

### Step 1: AI 分析构建文件

用户将项目的构建文件内容发送给 AI：

```
请分析这个 CMakeLists.txt，生成 HarmonyOS 编译脚本：

[粘贴 CMakeLists.txt 内容]
```

AI 会分析：
- 构建系统类型（CMake/Makefile/GN）
- 依赖库和编译选项
- 目标架构和输出格式

### Step 2: AI 生成编译脚本

AI 生成完整的编译脚本：

```bash
#!/bin/bash
# 由 AI 生成的编译脚本

REPO_URL="https://github.com/example/library.git"
VERSION="v1.0.0"
LOCAL_PATH="./library"
BUILD_DIR="./build_harmonyos"

# ... 完整的编译逻辑
```

### Step 3: 用户本地执行

用户在本地终端执行脚本：

```bash
# 设置环境变量（如果需要）
export HARMONYOS_SDK_PATH="/path/to/sdk"

# 执行脚本
bash compile_cmake.sh
```

脚本执行完成后，输出 `.so` 文件位置。

### Step 4: MCP 验证结果

AI 调用 `verify_compile_result` 工具验证编译结果：

```python
result = await client.call_tool("verify_compile_result", {
    "project_dir": "./library",
    "output_dir": "./build_harmonyos"
})
```

验证内容包括：
- ✅ 文件是否存在
- ✅ 文件格式（ELF）
- ✅ 架构信息（ARM/AArch64）
- ✅ 依赖库检查
- ✅ 符号表验证

### Step 5: 迭代优化（如需要）

如果验证失败，AI 根据错误信息调整脚本：

```
验证发现 .so 文件格式不正确，可能是编译器配置问题。
请修改脚本中的 CMAKE_TOOLCHAIN_FILE 路径，然后重新执行。
```

---

## 可用工具

### `verify_compile_result`

验证编译输出的 `.so` 文件。

**参数**:
- `project_dir` (必填): 项目目录路径
- `output_dir` (可选): 输出目录（默认为 `project_dir/build_harmonyos`）

**返回**:
```json
{
  "verified": true,
  "so_files": [...],
  "so_count": 1,
  "valid_count": 1
}
```

---

## 示例脚本

### CMake 项目

```bash
# 核心配置
cmake -S . -B ./build_harmonyos \
  -DCMAKE_TOOLCHAIN_FILE=$SDK/openharmony/native/build-tools/cmake/ohos.toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release

cmake --build ./build_harmonyos
```

### Makefile 项目

```bash
# 设置交叉编译环境变量
export CC=aarch64-unknown-linux-ohos-clang
export CXX=aarch64-unknown-linux-ohos-clang++

# 执行编译
./configure --host=aarch64-unknown-linux-ohos
make -j$(nproc)
```

---

## 环境准备

### 必需工具

| 工具 | 用途 | 安装方式 |
|------|------|---------|
| Git | 克隆代码仓库 | 系统包管理器 |
| CMake | CMake 项目编译 | `apt install cmake` |
| Make | Makefile 项目编译 | `apt install build-essential` |

### HarmonyOS SDK

从 [HarmonyOS 开发者官网](https://developer.huawei.com/consumer/cn/harmonyos/) 下载 SDK，并设置环境变量：

```bash
export HARMONYOS_SDK_PATH="/path/to/harmonyos/sdk"
```

### WSL（Windows 用户）

Windows 用户需要在 WSL 环境中执行编译：

```bash
# 安装 WSL (Windows 10/11)
wsl --install

# 在 WSL 中安装编译工具
sudo apt update && sudo apt install -y cmake build-essential git
```

---

## 常见问题

### Q: 验证失败，提示"不是有效的 ELF 文件"

**原因**: 使用了错误的编译器或编译参数。

**解决**:
1. 确认 `CMAKE_TOOLCHAIN_FILE` 指向正确的工具链文件
2. 检查 `CC` 和 `CXX` 环境变量是否指向 HarmonyOS 编译器
3. 清理构建目录后重新编译

### Q: 找不到 `.so` 文件

**原因**: 编译配置错误或输出目录不对。

**解决**:
1. 检查脚本中的 `BUILD_DIR` 配置
2. 查看编译日志，确认编译是否成功
3. 手动查找：`find . -name "*.so"`

### Q: 如何指定目标架构？

修改脚本中的 `TARGET_ARCH` 变量：

```bash
# 可选值：aarch64, armv7, x86_64
export TARGET_ARCH="aarch64"
```

---

## 最佳实践

1. **脚本版本控制**: 将 AI 生成的脚本保存到项目目录，便于复用和修改
2. **环境变量管理**: 使用 `.env` 文件管理 SDK 路径等配置
3. **增量编译**: 修改脚本后，先清理构建目录再重新编译
4. **验证先行**: 编译完成后立即调用 `verify_compile_result` 验证

---

## 相关资源

- [HarmonyOS 命令行工具文档](https://developer.huawei.com/consumer/cn/doc/harmonyos-guides/ide-commandline-get)
- [CMake 交叉编译指南](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html)
