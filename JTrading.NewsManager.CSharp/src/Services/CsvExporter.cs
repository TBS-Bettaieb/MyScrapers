using System.Globalization;
using CsvHelper;
using CsvHelper.Configuration;
using Microsoft.Extensions.Logging;
using JTrading.NewsManager.Domain.Models;

namespace JTrading.NewsManager.Services;

public class CsvExporter
{
    private readonly string _outputPath;
    private readonly ILogger<CsvExporter>? _logger;

    public CsvExporter(string outputPath, ILogger<CsvExporter>? logger = null)
    {
        _outputPath = outputPath;
        _logger = logger;
        EnsureOutputDirectory();
    }

    private void EnsureOutputDirectory()
    {
        var outputDir = Path.GetDirectoryName(_outputPath);
        if (!string.IsNullOrEmpty(outputDir) && !Directory.Exists(outputDir))
        {
            Directory.CreateDirectory(outputDir);
            _logger?.LogInformation("Created output directory: {Directory}", outputDir);
        }
    }

    public bool ExportEvents(List<EconomicEvent> events, string mode = "w")
    {
        if (events == null || !events.Any())
        {
            _logger?.LogWarning("No events to export");
            return false;
        }

        try
        {
            // Ensure required fields exist
            var eventsWithDefaults = events.Select(evt => new EconomicEvent(evt)
            {
                Actual = string.IsNullOrEmpty(evt.Actual) ? "N/A" : evt.Actual,
                Forecast = string.IsNullOrEmpty(evt.Forecast) ? "N/A" : evt.Forecast,
                Previous = string.IsNullOrEmpty(evt.Previous) ? "N/A" : evt.Previous,
                AffectedPairs = string.IsNullOrEmpty(evt.AffectedPairs) ? "N/A" : evt.AffectedPairs
            }).ToList();

            // Handle append mode
            if (mode == "a" && File.Exists(_outputPath))
            {
                // Read existing events
                var existingEvents = GetExistingEvents();
                if (existingEvents != null && existingEvents.Any())
                {
                    eventsWithDefaults.AddRange(existingEvents);
                    eventsWithDefaults = RemoveDuplicates(eventsWithDefaults);
                    // Write complete updated file
                    WriteEventsToFile(eventsWithDefaults);
                }
                else
                {
                    WriteEventsToFile(eventsWithDefaults);
                }
            }
            else
            {
                // Write mode (overwrite)
                WriteEventsToFile(eventsWithDefaults);
            }

            _logger?.LogInformation("Exported {Count} events to {Path}", eventsWithDefaults.Count, _outputPath);
            return true;
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Failed to export events");
            return false;
        }
    }

    private void WriteEventsToFile(List<EconomicEvent> events)
    {
        var config = new CsvConfiguration(CultureInfo.InvariantCulture)
        {
            HasHeaderRecord = true
        };

        using var writer = new StreamWriter(_outputPath, false, System.Text.Encoding.UTF8);
        using var csv = new CsvWriter(writer, config);
        csv.Context.RegisterClassMap<EconomicEventMap>();
        csv.WriteRecords(events);
    }

    public bool AppendEvents(List<EconomicEvent> events)
    {
        return ExportEvents(events, mode: "a");
    }

    public List<EconomicEvent>? GetExistingEvents()
    {
        try
        {
            if (!File.Exists(_outputPath))
            {
                _logger?.LogInformation("Output file {Path} does not exist", _outputPath);
                return null;
            }

            var config = new CsvConfiguration(CultureInfo.InvariantCulture)
            {
                HasHeaderRecord = true
            };

            using var reader = new StreamReader(_outputPath, System.Text.Encoding.UTF8);
            using var csv = new CsvReader(reader, config);
            csv.Context.RegisterClassMap<EconomicEventMap>();

            var events = new List<EconomicEvent>();
            csv.Read();
            csv.ReadHeader();

            while (csv.Read())
            {
                try
                {
                    var evt = csv.GetRecord<EconomicEvent>();
                    if (evt != null)
                    {
                        events.Add(evt);
                    }
                }
                catch (Exception ex)
                {
                    _logger?.LogWarning(ex, "Error reading CSV record at line {Line}", csv.Parser.Row);
                }
            }

            return events;
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Failed to read existing events");
            return null;
        }
    }

    private List<EconomicEvent> RemoveDuplicates(List<EconomicEvent> events)
    {
        if (events == null || !events.Any())
        {
            return events ?? new List<EconomicEvent>();
        }

        // Sort by DateTime descending to keep most recent version
        var sorted = events.OrderByDescending(e => e.DateTime).ToList();

        // Remove duplicates based on DateTime, Event, and Currency
        var uniqueEvents = sorted
            .GroupBy(e => new { e.DateTime, e.Event, e.Currency })
            .Select(g => g.First())
            .OrderBy(e => e.DateTime)
            .ToList();

        return uniqueEvents;
    }

    public bool AppendWithDeduplication(List<EconomicEvent> newEvents)
    {
        if (newEvents == null || !newEvents.Any())
        {
            _logger?.LogWarning("No new events to append");
            return false;
        }

        try
        {
            // Read existing events if file exists
            var existingEvents = new List<EconomicEvent>();
            if (File.Exists(_outputPath))
            {
                var loaded = GetExistingEvents();
                if (loaded != null)
                {
                    existingEvents = loaded;
                    _logger?.LogInformation("Loaded {Count} existing events from CSV", existingEvents.Count);
                }
            }

            // Create dictionary for deduplication (key = DateTime + Event + Currency)
            var eventsDict = new Dictionary<string, EconomicEvent>();

            // Add existing events
            foreach (var evt in existingEvents)
            {
                var key = $"{evt.DateTime:yyyy-MM-dd HH:mm:ss}|{evt.Event}|{evt.Currency}";
                if (!string.IsNullOrEmpty(evt.DateTime.ToString()) && !string.IsNullOrEmpty(evt.Event))
                {
                    eventsDict[key] = evt;
                }
            }

            // Add/update with new events
            int updatedCount = 0;
            int addedCount = 0;
            var holidayEvents = newEvents.Where(e => e.Impact == "Holiday").ToList();
            _logger?.LogInformation("Processing {Count} Holiday events in new events", holidayEvents.Count);

            foreach (var evt in newEvents)
            {
                var key = $"{evt.DateTime:yyyy-MM-dd HH:mm:ss}|{evt.Event}|{evt.Currency}";
                if (!string.IsNullOrEmpty(evt.DateTime.ToString()) && !string.IsNullOrEmpty(evt.Event))
                {
                    if (eventsDict.ContainsKey(key))
                    {
                        eventsDict[key] = evt;
                        updatedCount++;
                        if (evt.Impact == "Holiday")
                        {
                            _logger?.LogDebug("Updated Holiday event: {Event} on {DateTime}", evt.Event, evt.DateTime);
                        }
                    }
                    else
                    {
                        eventsDict[key] = evt;
                        addedCount++;
                        if (evt.Impact == "Holiday")
                        {
                            _logger?.LogDebug("Added Holiday event: {Event} on {DateTime}", evt.Event, evt.DateTime);
                        }
                    }
                }
            }

            // Convert back to list and sort by DateTime (newest first for validation)
            var allEvents = eventsDict.Values.OrderByDescending(e => e.DateTime).ToList();

            var finalHolidays = allEvents.Where(e => e.Impact == "Holiday").ToList();
            _logger?.LogInformation(
                "Final events after deduplication: {Total} total, {Holidays} holidays",
                allEvents.Count, finalHolidays.Count);

            // Sort by DateTime ascending for export
            allEvents = allEvents.OrderBy(e => e.DateTime).ToList();

            // Export the deduplicated events
            var success = ExportEvents(allEvents, mode: "w");

            if (success)
            {
                _logger?.LogInformation(
                    "Deduplication complete: {Added} new events added, {Updated} events updated. Total events in CSV: {Total}",
                    addedCount, updatedCount, allEvents.Count);
            }

            return success;
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Failed to append events with deduplication");
            return false;
        }
    }

    public void ValidateDataQuality(List<EconomicEvent> events)
    {
        if (events == null || !events.Any())
        {
            _logger?.LogWarning("No data to validate");
            return;
        }

        try
        {
            var totalEvents = events.Count;

            // Check for missing critical data
            var missingEventNames = events.Count(e => string.IsNullOrEmpty(e.Event));
            var missingCurrencies = events.Count(e => string.IsNullOrEmpty(e.Currency));
            var missingDates = events.Count(e => e.DateTime == default);

            // Check data quality metrics
            var eventsWithActual = events.Count(e => e.Actual != "N/A" && !string.IsNullOrEmpty(e.Actual));
            var eventsWithForecast = events.Count(e => e.Forecast != "N/A" && !string.IsNullOrEmpty(e.Forecast));
            var eventsWithPrevious = events.Count(e => e.Previous != "N/A" && !string.IsNullOrEmpty(e.Previous));

            // Count by impact level
            var impactCounts = events.GroupBy(e => e.Impact)
                .ToDictionary(g => g.Key, g => g.Count());

            // Count by currency
            var currencyCounts = events.GroupBy(e => e.Currency)
                .OrderByDescending(g => g.Count())
                .Take(10)
                .ToDictionary(g => g.Key, g => g.Count());

            _logger?.LogInformation("=" + new string('=', 50));
            _logger?.LogInformation("DATA QUALITY VALIDATION REPORT");
            _logger?.LogInformation("=" + new string('=', 50));
            _logger?.LogInformation("[STATS] Total events: {Total}", totalEvents);
            _logger?.LogInformation("[CHECK] Missing Event names: {Count}", missingEventNames);
            _logger?.LogInformation("[CURRENCY] Missing Currencies: {Count}", missingCurrencies);
            _logger?.LogInformation("[DATE] Missing Dates: {Count}", missingDates);
            _logger?.LogInformation(
                "[ACTUAL] Events with Actual values: {Count} ({Percentage:F1}%)",
                eventsWithActual, eventsWithActual * 100.0 / totalEvents);
            _logger?.LogInformation(
                "[FORECAST] Events with Forecast values: {Count} ({Percentage:F1}%)",
                eventsWithForecast, eventsWithForecast * 100.0 / totalEvents);
            _logger?.LogInformation(
                "[PREVIOUS] Events with Previous values: {Count} ({Percentage:F1}%)",
                eventsWithPrevious, eventsWithPrevious * 100.0 / totalEvents);

            _logger?.LogInformation("Impact Distribution:");
            foreach (var kvp in impactCounts)
            {
                _logger?.LogInformation("  {Impact}: {Count} ({Percentage:F1}%)",
                    kvp.Key, kvp.Value, kvp.Value * 100.0 / totalEvents);
            }

            _logger?.LogInformation("Top Currencies:");
            foreach (var kvp in currencyCounts)
            {
                _logger?.LogInformation("  {Currency}: {Count}", kvp.Key, kvp.Value);
            }

            _logger?.LogInformation("=" + new string('=', 50));
        }
        catch (Exception ex)
        {
            _logger?.LogWarning(ex, "Error during data validation");
        }
    }

    public Dictionary<string, string> GetFileInfo()
    {
        var info = new Dictionary<string, string>
        {
            ["path"] = _outputPath,
            ["exists"] = File.Exists(_outputPath).ToString(),
            ["size"] = "0 bytes"
        };

        try
        {
            if (File.Exists(_outputPath))
            {
                var fileInfo = new FileInfo(_outputPath);
                info["size"] = $"{fileInfo.Length} bytes";
                info["last_modified"] = fileInfo.LastWriteTime.ToString();
            }
        }
        catch (Exception ex)
        {
            _logger?.LogWarning(ex, "Could not get file info");
        }

        return info;
    }
}

