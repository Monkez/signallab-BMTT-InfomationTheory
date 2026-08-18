using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

internal sealed class SplashForm : Form
{
    private readonly Process child;
    private readonly Timer timer;
    private readonly string readyPath;
    private readonly DateTime startedAt = DateTime.UtcNow;

    public SplashForm(Process child, string readyPath)
    {
        this.child = child;
        this.readyPath = readyPath;
        Text = "SignalLab";
        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.CenterScreen;
        ClientSize = new Size(440, 250);
        BackColor = Color.FromArgb(246, 248, 251);
        TopMost = true;
        ShowInTaskbar = true;

        var logo = new Label { Text = "∿", AutoSize = false, TextAlign = ContentAlignment.MiddleCenter, Font = new Font("Segoe UI", 30, FontStyle.Bold), ForeColor = Color.White, BackColor = Color.FromArgb(35, 52, 75), Size = new Size(58, 58), Location = new Point(191, 42) };
        var title = new Label { Text = "SignalLab", AutoSize = true, Font = new Font("Segoe UI", 22, FontStyle.Bold), ForeColor = Color.FromArgb(35, 52, 75), Location = new Point(150, 116) };
        var subtitle = new Label { Text = "DIGITAL COMMUNICATIONS STUDIO", AutoSize = true, Font = new Font("Segoe UI", 9), ForeColor = Color.FromArgb(113, 128, 150), Location = new Point(113, 155) };
        Controls.Add(logo); Controls.Add(title); Controls.Add(subtitle);

        timer = new Timer { Interval = 35 };
        timer.Tick += (_, __) =>
        {
            if (child.HasExited || File.Exists(readyPath) || (DateTime.UtcNow - startedAt).TotalSeconds > 15)
            {
                timer.Stop();
                Close();
            }
        };
    }

    protected override void OnShown(EventArgs e)
    {
        base.OnShown(e);
        timer.Start();
    }
}

internal static class Program
{
    [STAThread]
    private static void Main()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        var corePath = Path.Combine(AppContext.BaseDirectory, "SignalLab.exe");
        if (!File.Exists(corePath))
        {
            MessageBox.Show("SignalLab.exe was not found next to the launcher.", "SignalLab", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        var readyPath = Path.Combine(AppContext.BaseDirectory, ".signallab-ready-" + Process.GetCurrentProcess().Id);
        try { File.Delete(readyPath); } catch { }
        var child = Process.Start(new ProcessStartInfo(corePath) { WorkingDirectory = AppContext.BaseDirectory, Arguments = "--launcher-ready-file \"" + readyPath + "\"" });
        if (child == null) return;
        using (child) using (var splash = new SplashForm(child, readyPath)) Application.Run(splash);
        try { File.Delete(readyPath); } catch { }
    }
}
