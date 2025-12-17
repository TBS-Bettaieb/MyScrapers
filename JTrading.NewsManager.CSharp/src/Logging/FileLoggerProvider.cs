using Microsoft.Extensions.Logging;

namespace JTrading.NewsManager.Logging;

public class FileLoggerProvider : ILoggerProvider
{
    private readonly string _logFile;

    public FileLoggerProvider(string logFile)
    {
        _logFile = logFile;
    }

    public ILogger CreateLogger(string categoryName)
    {
        return new FileLogger(categoryName, _logFile);
    }

    public void Dispose()
    {
    }
}

public class FileLogger : ILogger
{
    private readonly string _categoryName;
    private readonly string _logFile;
    private readonly object _lock = new();

    public FileLogger(string categoryName, string logFile)
    {
        _categoryName = categoryName;
        _logFile = logFile;
    }

    public IDisposable? BeginScope<TState>(TState state) where TState : notnull => null;

    public bool IsEnabled(LogLevel logLevel) => true;

    public void Log<TState>(
        LogLevel logLevel,
        EventId eventId,
        TState state,
        Exception? exception,
        Func<TState, Exception?, string> formatter)
    {
        if (!IsEnabled(logLevel))
        {
            return;
        }

        var message = formatter(state, exception);
        var logLevelName = logLevel.ToString().ToUpper();
        var timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
        var logMessage = $"{timestamp} - {_categoryName} - {logLevelName} - {message}";

        if (exception != null)
        {
            logMessage += $"\n{exception}";
        }

        lock (_lock)
        {
            File.AppendAllText(_logFile, logMessage + Environment.NewLine, System.Text.Encoding.UTF8);
        }
    }
}

