// SPDX-License-Identifier: MIT
namespace CrimsonSkiesKoreanPatch {
 public sealed partial class PatchEngine {
  sealed class NoSelection {}
  NoSelection PrepareApplySelection(){return new NoSelection();}
  NoSelection PrepareRestoreSelection(string key){if(key!="unchanged")throw new System.IO.InvalidDataException("Invalid unchanged-settings receipt.");return new NoSelection();}
  void EnsureSelectionUnchanged(NoSelection p){}
  void CommitSelection(NoSelection p){}
  void RollbackSelection(NoSelection p){}
  SelectionBefore CaptureSelectionBefore(NoSelection p){return new SelectionBefore{beforeKey="unchanged",restoreKey="unchanged",beforePresetId=0};}
  void ValidateSelectionBefore(SelectionBefore p){if(p==null||p.beforeKey!="unchanged"||p.restoreKey!="unchanged"||p.beforePresetId!=0)throw new System.IO.InvalidDataException("Invalid unchanged-settings receipt.");}
 }
}
