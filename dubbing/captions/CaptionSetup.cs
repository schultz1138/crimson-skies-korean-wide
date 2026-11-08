// SPDX-License-Identifier: MIT
// Materialize caption-owned local payloads from pinned user-owned game files.
// This executable never opens game files for writing or modifies saves/settings.
using System;using System.Collections.Generic;using System.Diagnostics;using System.IO;using System.Linq;using System.Security.Cryptography;using System.Text;using System.Threading;using System.Threading.Tasks;using System.Web.Script.Serialization;using System.Windows.Forms;
namespace CrimsonSkiesCaptionSetup {
 public sealed class Delta {public string path,sha256;public long bytes;}
 public sealed class Pair {public int fileIndex;public Delta forward,reverse;}
 public sealed class Bootstrap {public int schema;public string catalogSha256,legacyCatalogSha256,launcherSha256,toolSha256;public Pair[] deltas;}
 public sealed class FileRow {public string path,baselineSha256;public long bytes;}
 public sealed class Span {public int fileIndex;public long offset;public int bytes;}
 public sealed class Payload {public string path,sha256;public long bytes;}
 public sealed class Style {public string id;public string[] hashes;public Payload payload;}
 public sealed class Catalog {public FileRow[] files;public Span[] spans;public Style[] styles;}
 public static class Preparer {
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly JavaScriptSerializer Json=new JavaScriptSerializer{MaxJsonLength=4194304};
  public const string DefaultRoot=@"C:\XboxGames\Crimson Skies- High Road to Revenge\Content";
  static void Need(bool ok,string why){if(!ok)throw new InvalidDataException(why);}
  public static string Hash(string path){using(var h=SHA256.Create())using(var f=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read))return BitConverter.ToString(h.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
  static void Guard(string path){string p=Path.GetFullPath(path),volume=Path.GetPathRoot(p);Need(!String.IsNullOrEmpty(volume)&&!volume.StartsWith("\\\\",StringComparison.Ordinal),"Local disk required.");string at=volume;foreach(string part in p.Substring(volume.Length).Split(new[]{'\\','/'},StringSplitOptions.RemoveEmptyEntries)){at=Path.Combine(at,part);if(File.Exists(at)||Directory.Exists(at))Need((File.GetAttributes(at)&FileAttributes.ReparsePoint)==0,"Linked paths are not supported.");}}
  static string Child(string root,string relative){Need(!String.IsNullOrEmpty(relative)&&!Path.IsPathRooted(relative)&&relative.IndexOf(':')<0&&relative.Split(new[]{'\\','/'}).All(x=>x!=""&&x!="."&&x!=".."),"Unsafe relative path.");string p=Path.GetFullPath(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));Need(p.StartsWith(Path.GetFullPath(root).TrimEnd('\\','/')+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase),"Path escaped owner.");Guard(p);return p;}
  static string Quote(string p){Need(p.IndexOfAny(new[]{'"','\r','\n'})<0,"Invalid process path.");return "\""+p.TrimEnd('\\')+"\"";}
  static void Verify(string path,string hash,long? bytes){Guard(path);Need(File.Exists(path)&&(!bytes.HasValue||new FileInfo(path).Length==bytes.Value)&&Hash(path)==hash,"File verification failed: "+path);}
  static T Read<T>(string path,int max){Need(new FileInfo(path).Length<=max,"Metadata exceeds bound.");return Json.Deserialize<T>(File.ReadAllText(path,Utf8));}
  static void Decode(string bundle,string source,Delta d,string output,string toolHash){
   string tool=Child(bundle,"tools/xdelta3.exe"),delta=Child(bundle,d.path);Verify(tool,toolHash,null);Verify(delta,d.sha256,d.bytes);
   var start=new ProcessStartInfo(tool,"-d -D -R -s "+Quote(source)+" "+Quote(delta)+" "+Quote(output)){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden,RedirectStandardError=true,RedirectStandardOutput=true};start.EnvironmentVariables.Remove("XDELTA");
   using(var p=Process.Start(start)){var a=p.StandardError.ReadToEndAsync();var b=p.StandardOutput.ReadToEndAsync();if(!p.WaitForExit(180000)){try{p.Kill();}catch{}throw new IOException("Caption delta decode timed out. Game files were not written.");}Task.WaitAll(a,b);Need(p.ExitCode==0,"Caption delta decode failed: "+a.Result+b.Result);}
  }
  public static string Prepare(string bundle,string selected,Action<string> log){
   bundle=Path.GetFullPath(bundle);Guard(bundle);string bp=Child(bundle,"bootstrap.json");Verify(bp,BootstrapPin.Digest,null);var boot=Read<Bootstrap>(bp,262144);Need(boot.schema==1,"Unsupported bootstrap schema.");
   string cp=Child(bundle,"dub-caption-catalog.json");Verify(cp,boot.catalogSha256,null);Verify(Child(bundle,"catalog.json"),boot.legacyCatalogSha256,null);Verify(Child(bundle,"MultilingualLauncher.exe"),boot.launcherSha256,null);var catalog=Read<Catalog>(cp,4194304);
   Need(catalog.files.Length==3&&catalog.styles.Length==2&&boot.deltas.Length==3,"Invalid caption dimensions.");
   string content=Path.GetFullPath(selected);if(!File.Exists(Path.Combine(content,catalog.files[0].path)))content=Path.Combine(content,"Content");Guard(content);
   using(var mutex=new Mutex(false,"Local\\CrimsonSkies-CaptionPrepare-"+BootstrapPin.Digest)){
    bool held=false;try{try{held=mutex.WaitOne(0);}catch(AbandonedMutexException){held=true;}Need(held,"Another caption preparation is using this package.");
     if(catalog.styles.All(s=>File.Exists(Child(bundle,s.payload.path)))){foreach(var s in catalog.styles)Verify(Child(bundle,s.payload.path),s.payload.sha256,s.payload.bytes);log("Caption data already prepared. / 자막 준비 완료");return content;}
     string work=Child(bundle,".caption-prepare-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(work);var owned=new List<string>();var handles=new List<FileStream>();
     try{
      string[] current=new string[3];for(int i=0;i<3;i++){string p=Child(content,catalog.files[i].path);Guard(p);var f=new FileStream(p,FileMode.Open,FileAccess.Read,FileShare.Read);handles.Add(f);Need(f.Length==catalog.files[i].bytes,"Unsupported caption input size.");current[i]=Hash(p);}
      int sourceStyle=Array.FindIndex(catalog.styles,s=>s.hashes.SequenceEqual(current));Need(sourceStyle>=0,"전체 더빙 설치팩을 먼저 설치하세요. / Install the full Korean dub pack first. Unsupported/mixed caption baseline.");
      string[,] inputs=new string[2,3];for(int style=0;style<2;style++)for(int i=0;i<3;i++){
       string source=Child(content,catalog.files[i].path);if(current[i]==catalog.styles[style].hashes[i])inputs[style,i]=source;
       else{string output=Child(work,"decoded-"+style+"-"+i+".bin");owned.Add(output);Pair pair=boot.deltas.Single(x=>x.fileIndex==i);Decode(bundle,source,style==1?pair.forward:pair.reverse,output,boot.toolSha256);Verify(output,catalog.styles[style].hashes[i],catalog.files[i].bytes);inputs[style,i]=output;}
      }
      for(int style=0;style<2;style++){
       var s=catalog.styles[style];string destination=Child(bundle,s.payload.path);if(File.Exists(destination)){Verify(destination,s.payload.sha256,s.payload.bytes);continue;}
       string temp=Child(work,"payload-"+style+".bin");owned.Add(temp);using(var output=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){
        foreach(var span in catalog.spans){Need(span.fileIndex>=0&&span.fileIndex<3&&span.offset>=0&&span.bytes>0&&span.bytes<=1048576,"Invalid caption span.");using(var f=new FileStream(inputs[style,span.fileIndex],FileMode.Open,FileAccess.Read,FileShare.Read)){Need(span.offset+span.bytes<=f.Length,"Caption span exceeds input.");f.Position=span.offset;byte[] bytes=new byte[span.bytes];int n=0;while(n<bytes.Length){int got=f.Read(bytes,n,bytes.Length-n);Need(got>0,"Short caption read.");n+=got;}output.Write(bytes,0,bytes.Length);}}
        output.Flush(true);
       }Verify(temp,s.payload.sha256,s.payload.bytes);Guard(Path.GetDirectoryName(destination));Directory.CreateDirectory(Path.GetDirectoryName(destination));Need(!File.Exists(destination),"Caption payload appeared concurrently.");File.Move(temp,destination);Verify(destination,s.payload.sha256,s.payload.bytes);
      }
      for(int i=0;i<3;i++)Verify(Child(content,catalog.files[i].path),current[i],catalog.files[i].bytes);log("Prepared both caption styles from your owned game. Game files were not written. / 두 자막 종류 준비 완료");
     }finally{foreach(var f in handles)f.Dispose();foreach(string p in owned)if(File.Exists(p)){Guard(p);File.Delete(p);}Guard(work);Directory.Delete(work,false);}
     return content;
    }finally{if(held)mutex.ReleaseMutex();}
   }
  }
  public static void Open(string bundle,string content){var start=new ProcessStartInfo(Child(bundle,"MultilingualLauncher.exe"),"--gui-root "+Quote(content)){UseShellExecute=false,WindowStyle=ProcessWindowStyle.Normal};Process.Start(start);}
 }
 sealed class SetupForm:Form {
  readonly TextBox root=new TextBox{Dock=DockStyle.Fill,Text=Preparer.DefaultRoot};readonly TextBox output=new TextBox{Dock=DockStyle.Fill,Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Vertical};readonly Button run=new Button{Text="자막 선택기 열기 / Open",AutoSize=true};readonly Button browse=new Button{Text="폴더 / Folder",AutoSize=true};bool busy;
  public SetupForm(){Text="Crimson Skies — Alpha2 자막 준비 / Caption setup";Width=760;Height=330;StartPosition=FormStartPosition.CenterScreen;var layout=new TableLayoutPanel{Dock=DockStyle.Fill,RowCount=5,ColumnCount=1,Padding=new Padding(12)};layout.RowStyles.Add(new RowStyle(SizeType.Absolute,52));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,32));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,36));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.Controls.Add(new Label{Dock=DockStyle.Fill,Text="전체 한국어 더빙 설치 후 사용하세요. 처음 한 번 자막 데이터를 준비합니다.\r\nInstall the full Korean dub first. Caption data is generated locally from your game."},0,0);layout.Controls.Add(root,0,1);var row=new FlowLayoutPanel{Dock=DockStyle.Fill};row.Controls.Add(browse);row.Controls.Add(run);layout.Controls.Add(row,0,2);layout.Controls.Add(output,0,3);Controls.Add(layout);browse.Click+=delegate{using(var d=new FolderBrowserDialog()){if(d.ShowDialog(this)==DialogResult.OK)root.Text=d.SelectedPath;}};run.Click+=async delegate{if(busy)return;busy=true;run.Enabled=browse.Enabled=root.Enabled=false;string selected=root.Text;try{string bundle=AppDomain.CurrentDomain.BaseDirectory;string content=await Task.Run(()=>Preparer.Prepare(bundle,selected,Log));Preparer.Open(bundle,content);busy=false;Close();}catch(Exception e){Log(e.Message);}finally{busy=false;run.Enabled=browse.Enabled=root.Enabled=true;}};FormClosing+=delegate(object sender,FormClosingEventArgs e){if(busy)e.Cancel=true;};}
  void Log(string s){if(InvokeRequired){BeginInvoke(new Action<string>(Log),s);return;}output.AppendText(s+Environment.NewLine);}
 }
 static class Program {
  [STAThread]public static int Main(string[] args){if(args.Length==0){Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);Application.Run(new SetupForm());return 0;}try{Console.SetOut(new StreamWriter(Console.OpenStandardOutput(),new UTF8Encoding(false)){AutoFlush=true});Console.SetError(new StreamWriter(Console.OpenStandardError(),new UTF8Encoding(false)){AutoFlush=true});if(args.Length!=3||args[0]!="--prepare"||args[1]!="--root")throw new ArgumentException("Usage: PrepareSubtitleLauncher.exe --prepare --root CONTENT");Preparer.Prepare(AppDomain.CurrentDomain.BaseDirectory,args[2],Console.WriteLine);return 0;}catch(Exception e){Console.Error.WriteLine(e.Message);return 1;}}
 }
}
