// SPDX-License-Identifier: MIT
using System;
namespace CrimsonSkiesUnified {
 public enum InstallPreset {Original,KoreanSubtitles,KoreanVoicesOnly,KoreanVoicesAndSubtitles}
 public static class SelectionPolicy {
  public static string ProfileId(InstallPreset preset,bool wide){
   string korean,dub,captions;
   switch(preset){
    case InstallPreset.Original:korean="0";dub="0";captions="off";break;
    case InstallPreset.KoreanSubtitles:korean="1";dub="0";captions="original";break;
    case InstallPreset.KoreanVoicesOnly:korean="1";dub="1";captions="off";break;
    case InstallPreset.KoreanVoicesAndSubtitles:korean="1";dub="1";captions="dub";break;
    default:throw new ArgumentOutOfRangeException("preset");
   }
   return "k"+korean+"-w"+(wide?"1":"0")+"-d"+dub+"-"+captions;
  }
 }
}
