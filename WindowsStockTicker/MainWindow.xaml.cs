using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Animation;
using System.Windows.Threading;
using Newtonsoft.Json;
using System.IO;

namespace WindowsStockTicker
{
    public partial class MainWindow : Window
    {
        private DispatcherTimer _timer;
        private DispatcherTimer _marqueeTimer;
        private HttpClient _httpClient;
        
        private string _configFile = "config.json";
        private List<string> _indexSymbols = new List<string> { "sh000001", "sz399001", "sz399006" };
        private List<string> _symbols = new List<string>();
        private bool _isMinimized = false;

        private List<StockInfo> _allStocks = new List<StockInfo>();
        private double _marqueeOffset = 0;

        public MainWindow()
        {
            InitializeComponent();
            _httpClient = new HttpClient();
            _httpClient.DefaultRequestHeaders.Add("Referer", "http://finance.sina.com.cn");
            
            LoadConfig();
            ToggleMode(_isMinimized, false);

            _timer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(5) };
            _timer.Tick += async (s, e) => await FetchData();
            
            _marqueeTimer = new DispatcherTimer { Interval = TimeSpan.FromMilliseconds(20) };
            _marqueeTimer.Tick += MarqueeTimer_Tick;
        }

        private async void Window_Loaded(object sender, RoutedEventArgs e)
        {
            // Initial position (Bottom Right)
            var workArea = SystemParameters.WorkArea;
            this.Left = workArea.Right - this.Width - 20;
            this.Top = workArea.Bottom - this.Height - 60;

            await FetchData();
            _timer.Start();
        }

        // --- Config ---
        private void LoadConfig()
        {
            if (File.Exists(_configFile))
            {
                try
                {
                    var json = File.ReadAllText(_configFile);
                    dynamic? data = JsonConvert.DeserializeObject(json);
                    if (data != null)
                    {
                        if (data.symbols != null)
                        {
                            _symbols = data.symbols.ToObject<List<string>>();
                        }
                        if (data.is_minimized != null)
                        {
                            _isMinimized = data.is_minimized;
                        }
                    }
                }
                catch { }
            }
            
            if (_symbols.Count == 0)
            {
                _symbols = new List<string> { "sh600519", "sh601318", "sz000858", "sh600036" };
                SaveConfig();
            }
        }

        private void SaveConfig()
        {
            try
            {
                var data = new { symbols = _symbols, is_minimized = _isMinimized };
                File.WriteAllText(_configFile, JsonConvert.SerializeObject(data));
            }
            catch { }
        }

        // --- Window Interactions ---
        private void Window_MouseLeftButtonDown(object sender, MouseButtonEventArgs e)
        {
            DragMove();
        }

        private void CloseBtn_Click(object sender, RoutedEventArgs e) => Application.Current.Shutdown();
        private void MinBtn_Click(object sender, RoutedEventArgs e) => ToggleMode(true, true);
        private void MaxBtn_Click(object sender, RoutedEventArgs e) => ToggleMode(false, true);

        private void ToggleMode(bool minimize, bool animate)
        {
            _isMinimized = minimize;
            SaveConfig();

            double targetWidth = minimize ? 800 : 280;
            double targetHeight = minimize ? 40 : 500;
            
            // Anchor bottom-right
            double targetLeft = this.Left + this.Width - targetWidth;
            double targetTop = this.Top + this.Height - targetHeight;

            if (minimize)
            {
                ExpandedView.Visibility = Visibility.Collapsed;
                MinimizedView.Visibility = Visibility.Visible;
                BgBorder.CornerRadius = new CornerRadius(20);
                BgBorder.Background = new SolidColorBrush(Color.FromArgb(230, 20, 20, 20)); // Darker for marquee
                _marqueeTimer.Start();
            }
            else
            {
                ExpandedView.Visibility = Visibility.Visible;
                MinimizedView.Visibility = Visibility.Collapsed;
                BgBorder.CornerRadius = new CornerRadius(16);
                BgBorder.Background = new SolidColorBrush(Color.FromArgb(217, 30, 30, 32));
                _marqueeTimer.Stop();
            }

            if (animate)
            {
                var widthAnim = new DoubleAnimation(this.Width, targetWidth, TimeSpan.FromMilliseconds(200)) { EasingFunction = new CubicEase() };
                var heightAnim = new DoubleAnimation(this.Height, targetHeight, TimeSpan.FromMilliseconds(200)) { EasingFunction = new CubicEase() };
                var leftAnim = new DoubleAnimation(this.Left, targetLeft, TimeSpan.FromMilliseconds(200)) { EasingFunction = new CubicEase() };
                var topAnim = new DoubleAnimation(this.Top, targetTop, TimeSpan.FromMilliseconds(200)) { EasingFunction = new CubicEase() };
                
                this.BeginAnimation(Window.WidthProperty, widthAnim);
                this.BeginAnimation(Window.HeightProperty, heightAnim);
                this.BeginAnimation(Window.LeftProperty, leftAnim);
                this.BeginAnimation(Window.TopProperty, topAnim);
            }
            else
            {
                this.Width = targetWidth;
                this.Height = targetHeight;
                this.Left = targetLeft;
                this.Top = targetTop;
            }
        }

        // --- Logic ---
        private string NormalizeSymbol(string s)
        {
            s = s.Trim().ToLower();
            if (s.Length == 6 && s.All(char.IsDigit))
            {
                return (s.StartsWith("6") || s.StartsWith("9") || s.StartsWith("5")) ? $"sh{s}" : $"sz{s}";
            }
            return s;
        }

        private async void AddBtn_Click(object sender, RoutedEventArgs e)
        {
            string s = InputBox.Text;
            InputBox.Text = "";
            Keyboard.ClearFocus();
            if (string.IsNullOrWhiteSpace(s)) return;

            string normalized = NormalizeSymbol(s);
            if (!_symbols.Contains(normalized) && !_indexSymbols.Contains(normalized))
            {
                _symbols.Add(normalized);
                SaveConfig();
                await FetchData();
            }
        }

        private void InputBox_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.Key == Key.Enter) AddBtn_Click(sender, e);
        }

        private async void RemoveStock(string symbol)
        {
            if (_symbols.Remove(symbol))
            {
                SaveConfig();
                await FetchData();
            }
        }

        private async Task FetchData()
        {
            try
            {
                var allQuery = _indexSymbols.Concat(_symbols);
                string url = $"http://hq.sinajs.cn/list={string.Join(",", allQuery)}";
                var bytes = await _httpClient.GetByteArrayAsync(url);
                string content = Encoding.GetEncoding("GBK").GetString(bytes);
                ParseData(content);
            }
            catch { }
        }

        private void ParseData(string content)
        {
            var newIndices = new List<StockInfo>();
            var newStocks = new List<StockInfo>();
            var validSymbols = new List<string>();

            var lines = content.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (var line in lines)
            {
                if (!line.Contains("=\"")) continue;
                
                var parts1 = line.Split(new[] { "=\"" }, StringSplitOptions.None);
                if (parts1.Length < 2) continue;
                
                string symbol = parts1[0].Replace("var hq_str_", "");
                string dataStr = parts1[1].TrimEnd(';', '"');
                var dataParts = dataStr.Split(',');

                if (dataParts.Length >= 32 && !string.IsNullOrWhiteSpace(dataParts[0]))
                {
                    var info = new StockInfo
                    {
                        Symbol = symbol,
                        Name = dataParts[0],
                        Open = double.Parse(dataParts[1]),
                        LastClose = double.Parse(dataParts[2]),
                        Price = double.Parse(dataParts[3]),
                        High = double.Parse(dataParts[4]),
                        Low = double.Parse(dataParts[5]),
                        Volume = double.Parse(dataParts[8]),
                        Time = dataParts[31]
                    };
                    
                    validSymbols.Add(symbol);
                    if (_indexSymbols.Contains(symbol)) newIndices.Add(info);
                    else newStocks.Add(info);
                }
            }

            // Cleanup invalid
            if (newStocks.Count != _symbols.Count)
            {
                _symbols = _symbols.Where(s => validSymbols.Contains(s)).ToList();
                SaveConfig();
            }

            _allStocks = newIndices.Concat(newStocks).ToList();
            
            // Dispatch UI updates
            Dispatcher.Invoke(() => UpdateUI(newIndices, newStocks));
        }

        private void UpdateUI(List<StockInfo> indices, List<StockInfo> stocks)
        {
            if (_allStocks.Any())
                TimeLabel.Text = $"更新: {_allStocks.First().Time}";

            UpdateExpandedIndices(indices);
            UpdateExpandedStocks(stocks);
            UpdateMarquee();
        }

        // --- UI Rendering ---
        private void UpdateExpandedIndices(List<StockInfo> indices)
        {
            IndicesPanel.Children.Clear();
            for (int i = 0; i < indices.Count; i++)
            {
                var stock = indices[i];
                var sp = new StackPanel { Margin = new Thickness(10, 2, 10, 2) };
                
                sp.Children.Add(new TextBlock { Text = stock.Name, Foreground = Brushes.White, FontSize = 12, FontWeight = FontWeights.Bold, HorizontalAlignment = HorizontalAlignment.Center });
                sp.Children.Add(new TextBlock { Text = stock.FormattedPrice, Foreground = stock.ColorBrush, FontSize = 14, FontWeight = FontWeights.Bold, FontFamily = new FontFamily("Consolas"), HorizontalAlignment = HorizontalAlignment.Center });
                sp.Children.Add(new TextBlock { Text = stock.FormattedPercent, Foreground = stock.ColorBrush, FontSize = 10, FontFamily = new FontFamily("Consolas"), HorizontalAlignment = HorizontalAlignment.Center });
                
                IndicesPanel.Children.Add(sp);

                if (i < indices.Count - 1)
                {
                    IndicesPanel.Children.Add(new Border { Width = 1, Background = new SolidColorBrush(Color.FromArgb(50, 255, 255, 255)), Margin = new Thickness(0, 5, 0, 5) });
                }
            }
        }

        private void UpdateExpandedStocks(List<StockInfo> stocks)
        {
            StocksPanel.Children.Clear();
            foreach (var stock in stocks)
            {
                var card = new Border
                {
                    Background = new SolidColorBrush(Color.FromArgb(76, 0, 0, 0)),
                    CornerRadius = new CornerRadius(10),
                    Padding = new Thickness(10),
                    Margin = new Thickness(0, 0, 0, 8)
                };

                var mainGrid = new Grid();
                mainGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
                mainGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });
                mainGrid.RowDefinitions.Add(new RowDefinition { Height = GridLength.Auto });

                // Top row
                var topGrid = new Grid();
                topGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                topGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

                var nameSp = new StackPanel();
                nameSp.Children.Add(new TextBlock { Text = stock.Name, Foreground = Brushes.White, FontSize = 14, FontWeight = FontWeights.Bold });
                nameSp.Children.Add(new TextBlock { Text = stock.Symbol.ToUpper(), Foreground = new SolidColorBrush(Color.FromArgb(180, 255, 255, 255)), FontSize = 10 });
                Grid.SetColumn(nameSp, 0);

                var priceSp = new StackPanel();
                priceSp.Children.Add(new TextBlock { Text = stock.FormattedPrice, Foreground = stock.ColorBrush, FontSize = 18, FontWeight = FontWeights.Bold, FontFamily = new FontFamily("Consolas"), HorizontalAlignment = HorizontalAlignment.Right });
                priceSp.Children.Add(new TextBlock { Text = $"{stock.FormattedChange}  {stock.FormattedPercent}", Foreground = stock.ColorBrush, FontSize = 11, FontFamily = new FontFamily("Consolas"), HorizontalAlignment = HorizontalAlignment.Right });
                Grid.SetColumn(priceSp, 1);

                topGrid.Children.Add(nameSp);
                topGrid.Children.Add(priceSp);
                Grid.SetRow(topGrid, 0);

                // Line
                var line = new Border { Height = 1, Background = new SolidColorBrush(Color.FromArgb(50, 255, 255, 255)), Margin = new Thickness(0, 5, 0, 5) };
                Grid.SetRow(line, 1);

                // Bottom row
                var botGrid = new Grid();
                for (int i = 0; i < 4; i++) botGrid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
                
                botGrid.Children.Add(CreateIndicator("高", stock.High.ToString("F2"), "#ff4c4c", 0));
                botGrid.Children.Add(CreateIndicator("低", stock.Low.ToString("F2"), "#33cc33", 1));
                botGrid.Children.Add(CreateIndicator("开", stock.Open.ToString("F2"), "White", 2));
                botGrid.Children.Add(CreateIndicator("量", stock.FormattedVolume, "White", 3));
                Grid.SetRow(botGrid, 2);

                mainGrid.Children.Add(topGrid);
                mainGrid.Children.Add(line);
                mainGrid.Children.Add(botGrid);

                // Delete Button Overlay
                var delBtn = new Button
                {
                    Content = "×",
                    Style = (Style)FindResource("DelBtn"),
                    Width = 20, Height = 20,
                    HorizontalAlignment = HorizontalAlignment.Right,
                    VerticalAlignment = HorizontalAlignment.Top,
                    Margin = new Thickness(0, -5, -5, 0),
                    Visibility = Visibility.Hidden,
                    Tag = stock.Symbol
                };
                delBtn.Click += (s, e) => RemoveStock((s as Button)!.Tag.ToString()!);

                var cardGrid = new Grid();
                cardGrid.Children.Add(mainGrid);
                cardGrid.Children.Add(delBtn);
                
                cardGrid.MouseEnter += (s, e) => delBtn.Visibility = Visibility.Visible;
                cardGrid.MouseLeave += (s, e) => delBtn.Visibility = Visibility.Hidden;

                card.Child = cardGrid;
                StocksPanel.Children.Add(card);
            }
        }

        private UIElement CreateIndicator(string label, string val, string colorHex, int col)
        {
            var sp = new StackPanel { Orientation = Orientation.Horizontal, HorizontalAlignment = col == 3 ? HorizontalAlignment.Right : (col == 0 ? HorizontalAlignment.Left : HorizontalAlignment.Center) };
            sp.Children.Add(new TextBlock { Text = label + " ", Foreground = new SolidColorBrush(Color.FromArgb(150, 255, 255, 255)), FontSize = 10 });
            sp.Children.Add(new TextBlock { Text = val, Foreground = new SolidColorBrush((Color)ColorConverter.ConvertFromString(colorHex)), FontSize = 10 });
            Grid.SetColumn(sp, col);
            return sp;
        }

        private void UpdateMarquee()
        {
            MarqueePanel.Children.Clear();
            if (!_allStocks.Any()) return;

            // Double for seamless
            for (int loop = 0; loop < 2; loop++)
            {
                foreach (var stock in _allStocks)
                {
                    var sp = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 30, 0), VerticalAlignment = VerticalAlignment.Center };
                    sp.Children.Add(new TextBlock { Text = stock.Name + " ", Foreground = Brushes.White, FontSize = 14, FontWeight = FontWeights.Bold, VerticalAlignment = VerticalAlignment.Bottom });
                    sp.Children.Add(new TextBlock { Text = stock.FormattedPrice + " ", Foreground = stock.ColorBrush, FontSize = 14, FontWeight = FontWeights.Bold, FontFamily = new FontFamily("Consolas"), VerticalAlignment = VerticalAlignment.Bottom });
                    sp.Children.Add(new TextBlock { Text = stock.FormattedPercent, Foreground = stock.ColorBrush, FontSize = 14, FontFamily = new FontFamily("Consolas"), VerticalAlignment = VerticalAlignment.Bottom });
                    MarqueePanel.Children.Add(sp);
                }
            }
            
            // Force layout update to get actual width
            MarqueePanel.Measure(new Size(double.PositiveInfinity, double.PositiveInfinity));
            MarqueePanel.Arrange(new Rect(0, 0, MarqueePanel.DesiredSize.Width, MarqueePanel.DesiredSize.Height));
        }

        private void MarqueeTimer_Tick(object? sender, EventArgs e)
        {
            if (MarqueePanel.ActualWidth == 0) return;
            
            _marqueeOffset -= 1;
            double halfWidth = MarqueePanel.ActualWidth / 2;
            
            if (Math.Abs(_marqueeOffset) >= halfWidth)
            {
                _marqueeOffset = 0;
            }
            
            Canvas.SetLeft(MarqueePanel, _marqueeOffset);
        }
    }
}