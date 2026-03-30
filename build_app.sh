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
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
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
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>
        <true/>
    </dict>
</dict>
</plist>
EOF

echo "正在生成基础应用图标..."
ICONSET_DIR="AppIcon.iconset"
mkdir -p "${ICONSET_DIR}"

# 创建一个带股票图表的精美图标
cat > create_icon.swift <<'EOF'
import AppKit

let size = CGSize(width: 1024, height: 1024)
let image = NSImage(size: size)
image.lockFocus()

// 1. 绘制圆角矩形背景 (深灰色，带一点质感)
let bounds = NSRect(origin: .zero, size: size)
let bgPath = NSBezierPath(roundedRect: bounds, xRadius: 224, yRadius: 224)
NSColor(red: 0.15, green: 0.15, blue: 0.17, alpha: 1.0).setFill()
bgPath.fill()

// 2. 绘制股票走势线 (绿色上升)
let path = NSBezierPath()
path.lineWidth = 60
path.lineCapStyle = .round
path.lineJoinStyle = .round
path.move(to: NSPoint(x: 200, y: 300))
path.line(to: NSPoint(x: 400, y: 450))
path.line(to: NSPoint(x: 600, y: 350))
path.line(to: NSPoint(x: 800, y: 700))
NSColor(red: 0.2, green: 0.8, blue: 0.2, alpha: 1.0).setStroke()
path.stroke()

// 3. 绘制上涨箭头
let arrowPath = NSBezierPath()
arrowPath.move(to: NSPoint(x: 700, y: 700))
arrowPath.line(to: NSPoint(x: 800, y: 700))
arrowPath.line(to: NSPoint(x: 800, y: 600))
arrowPath.lineWidth = 60
arrowPath.lineCapStyle = .round
arrowPath.lineJoinStyle = .round
arrowPath.stroke()

image.unlockFocus()

if let tiff = image.tiffRepresentation, let bitmap = NSBitmapImageRep(data: tiff) {
    let pngData = bitmap.representation(using: .png, properties: [:])
    try? pngData?.write(to: URL(fileURLWithPath: "icon_1024.png"))
}
EOF

swift create_icon.swift

# 使用 sips 生成各个尺寸的图标
sips -z 1024 1024 icon_1024.png --out "${ICONSET_DIR}/icon_512x512@2x.png" > /dev/null 2>&1
sips -z 512 512 icon_1024.png --out "${ICONSET_DIR}/icon_512x512.png" > /dev/null 2>&1
sips -z 512 512 icon_1024.png --out "${ICONSET_DIR}/icon_256x256@2x.png" > /dev/null 2>&1
sips -z 256 256 icon_1024.png --out "${ICONSET_DIR}/icon_256x256.png" > /dev/null 2>&1
sips -z 256 256 icon_1024.png --out "${ICONSET_DIR}/icon_128x128@2x.png" > /dev/null 2>&1
sips -z 128 128 icon_1024.png --out "${ICONSET_DIR}/icon_128x128.png" > /dev/null 2>&1
sips -z 128 128 icon_1024.png --out "${ICONSET_DIR}/icon_64x64@2x.png" > /dev/null 2>&1
sips -z 64 64 icon_1024.png --out "${ICONSET_DIR}/icon_64x64.png" > /dev/null 2>&1
sips -z 64 64 icon_1024.png --out "${ICONSET_DIR}/icon_32x32@2x.png" > /dev/null 2>&1
sips -z 32 32 icon_1024.png --out "${ICONSET_DIR}/icon_32x32.png" > /dev/null 2>&1
sips -z 32 32 icon_1024.png --out "${ICONSET_DIR}/icon_16x16@2x.png" > /dev/null 2>&1
sips -z 16 16 icon_1024.png --out "${ICONSET_DIR}/icon_16x16.png" > /dev/null 2>&1

iconutil -c icns "${ICONSET_DIR}" -o "${RESOURCES_DIR}/AppIcon.icns"
rm -rf "${ICONSET_DIR}" create_icon.swift icon_1024.png

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
