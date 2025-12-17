using System.Threading;
using Microsoft.Extensions.Logging;
using JTrading.NewsManager.Configuration;
using JTrading.NewsManager.Logging;

namespace JTrading.NewsManager.Services;

public class NewsScheduler
{
    private readonly string _configPath;
    private readonly ILogger<NewsScheduler>? _logger;
    private AppConfig? _config;
    private Timer? _timer;
    private bool _running;
    private readonly CancellationTokenSource _cancellationTokenSource;

    public NewsScheduler(string configPath, ILogger<NewsScheduler>? logger = null)
    {
        _configPath = configPath;
        _logger = logger;
        _cancellationTokenSource = new CancellationTokenSource();
        
        // Setup signal handlers for graceful shutdown
        Console.CancelKeyPress += (sender, e) =>
        {
            e.Cancel = true;
            _logger?.LogInformation("Received Ctrl+C signal. Initiating graceful shutdown...");
            _running = false;
            _cancellationTokenSource.Cancel();
        };
    }

    private bool LoadAndSetup()
    {
        try
        {
            _config = ConfigLoader.LoadConfig(_configPath, _logger);
            return true;
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Failed to load configuration");
            return false;
        }
    }

    private async void ScheduledJob(object? state)
    {
        if (_config == null)
        {
            return;
        }

        _logger?.LogInformation("=" + new string('=', 50));
        _logger?.LogInformation("Scheduled job started at {Time}", DateTime.Now);

        try
        {
            // We need to create a new logger factory for the pipeline
            var loggerFactory = CreateLoggerFactory(_config);
            
            // Use the pipeline runner
            var pipelineRunner = new PipelineRunner();
            var success = await pipelineRunner.RunPipelineAsync(
                _config,
                _config.InvestingCom?.DefaultMode ?? "range",
                null,
                false,
                loggerFactory);

            if (success)
            {
                _logger?.LogInformation("Scheduled job completed successfully");
            }
            else
            {
                _logger?.LogError("Scheduled job failed");
            }
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Scheduled job failed with exception");
        }

        _logger?.LogInformation("Scheduled job finished at {Time}", DateTime.Now);
        _logger?.LogInformation("=" + new string('=', 50));
    }

    private ILoggerFactory CreateLoggerFactory(AppConfig config)
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

    public void StartScheduler()
    {
        if (!LoadAndSetup())
        {
            _logger?.LogError("Failed to setup scheduler. Exiting.");
            Environment.Exit(1);
            return;
        }

        var schedulerConfig = _config?.Scheduler ?? new SchedulerConfig();
        var runTimeStr = schedulerConfig.RunTime ?? "06:00";

        // Parse run time (HH:mm format)
        if (!TimeSpan.TryParse(runTimeStr, out var runTime))
        {
            _logger?.LogError("Invalid run_time format in config: {RunTime}. Expected HH:mm format.", runTimeStr);
            Environment.Exit(1);
            return;
        }

        _logger?.LogInformation("Setting up scheduled job for daily execution at {RunTime}", runTimeStr);

        // Calculate initial delay until next run time
        var now = DateTime.Now;
        var nextRun = now.Date.Add(runTime);
        if (nextRun <= now)
        {
            nextRun = nextRun.AddDays(1);
        }

        var initialDelay = nextRun - now;
        _logger?.LogInformation("Next scheduled run: {NextRun}", nextRun);

        _running = true;

        // Create a timer that runs daily
        _timer = new Timer(ScheduledJob, null, initialDelay, TimeSpan.FromDays(1));

        _logger?.LogInformation("Scheduler started. Waiting for next execution...");

        // Keep the application running
        try
        {
            while (_running && !_cancellationTokenSource.Token.IsCancellationRequested)
            {
                Thread.Sleep(1000); // Check every second for shutdown signal
            }
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Scheduler error");
        }
        finally
        {
            _logger?.LogInformation("Scheduler shutdown complete");
            _timer?.Dispose();
            _running = false;
        }
    }

    public async Task RunOnceNowAsync()
    {
        if (!LoadAndSetup())
        {
            _logger?.LogError("Failed to setup scheduler. Exiting.");
            Environment.Exit(1);
            return;
        }

        _logger?.LogInformation("Running job once immediately...");
        ScheduledJob(null);
    }

    public DateTime? GetNextRunTime()
    {
        var schedulerConfig = _config?.Scheduler ?? new SchedulerConfig();
        var runTimeStr = schedulerConfig.RunTime ?? "06:00";

        if (TimeSpan.TryParse(runTimeStr, out var runTime))
        {
            var now = DateTime.Now;
            var nextRun = now.Date.Add(runTime);
            if (nextRun <= now)
            {
                nextRun = nextRun.AddDays(1);
            }
            return nextRun;
        }

        return null;
    }
}

