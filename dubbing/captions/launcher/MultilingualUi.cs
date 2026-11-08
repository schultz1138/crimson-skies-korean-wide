// SPDX-License-Identifier: MIT
using System;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;

[assembly: AssemblyVersion("0.13.0.2")]
[assembly: AssemblyFileVersion("0.13.0.2")]
[assembly: AssemblyTitle("Crimson Skies Korean Subtitle Styles & Profiles")]

namespace CrimsonSkiesMultilingual
{
    sealed class PackChoice
    {
        public CaptionStyle Style;
        public string Id { get { return Style.id; } }
        public override string ToString() { return Style.displayName; }
    }

    sealed class UiPreferences
    {
        public string root;
        public string pack;
    }

    sealed class LanguageForm : Form
    {
        readonly TextBox root = new TextBox();
        readonly ComboBox choices = new ComboBox();
        readonly TextBox coverage = new TextBox();
        readonly TextBox output = new TextBox();
        readonly Button browse = new Button();
        readonly Button check = new Button();
        readonly Button apply = new Button();
        readonly Button play = new Button();
        readonly Button restore = new Button();
        readonly Button profiles = new Button();
        readonly PackEngine engine;
        readonly CaptionSpanEngine captions;
        bool busy;

        public LanguageForm(string initialRoot = null)
        {
            Text = "Crimson Skies 한국어 자막 선택 · 프로필 / Korean Subtitle Styles & Profiles — 0.13.0 Alpha 2";
            Width = 960; Height = 620; MinimumSize = new Size(850, 560);
            StartPosition = FormStartPosition.CenterScreen;
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 7, Padding = new Padding(12) };
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 54));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 76));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 36));
            layout.Controls.Add(new Label { Dock = DockStyle.Fill, Text =
                "전체 더빙 베타 1에서 자막을 선택하세요. 게임과 기존 플레이 창을 닫고 적용합니다.\r\n" +
                "Full Dub Beta 1 caption styles. Close the game and original Play window before switching." }, 0, 0);
            var pathRow = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
            pathRow.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            pathRow.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 155));
            root.Dock = DockStyle.Fill; root.AccessibleName = "게임 폴더 / Game folder";
            browse.Text = "폴더 / Select folder"; browse.Dock = DockStyle.Fill;
            browse.Click += delegate { using (var picker = new FolderBrowserDialog()) { picker.Description = "Game folder or Content"; if (Directory.Exists(root.Text)) picker.SelectedPath = root.Text; if (picker.ShowDialog(this) == DialogResult.OK) root.Text = picker.SelectedPath; } };
            pathRow.Controls.Add(root, 0, 0); pathRow.Controls.Add(browse, 1, 0); layout.Controls.Add(pathRow, 0, 1);
            var languageRow = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2 };
            languageRow.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 195));
            languageRow.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
            languageRow.Controls.Add(new Label { Dock = DockStyle.Fill, Text = "자막 언어 / Subtitle language", TextAlign = ContentAlignment.MiddleLeft }, 0, 0);
            choices.DropDownStyle = ComboBoxStyle.DropDownList; choices.Dock = DockStyle.Fill;
            languageRow.Controls.Add(choices, 1, 0); layout.Controls.Add(languageRow, 0, 2);
            coverage.Dock = DockStyle.Fill; coverage.Multiline = true; coverage.ReadOnly = true; coverage.ScrollBars = ScrollBars.Vertical;
            layout.Controls.Add(coverage, 0, 3);
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, WrapContents = true };
            check.Text = "상태 확인 / Check"; check.Width = 155;
            apply.Text = "언어 적용 / Apply"; apply.Width = 155;
            play.Text = "적용 후 실행 / Apply && open"; play.Width = 220;
            restore.Text = "원본 자막 복구 / Restore captions"; restore.Width = 240;
            profiles.Text = "프로필 관리 / Profiles"; profiles.Width = 205;
            foreach (Button button in new[] { check, apply, play, restore, profiles }) { button.Height = 34; buttons.Controls.Add(button); }
            layout.Controls.Add(buttons, 0, 4);
            output.Dock = DockStyle.Fill; output.Multiline = true; output.ReadOnly = true;
            output.ScrollBars = ScrollBars.Both; output.WordWrap = false; layout.Controls.Add(output, 0, 5);
            layout.Controls.Add(new Label { Dock = DockStyle.Fill, Text =
                "자막 전환·복구 시 전체 한국어 더빙과 다른 설정은 유지됩니다. / Full Korean audio and other settings are preserved.\r\n" +
                "이번 전체 더빙용 선택기는 두 한국어 자막을 제공합니다. / This Full Dub chooser provides the two Korean caption styles." }, 0, 6);
            Controls.Add(layout);
            if (Directory.Exists(CaptionSpanEngine.DefaultGameRoot)) root.Text = CaptionSpanEngine.DefaultGameRoot;
            engine = new PackEngine(AppDomain.CurrentDomain.BaseDirectory, AppendLog);
            captions = new CaptionSpanEngine(AppDomain.CurrentDomain.BaseDirectory, AppendLog, engine.LaunchOriginal);
            foreach (CaptionStyle style in captions.Catalog.styles) choices.Items.Add(new PackChoice { Style = style });
            choices.SelectedIndexChanged += delegate { ShowCoverage(); };
            if (choices.Items.Count > 0) choices.SelectedIndex = 0;
            LoadPreferences();
            if (initialRoot != null) root.Text = initialRoot;
            check.Click += async delegate { await Run("--check", false); };
            apply.Click += async delegate { await Run("--activate", false); };
            play.Click += async delegate { await Run("--activate", true); };
            restore.Click += async delegate { await Run("--restore", false); };
            profiles.Click += delegate { OpenProfiles(); };
            FormClosing += delegate(object sender, FormClosingEventArgs args) { if (busy) args.Cancel = true; };
        }

        string PreferencePath()
        {
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "CrimsonSkiesLanguagePacks", "ui.json");
        }
        void LoadPreferences()
        {
            try
            {
                string path = PreferencePath();
                if (!File.Exists(path) || new FileInfo(path).Length > 8192) return;
                var before = new JavaScriptSerializer().Deserialize<UiPreferences>(File.ReadAllText(path, Encoding.UTF8));
                if (before == null) return;
                if (before.root != null && before.root.Length < 1024) root.Text = before.root;
                for (int i = 0; i < choices.Items.Count; i++) if (((PackChoice)choices.Items[i]).Id == before.pack) choices.SelectedIndex = i;
            }
            catch { /* UI memory is optional; verified activation state belongs to the engine. */ }
        }
        void SavePreferences(string selectedRoot, string id)
        {
            try
            {
                string path = PreferencePath();
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.WriteAllText(path, new JavaScriptSerializer().Serialize(new UiPreferences { root = selectedRoot, pack = id }), new UTF8Encoding(false));
            }
            catch (Exception error) { AppendLog("UI preference could not be saved: " + error.Message); }
        }
        void ShowCoverage()
        {
            var choice = choices.SelectedItem as PackChoice;
            coverage.Text = choice == null ? "" : choice.Style.coverage;
            restore.Text = "원본 자막 복구 / Restore captions";
        }
        void AppendLog(string message)
        {
            if (IsDisposed) return;
            if (InvokeRequired) { BeginInvoke((Action)(delegate { AppendLog(message); })); return; }
            output.AppendText(message + Environment.NewLine);
        }
        void OpenProfiles()
        {
            if (busy) return;
            string selectedRoot = root.Text;
            busy = true;
            foreach (Control control in new Control[] { root, choices, browse, check, apply, play, restore, profiles }) control.Enabled = false;
            try { ProfileManagerUi.Open(this, selectedRoot); }
            finally
            {
                busy = false;
                foreach (Control control in new Control[] { root, choices, browse, check, apply, play, restore, profiles }) control.Enabled = true;
            }
        }
        async Task Run(string mode, bool open)
        {
            if (busy) return;
            var choice = choices.SelectedItem as PackChoice;
            if (choice == null) return;
            string selectedRoot = root.Text, selectedId = choice.Id;
            busy = true;
            foreach (Control control in new Control[] { root, choices, browse, check, apply, play, restore, profiles }) control.Enabled = false;
            try
            {
                var launchGuard = ProfileManagerUi.BeforeGameLaunch;
                if (open && launchGuard != null) await launchGuard(selectedRoot);
                await Task.Run(delegate { if (choice.Style == null) throw new InvalidOperationException("Only Full Dub caption styles are supported here."); captions.Run(mode, selectedRoot, selectedId, open); });
                if (mode == "--activate") SavePreferences(selectedRoot, selectedId);
            }
            catch (Exception error) { AppendLog("중단 / Stopped: " + error.Message); }
            finally
            {
                busy = false;
                foreach (Control control in new Control[] { root, choices, browse, check, apply, play, restore, profiles }) control.Enabled = true;
            }
        }
    }

    static class Program
    {
        [STAThread]
        public static int Main(string[] args)
        {
            ProfileManagerServices.Configure();
            if (args.Length == 0 || (args.Length == 2 && args[0] == "--gui-root"))
            {
                Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
                try { Application.Run(new LanguageForm(args.Length == 2 ? args[1] : null)); return 0; }
                catch (Exception error) { MessageBox.Show(error.Message, "Crimson Skies — package error", MessageBoxButtons.OK, MessageBoxIcon.Error); return 1; }
            }
            Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true });
            Console.SetError(new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) { AutoFlush = true });
            try
            {
                string mode = null, selectedRoot = null, id = null; bool open = false;
                for (int i = 0; i < args.Length; i++)
                {
                    string arg = args[i];
                    if ((arg == "--check" || arg == "--activate" || arg == "--restore") && mode == null) mode = arg;
                    else if (arg == "--root" && selectedRoot == null && i + 1 < args.Length) selectedRoot = args[++i];
                    else if (arg == "--pack" && id == null && i + 1 < args.Length) id = args[++i];
                    else if (arg == "--style" && id == null && i + 1 < args.Length) { string style = args[++i]; id = style == "original" ? "ko-KR" : style == "dub" ? "ko-KR-dub" : style; }
                    else if (arg == "--open" && !open) open = true;
                    else throw new ArgumentException("Usage: MultilingualLauncher.exe --check|--activate|--restore [--root GAME_FOLDER] [--style original|dub | --pack ID] [--open]");
                }
                if (selectedRoot == null) selectedRoot = CaptionSpanEngine.DefaultGameRoot;
                if (mode == null || (mode == "--activate" && id == null) || (open && mode != "--activate"))
                    throw new ArgumentException("Specify a mode/root and a pack ID for activation; --open applies only to activation.");
                var launchGuard = ProfileManagerUi.BeforeGameLaunch;
                if (open && launchGuard != null) launchGuard(selectedRoot).GetAwaiter().GetResult();
                string bundle = AppDomain.CurrentDomain.BaseDirectory;
                var legacy = new PackEngine(bundle, Console.WriteLine);
                var current = new CaptionSpanEngine(bundle, Console.WriteLine, legacy.LaunchOriginal);
                if (id == null || current.HasStyle(id)) current.Run(mode, selectedRoot, id, open);
                else throw new ArgumentException("This Full Dub chooser supports its pinned caption styles only. Existing English/Spanish packs require the separate legacy 0.12.2 launcher and its compatible foundation; their whole-file engine is not routed onto Full Dub.");
                return 0;
            }
            catch (Exception error) { Console.Error.WriteLine("중단 / Stopped: " + error.Message); return 1; }
        }
    }
}
