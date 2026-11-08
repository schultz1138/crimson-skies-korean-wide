// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Crimson Skies Korean patch contributors.
using System;using System.IO;using System.Text;using System.Threading.Tasks;using System.Windows.Forms;using System.Reflection;
[assembly: AssemblyVersion("0.13.0.2")]
[assembly: AssemblyFileVersion("0.13.0.2")]
[assembly: AssemblyTitle("Crimson Skies 전체 한국어 더빙 0.13.0 Alpha 2")]
namespace CrimsonSkiesKoreanPatch {
    sealed class InstallerForm : Form
    {
        readonly TextBox selected = new TextBox();
        readonly TextBox output = new TextBox();
        readonly Button browse = new Button();
        readonly Button check = new Button(); readonly Button apply = new Button(); readonly Button restore = new Button();
        bool busy;
        public InstallerForm()
        {
            Text = "Crimson Skies 전체 한국어 더빙 0.13.0 Alpha 2"; Width = 850; Height = 590; MinimumSize = new System.Drawing.Size(760, 500);
            StartPosition = FormStartPosition.CenterScreen;
            var main = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 5, Padding = new Padding(14) };
            main.RowStyles.Add(new RowStyle(SizeType.Absolute, 50)); main.RowStyles.Add(new RowStyle(SizeType.Absolute, 36));
            main.RowStyles.Add(new RowStyle(SizeType.Absolute, 44)); main.RowStyles.Add(new RowStyle(SizeType.Percent, 100)); main.RowStyles.Add(new RowStyle(SizeType.Absolute, 35));
            var intro = new Label { Dock = DockStyle.Fill, Text = "공개 0.11.0 베타 1 기반에 전체 한국어 더빙을 설치합니다. / Requires the 0.11.0 beta 1 foundation.\r\n게임 폴더 또는 Content를 선택하고, 설치·복구 전에는 게임과 원래 실행기를 종료하세요." };
            main.Controls.Add(intro, 0, 0);
            var row = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
            row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100)); row.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 105));
            selected.Dock = DockStyle.Fill; browse.Text = "폴더 선택"; browse.Dock = DockStyle.Fill;
            row.Controls.Add(selected, 0, 0); row.Controls.Add(browse, 1, 0); main.Controls.Add(row, 0, 1);
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill };
            check.Text = "검사 / Check"; apply.Text = "더빙 설치 / Install dub"; restore.Text = "복구 / Restore";
            foreach (Button b in new[] { check, apply, restore }) { b.Width = 150; b.Height = 32; buttons.Controls.Add(b); }
            main.Controls.Add(buttons, 0, 2);
            output.Multiline = true; output.ReadOnly = true; output.WordWrap = false; output.ScrollBars = ScrollBars.Both; output.Dock = DockStyle.Fill;
            main.Controls.Add(output, 0, 3);
            main.Controls.Add(new Label { Dock = DockStyle.Fill, Text = "설치 전 파일은 현재 Windows 계정의 로컬 앱 데이터에 보관합니다. 복구는 이 설치 직전 상태로 되돌립니다.", Padding = new Padding(0, 8, 0, 0) }, 0, 4);
            Controls.Add(main);
            browse.Click += delegate { using (var dialog = new FolderBrowserDialog { Description = "크림슨 스카이 게임 폴더 또는 Content 폴더를 선택하세요.", ShowNewFolderButton = false }) { if (dialog.ShowDialog(this) == DialogResult.OK) selected.Text = dialog.SelectedPath; } };
            check.Click += async delegate { await Run("--check"); };
            apply.Click += async delegate { await Run("--apply"); };
            restore.Click += async delegate { await Run("--restore"); };
            FormClosing += delegate(object sender, FormClosingEventArgs e) { if (busy) { e.Cancel = true; MessageBox.Show(this, "작업이 끝난 뒤 닫아 주세요.", "작업 중", MessageBoxButtons.OK, MessageBoxIcon.Information); } };
            AcceptButton = check;
        }
        void Log(string text)
        {
            if (InvokeRequired) { BeginInvoke(new Action<string>(Log), text); return; }
            output.AppendText(text + Environment.NewLine);
        }
        async Task Run(string mode)
        {
            if (busy) return;
            busy = true; string root = selected.Text;
            foreach (Control c in new Control[] { selected, browse, check, apply, restore }) c.Enabled = false;
            output.Clear();
            try { await Task.Run(delegate { new PatchEngine(AppDomain.CurrentDomain.BaseDirectory, Log).Run(mode, root); }); }
            catch (Exception e) { Log("중단: " + e.Message); MessageBox.Show(this, e.Message, "작업 중단", MessageBoxButtons.OK, MessageBoxIcon.Warning); }
            finally { busy = false; foreach (Control c in new Control[] { selected, browse, check, apply, restore }) c.Enabled = true; }
        }
    }

    static class Program
    {
        [STAThread]
        public static int Main(string[] args)
        {
            if (args.Length == 0)
            {
                Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false); Application.Run(new InstallerForm()); return 0;
            }
            try
            {
                Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true });
                Console.SetError(new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) { AutoFlush = true });
                string mode = null, root = null;
                for (int i = 0; i < args.Length; i++)
                {
                    string arg = args[i];
                    if ((arg == "--check" || arg == "--apply" || arg == "--restore") && mode == null) mode = arg;
                    else if (arg == "--root" && root == null && ++i < args.Length) root = args[i];
                    else throw new ArgumentException("Usage: KoreanWidePatchInstaller.exe --check|--apply|--restore --root GAME_FOLDER");
                }
                if (mode == null || root == null) throw new ArgumentException("Usage: KoreanWidePatchInstaller.exe --check|--apply|--restore --root GAME_FOLDER");
                new PatchEngine(AppDomain.CurrentDomain.BaseDirectory, Console.WriteLine).Run(mode, root); return 0;
            }
            catch (Exception e) { Console.Error.WriteLine("중단: " + e.Message); return 1; }
        }
    }
}
