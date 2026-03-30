#!/bin/bash

# 获取当前脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

APP_NAME="MacStockTicker"
APP_BUNDLE="${APP_NAME}.app"
CONTENTS_DIR="${APP_BUNDLE}/Contents"
MACOS_DIR="${CONTENTS_DIR}/MacOS"
RESOURCES_DIR="${CONTENTS_DIR}/Resources"

echo "正在清理旧的构建..."
rm -rf "${APP_BUNDLE}"

echo "正在创建 App 结构..."
mkdir -p "${MACOS_DIR}"
mkdir -p "${RESOURCES_DIR}"

echo "正在编译 Swift 代码..."
swiftc -o "${MACOS_DIR}/${APP_NAME}" StockTicker.swift -framework SwiftUI -framework AppKit -framework Combine

if [ $? -eq 0 ]; then
    echo "编译成功！"
else
    echo "编译失败。"
    exit 1
fi

echo "正在生成 Info.plist..."
cat > "${CONTENTS_DIR}/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIdentifier</key>
    <string>com.hahaho.${APP_NAME}</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleVersion</key>
    <string>1</string>
    <key>LSMinimumSystemVersion</key>
    <string>11.0</string>
    <key>LSUIElement</key>
    <true/>
</dict>
</plist>
EOF

echo "App 打包完成: ${APP_BUNDLE}"

# 询问是否安装到 Applications
read -p "是否要安装到 /Applications 目录? (y/n): " INSTALL
if [[ "$INSTALL" == "y" || "$INSTALL" == "Y" ]]; then
    echo "正在复制到 /Applications..."
    cp -R "${APP_BUNDLE}" /Applications/
    echo "安装完成！您现在可以在启动台中找到 ${APP_NAME}，或通过 Spotlight 搜索打开它。"
else
    echo "您可以直接双击当前目录下的 ${APP_BUNDLE} 运行它。"
fi
