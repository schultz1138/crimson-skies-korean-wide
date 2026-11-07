using System;
using System.IO;
using CrimsonSkiesMultilingual;
static class ProfilePathProbe {
 static int Main(string[] args) {
  string qa=Path.GetFullPath(args[0]).TrimEnd('\\')+"\\",target=Path.GetFullPath(args[1]);
  if(!target.StartsWith(qa,StringComparison.OrdinalIgnoreCase))throw new Exception("QA-only boundary");
  try{ProfileStore.Scan(target);Console.Error.WriteLine("Unexpected path acceptance");return 1;}
  catch(IOException e){if(!e.Message.Contains("reparse"))throw;Console.WriteLine("PASS reparse refused");return 0;}
 }
}
