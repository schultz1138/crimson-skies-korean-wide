// SPDX-License-Identifier: MIT
// Xbox deployment and Verify/Repair can leave different metadata for the same
// supported game build. Accept only the two observed complete byte identities;
// an equal Package/Identity by itself never authorizes unpinned XML.
using System;using System.IO;using System.Security.Cryptography;using System.Xml;
namespace CrimsonSkiesUnified {
 public static class HostManifest {
  internal const int MaxBytes=131072;
  internal const string DeployedHash="7d9e362e1af1b0c2e7f4b5f6bca9258530fd04a03a21640b1cbeff8049d9ed71";
  internal const long DeployedBytes=4815;
  internal const string RepairedHash="00e65011722a9efb2ad75a197398cef798311ce5d7f08bde47c8cc96aacf6633";
  internal const long RepairedBytes=4767;
  static bool Known(string hash,long bytes){return hash==DeployedHash&&bytes==DeployedBytes||hash==RepairedHash&&bytes==RepairedBytes;}
  internal static bool MatchesPinnedOrKnown(string pinnedHash,long pinnedBytes,string actualHash,long actualBytes){
   return pinnedHash==actualHash&&pinnedBytes==actualBytes||Known(pinnedHash,pinnedBytes)&&Known(actualHash,actualBytes);
  }
  public static void Verify(string path,string pinnedHash,long pinnedBytes,Identity expected){
   PatchEngine.NoReparse(path,false);
   byte[] raw;
   // Parse the same bounded snapshot whose complete SHA-256 was accepted.
   // Do not reopen the path between hashing and identity validation.
   using(var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
    if(stream.Length<=0||stream.Length>MaxBytes)throw new InvalidDataException("Unsupported host manifest size");
    raw=new byte[(int)stream.Length];int offset=0;
    while(offset<raw.Length){int read=stream.Read(raw,offset,raw.Length-offset);if(read==0)throw new EndOfStreamException("Host manifest changed while reading");offset+=read;}
   }
   string hash;using(var sha=SHA256.Create())hash=BitConverter.ToString(sha.ComputeHash(raw)).Replace("-","").ToLowerInvariant();
   if(!MatchesPinnedOrKnown(pinnedHash,pinnedBytes,hash,raw.LongLength))
    throw new InvalidDataException("지원하지 않는 설치 메타데이터입니다. / Hash mismatch: "+path);
   var settings=new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=MaxBytes};
   int count=0;
   using(var stream=new MemoryStream(raw,false))using(var reader=XmlReader.Create(stream,settings)){
    while(reader.Read())if(reader.NodeType==XmlNodeType.Element&&reader.LocalName=="Identity"){
     count++;
     if(expected==null||reader.Depth!=1||reader.NamespaceURI!="http://schemas.microsoft.com/appx/manifest/foundation/windows10"||
        reader.GetAttribute("Name")!=expected.name||reader.GetAttribute("Version")!=expected.version||
        reader.GetAttribute("ProcessorArchitecture")!=expected.architecture||reader.GetAttribute("Publisher")!=expected.publisher)
      throw new InvalidDataException("Unsupported identity");
    }
   }
   if(count!=1)throw new InvalidDataException("Invalid host identity");
  }
 }
}
