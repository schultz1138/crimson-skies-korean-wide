// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Crimson Skies Korean patch contributors.
using System;using System.IO;using System.Linq;using System.Text;using System.Text.RegularExpressions;using System.Collections.Generic;
namespace CrimsonSkiesKoreanPatch {
 public static class ResolutionSelectionMigration {
  public sealed class Plan {
   internal byte[] Before,After;internal bool Applied;
   public string SourceKey,CanonicalKey;public int PresetId;
   public bool Changed { get { return Before!=null&&After!=null&&!Before.SequenceEqual(After); } }
  }
  sealed class Mapping { public int Id;public string Canonical; }
  static readonly UTF8Encoding StrictUtf8=new UTF8Encoding(false,true);
  static readonly Regex Line=new Regex(@"(?m)^(\uFEFF?[ \t]*scaling[ \t]*=[ \t]*)([^\r\n]*)",RegexOptions.CultureInvariant);
  static readonly Dictionary<string,Mapping> Aliases=new Dictionary<string,Mapping>(StringComparer.Ordinal) {
   { "1x - 640x480",new Mapping { Id=1,Canonical="640×480 (4:3)" } },
   { "2x - 1280x960",new Mapping { Id=2,Canonical="1280×960 (4:3)" } },
   { "3x - 1920x1440",new Mapping { Id=3,Canonical="1920×1440 (4:3)" } },
   { "4x - 2560x1920",new Mapping { Id=4,Canonical="2560×1920 (4:3)" } },
   { "res-800x600",new Mapping { Id=5,Canonical="800×600 (4:3)" } },
   { "res-1024x768",new Mapping { Id=6,Canonical="1024×768 (4:3)" } },
   { "res-1280x720",new Mapping { Id=7,Canonical="1280×720 (720p, 16:9)" } },
   { "res-1600x900",new Mapping { Id=8,Canonical="1600×900 (16:9)" } },
   { "res-1920x1080",new Mapping { Id=9,Canonical="1920×1080 (1080p, 16:9)" } },
   { "res-2560x1440",new Mapping { Id=10,Canonical="2560×1440 (1440p, 16:9)" } },
   { "res-3840x2160",new Mapping { Id=11,Canonical="3840×2160 (4K, 16:9)" } },
   { "640×480 (4:3)",new Mapping { Id=1,Canonical="640×480 (4:3)" } },
   { "800×600 (4:3)",new Mapping { Id=5,Canonical="800×600 (4:3)" } },
   { "1024×768 (4:3)",new Mapping { Id=6,Canonical="1024×768 (4:3)" } },
   { "1280×720 (720p, 16:9)",new Mapping { Id=7,Canonical="1280×720 (720p, 16:9)" } },
   { "1280×960 (4:3)",new Mapping { Id=2,Canonical="1280×960 (4:3)" } },
   { "1600×900 (16:9)",new Mapping { Id=8,Canonical="1600×900 (16:9)" } },
   { "1920×1080 (1080p, 16:9)",new Mapping { Id=9,Canonical="1920×1080 (1080p, 16:9)" } },
   { "1920×1440 (4:3)",new Mapping { Id=3,Canonical="1920×1440 (4:3)" } },
   { "2560×1440 (1440p, 16:9)",new Mapping { Id=10,Canonical="2560×1440 (1440p, 16:9)" } },
   { "2560×1920 (4:3)",new Mapping { Id=4,Canonical="2560×1920 (4:3)" } },
   { "3840×2160 (4K, 16:9)",new Mapping { Id=11,Canonical="3840×2160 (4K, 16:9)" } },
   { "3840×2160 (4K, 16:9, AA 자동 끔)",new Mapping { Id=11,Canonical="3840×2160 (4K, 16:9)" } },

  };
  public static Plan PrepareBytes(byte[] raw) {return PrepareParsed(raw,true);}
  static Plan PrepareParsed(byte[] raw,bool canonicalize) {
   var p=new Plan{Before=raw==null?null:(byte[])raw.Clone(),After=raw==null?null:(byte[])raw.Clone()};if(raw==null)return p;
   if(raw.Length>65536)throw new InvalidDataException("Resolution settings exceed64KiB");
   string text=StrictUtf8.GetString(raw);MatchCollection matches=Line.Matches(text);if(matches.Count==0)return p;
   if(matches.Count!=1)throw new InvalidDataException("Duplicate resolution setting");
   Match m=matches[0];string value=m.Groups[2].Value,key=value.Trim();Mapping map;if(!Aliases.TryGetValue(key,out map))throw new InvalidDataException("Unknown resolution key");
   p.SourceKey=key;p.CanonicalKey=map.Canonical;p.PresetId=map.Id;if(key==map.Canonical||!canonicalize)return p;
   int lead=value.Length-value.TrimStart().Length,trail=value.Length-value.TrimEnd().Length;
   int at=m.Groups[2].Index+lead,len=value.Length-lead-trail;
   p.After=StrictUtf8.GetBytes(text.Substring(0,at)+map.Canonical+text.Substring(at+len));if(p.After.Length>65536)throw new InvalidDataException("Migrated resolution settings exceed64KiB");return p;
  }
  public static bool Describe(string key,out int id,out string canonical) {Mapping m;if(key!=null&&Aliases.TryGetValue(key,out m)){id=m.Id;canonical=m.Canonical;return true;}id=0;canonical=null;return false;}
  public static Plan PrepareReplacement(byte[] raw,string target) {
   int id;string canonical;if(!Describe(target,out id,out canonical))throw new InvalidDataException("Unknown replacement resolution");Plan p=PrepareParsed(raw,false);if(p.SourceKey==null)return p;
   string text=StrictUtf8.GetString(raw);Match m=Line.Matches(text)[0];string value=m.Groups[2].Value;int lead=value.Length-value.TrimStart().Length,trail=value.Length-value.TrimEnd().Length,at=m.Groups[2].Index+lead,len=value.Length-lead-trail;
   p.After=StrictUtf8.GetBytes(text.Substring(0,at)+target+text.Substring(at+len));if(p.After.Length>65536)throw new InvalidDataException("Restored resolution settings exceed64KiB");p.CanonicalKey=target;return p;
  }
  static void GuardExisting(string path,Action<string,bool> guard) {
   if(File.Exists(path)){guard(path,false);return;}
   string p=Path.GetDirectoryName(path);while(!Directory.Exists(p)){string n=Path.GetDirectoryName(p);if(String.IsNullOrEmpty(n)||n==p)throw new IOException("No owned settings ancestor");p=n;}guard(p,true);
  }
  static byte[] Read(string path,Action<string,bool> guard) {
   GuardExisting(path,guard);if(!File.Exists(path))return null;
   if(new FileInfo(path).Length>65536)throw new InvalidDataException("Resolution settings exceed64KiB");return File.ReadAllBytes(path);
  }
  static bool Equal(byte[] a,byte[] b){return a==null?b==null:b!=null&&a.SequenceEqual(b);}
  public static Plan PrepareFile(string path,Action<string,bool> guard){return PrepareBytes(Read(path,guard));}
  public static void EnsureUnchanged(string path,Plan p,Action<string,bool> guard){if(p==null)throw new InvalidOperationException("Migration not prepared");if(!Equal(Read(path,guard),p.Applied?p.After:p.Before))throw new IOException("Resolution settings changed concurrently");}
  static void Replace(string path,Plan p,byte[] expected,byte[] desired,bool applied,Action stopped,Action<string,bool> guard) {
   stopped();if(desired==null||expected==null)throw new InvalidOperationException("Migration never creates or deletes settings");
   if(!Equal(Read(path,guard),expected))throw new IOException("Resolution settings changed concurrently");
   string parent=Path.GetDirectoryName(path);guard(parent,true);string temp=Path.Combine(parent,".CrimsonSkies-selection-"+Guid.NewGuid().ToString("N")+".tmp");
   try {
    using(var stream=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){stream.Write(desired,0,desired.Length);stream.Flush(true);}
    stopped();guard(path,false);if(!Equal(Read(path,guard),expected))throw new IOException("Resolution settings changed before commit");
    File.Replace(temp,path,null);p.Applied=applied;
    if(!Equal(Read(path,guard),desired))throw new IOException("Resolution migration verification failed");
   } finally {if(File.Exists(temp)){guard(temp,false);File.Delete(temp);}}
  }
  public static void Commit(string path,Plan p,Action stopped,Action<string,bool> guard) {
   stopped();EnsureUnchanged(path,p,guard);if(!p.Changed||p.Applied)return;Replace(path,p,p.Before,p.After,true,stopped,guard);
  }
  public static void Rollback(string path,Plan p,Action stopped,Action<string,bool> guard) {
   if(p==null||!p.Applied||!p.Changed)return;Replace(path,p,p.After,p.Before,false,stopped,guard);
  }
 }
}
