using System;
using System.IO;
using System.Reflection;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Web.Script.Serialization;
using CrimsonSkiesMultilingual;
static class FixtureState {public static string PreferencePath;}
namespace CrimsonSkiesMultilingual { public static class ProfileManagerServices { public static void Configure() {} }
 public sealed class PackDefinition {public string id="en-US",displayName="Synthetic",coverage="Synthetic only";}
 public sealed class CatalogDefinition {public PackDefinition[] packs=new[]{new PackDefinition()};}
 public sealed class PackEngine {
  public static int Runs,Constructors;public static bool FailRun;public static string LastMode,LastRoot,LastPack;public static bool LastOpen;
  public CatalogDefinition Catalog=new CatalogDefinition();
  public PackEngine(string p,Action<string> log){Constructors++;}
  public void Run(string mode,string root,string pack,bool open){Runs++;LastMode=mode;LastRoot=root;LastPack=pack;LastOpen=open;if(FailRun)throw new IOException("synthetic engine stop before preferences");}
 }
}
static class ProfileLaunchGuardFixture {
 static List<object> rows=new List<object>();
 static void Check(string n,bool value){rows.Add(new{name=n,status=value?"PASS":"FAIL"});if(!value)throw new Exception(n);}
 static void Wait(Task t){var until=DateTime.UtcNow.AddSeconds(5);while(!t.IsCompleted){Application.DoEvents();System.Threading.Thread.Sleep(1);if(DateTime.UtcNow>until)throw new Exception("timeout");}t.GetAwaiter().GetResult();}
 static void Reset(){PackEngine.Runs=0;PackEngine.Constructors=0;PackEngine.FailRun=false;}
 [STAThread] static int Main(string[] args){FixtureState.PreferencePath=Path.Combine(args[0],"ui-preferences.json");try{
 foreach(string mode in new[]{"null","allow","reject"}){Reset();int guards=0;ProfileManagerUi.BeforeGameLaunch=mode=="null"?null:(Func<string,Task>)(p=>{guards++;if(mode=="reject")throw new IOException("synthetic pending recovery");return Task.FromResult(0);});int result=Program.Main(new[]{"--activate","--root",args[0],"--pack","en-US","--open"});Check("CLI launch guard "+mode,result==(mode=="reject"?1:0)&&PackEngine.Runs==(mode=="reject"?0:1)&&guards==(mode=="null"?0:1));if(mode!="reject")Check("CLI forwards coherent mode/root/pack/open "+mode,PackEngine.LastMode=="--activate"&&PackEngine.LastRoot==args[0]&&PackEngine.LastPack=="en-US"&&PackEngine.LastOpen);else Check("CLI refuses before engine construction",PackEngine.Constructors==0);}
 Reset();int count=0;ProfileManagerUi.BeforeGameLaunch=p=>{count++;throw new IOException("must not invoke");};int rc=Program.Main(new[]{"--check","--root",args[0]});Check("CLI nonlaunch check does not call guard",rc==0&&count==0&&PackEngine.Runs==1&&!PackEngine.LastOpen);Reset();rc=Program.Main(new[]{"--check","--root",args[0],"--open"});Check("CLI malformed open rejected before guard/engine",rc==1&&count==0&&PackEngine.Runs==0);
 foreach(string mode in new[]{"null","allow","reject","nonlaunch"}){Reset();PackEngine.FailRun=true;int guards=0;ProfileManagerUi.BeforeGameLaunch=mode=="null"?null:(Func<string,Task>)(p=>{guards++;if(mode=="reject")throw new IOException("synthetic pending recovery");return Task.FromResult(0);});using(var f=new LanguageForm()){typeof(LanguageForm).GetField("root",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(f).GetType().GetProperty("Text").SetValue(typeof(LanguageForm).GetField("root",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(f),args[0],null);Task t=(Task)typeof(LanguageForm).GetMethod("Run",BindingFlags.Instance|BindingFlags.NonPublic).Invoke(f,new object[]{"--activate",mode!="nonlaunch"});Wait(t);Check("GUI launch guard "+mode,PackEngine.Runs==(mode=="reject"?0:1)&&guards==(mode=="null"||mode=="nonlaunch"?0:1));}}
 Check("fixture preferences never written",!File.Exists(FixtureState.PreferencePath));File.WriteAllText(args[1],new JavaScriptSerializer().Serialize(new{status="PASS",cases=rows.Count,rows=rows,scope="Actual GUI/CLI guard ordering with stubbed engine; named PreferencePath clamped into QA; no real engine/settings/process/store."}));Console.WriteLine("PASS "+rows.Count);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
