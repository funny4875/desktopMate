using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UniGLTF.Extensions.VRMC_vrm;
using UniVRM10;

public static class Vrm0ToVrm1BatchConverter
{
    private const string DefaultInputRelative = "../charactor.vrm";
    private const string DefaultOutputRelative = "../charactor_vrm1.vrm";

    [MenuItem("Tools/VRM/Convert ../charactor.vrm to VRM1")]
    public static void ConvertDefaultFromMenu()
    {
        Convert(DefaultInputRelative, DefaultOutputRelative);
    }

    public static void ConvertDefault()
    {
        try
        {
            Convert(DefaultInputRelative, DefaultOutputRelative);
            EditorApplication.Exit(0);
        }
        catch (Exception ex)
        {
            Debug.LogException(ex);
            EditorApplication.Exit(1);
        }
    }

    private static void Convert(string inputRelative, string outputRelative)
    {
        var projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
        var inputPath = Path.GetFullPath(Path.Combine(projectRoot, inputRelative));
        var outputPath = Path.GetFullPath(Path.Combine(projectRoot, outputRelative));

        if (!File.Exists(inputPath))
        {
            throw new FileNotFoundException("Input VRM0 file was not found.", inputPath);
        }

        var inputBytes = File.ReadAllBytes(inputPath);
        var meta = CreateRestrictiveMeta(inputPath);

        var vrm1Bytes = Migrator.Migrate(inputBytes, meta, gltf =>
        {
            gltf.asset.generator = "UniVRM 0.131.1 VRM0 to VRM1 batch converter";
        });

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
        File.WriteAllBytes(outputPath, vrm1Bytes);
        Debug.Log($"Converted VRM0 to VRM1: {outputPath} ({vrm1Bytes.Length} bytes)");
    }

    private static VRM10ObjectMeta CreateRestrictiveMeta(string inputPath)
    {
        return new VRM10ObjectMeta
        {
            Name = Path.GetFileNameWithoutExtension(inputPath),
            Version = "vrm1-converted",
            Authors = new List<string> { "Converted with UniVRM" },
            CopyrightInformation = "",
            ContactInformation = "",
            References = new List<string>(),
            ThirdPartyLicenses = "",
            AvatarPermission = AvatarPermissionType.onlyAuthor,
            ViolentUsage = false,
            SexualUsage = false,
            CommercialUsage = CommercialUsageType.personalNonProfit,
            PoliticalOrReligiousUsage = false,
            AntisocialOrHateUsage = false,
            CreditNotation = CreditNotationType.required,
            Redistribution = false,
            Modification = ModificationType.prohibited,
            OtherLicenseUrl = "",
        };
    }
}
