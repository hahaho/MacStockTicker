#!/bin/bash

# 获取当前脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 如果没有提供参数，则使用默认股票 (新浪接口支持 sh/sz 前缀)
# 支持通过参数传递，或在 ~/.stock_ticker_config.txt 中配置
STOCKS=${@}

echo "正在编译 StockTicker (新浪财经版)..."
swiftc -o StockTicker StockTicker.swift -framework SwiftUI -framework AppKit -framework Combine

if [ $? -eq 0 ]; then
    echo "启动成功！"
    echo "提示：已默认置顶大盘指数 (上证/深证/创业板)。"
    echo "配置说明：您可以在命令行传入参数，或在 ~/.stock_ticker_config.txt 中每行写入一个股票代码。"
    # 后台运行
    ./StockTicker $STOCKS &
else
    echo "编译失败。"
fi
