// SPDX-License-Identifier: MIT
using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;

namespace CrimsonSkiesMultilingual
{
    public static class MenuPolicy
    {
        public const string FoundationSha256 = "200b609e7b279c25814fb42ed1dd1cdcd6f3203b670dc3b05749a6ee26686265";
        static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);

        public static bool IsPackId(string id)
        {
            return id != null && id.Length <= 35 && Regex.IsMatch(id,
                "^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8}){0,3}$", RegexOptions.CultureInvariant);
        }

        public static byte[] BuildMenu(byte[] baseMenu, CatalogDefinition catalog, string packId)
        {
            if (catalog == null) throw new ArgumentNullException("catalog");
            return Build(baseMenu, packId);
        }

        public static byte[] Build(byte[] baseMenu, string packId)
        {
            if (!IsPackId(packId)) throw new ArgumentException("Invalid subtitle pack ID.");
            string digest;
            using (var hash = SHA256.Create()) digest = BitConverter.ToString(hash.ComputeHash(baseMenu)).Replace("-", "").ToLowerInvariant();
            if (digest != FoundationSha256) throw new ArgumentException("The verified 0.11 launcher menu is required.");
            var serializer = new JavaScriptSerializer { MaxJsonLength = 262144 };
            var root = serializer.DeserializeObject(Utf8.GetString(baseMenu)) as Dictionary<string, object>;
            if (root == null || !root.ContainsKey("Categories")) throw new ArgumentException("Invalid base launcher menu.");
            var categories = root["Categories"] as object[];
            if (categories == null) throw new ArgumentException("Invalid launcher categories.");
            int matches = 0;
            foreach (object categoryObject in categories)
            {
                var category = categoryObject as Dictionary<string, object>;
                if (category == null || !category.ContainsKey("Items")) throw new ArgumentException("Invalid launcher category.");
                var items = category["Items"] as object[];
                if (items == null) throw new ArgumentException("Invalid launcher items.");
                foreach (object itemObject in items)
                {
                    var item = itemObject as Dictionary<string, object>;
                    if (item == null) throw new ArgumentException("Invalid launcher item.");
                    object id;
                    if (!item.TryGetValue("Id", out id) || !String.Equals(id as string, "game-language", StringComparison.Ordinal)) continue;
                    matches++;
                    // The owned launcher is the pack selector. This existing item
                    // expresses its stable pack ID while routing the game's font,
                    // Unicode, Bink and UI assets through the Korean resource slot.
                    // OptionLabels is JsonIgnoreAlways in the original launcher.
                    item["Options"] = new object[] { packId };
                    item["ArgValues"] = new object[] { "-locale ko-KR" };
                    item["Default"] = packId;
                    item["LaunchOnly"] = true;
                    item["IsLaunchArgument"] = true;
                    // Suppress positional stock labels (option 0 => "System").
                    // Unknown dynamic providers retain these explicit Options.
                    item["DynamicOptions"] = "cs-subtitle-pack-v1";
                }
            }
            if (matches != 1) throw new ArgumentException("Expected exactly one game-language item.");
            return Utf8.GetBytes(serializer.Serialize(root) + "\n");
        }
    }

    public sealed class SelectionBefore
    {
        public bool HadKey;
        public string OriginalLine;
    }

    public sealed class SettingsPlan
    {
        public string Path;
        public byte[] BeforeBytes;
        public byte[] AfterBytes;
        public SelectionBefore OriginalGameLanguage;
        [ScriptIgnore]
        public bool Changed { get { return !LanguageSettings.Equal(BeforeBytes, AfterBytes); } }
    }

    public static class LanguageSettings
    {
        const int MaximumBytes = 65536;
        static readonly UTF8Encoding Utf8 = new UTF8Encoding(false, true);
        // Match StreamReader.ReadLine's CR/LF/CRLF boundaries and String.Trim's
        // Unicode whitespace, as used by the original launcher INI parser.
        static readonly Regex KeyLine = new Regex(
            @"(?:\A|(?<=[\r\n]))(?<line>[^\S\r\n]*game-language[^\S\r\n]*=[^\r\n]*)(?=[\r\n]|\z)",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        sealed class Parsed
        {
            public string Body;
            public bool Bom;
            public Match Match;
            public bool HasKey { get { return Match != null; } }
            public string Line { get { return HasKey ? Match.Groups["line"].Value : null; } }
            public string Value { get { return HasKey ? Line.Substring(Line.IndexOf('=') + 1).Trim() : null; } }
        }

        static byte[] Copy(byte[] bytes) { return bytes == null ? null : (byte[])bytes.Clone(); }
        public static bool Equal(byte[] first, byte[] second)
        {
            return first == null ? second == null : second != null && first.SequenceEqual(second);
        }
        static Parsed Parse(byte[] bytes)
        {
            if (bytes == null) return new Parsed { Body = null };
            if (bytes.Length > MaximumBytes) throw new ArgumentException("Settings exceed 64KiB.");
            string text = Utf8.GetString(bytes);
            if (text.IndexOf('\0') >= 0) throw new ArgumentException("Settings contain a NUL character.");
            bool bom = text.StartsWith("\ufeff", StringComparison.Ordinal);
            string body = bom ? text.Substring(1) : text;
            MatchCollection matches = KeyLine.Matches(body);
            if (matches.Count > 1) throw new ArgumentException("Duplicate game-language settings.");
            return new Parsed { Body = body, Bom = bom, Match = matches.Count == 1 ? matches[0] : null };
        }
        static byte[] Encode(Parsed parsed, string body)
        {
            byte[] result = Utf8.GetBytes((parsed.Bom ? "\ufeff" : "") + body);
            if (result.Length > MaximumBytes) throw new ArgumentException("Updated settings exceed 64KiB.");
            return result;
        }
        static string ReplaceLine(Parsed parsed, string line)
        {
            int at = parsed.Match.Groups["line"].Index;
            int length = parsed.Match.Groups["line"].Length;
            return parsed.Body.Substring(0, at) + line + parsed.Body.Substring(at + length);
        }
        static string RemoveLine(Parsed parsed)
        {
            int at = parsed.Match.Groups["line"].Index, length = parsed.Match.Groups["line"].Length;
            if (at + length < parsed.Body.Length && parsed.Body[at + length] == '\r') length++;
            if (at + length < parsed.Body.Length && parsed.Body[at + length] == '\n') length++;
            return parsed.Body.Remove(at, length);
        }
        static void ValidateBefore(SelectionBefore before)
        {
            if (before == null) throw new ArgumentNullException("before");
            if (!before.HadKey)
            {
                if (!String.IsNullOrEmpty(before.OriginalLine)) throw new ArgumentException("Invalid missing-key record.");
                return;
            }
            if (before.OriginalLine == null || before.OriginalLine.IndexOfAny(new[] { '\r', '\n', '\0', '\ufeff' }) >= 0)
                throw new ArgumentException("Invalid original language record.");
            Parsed parsed = Parse(Utf8.GetBytes(before.OriginalLine));
            if (!parsed.HasKey || parsed.Match.Index != 0 || parsed.Match.Length != parsed.Body.Length)
                throw new ArgumentException("Original language record is not one complete setting.");
        }
        static SettingsPlan Plan(byte[] before, byte[] after)
        {
            return new SettingsPlan { BeforeBytes = Copy(before), AfterBytes = Copy(after), OriginalGameLanguage = Capture(before) };
        }

        public static SelectionBefore Capture(byte[] raw)
        {
            Parsed parsed = Parse(raw);
            return new SelectionBefore { HadKey = parsed.HasKey, OriginalLine = parsed.Line };
        }

        public static SettingsPlan Prepare(byte[] raw, string id)
        {
            if (!MenuPolicy.IsPackId(id)) throw new ArgumentException("Invalid pack ID.");
            Parsed parsed = Parse(raw);
            // The managed menu's Default is this ID, so a missing file/key needs
            // no synthetic settings file that might hide original title defaults.
            if (!parsed.HasKey) return Plan(raw, raw);
            string line = parsed.Line;
            int equal = line.IndexOf('=');
            string value = line.Substring(equal + 1);
            int first = 0, last = value.Length;
            while (first < value.Length && Char.IsWhiteSpace(value[first])) first++;
            while (last > first && Char.IsWhiteSpace(value[last - 1])) last--;
            string changed = line.Substring(0, equal + 1) + value.Substring(0, first) + id + value.Substring(last);
            return Plan(raw, Encode(parsed, ReplaceLine(parsed, changed)));
        }

        public static SettingsPlan PrepareRestore(byte[] raw, SelectionBefore before, IEnumerable<string> ownedIds)
        {
            ValidateBefore(before);
            Parsed parsed = Parse(raw);
            var ids = new HashSet<string>(ownedIds ?? Enumerable.Empty<string>(), StringComparer.OrdinalIgnoreCase);
            if (!parsed.HasKey || !ids.Contains(parsed.Value)) return Plan(raw, raw);
            return Plan(raw, Encode(parsed, before.HadKey ? ReplaceLine(parsed, before.OriginalLine) : RemoveLine(parsed)));
        }

        public static byte[] RollbackBytes(byte[] current, SettingsPlan applied, string appliedId)
        {
            if (applied == null || !applied.Changed) return Copy(current);
            if (Equal(current, applied.AfterBytes)) return Copy(applied.BeforeBytes);
            Parsed after = Parse(applied.AfterBytes), now = Parse(current);
            if (appliedId != null && after.HasKey && !String.Equals(after.Value, appliedId, StringComparison.OrdinalIgnoreCase))
                throw new ArgumentException("Rollback selector does not match its settings plan.");
            ValidateBefore(applied.OriginalGameLanguage);
            if (now.Body == null) return null; // Preserve an external deletion.
            if (after.HasKey)
            {
                if (!now.HasKey || !String.Equals(now.Value, after.Value, StringComparison.OrdinalIgnoreCase)) return Copy(current);
                string body = applied.OriginalGameLanguage.HadKey
                    ? ReplaceLine(now, applied.OriginalGameLanguage.OriginalLine) : RemoveLine(now);
                return Encode(now, body);
            }
            // A restore may have removed our key. If it is still absent, restore
            // that one line while retaining concurrent changes to other settings.
            if (now.HasKey || !applied.OriginalGameLanguage.HadKey) return Copy(current);
            string ending = now.Body.Contains("\r\n") ? "\r\n" : now.Body.Contains("\n") ? "\n" : now.Body.Contains("\r") ? "\r" : "\r\n";
            bool endsLine = now.Body.EndsWith("\n", StringComparison.Ordinal) || now.Body.EndsWith("\r", StringComparison.Ordinal);
            string separator = now.Body.Length > 0 && !endsLine ? ending : "";
            return Encode(now, now.Body + separator + applied.OriginalGameLanguage.OriginalLine + ending);
        }
    }
}
