using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace JTrading.NewsManager.Configuration;

public static class ConfigLoader
{
    public static AppConfig LoadConfig(string configPath = "config/config.json", ILogger? logger = null)
    {
        var fullConfigPath = ResolvePath(configPath);

        if (!File.Exists(fullConfigPath))
        {
            var errorMsg = $"Config file not found: {fullConfigPath}";
            logger?.LogError(errorMsg);
            throw new FileNotFoundException(errorMsg, fullConfigPath);
        }

        try
        {
            var jsonContent = File.ReadAllText(fullConfigPath);
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };
            var config = JsonSerializer.Deserialize<AppConfig>(jsonContent, options);

            if (config == null)
            {
                throw new InvalidOperationException("Failed to deserialize configuration file");
            }

            logger?.LogInformation($"Configuration loaded from {fullConfigPath}");
            return config;
        }
        catch (JsonException ex)
        {
            var errorMsg = $"Invalid JSON in config file: {ex.Message}";
            logger?.LogError(ex, errorMsg);
            throw new InvalidOperationException(errorMsg, ex);
        }
    }

    private static string ResolvePath(string relativePath)
    {
        if (Path.IsPathRooted(relativePath))
        {
            return relativePath;
        }

        // Get project root (assuming config is at project root level)
        var currentDir = Directory.GetCurrentDirectory();
        var projectRoot = currentDir;

        // Try to find project root by looking for config directory
        var dir = new DirectoryInfo(currentDir);
        while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "config")))
        {
            dir = dir.Parent;
        }

        if (dir != null)
        {
            projectRoot = dir.FullName;
        }

        return Path.Combine(projectRoot, relativePath);
    }
}

