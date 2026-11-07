// SPDX-License-Identifier: MIT
using System;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace CrimsonSkiesMultilingual
{
    // Data-only UI boundary. The production backend owns store/account/revision
    // validation, stopped-process guards, verified backups and targeted deletion.
    public sealed class ManagedProfileEntry
    {
        public string Id, DisplayName, ProgressSummary, ContextToken, RevisionToken;
    }
    public sealed class ProfileListResult
    {
        public string ScopeLabel, DeleteBlockedReason, RecoveryMessage;
        public ManagedProfileEntry[] Entries;
        public bool CanBackup, CanDelete, CanRestore, RecoveryRequired;
    }
    public sealed class ProfileBackupResult
    {
        public string ProfileId, BackupPath;
        public bool BackupVerified;
    }
    public sealed class ProfileDeleteResult
    {
        public string DeletedProfileId, BackupPath;
        public bool BackupVerified, OtherProfilesPreserved, PendingCloudSync;
    }
    public sealed class ProfileRecoveryResult
    {
        public bool Recovered, OtherProfilesPreserved;
        public string Message;
    }
    public sealed class ProfileRestorePreview
    {
        // ProfileId belongs to the source archive. Destination identity may differ.
        public string ProfileId, ProfileName, ContextLabel, ContextToken, RevisionToken;
        public string BackupPath, BackupSha256;
        public long BackupBytes;
        public bool SameProfileExists, CanRestore;
        public string BlockedReason;
    }
    public sealed class ProfileRestoreResult
    {
        public string ProfileId, BackupPath, RestoredProfileId;
        public bool OtherProfilesPreserved, PendingCloudSync;
    }
    public interface IProfileManagerBackend
    {
        Task<ProfileListResult> ListAsync();
        Task<ProfileRecoveryResult> RecoverAsync(IProgress<string> log);
        Task<ProfileBackupResult> BackupAsync(ManagedProfileEntry selected, IProgress<string> log);
        // Inspection is read-only. Restore must revalidate archive hash, destination
        // context/revision and conflicts under the backend's stopped-process locks.
        Task<ProfileRestorePreview> InspectBackupAsync(string path);
        Task<ProfileRestoreResult> RestoreAsync(ProfileRestorePreview verifiedPreview, IProgress<string> log);
        // This single operation MUST create and verify a backup before deletion.
        // There is deliberately no standalone Delete API on the UI boundary.
        Task<ProfileDeleteResult> BackupAndDeleteAsync(ManagedProfileEntry selected, IProgress<string> log);
    }

    public static class ProfileManagerUi
    {
        // Root integration supplies the proven production adapter. A missing
        // adapter is an explicit unavailable state, never an empty success stub.
        public static Func<string, IProfileManagerBackend> BackendFactory;
        // Validation-only hook. Root binds EnsureNoPending; it must not silently recover.
        public static Func<string, Task> BeforeGameLaunch;
        public static void Open(IWin32Window owner, string selectedGameFolder)
        {
            try
            {
                var factory = BackendFactory;
                if (factory == null) throw new InvalidOperationException(
                    "프로필 백엔드가 아직 연결되지 않았습니다. 삭제 기능은 사용할 수 없습니다.\r\n" +
                    "The profile backend is not configured. Deletion is unavailable.");
                IProfileManagerBackend backend = factory(selectedGameFolder);
                if (backend == null) throw new InvalidOperationException("프로필 백엔드를 열지 못했습니다. / The profile backend could not be opened.");
                using (var form = new ProfileManagerForm(backend)) form.ShowDialog(owner);
            }
            catch (Exception error)
            {
                MessageBox.Show(owner, error.Message, "프로필 관리자 중단 / Profile manager unavailable", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }
    }

    public sealed class ProfileManagerForm : Form
    {
        readonly IProfileManagerBackend backend;
        readonly Func<string, DialogResult> testConfirmation;
        readonly DataGridView profiles = new DataGridView();
        readonly TextBox scope = new TextBox(), selected = new TextBox(), output = new TextBox();
        readonly Button refresh = new Button(), backup = new Button(), remove = new Button(), restore = new Button(), recover = new Button(), close = new Button();
        readonly Label status = new Label();
        readonly ToolTip tips = new ToolTip();
        ProfileListResult snapshot;
        bool busy;

        public ProfileManagerForm(IProfileManagerBackend backend) : this(backend, null) { }
        // Fixture-only seam: the production Open path never supplies a callback.
        internal ProfileManagerForm(IProfileManagerBackend backend, Func<string, DialogResult> fixtureConfirmation)
        {
            if (backend == null) throw new ArgumentNullException("backend");
            this.backend = backend; testConfirmation = fixtureConfirmation;
            Text = "Crimson Skies 프로필 관리 / Profile Manager — 0.12.2";
            Width = 1040; Height = 760; MinimumSize = new Size(900, 650);
            StartPosition = FormStartPosition.CenterParent;
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 7, Padding = new Padding(12) };
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 58));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 46));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 62));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 88));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 38));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
            layout.Controls.Add(new Label { Dock = DockStyle.Fill, Text =
                "선택 프로필을 백업하거나 백업 ZIP을 검사해 복원합니다. 기존 프로필은 덮어쓰지 않습니다.\r\n" +
                "Back up selected profiles or inspect a backup ZIP to restore. Existing profiles are never overwritten." }, 0, 0);
            scope.ReadOnly = true; scope.Multiline = true; scope.Dock = DockStyle.Fill;
            scope.AccessibleName = "저장소 / Save store"; scope.Text = "목록을 읽기 전입니다. / Profile list has not been read.";
            layout.Controls.Add(scope, 0, 1);
            profiles.Dock = DockStyle.Fill; profiles.ReadOnly = true; profiles.MultiSelect = false;
            profiles.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
            profiles.AllowUserToAddRows = false; profiles.AllowUserToDeleteRows = false;
            profiles.AllowUserToResizeRows = false; profiles.RowHeadersVisible = false;
            profiles.AutoGenerateColumns = false; profiles.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
            profiles.EditMode = DataGridViewEditMode.EditProgrammatically;
            profiles.AccessibleName = "프로필 목록 / Profiles";
            profiles.Columns.Add(new DataGridViewTextBoxColumn { Name = "name", HeaderText = "프로필 / Profile", FillWeight = 27, MinimumWidth = 150, SortMode = DataGridViewColumnSortMode.NotSortable });
            profiles.Columns.Add(new DataGridViewTextBoxColumn { Name = "progress", HeaderText = "저장 크기 / Save size", FillWeight = 43, MinimumWidth = 220, SortMode = DataGridViewColumnSortMode.NotSortable });
            profiles.Columns.Add(new DataGridViewTextBoxColumn { Name = "identity", HeaderText = "저장 식별자 / Save identity", FillWeight = 30, MinimumWidth = 210, SortMode = DataGridViewColumnSortMode.NotSortable });
            profiles.SelectionChanged += delegate { ShowSelection(); };
            // No double-click/selection/initial-load handler calls a mutation.
            layout.Controls.Add(profiles, 0, 2);
            selected.Dock = DockStyle.Fill; selected.Multiline = true; selected.ReadOnly = true; selected.ScrollBars = ScrollBars.Vertical;
            selected.AccessibleName = "선택한 프로필 / Selected profile"; layout.Controls.Add(selected, 0, 3);
            var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, WrapContents = true };
            refresh.Text = "새로 고침 / Refresh"; refresh.Width = 170;
            backup.Text = "선택 프로필 백업 / Back up selected"; backup.Width = 265;
            remove.Text = "백업 후 삭제 / Backup + delete"; remove.Width = 285; remove.ForeColor = Color.DarkRed;
            restore.Text = "백업 ZIP 복원 / Restore ZIP"; restore.Width = 255;
            recover.Text = "중단 작업 복구 / Recover"; recover.Width = 230;
            close.Text = "닫기 / Close"; close.Width = 140;
            foreach (Button button in new[] { refresh, backup, remove, restore, recover, close }) { button.Height = 34; button.UseMnemonic = false; buttons.Controls.Add(button); }
            layout.Controls.Add(buttons, 0, 4);
            output.Dock = DockStyle.Fill; output.Multiline = true; output.ReadOnly = true; output.ScrollBars = ScrollBars.Both; output.WordWrap = false;
            output.AccessibleName = "작업 기록 / Operation log"; layout.Controls.Add(output, 0, 5);
            status.Dock = DockStyle.Fill; status.TextAlign = ContentAlignment.MiddleLeft;
            layout.Controls.Add(status, 0, 6); Controls.Add(layout);
            refresh.Click += async delegate { await RefreshProfilesAsync(); };
            backup.Click += async delegate { await RunSelectedAsync(false); };
            remove.Click += async delegate { await RunSelectedAsync(true); };
            restore.Click += async delegate { await ChooseRestoreBackupAsync(); };
            recover.Click += async delegate { await RecoverPendingAsync(); };
            close.Click += delegate { if (!busy) Close(); };
            Shown += async delegate { await RefreshProfilesAsync(); };
            FormClosing += delegate(object sender, FormClosingEventArgs args) { if (busy) args.Cancel = true; };
            UpdateActions(); ShowSelection();
        }

        static string Plain(string value, int maximum)
        {
            if (String.IsNullOrEmpty(value)) return "";
            var result = new StringBuilder();
            foreach (char c in value)
            {
                if (result.Length >= maximum) break;
                result.Append(Char.IsControl(c) || CharUnicodeInfo.GetUnicodeCategory(c) == UnicodeCategory.Format ? ' ' : c);
            }
            return result.ToString();
        }
        static ManagedProfileEntry Copy(ManagedProfileEntry entry)
        {
            return new ManagedProfileEntry { Id = entry.Id, DisplayName = entry.DisplayName, ProgressSummary = entry.ProgressSummary, ContextToken = entry.ContextToken, RevisionToken = entry.RevisionToken };
        }
        static ProfileRestorePreview Copy(ProfileRestorePreview entry)
        {
            return new ProfileRestorePreview { ProfileId = entry.ProfileId, ProfileName = entry.ProfileName,
                ContextLabel = entry.ContextLabel, ContextToken = entry.ContextToken, RevisionToken = entry.RevisionToken,
                BackupPath = entry.BackupPath, BackupSha256 = entry.BackupSha256, BackupBytes = entry.BackupBytes,
                SameProfileExists = entry.SameProfileExists, CanRestore = entry.CanRestore, BlockedReason = entry.BlockedReason };
        }
        static string NameOf(ManagedProfileEntry entry)
        {
            string name = Plain(entry.DisplayName, 256).Trim();
            return name.Length == 0 ? "이름 미확인 / Name unavailable" : name;
        }
        static string ProgressOf(ManagedProfileEntry entry)
        {
            string progress = Plain(entry.ProgressSummary, 512).Trim();
            return progress.Length == 0 ? "저장 크기 정보 없음 / Save size unavailable" : progress;
        }
        ManagedProfileEntry Selection()
        {
            return profiles.SelectedRows.Count == 1 ? profiles.SelectedRows[0].Tag as ManagedProfileEntry : null;
        }
        void ShowSelection()
        {
            var entry = Selection();
            selected.Text = snapshot != null && snapshot.RecoveryRequired ? "중단 작업 복구 필요 / Interrupted operation needs recovery\r\n" + RecoveryReason() : entry == null ? "프로필을 선택하세요. / Select a profile." :
                NameOf(entry) + "\r\n" + ProgressOf(entry) + "\r\nID: " + Plain(entry.Id, 512);
            UpdateActions();
        }
        void UpdateActions()
        {
            var entry = Selection();
            refresh.Enabled = !busy; profiles.Enabled = !busy; close.Enabled = !busy;
            backup.Enabled = !busy && snapshot != null && snapshot.CanBackup && !snapshot.RecoveryRequired && entry != null;
            remove.Enabled = !busy && snapshot != null && snapshot.CanBackup && snapshot.CanDelete && !snapshot.RecoveryRequired && entry != null;
            restore.Enabled = !busy && snapshot != null && snapshot.CanRestore && !snapshot.RecoveryRequired;
            recover.Enabled = !busy && snapshot != null && snapshot.RecoveryRequired;
            tips.SetToolTip(restore, "백업 ZIP을 먼저 검사하고 별도 확인 후 복원합니다. 같은 프로필이 있으면 중단합니다. / Inspect a backup ZIP, then confirm restoration. Existing profiles block restoration.");
            tips.SetToolTip(recover, "이 도구가 중단한 프로필 작업만 복구합니다. / Recover only an interrupted profile operation owned by this manager.");
            string reason = snapshot == null || String.IsNullOrWhiteSpace(snapshot.DeleteBlockedReason) ?
                "선택한 프로필과 검증된 삭제 경로가 필요합니다. / A selected profile and a proven deletion route are required." : Plain(snapshot.DeleteBlockedReason, 1024);
            tips.SetToolTip(remove, reason);
            status.Text = busy ? "작업 중입니다. 완료될 때까지 창을 닫을 수 없습니다. / Working; closing is blocked until completion." :
                snapshot != null && snapshot.RecoveryRequired ? "복구 필요 / Recovery required: " + RecoveryReason() :
                snapshot != null && !snapshot.CanDelete ? "삭제 비활성 / Deletion disabled: " + reason : "선택만으로 저장 데이터가 변경되지는 않습니다. / Selecting a row does not change save data.";
        }
        string RecoveryReason()
        {
            string message = Plain(snapshot == null ? null : snapshot.RecoveryMessage, 2048).Trim();
            return message.Length == 0 ? "복구 버튼을 눌러 중단 작업을 먼저 복구하세요. / Use Recover before other profile operations or game launch." : message;
        }
        void SetBusy(bool value) { busy = value; UpdateActions(); }
        void AppendLog(string message)
        {
            if (IsDisposed) return;
            if (InvokeRequired)
            {
                try { BeginInvoke((Action)(delegate { AppendLog(message); })); }
                catch (InvalidOperationException) { }
                return;
            }
            if (output.TextLength > 900000) output.Text = output.Text.Substring(output.TextLength - 450000);
            output.AppendText((message ?? "").Substring(0, Math.Min((message ?? "").Length, 8192)) + Environment.NewLine);
        }
        void ClearList()
        {
            snapshot = null; profiles.Rows.Clear(); profiles.ClearSelection(); ShowSelection();
        }
        async Task ReloadCoreAsync(string reselectId)
        {
            ClearList();
            ProfileListResult result = await backend.ListAsync();
            if (result == null || !result.RecoveryRequired && result.Entries == null || result.Entries != null && result.Entries.Length > 1024) throw new InvalidDataException("프로필 목록을 확인하지 못했습니다. / Invalid profile list result.");
            var ids = new System.Collections.Generic.HashSet<string>(StringComparer.Ordinal);
            ManagedProfileEntry[] entries = result.RecoveryRequired ? new ManagedProfileEntry[0] : result.Entries;
            foreach (ManagedProfileEntry source in entries)
            {
                if (source == null || String.IsNullOrEmpty(source.Id) || source.Id.Length > 512 ||
                    String.IsNullOrEmpty(source.ContextToken) || source.ContextToken.Length > 8192 ||
                    String.IsNullOrEmpty(source.RevisionToken) || source.RevisionToken.Length > 8192 || !ids.Add(source.Id))
                    throw new InvalidDataException("프로필의 저장소/버전 식별자가 유효하지 않습니다. / Invalid or duplicate profile/store/revision identity.");
                ManagedProfileEntry entry = Copy(source);
                int i = profiles.Rows.Add(NameOf(entry), ProgressOf(entry), Plain(entry.Id, 512)); profiles.Rows[i].Tag = entry;
            }
            snapshot = new ProfileListResult { ScopeLabel = result.ScopeLabel, CanBackup = result.CanBackup, CanDelete = result.CanDelete, CanRestore = result.CanRestore, DeleteBlockedReason = result.DeleteBlockedReason, RecoveryRequired = result.RecoveryRequired, RecoveryMessage = result.RecoveryMessage, Entries = entries };
            scope.Text = Plain(result.ScopeLabel, 2048); profiles.ClearSelection();
            if (reselectId != null) foreach (DataGridViewRow row in profiles.Rows) if (String.Equals(((ManagedProfileEntry)row.Tag).Id, reselectId, StringComparison.Ordinal)) { row.Selected = true; break; }
            AppendLog(result.RecoveryRequired ? "복구 필요 / Recovery required: " + RecoveryReason() : "목록 새로 고침 / Refreshed: " + profiles.Rows.Count + "개 프로필 / profiles."); ShowSelection();
        }
        internal async Task RefreshProfilesAsync()
        {
            if (busy) return; SetBusy(true);
            try { await ReloadCoreAsync(null); }
            catch (Exception error) { ClearList(); scope.Text = "저장소 읽기 실패 / Store read failed"; AppendLog("중단 / Stopped: " + error.Message); }
            finally { SetBusy(false); }
        }
        internal async Task RecoverPendingAsync()
        {
            if (busy || snapshot == null || !snapshot.RecoveryRequired) return;
            SetBusy(true);
            try
            {
                try
                {
                    ProfileRecoveryResult result = await backend.RecoverAsync(new Progress<string>(AppendLog));
                    if (result == null || !result.Recovered || !result.OtherProfilesPreserved)
                        throw new InvalidDataException("중단 작업 복구와 다른 프로필의 보존을 확인하지 못했습니다. / Recovery and preservation of other profiles were not confirmed." + (result == null ? "" : " " + Plain(result.Message, 2048)));
                    AppendLog("중단 작업 복구 확인 / Interrupted operation recovered: " + Plain(result.Message, 2048));
                }
                catch (Exception error) { AppendLog("중단 / Stopped: " + error.Message); }
                try { await ReloadCoreAsync(null); }
                catch (Exception error) { ClearList(); AppendLog("복구 후 목록 확인 실패 / Could not refresh after recovery: " + error.Message); }
            }
            finally { SetBusy(false); }
        }
        async Task ChooseRestoreBackupAsync()
        {
            if (busy || snapshot == null || snapshot.RecoveryRequired || !snapshot.CanRestore) return;
            // File selection has no store side effects; cancellation calls no backend.
            using (var dialog = new OpenFileDialog())
            {
                dialog.Title = "복원할 프로필 백업 ZIP 선택 / Select a profile backup ZIP";
                dialog.Filter = "프로필 백업 ZIP / Profile backup ZIP (*.zip)|*.zip";
                dialog.CheckFileExists = true; dialog.CheckPathExists = true;
                dialog.Multiselect = false; dialog.RestoreDirectory = true;
                if (dialog.ShowDialog(this) == DialogResult.OK) await InspectAndRestoreAsync(dialog.FileName);
            }
        }
        static bool Sha256Text(string value)
        {
            if (value == null || value.Length != 64) return false;
            foreach (char c in value) if (!(c >= '0' && c <= '9' || c >= 'a' && c <= 'f' || c >= 'A' && c <= 'F')) return false;
            return true;
        }
        static void RequireRestorePreview(ProfileRestorePreview preview)
        {
            if (preview == null || String.IsNullOrWhiteSpace(preview.ProfileId) || preview.ProfileId.Length > 512 ||
                String.IsNullOrWhiteSpace(preview.ContextToken) || preview.ContextToken.Length > 8192 ||
                String.IsNullOrWhiteSpace(preview.RevisionToken) || preview.RevisionToken.Length > 8192 ||
                String.IsNullOrWhiteSpace(preview.BackupPath) || preview.BackupPath.Length > 32768 ||
                preview.BackupBytes <= 0 || !Sha256Text(preview.BackupSha256))
                throw new InvalidDataException("백업 식별자, 해시, 크기 또는 대상 저장소 정보가 유효하지 않습니다. / Invalid backup identity, hash, size or destination context.");
        }
        public static string RestoreConfirmationText(ProfileRestorePreview preview)
        {
            if (preview == null) throw new ArgumentNullException("preview");
            string name = Plain(preview.ProfileName, 256).Trim();
            if (name.Length == 0) name = "이름 미확인 / Name unavailable";
            return "검사한 백업 ZIP의 프로필을 현재 저장소에 복원할까요?\r\n" +
                "Restore this inspected backup profile into the current save store?\r\n\r\n" +
                "프로필 / Profile: " + name + "\r\n원본 프로필 ID / Source profile ID: " + Plain(preview.ProfileId, 512) +
                "\r\n대상 저장소 / Destination: " + Plain(preview.ContextLabel, 2048) +
                "\r\n백업 ZIP / Backup ZIP: " + Plain(preview.BackupPath, 4096) +
                "\r\n파일 크기 / File bytes: " + preview.BackupBytes.ToString(CultureInfo.InvariantCulture) +
                "\r\nSHA-256: " + Plain(preview.BackupSha256, 64) +
                "\r\n\r\n같은 프로필이 있으면 중단하며 덮어쓰지 않습니다. 다른 프로필은 유지합니다.\r\n" +
                "An existing profile blocks restoration. No overwrite is offered. Other profiles are preserved.\r\n\r\n" +
                "복원 직전에 파일과 저장소를 다시 검사합니다. 계속할까요?\r\n" +
                "The archive and destination are checked again immediately before restoration. Continue?";
        }
        bool ConfirmRestore(ProfileRestorePreview preview)
        {
            string text = RestoreConfirmationText(preview);
            DialogResult answer = testConfirmation == null ? MessageBox.Show(this, text,
                "백업 ZIP 복원 확인 / Confirm backup ZIP restoration", MessageBoxButtons.YesNo,
                MessageBoxIcon.Question, MessageBoxDefaultButton.Button2) : testConfirmation(text);
            return answer == DialogResult.Yes;
        }
        internal async Task InspectAndRestoreAsync(string path)
        {
            if (busy || snapshot == null || snapshot.RecoveryRequired || !snapshot.CanRestore || String.IsNullOrWhiteSpace(path)) return;
            SetBusy(true);
            string reselectId = null;
            try
            {
                try
                {
                    // Only the explicit restore action reaches inspection. Keep a
                    // private DTO copy so list/inspection providers cannot replace
                    // the identity the user confirmed while an await is pending.
                    ProfileRestorePreview inspected = await backend.InspectBackupAsync(path);
                    RequireRestorePreview(inspected);
                    ProfileRestorePreview preview = Copy(inspected);
                    bool listed = false;
                    foreach (ManagedProfileEntry entry in snapshot.Entries)
                        if (String.Equals(entry.Id, preview.ProfileId, StringComparison.Ordinal)) { listed = true; break; }
                    if (preview.SameProfileExists || listed || !preview.CanRestore)
                    {
                        string reason = Plain(preview.BlockedReason, 2048).Trim();
                        if (preview.SameProfileExists || listed)
                            reason = "같은 프로필이 이미 있습니다. 덮어쓰지 않고 중단했습니다. / The same profile already exists. Restoration was refused without overwriting." + (reason.Length == 0 ? "" : " " + reason);
                        if (reason.Length == 0) reason = "이 백업은 현재 저장소에 복원할 수 없습니다. / This backup cannot be restored into the current store.";
                        AppendLog("복원 중단 / Restore refused: " + reason);
                    }
                    else if (!ConfirmRestore(preview))
                        AppendLog("복원 취소 / Restoration cancelled; save data was not changed.");
                    else
                    {
                        string confirmedId = preview.ProfileId;
                        ProfileRestoreResult result = await backend.RestoreAsync(Copy(preview), new Progress<string>(AppendLog));
                        if (result == null || !String.Equals(result.ProfileId, confirmedId, StringComparison.Ordinal) ||
                            String.IsNullOrWhiteSpace(result.BackupPath) || !result.OtherProfilesPreserved)
                            throw new InvalidDataException("선택 백업의 복원과 다른 프로필 보존을 확인하지 못했습니다. / Restoration of the selected backup and preservation of other profiles were not confirmed.");
                        if (result.RestoredProfileId != null && result.RestoredProfileId.Length > 512)
                            throw new InvalidDataException("복원된 프로필 식별자가 유효하지 않습니다. / Invalid restored profile identity.");
                        reselectId = String.IsNullOrWhiteSpace(result.RestoredProfileId) ? confirmedId : result.RestoredProfileId;
                        AppendLog("선택 백업 프로필 복원 확인 / Confirmed selected backup restoration: " + Plain(preview.ProfileName, 256));
                        AppendLog("검증된 복원용 백업 사본 / Verified restoration backup copy: " + result.BackupPath);
                        if (result.PendingCloudSync) AppendLog("클라우드 동기화 대기: 다음 게임/저장 공급자 실행 때 동기화됩니다. / Cloud synchronization is pending the next game/save-provider launch.");
                    }
                }
                catch (Exception error) { AppendLog("복원 중단 / Restoration stopped: " + error.Message); }
                try { await ReloadCoreAsync(reselectId); }
                catch (Exception error) { ClearList(); AppendLog("복원 후 목록 확인 실패 / Could not refresh after restoration: " + error.Message); }
            }
            finally { SetBusy(false); }
        }
        public static string DeleteConfirmationText(ManagedProfileEntry entry)
        {
            if (entry == null) throw new ArgumentNullException("entry");
            return "선택한 프로필과 그 진행 기록을 현재 저장소에서 삭제할까요?\r\n" +
                "Remove this selected profile and its game progress from the active save store?\r\n\r\n" +
                "프로필 / Profile: " + NameOf(entry) + "\r\n저장 크기 / Save size: " + ProgressOf(entry) + "\r\nID: " + Plain(entry.Id, 512) +
                "\r\n\r\n먼저 백업을 만들고 검증합니다. 다른 프로필은 유지합니다.\r\n" +
                "A backup must be created and verified first. Other profiles are preserved.\r\n\r\n" +
                "실행 중에는 창을 닫을 수 없습니다. 계속할까요? / Continue?";
        }
        bool ConfirmDelete(ManagedProfileEntry entry)
        {
            string text = "저장소 / Store: " + Plain(snapshot == null ? null : snapshot.ScopeLabel, 1024) + "\r\n\r\n" + DeleteConfirmationText(entry);
            DialogResult answer = testConfirmation == null ? MessageBox.Show(this, text,
                "프로필 및 진행 삭제 확인 / Confirm profile + progress deletion", MessageBoxButtons.YesNo, MessageBoxIcon.Warning, MessageBoxDefaultButton.Button2) : testConfirmation(text);
            return answer == DialogResult.Yes;
        }
        static void RequireBackup(string actualId, string path, bool verified, ManagedProfileEntry selected)
        {
            if (!verified || !String.Equals(actualId, selected.Id, StringComparison.Ordinal) || String.IsNullOrWhiteSpace(path))
                throw new InvalidDataException("선택한 프로필의 검증된 백업을 확인하지 못했습니다. / A verified backup for the selected profile was not confirmed.");
        }
        internal async Task RunSelectedAsync(bool deleting)
        {
            if (busy || snapshot == null) return;
            ManagedProfileEntry current = Selection(); if (current == null) return;
            if (snapshot.RecoveryRequired || !snapshot.CanBackup || deleting && !snapshot.CanDelete) return;
            ManagedProfileEntry entry = Copy(current);
            if (deleting && !ConfirmDelete(entry)) return;
            SetBusy(true);
            try
            {
                try
                {
                    var log = new Progress<string>(AppendLog);
                    if (deleting)
                    {
                        ProfileDeleteResult result = await backend.BackupAndDeleteAsync(entry, log);
                        if (result == null) throw new InvalidDataException("삭제 결과를 확인하지 못했습니다. / No deletion receipt was returned.");
                        RequireBackup(result.DeletedProfileId, result.BackupPath, result.BackupVerified, entry);
                        if (!result.OtherProfilesPreserved) throw new InvalidDataException("다른 프로필의 보존 여부를 확인하지 못했습니다. / Preservation of other profiles was not confirmed.");
                        AppendLog("선택한 로컬 프로필 삭제 확인 / Confirmed selected local profile deletion: " + NameOf(entry));
                        AppendLog("검증된 백업 / Verified backup: " + result.BackupPath);
                        if (result.PendingCloudSync) AppendLog("클라우드 동기화 대기: 다음 게임/저장 공급자 실행 때 동기화됩니다. / Cloud synchronization is pending the next game/save-provider launch.");
                    }
                    else
                    {
                        ProfileBackupResult result = await backend.BackupAsync(entry, log);
                        if (result == null) throw new InvalidDataException("백업 결과를 확인하지 못했습니다. / No backup receipt was returned.");
                        RequireBackup(result.ProfileId, result.BackupPath, result.BackupVerified, entry);
                        AppendLog("백업 검증 완료 / Backup verified: " + result.BackupPath);
                    }
                }
                catch (Exception error) { AppendLog("중단 / Stopped: " + error.Message); }
                try { await ReloadCoreAsync(deleting ? null : entry.Id); }
                catch (Exception error) { ClearList(); AppendLog("목록 재확인 실패 / Could not refresh the list: " + error.Message); }
            }
            finally { SetBusy(false); }
        }
    }
}
