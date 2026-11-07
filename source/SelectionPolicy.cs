// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Crimson Skies Korean patch contributors.
using System;using System.IO;using System.Linq;
namespace CrimsonSkiesKoreanPatch {
 public sealed partial class PatchEngine {
  static readonly string[] LegacyScaling={"1x - 640x480","2x - 1280x960","3x - 1920x1440","4x - 2560x1920"};
  static byte[] ReadSelectionBytes() {string p=SettingsPath();if(!File.Exists(p))return null;NoReparse(p,false);if(new FileInfo(p).Length>65536)throw new InvalidDataException("해상도 설정 파일 크기가 올바르지 않습니다.");return File.ReadAllBytes(p);}
  ResolutionSelectionMigration.Plan PrepareApplySelection(){return ResolutionSelectionMigration.PrepareFile(SettingsPath(),NoReparse);}
  ResolutionSelectionMigration.Plan PrepareRestoreSelection(string restore){if(!LegacyScaling.Contains(restore))throw new InvalidDataException("복구할 해상도 기록이 올바르지 않습니다.");return ResolutionSelectionMigration.PrepareReplacement(ReadSelectionBytes(),restore);}
  void EnsureSelectionUnchanged(ResolutionSelectionMigration.Plan p){ResolutionSelectionMigration.EnsureUnchanged(SettingsPath(),p,NoReparse);}
  void CommitSelection(ResolutionSelectionMigration.Plan p){ResolutionSelectionMigration.Commit(SettingsPath(),p,RequireStopped,NoReparse);}
  void RollbackSelection(ResolutionSelectionMigration.Plan p){ResolutionSelectionMigration.Rollback(SettingsPath(),p,RequireStopped,NoReparse);}
  static string CompatibleBefore(string key,int id){if(key!=null&&LegacyScaling.Contains(key))return key;return id>=1&&id<=4?LegacyScaling[id-1]:LegacyScaling[1];}
  SelectionBefore CaptureSelectionBefore(ResolutionSelectionMigration.Plan p){return new SelectionBefore{beforeKey=p.SourceKey,beforePresetId=p.PresetId,restoreKey=CompatibleBefore(p.SourceKey,p.PresetId)};}
  void ValidateSelectionBefore(SelectionBefore p){if(p==null)throw new InvalidDataException("설치 전 해상도 기록이 없습니다.");int id;string canonical;if(p.beforeKey==null){if(p.beforePresetId!=0)throw new InvalidDataException("설치 전 해상도 기록이 올바르지 않습니다.");id=0;}else if(p.beforeKey.Length>128||!ResolutionSelectionMigration.Describe(p.beforeKey,out id,out canonical)||id!=p.beforePresetId)throw new InvalidDataException("설치 전 해상도 기록이 올바르지 않습니다.");if(p.restoreKey!=CompatibleBefore(p.beforeKey,id))throw new InvalidDataException("복구 해상도 기록이 원래 선택과 일치하지 않습니다.");}
 }
}
