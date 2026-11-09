// SPDX-License-Identifier: MIT
// Own UI controls only. Never click installation/restore/open or read game data.
using System;using System.Collections.Generic;using System.Drawing;using System.Drawing.Imaging;using System.IO;using System.Linq;using System.Reflection;using System.Windows.Forms;
using CrimsonSkiesUnified;
class PresetTests {
 static int checks;
 static void Need(bool condition,string why){checks++;if(!condition)throw new Exception(why);}
 static IEnumerable<Control> Descendants(Control root){foreach(Control c in root.Controls){yield return c;foreach(var d in Descendants(c))yield return d;}}
 static string Selected(SetupForm form){return (string)typeof(SetupForm).GetMethod("ProfileId",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(form,null);}
 static void Layout(Control root){root.PerformLayout();foreach(Control c in root.Controls)Layout(c);}
 static void Render(SetupForm form,string path){
  // Hidden WinForms parents omit child controls from DrawToBitmap. Show our
  // own fixture off-screen on CI so that native children are created/painted.
  if(!form.Visible){form.StartPosition=FormStartPosition.Manual;form.Location=new Point(-10000,-10000);form.Show();}
  Layout(form);form.Refresh();Application.DoEvents();
  using(var bitmap=new Bitmap(form.Width,form.Height)){form.DrawToBitmap(bitmap,new Rectangle(Point.Empty,form.Size));bitmap.Save(path,ImageFormat.Png);}
  foreach(var c in Descendants(form).Where(c=>c is RadioButton||c is CheckBox)){
   Need(c.Visible,"Choice hidden: "+c.Text);
   Need(c.Parent.ClientRectangle.Contains(c.Bounds),"Choice clipped: "+c.Text);
  }
 }
 [STAThread]static int Main(string[] args){try{
  Directory.CreateDirectory(args[0]);Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
  using(var form=new SetupForm(@"X:\Owned game\Content")){
   var radios=Descendants(form).OfType<RadioButton>().ToArray();var wides=Descendants(form).OfType<CheckBox>().ToArray();
   Need(radios.Length==4,"Four clear presets");Need(wides.Length==1,"Only widescreen is independent");
   Need(Selected(form)=="k1-w1-d1-dub","Full Korean default preserved");
   Render(form,Path.Combine(args[0],"01-default.png"));
   string[] prefixes={"원본 음성","영어 음성","한국어 더빙만","한국어 더빙 +"};
   string[] narrow={"k0-w0-d0-off","k1-w0-d0-original","k1-w0-d1-off","k1-w0-d1-dub"};
   for(int i=0;i<prefixes.Length;i++){
    var radio=radios.Single(r=>r.Text.StartsWith(prefixes[i]));radio.Checked=true;
    Need(radios.Count(r=>r.Checked)==1,"Presets are mutually exclusive");
    foreach(bool wide in new[]{false,true}){
     wides[0].Checked=wide;
     string expected=wide?narrow[i].Replace("-w0-","-w1-"):narrow[i];
     Need(Selected(form)==expected,"UI selects expected voice/caption/wide result");
     Need(!Selected(form).EndsWith("d1-original"),"No mismatched dub/translation choice");
     Console.WriteLine("PROFILE "+Selected(form));
    }
   }
   radios.Single(r=>r.Text.StartsWith("한국어 더빙만")).Checked=true;
   Need(wides[0].Checked,"Changing voice preset preserves widescreen choice");
   var labels=Descendants(form).OfType<Label>().Select(l=>l.Text).ToArray();
   Need(labels.Any(t=>t.Contains("기본 영상 자막은 유지")&&t.Contains("한글 메뉴·글꼴")),"Voice-only limitations visible");
   Render(form,Path.Combine(args[0],"02-voices-only-wide.png"));
   wides[0].Checked=false;Render(form,Path.Combine(args[0],"03-voices-only.png"));
   form.Size=form.MinimumSize;Render(form,Path.Combine(args[0],"04-minimum-size.png"));
  }
  bool refused=false;try{SelectionPolicy.ProfileId((InstallPreset)99,false);}catch(ArgumentOutOfRangeException){refused=true;}
  Need(refused,"Unknown preset refused");Console.WriteLine("PASS_PRESET_UI assertions="+checks);return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
