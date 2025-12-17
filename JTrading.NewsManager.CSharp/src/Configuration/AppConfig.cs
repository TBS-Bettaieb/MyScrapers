using System.Text.Json.Serialization;

namespace JTrading.NewsManager.Configuration;

public class AppConfig
{
    [JsonPropertyName("scheduler")]
    public SchedulerConfig? Scheduler { get; set; }

    [JsonPropertyName("output")]
    public OutputConfig? Output { get; set; }

    [JsonPropertyName("symbol_mapping")]
    public SymbolMappingConfig? SymbolMapping { get; set; }

    [JsonPropertyName("logging")]
    public LoggingConfig? Logging { get; set; }

    [JsonPropertyName("investing_com")]
    public InvestingComConfig? InvestingCom { get; set; }
}

public class SchedulerConfig
{
    [JsonPropertyName("run_time")]
    public string RunTime { get; set; } = "06:00";

    [JsonPropertyName("timezone")]
    public string Timezone { get; set; } = "local";
}

public class OutputConfig
{
    [JsonPropertyName("csv_path")]
    public string CsvPath { get; set; } = "output/economic_events.csv";
}

public class SymbolMappingConfig
{
    [JsonPropertyName("auto_mapping")]
    public Dictionary<string, List<string>> AutoMapping { get; set; } = new();

    [JsonPropertyName("custom_overrides")]
    public Dictionary<string, List<string>> CustomOverrides { get; set; } = new();
}

public class LoggingConfig
{
    [JsonPropertyName("level")]
    public string Level { get; set; } = "INFO";

    [JsonPropertyName("file")]
    public string File { get; set; } = "logs/app.log";

    [JsonPropertyName("format")]
    public string Format { get; set; } = "%(asctime)s - %(name)s - %(levelname)s - %(message)s";
}

public class InvestingComConfig
{
    [JsonPropertyName("enabled")]
    public bool Enabled { get; set; } = true;

    [JsonPropertyName("default_mode")]
    public string DefaultMode { get; set; } = "range";

    [JsonPropertyName("months_back")]
    public int MonthsBack { get; set; } = 4;

    [JsonPropertyName("months_forward")]
    public int MonthsForward { get; set; } = 0;

    [JsonPropertyName("base_url")]
    public string BaseUrl { get; set; } = "https://www.investing.com/economic-calendar/Service/getCalendarFilteredData";

    [JsonPropertyName("countries")]
    public List<int> Countries { get; set; } = new();

    [JsonPropertyName("timezone")]
    public int Timezone { get; set; } = 55;

    [JsonPropertyName("timeout")]
    public int Timeout { get; set; } = 30;

    [JsonPropertyName("retry_attempts")]
    public int RetryAttempts { get; set; } = 3;
}

