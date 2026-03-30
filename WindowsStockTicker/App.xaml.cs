using System;
using System.Windows;
using System.Runtime.InteropServices;
using System.Windows.Interop;
using System.Text;

namespace WindowsStockTicker
{
    public partial class App : Application
    {
        [STAThread]
        public static void Main()
        {
            // 支持 GBK 编码（新浪财经接口需要）
            Encoding.RegisterProvider(CodePagesEncodingProvider.Instance);

            App app = new App();
            app.InitializeComponent();
            app.Run();
        }

        public void InitializeComponent()
        {
            this.StartupUri = new System.Uri("MainWindow.xaml", System.UriKind.Relative);
        }
    }
}
