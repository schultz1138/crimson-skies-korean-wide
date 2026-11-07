// SPDX-License-Identifier: MIT
// Synthetic UI boundary only. No file picker, save store, game, SDK or cloud access.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using CrimsonSkiesMultilingual;

sealed class RestoreUiBackend : IProfileManagerBackend
{
    public int Lists, Inspects, Restores, Backups, Deletes, Recoveries;
    public string InspectedPath;
    public ProfileRestorePreview LastRestore;
    public ProfileListResult Listing;
    public ProfileRestorePreview Preview;
    public ProfileRestoreResult Receipt;
    public TaskCompletionSource<ProfileRestorePreview> PendingInspect;
    public TaskCompletionSource<ProfileRestoreResult> PendingRestore;
    public Exception InspectError, RestoreError;
    public Action BeforeReceipt;
    public RestoreUiBackend()
    {
        Listing = new ProfileListResult { ScopeLabel = "Synthetic destination only", Entries = new[] { Entry("active/A"), Entry("active/B") }, CanBackup = true, CanDelete = true, CanRestore = true };
        Preview = new ProfileRestorePreview { ProfileId = "source/archive", ProfileName = "Archived fixture", ContextLabel = "Synthetic account/store", ContextToken = "context/1", RevisionToken = "snapshot/1", BackupPath = @"C:\fixture-only\selected.zip", BackupSha256 = new string('a', 64), BackupBytes = 4096, CanRestore = true };
        Receipt = new ProfileRestoreResult { ProfileId = Preview.ProfileId, RestoredProfileId = "destination/new-guid", BackupPath = @"C:\fixture-only\owned-copy.zip", OtherProfilesPreserved = true, PendingCloudSync = true };
    }
    public static ManagedProfileEntry Entry(string id) { return new ManagedProfileEntry { Id = id, DisplayName = "Synthetic " + id, ContextToken = "context/1", RevisionToken = "snapshot/1", ProgressSummary = "4096 bytes" }; }
    public Task<ProfileListResult> ListAsync() { Lists++; return Task.FromResult(Listing); }
    public Task<ProfileRestorePreview> InspectBackupAsync(string path) { Inspects++; InspectedPath = path; if (InspectError != null) throw InspectError; return PendingInspect == null ? Task.FromResult(Preview) : PendingInspect.Task; }
    public Task<ProfileRestoreResult> RestoreAsync(ProfileRestorePreview preview, IProgress<string> log) { Restores++; LastRestore = preview; if (RestoreError != null) throw RestoreError; if (BeforeReceipt != null) BeforeReceipt(); return PendingRestore == null ? Task.FromResult(Receipt) : PendingRestore.Task; }
    public Task<ProfileBackupResult> BackupAsync(ManagedProfileEntry entry, IProgress<string> log) { Backups++; throw new InvalidOperationException("Unexpected synthetic backup"); }
    public Task<ProfileDeleteResult> BackupAndDeleteAsync(ManagedProfileEntry entry, IProgress<string> log) { Deletes++; throw new InvalidOperationException("Unexpected synthetic deletion"); }
    public Task<ProfileRecoveryResult> RecoverAsync(IProgress<string> log) { Recoveries++; throw new InvalidOperationException("Unexpected synthetic recovery"); }
}

static class ProfileRestoreUiFixture
{
    static readonly List<object> Results = new List<object>();
    static T Field<T>(object target, string name) { return (T)target.GetType().GetField(name, BindingFlags.NonPublic | BindingFlags.Instance).GetValue(target); }
    static void Check(string name, bool okay) { Results.Add(new { name = name, status = okay ? "PASS" : "FAIL" }); if (!okay) throw new Exception(name); }
    static void Wait(Task task) { DateTime end = DateTime.UtcNow.AddSeconds(5); while (!task.IsCompleted) { Application.DoEvents(); System.Threading.Thread.Sleep(1); if (DateTime.UtcNow > end) throw new Exception("Synthetic UI timeout"); } task.GetAwaiter().GetResult(); Application.DoEvents(); }
    static string Log(ProfileManagerForm form) { return Field<TextBox>(form, "output").Text; }
    static void Select(ProfileManagerForm form, int row) { var grid = Field<DataGridView>(form, "profiles"); grid.ClearSelection(); grid.Rows[row].Selected = true; }
    static bool Success(ProfileManagerForm form) { return Log(form).Contains("Confirmed selected backup restoration:"); }
    static void UnrelatedCounts(RestoreUiBackend backend, string label) { Check(label + " does not call backup/delete/recover", backend.Backups == 0 && backend.Deletes == 0 && backend.Recoveries == 0); }
    static void InitialAndCancel()
    {
        var backend = new RestoreUiBackend(); int confirmations = 0; string confirmation = null;
        using (var form = new ProfileManagerForm(backend, text => { confirmations++; confirmation = text; return DialogResult.No; }))
        {
            Check("restore starts disabled", !Field<Button>(form, "restore").Enabled);
            Wait(form.InspectAndRestoreAsync("ignored-before-list"));
            Check("before-list restore has no backend call", backend.Inspects == 0 && backend.Restores == 0);
            Wait(form.RefreshProfilesAsync());
            Check("readonly list neither inspects nor restores", backend.Inspects == 0 && backend.Restores == 0 && confirmations == 0);
            Select(form, 0); Select(form, 1);
            Check("selection neither inspects nor restores", backend.Inspects == 0 && backend.Restores == 0 && confirmations == 0);
            Field<DataGridView>(form, "profiles").ClearSelection();
            Check("restore needs no selected row", Field<Button>(form, "restore").Enabled);
            Wait(form.InspectAndRestoreAsync(null)); Wait(form.InspectAndRestoreAsync("  "));
            Check("empty selected path does nothing", backend.Inspects == 0);
            Wait(form.InspectAndRestoreAsync(@"D:\moved-zip\backup.zip"));
            Check("selected ZIP path passed unchanged to readonly inspection", backend.InspectedPath == @"D:\moved-zip\backup.zip" && backend.Inspects == 1);
            Check("No confirms once and never restores", confirmations == 1 && backend.Restores == 0 && !Success(form));
            Check("preview names source destination file hash and size", confirmation.Contains("Archived fixture") && confirmation.Contains("source/archive") && confirmation.Contains("Synthetic account/store") && confirmation.Contains("selected.zip") && confirmation.Contains(new string('a', 64)) && confirmation.Contains("4096"));
            Check("cancel refreshes readonly list", backend.Lists == 2 && Log(form).Contains("Restoration cancelled"));
            UnrelatedCounts(backend, "Cancel");
        }
    }
    static void CapabilityAndPending()
    {
        foreach (bool pending in new[] { false, true })
        {
            var backend = new RestoreUiBackend(); backend.Listing.CanRestore = pending; backend.Listing.RecoveryRequired = pending;
            if (pending) backend.Listing.Entries = null;
            int confirmations = 0;
            using (var form = new ProfileManagerForm(backend, text => { confirmations++; return DialogResult.Yes; }))
            {
                Wait(form.RefreshProfilesAsync()); Wait(form.InspectAndRestoreAsync("not-read.zip"));
                Check("capability/pending blocks picker " + pending, !Field<Button>(form, "restore").Enabled);
                Check("capability/pending blocks inspect confirmation restore " + pending, backend.Inspects == 0 && backend.Restores == 0 && confirmations == 0);
                Check("pending listing is not automatic recovery " + pending, backend.Recoveries == 0);
            }
        }
    }
    static void Conflicts()
    {
        foreach (string kind in new[] { "same-flag", "same-listed-id", "wrong-account", "wrong-store", "name-conflict", "guid-conflict", "unsupported" })
        {
            var backend = new RestoreUiBackend();
            if (kind == "same-flag") backend.Preview.SameProfileExists = true;
            else if (kind == "same-listed-id") backend.Preview.ProfileId = "active/A";
            else { backend.Preview.CanRestore = false; backend.Preview.BlockedReason = "Synthetic refusal: " + kind; }
            int confirmations = 0;
            using (var form = new ProfileManagerForm(backend, text => { confirmations++; return DialogResult.Yes; }))
            {
                Wait(form.RefreshProfilesAsync()); Wait(form.InspectAndRestoreAsync("fixture.zip"));
                Check("refuse preview before confirmation " + kind, backend.Inspects == 1 && confirmations == 0 && backend.Restores == 0 && !Success(form));
                Check("refusal refreshes and states refusal " + kind, backend.Lists == 2 && Log(form).Contains("Restore refused"));
                UnrelatedCounts(backend, kind);
            }
        }
    }
    static void InvalidPreviews()
    {
        foreach (string kind in new[] { "null", "id-null", "id-blank", "id-long", "context", "context-long", "revision", "revision-long", "path", "path-long", "hash-null", "hash-short", "hash-nonhex", "bytes-zero", "bytes-negative" })
        {
            var backend = new RestoreUiBackend();
            switch (kind)
            {
                case "null": backend.Preview = null; break;
                case "id-null": backend.Preview.ProfileId = null; break;
                case "id-blank": backend.Preview.ProfileId = " \t"; break;
                case "id-long": backend.Preview.ProfileId = new string('x', 513); break;
                case "context": backend.Preview.ContextToken = ""; break;
                case "context-long": backend.Preview.ContextToken = new string('x', 8193); break;
                case "revision": backend.Preview.RevisionToken = null; break;
                case "revision-long": backend.Preview.RevisionToken = new string('x', 8193); break;
                case "path": backend.Preview.BackupPath = " "; break;
                case "path-long": backend.Preview.BackupPath = new string('x', 32769); break;
                case "hash-null": backend.Preview.BackupSha256 = null; break;
                case "hash-short": backend.Preview.BackupSha256 = "abc"; break;
                case "hash-nonhex": backend.Preview.BackupSha256 = new string('g', 64); break;
                case "bytes-zero": backend.Preview.BackupBytes = 0; break;
                case "bytes-negative": backend.Preview.BackupBytes = -1; break;
            }
            int confirmations = 0;
            using (var form = new ProfileManagerForm(backend, text => { confirmations++; return DialogResult.Yes; }))
            {
                Wait(form.RefreshProfilesAsync()); Wait(form.InspectAndRestoreAsync("fixture.zip"));
                Check("invalid preview no confirm/write " + kind, backend.Inspects == 1 && confirmations == 0 && backend.Restores == 0 && !Success(form));
                Check("invalid preview failclosed refresh " + kind, backend.Lists == 2 && Log(form).Contains("Restoration stopped"));
            }
        }
    }
    static void CopyAndSuccess()
    {
        var backend = new RestoreUiBackend();
        using (var form = new ProfileManagerForm(backend, text =>
        {
            backend.Preview.ProfileId = "tampered-after-inspect";
            backend.Preview.ContextToken = "tampered-context";
            backend.Preview.RevisionToken = "tampered-revision";
            backend.Preview.BackupSha256 = new string('b', 64);
            return DialogResult.Yes;
        }))
        {
            backend.BeforeReceipt = () => backend.Listing.Entries = new[] { RestoreUiBackend.Entry("active/A"), RestoreUiBackend.Entry("active/B"), RestoreUiBackend.Entry("destination/new-guid") };
            Wait(form.RefreshProfilesAsync()); Wait(form.InspectAndRestoreAsync("fixture.zip"));
            Check("confirmed preview is private from provider DTO", backend.LastRestore.ProfileId == "source/archive" && backend.LastRestore.ContextToken == "context/1" && backend.LastRestore.RevisionToken == "snapshot/1" && backend.LastRestore.BackupSha256 == new string('a', 64));
            Check("different destination ID and owned ZIP path accepted", Success(form) && backend.LastRestore.BackupPath != backend.Receipt.BackupPath && backend.Receipt.ProfileId != backend.Receipt.RestoredProfileId);
            Check("success reselects destination-derived stable ID", Field<DataGridView>(form, "profiles").SelectedRows.Count == 1 && ((ManagedProfileEntry)Field<DataGridView>(form, "profiles").SelectedRows[0].Tag).Id == "destination/new-guid");
            Check("pending cloud sync is explicit only", Log(form).Contains("Cloud synchronization is pending"));
            Check("restore success does not call other mutations", backend.Restores == 1 && backend.Backups == 0 && backend.Deletes == 0 && backend.Recoveries == 0);
        }
        backend = new RestoreUiBackend(); backend.Receipt.RestoredProfileId = null;
        using (var form = new ProfileManagerForm(backend, text => DialogResult.Yes))
        {
            Wait(form.RefreshProfilesAsync()); Wait(form.InspectAndRestoreAsync("fixture.zip"));
            Check("optional destination identity may be null", Success(form));
        }
    }
    static void InvalidReceiptsAndErrors()
    {
        foreach (string kind in new[] { "null", "source-id", "path", "others", "dest-long", "inspect-error", "stale-revision", "zip-changed", "active-conflict-after-confirm", "source-mutated-by-backend" })
        {
            var backend = new RestoreUiBackend();
            if (kind == "null") backend.Receipt = null;
            else if (kind == "source-id") backend.Receipt.ProfileId = "wrong-source";
            else if (kind == "path") backend.Receipt.BackupPath = " ";
            else if (kind == "others") backend.Receipt.OtherProfilesPreserved = false;
            else if (kind == "dest-long") backend.Receipt.RestoredProfileId = new string('x', 513);
            else if (kind == "inspect-error") backend.InspectError = new IOException("Synthetic inspect failure");
            else if (kind == "source-mutated-by-backend") backend.BeforeReceipt = () => { backend.LastRestore.ProfileId = "mutated-by-backend"; backend.Receipt.ProfileId = "mutated-by-backend"; };
            else backend.RestoreError = new IOException("Synthetic backend rejects " + kind);
            using (var form = new ProfileManagerForm(backend, text => DialogResult.Yes))
            {
                Wait(form.RefreshProfilesAsync()); Wait(form.InspectAndRestoreAsync("fixture.zip"));
                Check("invalid receipt/error no success " + kind, !Success(form) && Log(form).Contains("Restoration stopped"));
                Check("invalid receipt/error refreshes readonly " + kind, backend.Lists == 2 && backend.Restores == (kind == "inspect-error" ? 0 : 1));
            }
        }
    }
    static void AssertBusy(ProfileManagerForm form, RestoreUiBackend backend, int restores, string phase)
    {
        foreach (string field in new[] { "refresh", "backup", "remove", "restore", "recover", "close" }) Check(phase + " disables " + field, !Field<Button>(form, field).Enabled);
        Check(phase + " disables grid", !Field<DataGridView>(form, "profiles").Enabled);
        Wait(form.InspectAndRestoreAsync("reentry.zip")); Wait(form.RunSelectedAsync(false)); Wait(form.RunSelectedAsync(true)); Wait(form.RefreshProfilesAsync()); Wait(form.RecoverPendingAsync());
        Check(phase + " blocks reentry", backend.Inspects == 1 && backend.Restores == restores && backend.Lists == 1 && backend.Backups == 0 && backend.Deletes == 0 && backend.Recoveries == 0);
        var closing = new FormClosingEventArgs(CloseReason.UserClosing, false);
        typeof(Form).GetMethod("OnFormClosing", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(form, new object[] { closing });
        Check(phase + " blocks close", closing.Cancel);
    }
    static void Busy()
    {
        var backend = new RestoreUiBackend(); backend.PendingInspect = new TaskCompletionSource<ProfileRestorePreview>();
        using (var form = new ProfileManagerForm(backend, text => DialogResult.No))
        {
            Wait(form.RefreshProfilesAsync()); Task operation = form.InspectAndRestoreAsync("fixture.zip"); AssertBusy(form, backend, 0, "Inspection busy"); backend.PendingInspect.SetResult(backend.Preview); Wait(operation);
            Check("inspection completion unlocks", Field<Button>(form, "restore").Enabled && Field<Button>(form, "close").Enabled && backend.Lists == 2);
        }
        backend = new RestoreUiBackend(); backend.PendingRestore = new TaskCompletionSource<ProfileRestoreResult>();
        using (var form = new ProfileManagerForm(backend, text => DialogResult.Yes))
        {
            Wait(form.RefreshProfilesAsync()); Task operation = form.InspectAndRestoreAsync("fixture.zip"); AssertBusy(form, backend, 1, "Restoration busy"); backend.PendingRestore.SetResult(backend.Receipt); Wait(operation);
            Check("restore completion unlocks", Field<Button>(form, "restore").Enabled && Field<Button>(form, "close").Enabled && backend.Lists == 2);
        }
    }
    static void Confirmation()
    {
        var preview = new RestoreUiBackend().Preview; preview.ProfileName = "Name\r\nspoof\u202e\u0000"; preview.ContextLabel = "context\u202d"; preview.BackupPath = "path\nspoof";
        string text = ProfileManagerForm.RestoreConfirmationText(preview);
        Check("restore confirmation strips injected label controls", !text.Contains("Name\r\nspoof") && !text.Contains("path\nspoof") && !text.Contains("\u202e") && !text.Contains("\u202d") && !text.Contains("\u0000"));
        Check("restore confirmation states refusal and preservation", text.Contains("No overwrite is offered") && text.Contains("Other profiles are preserved") && text.Contains("checked again"));
    }
    [STAThread] static int Main(string[] args)
    {
        Application.SetCompatibleTextRenderingDefault(false);
        try
        {
            InitialAndCancel(); CapabilityAndPending(); Conflicts(); InvalidPreviews(); CopyAndSuccess(); InvalidReceiptsAndErrors(); Busy(); Confirmation();
            File.WriteAllText(args[0], new JavaScriptSerializer().Serialize(new { status = "PASS", cases = Results.Count, rows = Results, scope = "Production UI with synthetic backend only; no real ZIP/save/game/cloud access" }));
            Console.WriteLine("PASS " + Results.Count); return 0;
        }
        catch (Exception error) { Console.Error.WriteLine(error); return 1; }
    }
}
