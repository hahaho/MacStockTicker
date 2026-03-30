using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Windows.Media;

namespace WindowsStockTicker
{
    public class StockInfo : INotifyPropertyChanged
    {
        public string Symbol { get; set; } = string.Empty;
        
        private string _name = string.Empty;
        public string Name 
        { 
            get => _name; 
            set { _name = value; OnPropertyChanged(nameof(Name)); }
        }

        private double _price;
        public double Price 
        { 
            get => _price; 
            set { _price = value; OnPropertyChanged(nameof(Price)); OnPropertyChanged(nameof(FormattedPrice)); }
        }

        public double Open { get; set; }
        public double LastClose { get; set; }
        public double High { get; set; }
        public double Low { get; set; }
        public double Volume { get; set; }
        public string Time { get; set; } = string.Empty;

        public double Change => Price - LastClose;
        public double PercentChange => LastClose != 0 ? (Change / LastClose * 100) : 0.0;

        public Brush ColorBrush
        {
            get
            {
                if (Change > 0) return new SolidColorBrush((Color)ColorConverter.ConvertFromString("#ff4c4c")); // 红
                if (Change < 0) return new SolidColorBrush((Color)ColorConverter.ConvertFromString("#33cc33")); // 绿
                return Brushes.White;
            }
        }

        public string FormattedPrice => Price.ToString("F2");
        
        public string FormattedChange
        {
            get
            {
                string sign = Change > 0 ? "+" : "";
                return $"{sign}{Change:F2}";
            }
        }

        public string FormattedPercent
        {
            get
            {
                string sign = Change > 0 ? "+" : "";
                return $"{sign}{PercentChange:F2}%";
            }
        }

        public string FormattedVolume
        {
            get
            {
                if (Volume > 100000000) return $"{Volume / 100000000:F2}亿";
                if (Volume > 10000) return $"{Volume / 10000:F2}万";
                return Volume.ToString("F0");
            }
        }

        public event PropertyChangedEventHandler? PropertyChanged;
        protected void OnPropertyChanged(string propertyName)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }
}
