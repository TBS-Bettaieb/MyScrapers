using Microsoft.Extensions.Logging;
using JTrading.NewsManager.Configuration;
using JTrading.NewsManager.Domain.Models;

namespace JTrading.NewsManager.Services;

public class PipelineRunner
{
    public async Task<bool> RunPipelineAsync(
        AppConfig config,
        string mode,
        DateTime? targetDate,
        bool scrapeOnly,
        ILoggerFactory loggerFactory)
    {
        var logger = loggerFactory.CreateLogger(typeof(PipelineRunner));

        try
        {
            // Initialize components
            var investingConfig = config.InvestingCom ?? new InvestingComConfig();

            // Check if Investing.com scraper is enabled
            if (!investingConfig.Enabled)
            {
                logger.LogError("Investing.com scraper is not enabled in config");
                return false;
            }

            var symbolMapper = new SymbolMapper(config, loggerFactory.CreateLogger<SymbolMapper>());
            var outputConfig = config.Output ?? new OutputConfig();

            // Resolve CSV output path
            var csvOutputPath = outputConfig.CsvPath;
            if (!Path.IsPathRooted(csvOutputPath))
            {
                var currentDir = Directory.GetCurrentDirectory();
                var dir = new DirectoryInfo(currentDir);
                while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "config")))
                {
                    dir = dir.Parent;
                }
                if (dir != null)
                {
                    csvOutputPath = Path.Combine(dir.FullName, csvOutputPath);
                }
                else
                {
                    csvOutputPath = Path.Combine(currentDir, csvOutputPath);
                }
            }

            var csvExporter = new CsvExporter(csvOutputPath, loggerFactory.CreateLogger<CsvExporter>());

            // Initialize Investing.com scraper
            var investingScraper = new InvestingComScraper(investingConfig, loggerFactory.CreateLogger<InvestingComScraper>());
            logger.LogInformation("Investing.com scraper initialized");

            List<EconomicEvent> allEvents = new();

            if (mode == "daily")
            {
                // Daily mode: scrape single date
                if (!targetDate.HasValue)
                {
                    logger.LogError("Target date is required for daily mode");
                    return false;
                }

                logger.LogInformation("Daily mode: scraping events for {Date}", targetDate.Value.Date);

                if (!scrapeOnly)
                {
                    logger.LogInformation("Daily mode: appending to existing CSV file");
                }

                // Scrape from Investing.com
                logger.LogInformation("Scraping Investing.com for {Date}", targetDate.Value.Date);
                var events = await investingScraper.ScrapeSingleDayAsync(targetDate.Value);
                allEvents.AddRange(events);
                logger.LogInformation("Investing.com scrape completed: {Count} events found", events.Count);
            }
            else
            {
                // Range mode: scrape date range
                var monthsBack = investingConfig.MonthsBack;
                var monthsForward = investingConfig.MonthsForward;

                // Convert months to days (using 30 days per month)
                var daysBack = monthsBack * 30;
                var daysForward = monthsForward * 30;

                var endDate = DateTime.Now.AddDays(daysForward);
                var startDate = DateTime.Now.AddDays(-daysBack);

                logger.LogInformation("Range mode: scraping events from {StartDate} to {EndDate}", startDate.Date, endDate.Date);

                // Scrape from Investing.com
                logger.LogInformation("Starting Investing.com range data scraping...");
                var events = await investingScraper.ScrapeDateRangeAsync(startDate, endDate);
                allEvents.AddRange(events);
                logger.LogInformation("Investing.com range scrape completed: {Count} events found", events.Count);
            }

            // Remove duplicates based on DateTime, Event, and Currency
            if (allEvents.Any())
            {
                var uniqueEvents = allEvents
                    .GroupBy(e => new { e.DateTime, e.Event, e.Currency })
                    .Select(g => g.First())
                    .ToList();

                logger.LogInformation("After deduplication: {Count} unique events", uniqueEvents.Count);
                allEvents = uniqueEvents;
            }

            if (!allEvents.Any())
            {
                logger.LogWarning("No events scraped - this may indicate an issue with the scrapers or no events in the date range");
                return true; // Don't fail immediately
            }

            if (scrapeOnly)
            {
                logger.LogInformation("Scrape-only mode: not exporting to CSV");
                // Map events for final count even in scrape-only mode
                var mappedEvents = symbolMapper.MapEventsToPairs(allEvents);
                logger.LogInformation("Pipeline completed successfully with {Count} events processed", mappedEvents.Count);
                return true;
            }

            // Save events to CSV
            if (allEvents.Any() && csvExporter != null)
            {
                try
                {
                    // Map events to trading pairs before saving
                    var mappedEvents = symbolMapper.MapEventsToPairs(allEvents);

                    if (mode == "daily")
                    {
                        // Daily mode: append to existing CSV
                        var success = csvExporter.AppendEvents(mappedEvents);
                        if (success)
                        {
                            logger.LogInformation("Daily mode: appended {Count} events to CSV", mappedEvents.Count);
                        }
                        else
                        {
                            logger.LogWarning("Daily mode: failed to append events to CSV");
                        }
                    }
                    else
                    {
                        // Range mode: merge with deduplication
                        logger.LogInformation("Range mode: performing final CSV merge and deduplication");
                        var success = csvExporter.AppendWithDeduplication(mappedEvents);
                        if (success)
                        {
                            logger.LogInformation("Range mode: merged {Count} events to CSV", mappedEvents.Count);
                        }
                        else
                        {
                            logger.LogWarning("Range mode: failed to merge events to CSV");
                        }
                    }

                    // Validate data quality
                    csvExporter.ValidateDataQuality(mappedEvents);

                    // Get final file info
                    var fileInfo = csvExporter.GetFileInfo();
                    logger.LogInformation("Final CSV file: {Path} (size: {Size})", fileInfo["path"], fileInfo["size"]);

                    // Load and verify the final CSV file
                    try
                    {
                        var finalEvents = csvExporter.GetExistingEvents();
                        if (finalEvents != null)
                        {
                            logger.LogInformation("Pipeline completed successfully. Final CSV contains {Count} events", finalEvents.Count);
                            return true;
                        }
                        else
                        {
                            logger.LogWarning("Could not verify final CSV file state");
                            return true; // Still consider it successful
                        }
                    }
                    catch (Exception verifyError)
                    {
                        logger.LogError(verifyError, "Error verifying final CSV file");
                        return true; // Still consider it successful
                    }
                }
                catch (Exception saveError)
                {
                    logger.LogError(saveError, "Error saving events to CSV");
                    return false;
                }
            }
            else
            {
                logger.LogInformation("No events to save or no CSV exporter available");
                return true;
            }
        }
        catch (Exception ex)
        {
            logger.LogError(ex, "Pipeline failed with error");
            return false;
        }
    }
}

