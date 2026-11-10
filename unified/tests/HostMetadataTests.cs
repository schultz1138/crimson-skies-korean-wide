// SPDX-License-Identifier: MIT
// Synthetic XML and hash-policy tests. Optional owned snapshots are read only;
// no proprietary appxmanifest.xml is committed or included in the fixture.
using System;using System.IO;using System.Security.Cryptography;using System.Text;using System.Xml;using CrimsonSkiesUnified;
class HostMetadataTests {
 static int checks,owned;static string root;static int serial;
 static readonly Identity Expected=new Identity{name="Xbox360BackwardCompatibil.PrimaryCrimsonSkiesHighR",version="2608.3123.1.0",architecture="x64",publisher="CN=92ADE8CC-2A9A-4DF3-9BAF-18AF498CAA12"};
 const string Namespace="http://schemas.microsoft.com/appx/manifest/foundation/windows10";
 static void Need(bool ok,string message){checks++;if(!ok)throw new Exception(message);}
 static string Hash(byte[] raw){using(var sha=SHA256.Create())return BitConverter.ToString(sha.ComputeHash(raw)).Replace("-","").ToLowerInvariant();}
 static string IdentityXml(string name,string version,string architecture,string publisher){return "<Identity Name=\""+name+"\" Version=\""+version+"\" ProcessorArchitecture=\""+architecture+"\" Publisher=\""+publisher+"\"/>";}
 static string Id(){return IdentityXml(Expected.name,Expected.version,Expected.architecture,Expected.publisher);}
 static byte[] Xml(string inside){return Encoding.UTF8.GetBytes("<Package xmlns=\""+Namespace+"\">"+inside+"</Package>");}
 static string Write(byte[] raw){string path=Path.Combine(root,"fixture-"+(serial++)+".xml");File.WriteAllBytes(path,raw);return path;}
 static void Verify(byte[] raw){HostManifest.Verify(Write(raw),Hash(raw),raw.Length,Expected);}
 static void Reject(Action action,string message){
  try{action();}catch(InvalidDataException){Need(true,message);return;}catch(XmlException){Need(true,message);return;}
  throw new Exception("Unexpected acceptance: "+message);
 }
 static void Policy(){
  string[] hashes={HostManifest.DeployedHash,HostManifest.RepairedHash};long[] sizes={HostManifest.DeployedBytes,HostManifest.RepairedBytes};
  for(int p=0;p<2;p++)for(int a=0;a<2;a++){
   Need(HostManifest.MatchesPinnedOrKnown(hashes[p],sizes[p],hashes[a],sizes[a]),"Known deployment/repair pair");
   Need(!HostManifest.MatchesPinnedOrKnown(hashes[p],sizes[p],hashes[a],sizes[a]+1),"Known digest with wrong actual length");
   Need(!HostManifest.MatchesPinnedOrKnown(hashes[p],sizes[p]+1,hashes[a],sizes[a]),"Wrong pinned length cannot authorize variant");
   Need(!HostManifest.MatchesPinnedOrKnown(new string('a',64),sizes[p],hashes[a],sizes[a]),"Unrelated pin cannot authorize known variant");
  }
  string synthetic=new string('b',64);
  Need(HostManifest.MatchesPinnedOrKnown(synthetic,123,synthetic,123),"Exact producer pin remains supported");
  Need(!HostManifest.MatchesPinnedOrKnown(synthetic,123,synthetic,124),"Exact hash still binds length");
  Need(!HostManifest.MatchesPinnedOrKnown(HostManifest.DeployedHash,HostManifest.DeployedBytes,synthetic,HostManifest.RepairedBytes),"Unknown same-sized XML refused");
 }
 static void IdentityChecks(){
  byte[] good=Xml(Id());Verify(good);Need(true,"Synthetic pinned Identity");
  string path=Write(good);byte[] changed=Xml(Id()+" ");File.WriteAllBytes(path,changed);
  Reject(delegate{HostManifest.Verify(path,Hash(good),good.Length,Expected);},"Same Identity does not permit unpinned metadata changes");
  foreach(string field in new[]{"name","version","architecture","publisher"}){
   byte[] raw=Xml(IdentityXml(field=="name"?"Other.Game":Expected.name,field=="version"?"2608.3124.1.0":Expected.version,field=="architecture"?"arm64":Expected.architecture,field=="publisher"?"CN=Other":Expected.publisher));
   Reject(delegate{Verify(raw);},"Wrong "+field+" rejected even when byte-pinned");
  }
  Reject(delegate{Verify(Xml(Id()+Id()));},"Duplicate Identity");
  Reject(delegate{Verify(Xml("<Nested>"+Id()+"</Nested>"));},"Nested Identity");
  Reject(delegate{Verify(Xml("<Identity xmlns=\"urn:wrong\" Name=\""+Expected.name+"\"/>"));},"Wrong Identity namespace");
  Reject(delegate{Verify(Xml("<Properties/>"));},"Missing Identity");
  Reject(delegate{Verify(Encoding.UTF8.GetBytes("<!DOCTYPE Package [<!ENTITY x 'blocked'>]>"+Encoding.UTF8.GetString(good)));},"DTD refused");
  Reject(delegate{Verify(Encoding.UTF8.GetBytes("<Package>"));},"Malformed XML");
  Reject(delegate{Verify(new byte[HostManifest.MaxBytes+1]);},"Bounded host snapshot");
  Reject(delegate{Verify(new byte[0]);},"Empty host snapshot");
  string nullPath=Write(good);Reject(delegate{HostManifest.Verify(nullPath,Hash(good),good.Length,null);},"Missing expected identity");
 }
 static void Owned(string path){
  byte[] before=File.ReadAllBytes(path);string digest=Hash(before);
  Need(digest==HostManifest.DeployedHash&&before.Length==HostManifest.DeployedBytes||digest==HostManifest.RepairedHash&&before.Length==HostManifest.RepairedBytes,"Owned snapshot is one of the reproduced complete identities");
  HostManifest.Verify(path,HostManifest.DeployedHash,HostManifest.DeployedBytes,Expected);Need(true,"Owned snapshot against deployed pin");
  HostManifest.Verify(path,HostManifest.RepairedHash,HostManifest.RepairedBytes,Expected);Need(true,"Owned snapshot against repaired pin");
  byte[] altered=new byte[before.Length+1];Buffer.BlockCopy(before,0,altered,0,before.Length);altered[altered.Length-1]=10;
  string changed=Write(altered);Reject(delegate{HostManifest.Verify(changed,HostManifest.DeployedHash,HostManifest.DeployedBytes,Expected);},"Altered owned snapshot refused");
  Need(Hash(File.ReadAllBytes(path))==digest,"Owned source XML unchanged");owned++;
 }
 static int Main(string[] args){try{
  root=args[0];Directory.CreateDirectory(root);Policy();IdentityChecks();
  for(int i=1;i<args.Length;i++)Owned(args[i]);
  Console.WriteLine("PASS_HOST_METADATA assertions="+checks+" ownedSnapshots="+owned);return 0;
 }catch(Exception e){Console.Error.WriteLine(e.ToString());return 1;}}
}
