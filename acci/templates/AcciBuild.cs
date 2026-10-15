// Copy to Assets/Editor/AcciBuild.cs. Requires an owner-installed/licensed Editor.
// Produces an Xcode project only; does not sign, upload, or publish.
using System;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;

public static class AcciBuild
{
    public static void BuildIOS()
    {
        var output = Environment.GetEnvironmentVariable("ACCI_UNITY_EXPORT");
        if (string.IsNullOrWhiteSpace(output))
            throw new InvalidOperationException("Set ACCI_UNITY_EXPORT to a disposable output directory.");
        var scenes = EditorBuildSettings.scenes.Where(s => s.enabled).Select(s => s.path).ToArray();
        if (scenes.Length == 0)
            throw new InvalidOperationException("No enabled scenes. Configure build settings first.");
        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions {
            scenes = scenes,
            locationPathName = output,
            target = BuildTarget.iOS,
            options = BuildOptions.None
        });
        if (report.summary.result != BuildResult.Succeeded)
            throw new InvalidOperationException("iOS Xcode export failed: " + report.summary.result);
    }
}