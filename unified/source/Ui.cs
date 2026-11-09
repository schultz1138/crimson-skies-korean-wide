// SPDX-License-Identifier: MIT
using System;using System.Drawing;using System.IO;using System.Linq;using System.Text;using System.Threading.Tasks;using System.Windows.Forms;
namespace CrimsonSkiesUnified {
 sealed class SetupForm:Form {
  readonly TextBox root=new TextBox{Dock=DockStyle.Fill};readonly TextBox output=new TextBox{Dock=DockStyle.Fill,Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Both,WordWrap=false};
  readonly RadioButton original=new RadioButton{Text="원본 음성·자막 / Original voices and captions",AutoSize=true};
  readonly RadioButton subtitles=new RadioButton{Text="영어 음성 + 한국어 자막 / English voices + Korean captions",AutoSize=true};
  readonly RadioButton voicesOnly=new RadioButton{Text="한국어 더빙만 (추가 자막 끔) / Korean voices only (no added captions)",AutoSize=true};
  readonly RadioButton voicesAndSubtitles=new RadioButton{Text="한국어 더빙 + 맞춤 자막 / Korean voices + matched captions",AutoSize=true,Checked=true};
  readonly CheckBox wide=new CheckBox{Text="와이드스크린·고해상도 (별도 선택) / Widescreen & high resolutions (independent)",AutoSize=true,Checked=true};
  readonly Label description=new Label{Dock=DockStyle.Fill};readonly Button browse=new Button{Text="폴더 선택 / Browse",AutoSize=true};readonly Button check=new Button{Text="상태 검사 / Check",AutoSize=true};readonly Button apply=new Button{Text="선택 항목 설치 / Install selected",AutoSize=true};readonly Button restore=new Button{Text="설치 전 복구 / Restore",AutoSize=true};readonly Button recover=new Button{Text="중단 작업 복구 / Recover",AutoSize=true};readonly Button play=new Button{Text="플레이 창 열기 / Open game",AutoSize=true};bool busy;
  public SetupForm(string initial){
   Text="Crimson Skies 통합 설치기 / Unified Setup — "+PatchEngine.ReleaseId.Substring("CrimsonSkies-Unified-".Length);Font=new Font("맑은 고딕",10);Width=1000;Height=790;MinimumSize=new Size(900,710);StartPosition=FormStartPosition.CenterScreen;AutoScaleMode=AutoScaleMode.Dpi;
   var layout=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=7,Padding=new Padding(16)};layout.RowStyles.Add(new RowStyle(SizeType.Absolute,55));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,36));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,195));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,95));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,80));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,45));
   layout.Controls.Add(new Label{Dock=DockStyle.Fill,Text="원하는 음성·자막 구성을 선택하세요. 와이드스크린은 별도로 적용할 수 있습니다.\r\n지원 빌드 / Build: Windows x64 2608.3123.1.0 · 설치 전 게임과 플레이 창을 종료하세요."},0,0);
   var path=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=2};path.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));path.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));path.Controls.Add(root,0,0);path.Controls.Add(browse,1,0);layout.Controls.Add(path,0,1);root.AccessibleName="게임 폴더 / Game folder";root.Text=initial??@"C:\XboxGames\Crimson Skies- High Road to Revenge\Content";
   var group=new GroupBox{Dock=DockStyle.Fill,Text="음성·자막 프리셋 / Voice and caption preset"};
   var options=new TableLayoutPanel{Dock=DockStyle.Fill,ColumnCount=1,RowCount=5,Padding=new Padding(10)};
   int row=0;foreach(var radio in new[]{original,subtitles,voicesOnly,voicesAndSubtitles}){radio.UseMnemonic=false;radio.AccessibleName=radio.Text;options.RowStyles.Add(new RowStyle(SizeType.Absolute,30));options.Controls.Add(radio,0,row++);radio.CheckedChanged+=delegate{Describe();};}
   wide.UseMnemonic=false;options.RowStyles.Add(new RowStyle(SizeType.Absolute,30));options.Controls.Add(wide,0,4);group.Controls.Add(options);layout.Controls.Add(group,0,2);layout.Controls.Add(description,0,3);
   var buttons=new FlowLayoutPanel{Dock=DockStyle.Fill,WrapContents=true};foreach(var b in new[]{check,apply,restore,recover,play}){b.Height=34;buttons.Controls.Add(b);}layout.Controls.Add(buttons,0,4);layout.Controls.Add(output,0,5);layout.Controls.Add(new Label{Dock=DockStyle.Fill,Text="더빙 프리셋에는 필요한 한글 메뉴·글꼴이 함께 적용됩니다.\r\n백업은 로컬 앱 데이터에 보관합니다. 저장 프로필은 변경하지 않습니다. / Saves are not modified."},0,6);Controls.Add(layout);
   browse.Click+=delegate{using(var d=new FolderBrowserDialog{Description="게임 폴더 또는 Content / Game folder or Content",ShowNewFolderButton=false}){if(Directory.Exists(root.Text))d.SelectedPath=root.Text;if(d.ShowDialog(this)==DialogResult.OK)root.Text=d.SelectedPath;}};
   wide.CheckedChanged+=delegate{Describe();};
   check.Click+=async delegate{await Run("--check");};apply.Click+=async delegate{await Run("--apply");};restore.Click+=async delegate{await Run("--restore");};recover.Click+=async delegate{await Run("--recover");};play.Click+=async delegate{await Run("--open");};FormClosing+=delegate(object s,FormClosingEventArgs e){if(busy)e.Cancel=true;};Describe();
  }
  InstallPreset SelectedPreset(){return voicesOnly.Checked?InstallPreset.KoreanVoicesOnly:voicesAndSubtitles.Checked?InstallPreset.KoreanVoicesAndSubtitles:subtitles.Checked?InstallPreset.KoreanSubtitles:InstallPreset.Original;}
  string ProfileId(){return SelectionPolicy.ProfileId(SelectedPreset(),wide.Checked);}
  void Describe(){
   string text;switch(SelectedPreset()){
    case InstallPreset.Original:text="영어 음성과 게임 기본 자막을 사용합니다. 추가 한국어 자막·더빙은 설치하지 않습니다.";break;
    case InstallPreset.KoreanSubtitles:text="영어 음성을 유지하고 한국어 번역 자막과 한글 메뉴·글꼴을 적용합니다.";break;
    case InstallPreset.KoreanVoicesOnly:text="한국어 더빙만: 추가 무전·게임 내 컷신 자막을 표시하지 않습니다.\r\n더빙에 필요한 한글 메뉴·글꼴이 함께 적용되며, 기본 영상 자막은 유지됩니다.";break;
    default:text="한국어 더빙과 실제 더빙 대사에 맞춘 한국어 자막, 한글 메뉴·글꼴을 적용합니다.";break;
   }
   bool dubbed=voicesOnly.Checked||voicesAndSubtitles.Checked;
   description.Text=text+"\r\n"+(wide.Checked?"와이드스크린 적용 · 4:3/16:9 자동 · 최대 4K · AA 유지":"와이드스크린 미적용 · 기존 4:3 해상도")+(dubbed?"\r\n전체 더빙 설치는 약 14GB의 여유 공간을 권장합니다. API 키는 필요 없습니다.":"");
  }
  void Log(string s){if(InvokeRequired){BeginInvoke(new Action<string>(Log),s);return;}output.AppendText(s+Environment.NewLine);}
  Control[] InputControls(){return new Control[]{root,browse,original,subtitles,voicesOnly,voicesAndSubtitles,wide,check,apply,restore,recover,play};}
  async Task Run(string mode){if(busy)return;busy=true;string selected=root.Text,id=ProfileId();foreach(var c in InputControls())c.Enabled=false;output.Clear();try{await Task.Run(delegate{var e=new PatchEngine(AppDomain.CurrentDomain.BaseDirectory,Log);if(mode=="--open")e.Open(selected);else e.Run(mode,selected,id);});}catch(Exception e){Log("중단 / Stopped: "+e.Message);MessageBox.Show(this,e.Message,"작업 중단 / Stopped",MessageBoxButtons.OK,MessageBoxIcon.Warning);}finally{busy=false;foreach(var c in InputControls())c.Enabled=true;}}
 }
 static class Program {
  [STAThread]public static int Main(string[] args){if(args.Length==0||args.Length==2&&args[0]=="--gui-root"){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new SetupForm(args.Length==2?args[1]:null));return 0;}try{Console.SetOut(new StreamWriter(Console.OpenStandardOutput(),new UTF8Encoding(false)){AutoFlush=true});Console.SetError(new StreamWriter(Console.OpenStandardError(),new UTF8Encoding(false)){AutoFlush=true});string mode=null,root=null,profile="k1-w1-d1-dub";for(int i=0;i<args.Length;i++){if(new[]{"--check","--apply","--restore","--recover","--open"}.Contains(args[i])&&mode==null)mode=args[i];else if(args[i]=="--root"&&root==null&&++i<args.Length)root=args[i];else if(args[i]=="--profile"&&++i<args.Length)profile=args[i];else throw new ArgumentException("Invalid arguments");}if(mode==null||root==null)throw new ArgumentException("Usage: CrimsonSkiesSetup.exe --check|--apply|--restore|--recover|--open --root CONTENT [--profile k1-w1-d1-dub]");var e=new PatchEngine(AppDomain.CurrentDomain.BaseDirectory,Console.WriteLine);if(mode=="--open")e.Open(root);else e.Run(mode,root,profile);return 0;}catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}}
 }
}
