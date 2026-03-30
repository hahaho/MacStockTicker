import SwiftUI
import AppKit
import Combine

// --- Preference Keys ---
struct WidthPreferenceKey: PreferenceKey {
    static var defaultValue: CGFloat = 0
    static func reduce(value: inout CGFloat, nextValue: () -> CGFloat) {
        value = nextValue()
    }
}

// --- Window Manager ---
class WindowManager: ObservableObject {
    weak var window: NSPanel?
    
    // 保存用户的偏好
    @AppStorage("isMinimized") var isMinimized: Bool = false {
        didSet {
            updateWindowFrame()
        }
    }
    
    func updateWindowFrame() {
        guard let window = window else { return }
        
        // 展开状态下高度增加到 500 以显示更多股票，最小化状态变为长条
        let newSize = isMinimized ? CGSize(width: 800, height: 40) : CGSize(width: 280, height: 500)
        var frame = window.frame
        
        // 保持右上角/右侧锚点固定
        let maxX = frame.maxX
        let maxY = frame.maxY
        frame.size = newSize
        frame.origin.x = maxX - newSize.width
        frame.origin.y = maxY - newSize.height
        
        // 增加平滑动画
        NSAnimationContext.runAnimationGroup({ context in
            context.duration = 0.3
            context.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            window.animator().setFrame(frame, display: true)
        }, completionHandler: nil)
    }
}

// --- Data Models ---
struct StockInfo: Identifiable, Equatable {
    var id: String { symbol }
    let symbol: String
    var name: String
    var price: Double
    var open: Double
    var lastClose: Double
    var high: Double
    var low: Double
    var volume: Double
    var turnover: Double
    var date: String
    var time: String
    
    var change: Double {
        return price - lastClose
    }
    
    var percentChange: Double {
        return lastClose != 0 ? (change / lastClose) * 100 : 0.0
    }
    
    var color: Color {
        if change > 0 { return Color(red: 1.0, green: 0.3, blue: 0.3) }
        if change < 0 { return Color(red: 0.2, green: 0.8, blue: 0.2) }
        return .primary
    }
    
    var formattedPrice: String { String(format: "%.2f", price) }
    var formattedChange: String {
        let sign = change > 0 ? "+" : ""
        return "\(sign)\(String(format: "%.2f", change))"
    }
    var formattedPercent: String {
        let sign = change > 0 ? "+" : ""
        return "\(sign)\(String(format: "%.2f", percentChange))%"
    }
    var formattedVolume: String {
        if volume > 100000000 {
            return String(format: "%.2f亿", volume / 100000000)
        } else if volume > 10000 {
            return String(format: "%.2f万", volume / 10000)
        }
        return "\(Int(volume))"
    }
    
    static func == (lhs: StockInfo, rhs: StockInfo) -> Bool {
        return lhs.symbol == rhs.symbol && lhs.price == rhs.price && lhs.time == rhs.time
    }
}

class StockViewModel: ObservableObject {
    @Published var stocks: [StockInfo] = []
    @Published var indices: [StockInfo] = []
    private var cancellables = Set<AnyCancellable>()
    private var symbols: [String] = []
    
    private let indexSymbols = ["sh000001", "sz399001", "sz399006"]
    
    init() {
        loadConfig()
        fetchStocks()
        Timer.publish(every: 5, on: .main, in: .common)
            .autoconnect()
            .sink { [weak self] _ in
                self?.fetchStocks()
            }
            .store(in: &cancellables)
    }
    
    func loadConfig() {
        let defaults = UserDefaults.standard
        let savedSymbolsKey = "SavedStockSymbols"
        
        let args = ProcessInfo.processInfo.arguments
        if args.count > 1 {
            let argSymbols = Array(args[1...])
            let normalized = argSymbols.map { normalizeSymbol($0) }
            self.symbols = normalized
            defaults.set(normalized, forKey: savedSymbolsKey)
            return
        }
        
        if let savedSymbols = defaults.array(forKey: savedSymbolsKey) as? [String], !savedSymbols.isEmpty {
            self.symbols = savedSymbols
            return
        }
        
        let defaultSymbols = ["sh600519", "sh601318", "sz000858", "sh600036"]
        self.symbols = defaultSymbols
        defaults.set(defaultSymbols, forKey: savedSymbolsKey)
    }
    
    func addStock(_ symbol: String) {
        let normalized = normalizeSymbol(symbol)
        if !symbols.contains(normalized) && !indexSymbols.contains(normalized) {
            symbols.append(normalized)
            let defaults = UserDefaults.standard
            let savedSymbolsKey = "SavedStockSymbols"
            defaults.set(symbols, forKey: savedSymbolsKey)
            fetchStocks()
        }
    }
    
    func removeStock(_ symbol: String) {
        symbols.removeAll { $0 == symbol }
        let defaults = UserDefaults.standard
        let savedSymbolsKey = "SavedStockSymbols"
        defaults.set(symbols, forKey: savedSymbolsKey)
        stocks.removeAll { $0.symbol == symbol }
    }
    
    private func normalizeSymbol(_ s: String) -> String {
        if s.count == 6 && CharacterSet.decimalDigits.isSuperset(of: CharacterSet(charactersIn: s)) {
            return (s.hasPrefix("6") || s.hasPrefix("9") || s.hasPrefix("5")) ? "sh\(s)" : "sz\(s)"
        }
        return s.lowercased()
    }
    
    func fetchStocks() {
        let allSymbols = indexSymbols + symbols
        let list = allSymbols.joined(separator: ",")
        let urlString = "http://hq.sinajs.cn/list=\(list)"

        guard let url = URL(string: urlString) else { return }
        
        var request = URLRequest(url: url)
        request.setValue("http://finance.sina.com.cn", forHTTPHeaderField: "Referer")
        request.setValue("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", forHTTPHeaderField: "User-Agent")
        
        URLSession.shared.dataTaskPublisher(for: request)
            .map { $0.data }
            .receive(on: DispatchQueue.main)
            .sink(receiveCompletion: { _ in }, receiveValue: { [weak self] data in
                let cfEncoding = CFStringEncodings.GB_18030_2000
                let encoding = String.Encoding(rawValue: CFStringConvertEncodingToNSStringEncoding(CFStringEncoding(cfEncoding.rawValue)))
                guard let content = String(data: data, encoding: encoding) else { return }
                
                self?.parseSinaResponse(content)
            })
            .store(in: &cancellables)
    }
    
    private func parseSinaResponse(_ content: String) {
        let lines = content.components(separatedBy: .newlines)
        var newStocks: [StockInfo] = []
        var newIndices: [StockInfo] = []
        
        for line in lines where line.contains("\"") {
            guard let range = line.range(of: "hq_str_") else { continue }
            let afterPrefix = line[range.upperBound...]
            guard let equalIndex = afterPrefix.firstIndex(of: "=") else { continue }
            let symbol = String(afterPrefix[..<equalIndex])
            
            guard let dataStr = line.components(separatedBy: "\"").dropFirst().first else { continue }
            
            let parts = dataStr.components(separatedBy: ",")
            if parts.count >= 32 {
                let info = StockInfo(
                    symbol: String(symbol),
                    name: parts[0],
                    price: Double(parts[3]) ?? 0.0,
                    open: Double(parts[1]) ?? 0.0,
                    lastClose: Double(parts[2]) ?? 0.0,
                    high: Double(parts[4]) ?? 0.0,
                    low: Double(parts[5]) ?? 0.0,
                    volume: Double(parts[8]) ?? 0.0,
                    turnover: Double(parts[9]) ?? 0.0,
                    date: parts[30],
                    time: parts[31]
                )
                
                if self.indexSymbols.contains(info.symbol) {
                    newIndices.append(info)
                } else {
                    newStocks.append(info)
                }
            }
        }
        
        DispatchQueue.main.async {
            self.indices = newIndices.sorted { (a, b) -> Bool in
                guard let aIndex = self.indexSymbols.firstIndex(of: a.symbol),
                      let bIndex = self.indexSymbols.firstIndex(of: b.symbol) else { return false }
                return aIndex < bIndex
            }
            
            self.stocks = newStocks.sorted { (a, b) -> Bool in
                guard let aIndex = self.symbols.firstIndex(of: a.symbol),
                      let bIndex = self.symbols.firstIndex(of: b.symbol) else { return false }
                return aIndex < bIndex
            }
        }
    }
}

// --- UI Components ---

struct VisualEffectView: NSViewRepresentable {
    let material: NSVisualEffectView.Material
    let blendingMode: NSVisualEffectView.BlendingMode
    
    func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.material = material
        view.blendingMode = blendingMode
        view.state = .active
        return view
    }
    
    func updateNSView(_ nsView: NSVisualEffectView, context: Context) {}
}

// 提取单个股票的跑马灯视图
struct MarqueeItemView: View {
    let stock: StockInfo
    var body: some View {
        HStack(spacing: 8) {
            Text(stock.name)
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.white)
                .lineLimit(1)
                .fixedSize()
            Text(stock.formattedPrice)
                .font(.system(size: 14, weight: .semibold, design: .monospaced))
                .foregroundColor(stock.color)
                .lineLimit(1)
                .fixedSize()
            Text(stock.formattedPercent)
                .font(.system(size: 14, design: .monospaced))
                .foregroundColor(stock.color)
                .lineLimit(1)
                .fixedSize()
        }
        .padding(.horizontal, 10)
    }
}

// 极简跑马灯组件：利用 ScrollView 结合手动 Offset
struct MarqueeView: View {
    let stocks: [StockInfo]
    
    // 动画相关状态
    @State private var offset: CGFloat = 0
    @State private var isAnimating = false
    
    // 基础参数
    let spacing: CGFloat = 20
    let scrollSpeed: Double = 30.0 // 约 30px / 秒
    
    var body: some View {
        GeometryReader { geometry in
            // 计算全部内容的近似宽度（如果不准确，可以让它更宽）
            // 这里我们采用双倍渲染，确保首尾相连
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: spacing) {
                    stockList
                    stockList // 复制一份用于无缝连接
                }
                .fixedSize(horizontal: true, vertical: false)
                .background(GeometryReader { contentGeo -> Color in
                    // 在渲染完成时获取第一组内容的真实宽度
                    DispatchQueue.main.async {
                        let totalWidth = contentGeo.size.width
                        let singleWidth = (totalWidth - spacing) / 2
                        startAnimation(contentWidth: singleWidth)
                    }
                    return Color.clear
                })
                .offset(x: offset)
            }
            // 禁用手动滑动，完全交由动画接管
            .disabled(true)
        }
        .clipped()
    }
    
    var stockList: some View {
        HStack(spacing: spacing) {
            ForEach(stocks, id: \.symbol) { stock in
                MarqueeItemView(stock: stock)
            }
        }
    }
    
    private func startAnimation(contentWidth: CGFloat) {
        // 避免重复启动
        guard !isAnimating && contentWidth > 0 else { return }
        isAnimating = true
        
        // 计算完整滚过一轮所需的时间
        let duration = Double(contentWidth) / scrollSpeed
        
        // 重置位置
        offset = 0
        
        // 执行线性动画
        withAnimation(.linear(duration: duration).repeatForever(autoreverses: false)) {
            offset = -contentWidth - spacing
        }
    }
}

struct IndexRow: View {
    let stock: StockInfo
    var body: some View {
        VStack(spacing: 2) {
            Text(stock.name)
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(.white)
            Text(stock.formattedPrice)
                .font(.system(size: 14, weight: .semibold, design: .monospaced))
                .foregroundColor(stock.color)
            Text(stock.formattedPercent)
                .font(.system(size: 10, design: .monospaced))
                .foregroundColor(stock.color)
        }
        .frame(maxWidth: .infinity)
        .shadow(color: .black.opacity(0.8), radius: 1, x: 0, y: 1)
    }
}

struct StockRow: View {
    let stock: StockInfo
    @ObservedObject var viewModel: StockViewModel
    @State private var isHovered = false
    
    var body: some View {
        VStack(spacing: 4) {
            HStack(alignment: .bottom) {
                VStack(alignment: .leading, spacing: 0) {
                    Text(stock.name)
                        .font(.system(size: 14, weight: .bold))
                        .foregroundColor(.white)
                    Text(stock.symbol.uppercased())
                        .font(.system(size: 10))
                        .foregroundColor(.white.opacity(0.7))
                }
                Spacer()
                VStack(alignment: .trailing, spacing: 0) {
                    Text(stock.formattedPrice)
                        .font(.system(size: 18, weight: .semibold, design: .monospaced))
                        .foregroundColor(stock.color)
                    HStack(spacing: 4) {
                        Text(stock.formattedChange)
                        Text(stock.formattedPercent)
                    }
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundColor(stock.color)
                }
            }
            
            Divider().background(Color.white.opacity(0.2))
            
            HStack {
                IndicatorItem(label: "高", value: String(format: "%.2f", stock.high), color: Color(red: 1.0, green: 0.3, blue: 0.3))
                Spacer()
                IndicatorItem(label: "低", value: String(format: "%.2f", stock.low), color: Color(red: 0.2, green: 0.8, blue: 0.2))
                Spacer()
                IndicatorItem(label: "开", value: String(format: "%.2f", stock.open))
                Spacer()
                IndicatorItem(label: "量", value: stock.formattedVolume)
            }
        }
        .padding(10)
        .background(Color.black.opacity(0.3))
        .cornerRadius(10)
        .shadow(color: .black.opacity(0.5), radius: 1, x: 0, y: 1)
        .overlay(
            Group {
                if isHovered {
                    Button(action: {
                        viewModel.removeStock(stock.symbol)
                    }) {
                        Image(systemName: "trash.circle.fill")
                            .foregroundColor(.red.opacity(0.8))
                            .font(.system(size: 20))
                            .padding(4)
                            .background(Color.black.opacity(0.5).clipShape(Circle()))
                    }
                    .buttonStyle(PlainButtonStyle())
                    .position(x: 235, y: 10)
                }
            }
        )
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

struct IndicatorItem: View {
    let label: String
    let value: String
    var color: Color = .white
    
    var body: some View {
        HStack(spacing: 2) {
            Text(label).foregroundColor(.white.opacity(0.6))
            Text(value).foregroundColor(color)
        }
        .font(.system(size: 10))
    }
}

// 展开状态视图 (经典面板)
struct ExpandedView: View {
    @ObservedObject var viewModel: StockViewModel
    @EnvironmentObject var windowManager: WindowManager
    @State private var newSymbol: String = ""
    
    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("实时监控")
                        .font(.system(size: 15, weight: .bold))
                        .foregroundColor(.white)
                    if let first = viewModel.stocks.first ?? viewModel.indices.first {
                        Text("更新: \(first.time)")
                            .font(.system(size: 9))
                            .foregroundColor(.white.opacity(0.6))
                    }
                }
                Spacer()
                
                // 最小化按钮
                Button(action: { windowManager.isMinimized = true }) {
                    Image(systemName: "minus.rectangle.fill")
                        .font(.system(size: 16))
                        .foregroundColor(.white.opacity(0.8))
                }
                .buttonStyle(PlainButtonStyle())
                .padding(.trailing, 4)
                
                // 退出按钮
                Button(action: { NSApplication.shared.terminate(nil) }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 16))
                        .foregroundColor(.red.opacity(0.8))
                }
                .buttonStyle(PlainButtonStyle())
            }
            .padding(.horizontal, 14)
            .padding(.top, 14)
            .padding(.bottom, 8)
            
            // Add Stock Input
            HStack {
                TextField("输入代码 (如 600519)", text: $newSymbol)
                    .textFieldStyle(PlainTextFieldStyle())
                    .padding(6)
                    .background(Color.black.opacity(0.4))
                    .cornerRadius(6)
                    .foregroundColor(.white)
                    .font(.system(size: 12))
                    .onSubmit {
                        if !newSymbol.isEmpty {
                            viewModel.addStock(newSymbol)
                            newSymbol = ""
                        }
                    }
                
                Button(action: {
                    if !newSymbol.isEmpty {
                        viewModel.addStock(newSymbol)
                        newSymbol = ""
                    }
                }) {
                    Image(systemName: "plus.circle.fill")
                        .foregroundColor(.white)
                        .font(.system(size: 18))
                }
                .buttonStyle(PlainButtonStyle())
            }
            .padding(.horizontal, 14)
            .padding(.bottom, 8)
            
            // Market Indices
            if !viewModel.indices.isEmpty {
                HStack(spacing: 0) {
                    ForEach(viewModel.indices) { index in
                        IndexRow(stock: index)
                        if index.id != viewModel.indices.last?.id {
                            Divider().background(Color.white.opacity(0.2)).frame(height: 30)
                        }
                    }
                }
                .padding(.vertical, 8)
                .background(Color.black.opacity(0.3))
                .cornerRadius(10)
                .padding(.horizontal, 14)
                .padding(.bottom, 8)
            }
            
            // Individual Stocks (支持滚动，可以放下很多只股票)
            ScrollView(showsIndicators: false) {
                VStack(spacing: 8) {
                    ForEach(viewModel.stocks) { stock in
                        StockRow(stock: stock, viewModel: viewModel)
                    }
                }
                .padding(.horizontal, 14)
                .padding(.bottom, 14)
            }
        }
    }
}

// 最小化状态视图 (跑马灯)
struct MinimizedView: View {
    @ObservedObject var viewModel: StockViewModel
    @EnvironmentObject var windowManager: WindowManager
    
    var allStocks: [StockInfo] {
        viewModel.indices + viewModel.stocks
    }
    
    var body: some View {
        HStack(spacing: 0) {
            // 展开按钮
            Button(action: { windowManager.isMinimized = false }) {
                Image(systemName: "plus.rectangle.fill")
                    .font(.system(size: 16))
                    .foregroundColor(.white.opacity(0.8))
                    .padding(.horizontal, 12)
                    .frame(maxHeight: .infinity)
                    // 背景增加可点击区域
                    .contentShape(Rectangle())
            }
            .buttonStyle(PlainButtonStyle())
            
            // 跑马灯滚动区
            MarqueeView(stocks: allStocks)
                .padding(.vertical, 8)
            
            // 退出按钮
            Button(action: { NSApplication.shared.terminate(nil) }) {
                Image(systemName: "xmark.circle.fill")
                    .font(.system(size: 16))
                    .foregroundColor(.red.opacity(0.8))
                    .padding(.horizontal, 12)
                    .frame(maxHeight: .infinity)
                    .contentShape(Rectangle())
            }
            .buttonStyle(PlainButtonStyle())
        }
    }
}

// 根视图
struct MainView: View {
    @ObservedObject var viewModel: StockViewModel
    @EnvironmentObject var windowManager: WindowManager
    
    var body: some View {
        ZStack {
            // 透明玻璃背景
            VisualEffectView(material: .hudWindow, blendingMode: .behindWindow)
            Color.black.opacity(windowManager.isMinimized ? 0.6 : 0.3)
            
            if windowManager.isMinimized {
                MinimizedView(viewModel: viewModel)
            } else {
                ExpandedView(viewModel: viewModel)
            }
        }
        .frame(width: windowManager.isMinimized ? 800 : 280, height: windowManager.isMinimized ? 40 : 500) // 确保内部 SwiftUI 布局尺寸强制匹配窗口尺寸，避免渲染错乱
        // 根据状态调整圆角
        .cornerRadius(windowManager.isMinimized ? 20 : 16)
        .overlay(
            RoundedRectangle(cornerRadius: windowManager.isMinimized ? 20 : 16)
                .stroke(Color.white.opacity(0.15), lineWidth: 0.5)
        )
        .environment(\.colorScheme, .dark)
        // 给整个窗口加一点阴影
        .shadow(color: Color.black.opacity(0.5), radius: windowManager.isMinimized ? 8 : 15, x: 0, y: windowManager.isMinimized ? 2 : 5)
    }
}

// --- App Structure ---
class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSPanel!
    var viewModel: StockViewModel!
    var windowManager = WindowManager()
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        viewModel = StockViewModel()
        let contentView = MainView(viewModel: viewModel).environmentObject(windowManager)
        
        // 初始大小取决于缓存的状态
        let initialSize = windowManager.isMinimized ? CGSize(width: 800, height: 40) : CGSize(width: 280, height: 500)
        
        window = NSPanel(
            contentRect: NSRect(x: 0, y: 0, width: initialSize.width, height: initialSize.height),
            styleMask: [.nonactivatingPanel, .fullSizeContentView, .borderless],
            backing: .buffered, defer: false)
        
        window.isReleasedWhenClosed = false
        window.level = .mainMenu + 1
        window.isMovableByWindowBackground = true
        window.backgroundColor = .clear
        window.hasShadow = false // 由 SwiftUI 控制阴影，AppKit阴影在形状变化时表现不好
        window.contentView = NSHostingView(rootView: contentView)
        windowManager.window = window
        
        if let screen = NSScreen.main {
            let screenRect = screen.visibleFrame
            let x = screenRect.maxX - initialSize.width - 20
            let y = screenRect.maxY - initialSize.height - 20
            window.setFrameOrigin(NSPoint(x: x, y: y))
        }
        
        window.makeKeyAndOrderFront(nil)
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary, .ignoresCycle]
        
        NSApp.setActivationPolicy(.accessory)
    }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.run()
