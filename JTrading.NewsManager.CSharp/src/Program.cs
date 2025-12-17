using System.CommandLine;
using Microsoft.Extensions.Logging;
using JTrading.NewsManager.Configuration;
using JTrading.NewsManager.Domain.Models;
using JTrading.NewsManager.Services;
using JTrading.NewsManager.Logging;

namespace JTrading.NewsManager;

class Program
{
    static async Task<int> Main(string[] args)
    {
        var configOption = new Option<string?>(
            "--config",
            getDefaultValue: () => "config/config.json",
            description: "Path to configuration file");

        var scrapeOnlyOption = new Option<bool>(
            "--scrape-only",
            description: "Only scrape data without exporting to CSV");

        var testOption = new Option<bool>(
            "--test",
            description: "Test mode: scrape only 1 month back and forward");

        var modeOption = new Option<string?>(
            "--mode",
            description: "Scraping mode (daily or range)")
            .FromAmong("daily", "range");

        var dateOption = new Option<string?>(
            "--date",
            description: "Target date for daily mode (YYYY-MM-DD, default: today)");

        var rootCommand = new RootCommand("Economic News Manager")
        {
            configOption,
            scrapeOnlyOption,
            testOption,
            modeOption,
            dateOption
        };

        rootCommand.SetHandler(async (configPath, scrapeOnly, test, mode, date) =>
        {
            try
            {
                // Load configuration
                var config = ConfigLoader.LoadConfig(configPath ?? "config/config.json");

                // Setup logging
                var loggerFactory = SetupLogging(config);
                var logger = loggerFactory.CreateLogger<Program>();

                logger.LogInformation("Starting Economic News Manager Pipeline");

                // Determine scraping mode
                var investingConfig = config.InvestingCom ?? new InvestingComConfig();
                var scrapingMode = mode ?? investingConfig.DefaultMode;

                // Parse target date for daily mode
                DateTime? targetDate = null;
                if (scrapingMode == "daily")
                {
                    if (!string.IsNullOrEmpty(date))
                    {
                        if (DateTime.TryParseExact(date, "yyyy-MM-dd", null, System.Globalization.DateTimeStyles.None, out var parsedDate))
                        {
                            targetDate = parsedDate;
                        }
                        else
                        {
                            logger.LogError("Invalid date format: {Date}. Use YYYY-MM-DD format.", date);
                            Environment.Exit(1);
                            return;
                        }
                    }
                    else
                    {
                        targetDate = DateTime.Now;
                    }
                    logger.LogInformation("Daily mode: targeting date {Date}", targetDate.Value.Date);
                }
                else
                {
                    logger.LogInformation("Range mode: using config date range");
                }

                // Test mode adjustment
                if (test)
                {
                    if (config.InvestingCom != null)
                    {
                        config.InvestingCom.MonthsBack = 1;
                        config.InvestingCom.MonthsForward = 1;
                    }
                    logger.LogInformation("Test mode enabled: fetching 1 month back and forward");
                }

                // Run pipeline
                var pipelineRunner = new PipelineRunner();
                var success = await pipelineRunner.RunPipelineAsync(config, scrapingMode, targetDate, scrapeOnly, loggerFactory);

                if (success)
                {
                    logger.LogInformation("Economic News Manager completed successfully");
                    Environment.Exit(0);
                }
                else
                {
                    logger.LogError("Economic News Manager failed");
                    Environment.Exit(1);
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error: {ex.Message}");
                Environment.Exit(1);
            }
        }, configOption, scrapeOnlyOption, testOption, modeOption, dateOption);

        return await rootCommand.InvokeAsync(args);
    }

    static ILoggerFactory SetupLogging(AppConfig config)
    {
        var logConfig = config.Logging ?? new LoggingConfig();

        // Resolve log file path
        var logFile = logConfig.File;
        if (!Path.IsPathRooted(logFile))
        {
            var currentDir = Directory.GetCurrentDirectory();
            var dir = new DirectoryInfo(currentDir);
            while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "config")))
            {
                dir = dir.Parent;
            }
            if (dir != null)
            {
                logFile = Path.Combine(dir.FullName, logFile);
            }
            else
            {
                logFile = Path.Combine(currentDir, logFile);
            }
        }

        // Ensure log directory exists
        var logDir = Path.GetDirectoryName(logFile);
        if (!string.IsNullOrEmpty(logDir) && !Directory.Exists(logDir))
        {
            Directory.CreateDirectory(logDir);
        }

        // Parse log level
        var logLevel = logConfig.Level.ToUpper() switch
        {
            "DEBUG" => LogLevel.Debug,
            "INFO" => LogLevel.Information,
            "WARNING" => LogLevel.Warning,
            "WARN" => LogLevel.Warning,
            "ERROR" => LogLevel.Error,
            "CRITICAL" => LogLevel.Critical,
            _ => LogLevel.Information
        };

        // Create logger factory
        var loggerFactory = LoggerFactory.Create(builder =>
        {
            builder
                .SetMinimumLevel(logLevel)
                .AddConsole()
                .AddProvider(new FileLoggerProvider(logFile));
        });

        return loggerFactory;
    }
}

