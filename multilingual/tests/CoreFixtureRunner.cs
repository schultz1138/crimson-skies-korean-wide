// Portable QA runner. Production source is copied and clamped by run_core_fixtures.py.
// No game, launcher, user settings or Windows process inventory is accessed.
using System; using System.IO; using System.Linq; using System.Text;
using System.Collections.Generic; using System.Threading; using System.Web.Script.Serialization;
namespace CrimsonSkiesMultilingual {
 public static class CatalogPin {
  public const string ReleaseId="Fixture-0.12";
  public static string Digest {get{return QAHooks.ExpectedCatalogHash;}}
 }
 public sealed class FixtureConfig {
  public string package,content,settings,backups,mode,pack,catalogHash,faultPhase,lockFile,mutexRoot,concurrentAA;
  public bool open,emu,menu,blockRecovery,launchFail,launchSetsMenu;
 }
 public static class QAHooks {
  public static FixtureConfig Config;
  public static string ExpectedCatalogHash;
  public static readonly List<string> Events=new List<string>();
  public static int Launches;
  public static FileStream HeldFile;
  static string Root {get{return Path.GetFullPath(AppDomain.CurrentDomain.BaseDirectory).TrimEnd('\\')+"\\";}}
  public static void Check(string path) {if(!Path.GetFullPath(path).StartsWith(Root,StringComparison.OrdinalIgnoreCase))throw new IOException("Fixture path left the fresh QA workspace.");}
  public static string Settings(){Check(Config.settings);return Config.settings;}
  public static string Backups(){Check(Config.backups);return Config.backups;}
  public static bool Running(string name){Events.Add("probe:"+name);return name=="Emu"?Config.emu:name=="EmuMenu"?Config.menu:false;}
  public static void Fault(string phase){Events.Add("fault:"+phase);if(phase!=Config.faultPhase)return;if(Config.concurrentAA!=null){Check(Config.settings);File.WriteAllBytes(Config.settings,Encoding.UTF8.GetBytes(File.ReadAllText(Config.settings,Encoding.UTF8).Replace("AA=4x","AA="+Config.concurrentAA)));}if(Config.lockFile!=null){Check(Config.lockFile);HeldFile=new FileStream(Config.lockFile,FileMode.Open,FileAccess.Read,FileShare.Read);}if(Config.blockRecovery)Config.emu=true;throw new IOException("Synthetic fault: "+phase);}
  public static void Launch(string content,string exe){Check(content);Check(exe);Events.Add("launch");Launches++;if(Config.launchFail)throw new IOException("Synthetic original-launcher start failure.");if(Config.launchSetsMenu)Config.menu=true;}
 }
 static class CoreFixtureRunner {
  static int Main(string[] args){
   if(args.Length!=2)throw new ArgumentException("Fixture config and result paths are required.");
   QAHooks.Check(args[0]);QAHooks.Check(args[1]);var json=new JavaScriptSerializer{MaxJsonLength=2097152};var c=json.Deserialize<FixtureConfig>(File.ReadAllText(args[0],Encoding.UTF8));QAHooks.Config=c;QAHooks.ExpectedCatalogHash=c.catalogHash;
   foreach(string p in new[]{c.package,c.content,c.settings,c.backups})QAHooks.Check(p);
   string error=null;bool ok=false;List<string> logs=new List<string>();Thread held=null;ManualResetEvent release=null,ready=null;
   try{
    if(c.mutexRoot!=null){QAHooks.Check(c.mutexRoot);ready=new ManualResetEvent(false);release=new ManualResetEvent(false);held=new Thread(()=>{using(var m=new Mutex(false,"Local\\CrimsonSkies-KoreanPatch-"+PackEngine.RootIdentity(c.mutexRoot))){m.WaitOne();ready.Set();release.WaitOne();m.ReleaseMutex();}});held.Start();ready.WaitOne();}
    if(c.lockFile!=null&&c.faultPhase==null){QAHooks.Check(c.lockFile);QAHooks.HeldFile=new FileStream(c.lockFile,FileMode.Open,FileAccess.Read,FileShare.None);}
    var engine=new PackEngine(c.package,s=>logs.Add(s));engine.Run(c.mode,c.content,c.pack,c.open);ok=true;
   }catch(Exception e){error=e.GetType().Name+": "+e.Message;}
   finally{if(QAHooks.HeldFile!=null)QAHooks.HeldFile.Dispose();if(release!=null)release.Set();if(held!=null)held.Join();}
   var result=new Dictionary<string,object>{{"success",ok},{"error",error},{"events",QAHooks.Events},{"logs",logs},{"launches",QAHooks.Launches},{"actualGameSettingsOrProcessInventoryAccess",false}};
   File.WriteAllText(args[1],json.Serialize(result)+"\n",new UTF8Encoding(false));Console.WriteLine(json.Serialize(result));return ok?0:1;
  }
 }
}
