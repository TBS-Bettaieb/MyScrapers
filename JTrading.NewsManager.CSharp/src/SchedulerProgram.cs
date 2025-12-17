using System.CommandLine;
using Microsoft.Extensions.Logging;
using JTrading.NewsManager.Configuration;
using JTrading.NewsManager.Services;

namespace JTrading.NewsManager;

class SchedulerProgram
{
    static async Task<int> Main(string[] args)
    {
        var configOption = new Option<string?>(
            "--config",
            getDefaultValue: () => "../config/config.json",
            description: "Path to configuration file");

        var runOnceOption = new Option<bool>(
            "--run-once",
            description: "Run the job once immediately instead of scheduling");

        var rootCommand = new RootCommand("Economic News Scheduler")
        {
            configOption,
            runOnceOption
        };

        rootCommand.SetHandler(async (configPath, runOnce) =>
        {
            try
            {
                // Setup basic logging first
                var loggerFactory = LoggerFactory.Create(builder =>
                {
                    builder
                        .SetMinimumLevel(LogLevel.Information)
                        .AddConsole();
                });

                var logger = loggerFactory.CreateLogger<NewsScheduler>();

                var scheduler = new NewsScheduler(configPath ?? "../config/config.json", logger);

                if (runOnce)
                {
                    await scheduler.RunOnceNowAsync();
                }
                else
                {
                    scheduler.StartScheduler();
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Error: {ex.Message}");
                Environment.Exit(1);
            }
        }, configOption, runOnceOption);

        return await rootCommand.InvokeAsync(args);
    }
}

