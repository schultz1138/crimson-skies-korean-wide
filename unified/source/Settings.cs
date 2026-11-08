// SPDX-License-Identifier: MIT
// Own only the existing language/resolution keys. AA and every other setting
// survive component switches/restoration. Missing settings are never created.
using System;using System.IO;using System.Linq;using System.Text;using System.Text.RegularExpressions;
namespace CrimsonSkiesUnified {
 public sealed class SettingOrigin {public string language,scaling;}
 public static class Settings {
  static readonly UTF8Encoding Utf8=new UTF8Encoding(false,true);
  static readonly string[] Legacy={"1x - 640x480","2x - 1280x960","3x - 1920x1440","4x - 2560x1920"};
  static Regex Pattern(string key){return new Regex(@"(?:\A|(?<=[\r\n]))(?<line>\uFEFF?[^\S\r\n]*"+Regex.Escape(key)+@"[^\S\r\n]*=[^\r\n]*)(?=[\r\n]|\z)",RegexOptions.IgnoreCase|RegexOptions.CultureInvariant);}
  static Match Find(string text,string key){var all=Pattern(key).Matches(text??"");if(all.Count>1)throw new InvalidDataException("Duplicate settings key: "+key);return all.Count==0?null:all[0];}
  static string Text(byte[] raw){if(raw==null)return null;if(raw.Length>65536)throw new InvalidDataException("Settings exceed64KiB");string t=Utf8.GetString(raw);if(t.IndexOf('\0')>=0)throw new InvalidDataException("Invalid settings encoding");Find(t,"scaling");Find(t,"game-language");return t;}
  static string Line(string t,string key){var m=Find(t,key);return m==null?null:m.Groups["line"].Value;}
  static string Value(string line){return line==null?null:line.Substring(line.IndexOf('=')+1).Trim();}
  public static void ValidateOrigin(SettingOrigin o){if(o==null)throw new InvalidDataException("Missing settings origin");foreach(string key in new[]{"game-language","scaling"}){string line=key=="scaling"?o.scaling:o.language;if(line==null)continue;if(line.Length>65536||line.IndexOfAny(new[]{'\r','\n','\0'})>=0||Line(line,key)!=line)throw new InvalidDataException("Invalid settings origin line");}}
  public static SettingOrigin Capture(byte[] raw){string t=Text(raw);return new SettingOrigin{language=Line(t,"game-language"),scaling=Line(t,"scaling")};}
  static string SetLine(string text,string key,string line){var m=Find(text,key);if(m==null)return text;var g=m.Groups["line"];return text.Substring(0,g.Index)+(line??"")+text.Substring(g.Index+g.Length);}
  static string SetValue(string text,string key,string value){string line=Line(text,key);if(line==null)return text;int at=line.IndexOf('=')+1;string tail=line.Substring(at);int first=0,last=tail.Length;while(first<tail.Length&&Char.IsWhiteSpace(tail[first]))first++;while(last>first&&Char.IsWhiteSpace(tail[last-1]))last--;return SetLine(text,key,line.Substring(0,at)+tail.Substring(0,first)+value+tail.Substring(last));}
  public static byte[] Plan(byte[] before,SettingOrigin origin,bool korean,bool wide,bool restore){ValidateOrigin(origin);string t=Text(before);if(t==null)return null;
   string language=Value(Line(t,"game-language")),scale=Value(Line(t,"scaling"));
   if(restore){if(language=="ko-KR")t=SetLine(t,"game-language",origin.language);if(scale!=null){int id;string canonical;if(!ResolutionSelectionMigration.Describe(scale,out id,out canonical))throw new InvalidDataException("Unknown resolution key");t=SetLine(t,"scaling",origin.scaling);}}
   else{
    if(korean)t=SetValue(t,"game-language","ko-KR");else if(language=="ko-KR"){string old=Value(origin.language);t=SetLine(t,"game-language",origin.language);if(old!=null&&!new[]{"System","Deutsch","English","français","한국어","中文（繁體）"}.Contains(old))t=SetValue(t,"game-language","System");}
    if(scale!=null){int id;string canonical;if(!ResolutionSelectionMigration.Describe(scale,out id,out canonical))throw new InvalidDataException("Unknown resolution key");t=SetValue(t,"scaling",wide?canonical:Legacy[id>=1&&id<=4?id-1:1]);}
   }var result=Utf8.GetBytes(t);if(result.Length>65536)throw new InvalidDataException("Settings exceed64KiB");return result;
  }
  public static byte[] Read(string path){if(!File.Exists(path)){string p=Path.GetDirectoryName(path);while(!Directory.Exists(p)){if(File.Exists(p))throw new IOException("Settings parent is a file");p=Path.GetDirectoryName(p);}PatchEngine.NoReparse(p,true);return null;}PatchEngine.NoReparse(path,false);if(new FileInfo(path).Length>65536)throw new InvalidDataException("Settings exceed64KiB");byte[] b=File.ReadAllBytes(path);Text(b);return b;}
  public static bool Equal(byte[] a,byte[] b){return a==null?b==null:b!=null&&a.SequenceEqual(b);}
  public static string Encode(byte[] b){return b==null?null:Convert.ToBase64String(b);}
  public static byte[] Bytes(string s){if(s==null)return null;if(s.Length>90000)throw new InvalidDataException("Oversize settings journal");byte[] b=Convert.FromBase64String(s);Text(b);return b;}
  public static void Ensure(string path,byte[] expected){if(!Equal(Read(path),expected))throw new IOException("Settings changed concurrently");}
  public static void Commit(string path,byte[] before,byte[] after){PatchEngine.RequireStopped();Ensure(path,before);if(Equal(before,after))return;if(before==null||after==null)throw new IOException("Settings creation/deletion is not allowed");string folder=Path.GetDirectoryName(path),temp=Path.Combine(folder,".csunified-setting-"+Guid.NewGuid().ToString("N")+".tmp");try{using(var f=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){f.Write(after,0,after.Length);f.Flush(true);}PatchEngine.RequireStopped();Ensure(path,before);PatchEngine.NoReparse(folder,true);File.Replace(temp,path,null);Ensure(path,after);}finally{if(File.Exists(temp)){PatchEngine.NoReparse(temp,false);File.Delete(temp);}}}
  public static void Rollback(string path,byte[] before,byte[] after){byte[] current=Read(path);if(Equal(current,before)||Equal(before,after))return;if(Equal(current,after)){Commit(path,after,before);return;}if(current==null||before==null||after==null)throw new IOException("Settings recovery refused external creation/deletion");string now=Text(current),old=Text(before),applied=Text(after);foreach(string key in new[]{"game-language","scaling"}){string a=Line(old,key),b=Line(applied,key),c=Line(now,key);if(a==b||c==a)continue;if(c!=b)throw new IOException("Settings recovery refused concurrent change of "+key);now=SetLine(now,key,a);}Commit(path,current,Utf8.GetBytes(now));}
 }
}
