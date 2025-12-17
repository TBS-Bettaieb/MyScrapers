using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using HtmlAgilityPack;
using Microsoft.Extensions.Logging;
using JTrading.NewsManager.Configuration;
using JTrading.NewsManager.Domain.Models;

namespace JTrading.NewsManager.Services;

public class InvestingComScraper
{
    private readonly ILogger<InvestingComScraper>? _logger;
    private readonly HttpClient _httpClient;
    private readonly InvestingComConfig _config;
    private readonly Random _random = new();

    // Mapping des country IDs vers noms de pays
    private static readonly Dictionary<int, string> CountryMap = new()
    {
        [25] = "United States",
        [32] = "Eurozone",
        [6] = "Australia",
        [37] = "Japan",
        [72] = "Germany",
        [22] = "United Kingdom",
        [17] = "Canada",
        [39] = "Switzerland",
        [14] = "China",
        [10] = "New Zealand",
        [35] = "Sweden",
        [43] = "Norway",
        [56] = "France",
        [36] = "South Korea",
        [110] = "India",
        [11] = "Brazil",
        [26] = "Italy",
        [12] = "Russia",
        [4] = "South Africa",
        [5] = "Mexico"
    };

    // Mapping des niveaux d'impact
    private static readonly Dictionary<int, string> ImpactMap = new()
    {
        [1] = "Low",
        [2] = "Medium",
        [3] = "High"
    };

    private static readonly Dictionary<string, string> ImpactMapString = new()
    {
        ["low"] = "Low",
        ["medium"] = "Medium",
        ["high"] = "High",
        ["holiday"] = "Holiday"
    };

    public InvestingComScraper(InvestingComConfig config, ILogger<InvestingComScraper>? logger = null)
    {
        _config = config;
        _logger = logger;
        _httpClient = new HttpClient();
        SetupHttpClient();
    }

    private void SetupHttpClient()
    {
        _httpClient.BaseAddress = new Uri("https://www.investing.com");
        _httpClient.DefaultRequestHeaders.Add("Accept", "*/*");
        _httpClient.DefaultRequestHeaders.Add("Accept-Language", "fr-FR,fr;q=0.9,en-FR;q=0.8,en;q=0.7,ar-EG;q=0.6,ar;q=0.5,en-US;q=0.4");
        _httpClient.DefaultRequestHeaders.Add("Origin", "https://www.investing.com");
        _httpClient.DefaultRequestHeaders.Add("Referer", "https://www.investing.com/economic-calendar/");
        _httpClient.DefaultRequestHeaders.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36");
        _httpClient.DefaultRequestHeaders.Add("X-Requested-With", "XMLHttpRequest");
        _httpClient.Timeout = TimeSpan.FromSeconds(_config.Timeout);
    }

    private async Task<JsonDocument?> MakeApiRequestAsync(DateTime dateFrom, DateTime dateTo, int limitFrom = 0)
    {
        var dateFromStr = dateFrom.ToString("yyyy-MM-dd");
        var dateToStr = dateTo.ToString("yyyy-MM-dd");

        var postData = new List<KeyValuePair<string, string>>();

        // Ajouter les pays (valeurs multiples)
        foreach (var countryId in _config.Countries)
        {
            postData.Add(new KeyValuePair<string, string>("country[]", countryId.ToString()));
        }

        // Ajouter les autres paramètres
        postData.AddRange(new[]
        {
            new KeyValuePair<string, string>("dateFrom", dateFromStr),
            new KeyValuePair<string, string>("dateTo", dateToStr),
            new KeyValuePair<string, string>("timeZone", _config.Timezone.ToString()),
            new KeyValuePair<string, string>("timeFilter", "timeRemain"),
            new KeyValuePair<string, string>("currentTab", "custom"),
            new KeyValuePair<string, string>("limit_from", limitFrom.ToString())
        });

        var content = new FormUrlEncodedContent(postData);
        content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/x-www-form-urlencoded");

        for (int attempt = 0; attempt < _config.RetryAttempts; attempt++)
        {
            try
            {
                _logger?.LogDebug("API request attempt {Attempt}/{MaxAttempts}: {DateFrom} to {DateTo}",
                    attempt + 1, _config.RetryAttempts, dateFromStr, dateToStr);

                var response = await _httpClient.PostAsync(_config.BaseUrl, content);
                
                if (response.IsSuccessStatusCode)
                {
                    var responseText = await response.Content.ReadAsStringAsync();
                    try
                    {
                        var jsonDoc = JsonDocument.Parse(responseText);
                        return jsonDoc;
                    }
                    catch (JsonException ex)
                    {
                        _logger?.LogError(ex, "Failed to parse JSON response");
                        _logger?.LogDebug("Response text (first 500 chars): {ResponseText}",
                            responseText.Length > 500 ? responseText.Substring(0, 500) : responseText);
                        
                        if (attempt < _config.RetryAttempts - 1)
                        {
                            await Task.Delay(TimeSpan.FromSeconds(_random.Next(2, 5)));
                            continue;
                        }
                        return null;
                    }
                }
                else
                {
                    _logger?.LogWarning("API returned status {StatusCode}", response.StatusCode);
                    if (attempt < _config.RetryAttempts - 1)
                    {
                        await Task.Delay(TimeSpan.FromSeconds(_random.Next(2, 5)));
                        continue;
                    }
                    return null;
                }
            }
            catch (Exception ex)
            {
                _logger?.LogError(ex, "Request error on attempt {Attempt}", attempt + 1);
                if (attempt < _config.RetryAttempts - 1)
                {
                    var delay = TimeSpan.FromSeconds(_random.Next(2, 5) * (attempt + 1));
                    await Task.Delay(delay);
                    continue;
                }
                return null;
            }
        }

        return null;
    }

    private List<EconomicEvent> ParseJsonResponse(JsonDocument jsonDoc, DateTime? referenceDate = null)
    {
        var events = new List<EconomicEvent>();

        try
        {
            if (!jsonDoc.RootElement.TryGetProperty("data", out var dataElement))
            {
                _logger?.LogWarning("No 'data' property in JSON response");
                return events;
            }

            if (dataElement.ValueKind == JsonValueKind.String)
            {
                // Data is HTML string, parse it
                var htmlContent = dataElement.GetString();
                if (!string.IsNullOrEmpty(htmlContent))
                {
                    _logger?.LogDebug("Response contains HTML string (length: {Length}), parsing HTML table...", htmlContent.Length);
                    return ParseHtmlResponse(htmlContent, referenceDate);
                }
            }
            else if (dataElement.ValueKind == JsonValueKind.Array)
            {
                // Data is array of events
                foreach (var eventElement in dataElement.EnumerateArray())
                {
                    var eventDict = JsonSerializer.Deserialize<Dictionary<string, JsonElement>>(eventElement.GetRawText());
                    if (eventDict != null)
                    {
                        var evt = TransformEvent(eventDict, referenceDate);
                        if (evt != null)
                        {
                            events.Add(evt);
                        }
                    }
                }
            }
            else
            {
                _logger?.LogWarning("Unexpected data format: {ValueKind}", dataElement.ValueKind);
            }

            _logger?.LogInformation("Parsed {Count} events from API response", events.Count);
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Error parsing JSON response");
        }

        return events;
    }

    private List<EconomicEvent> ParseHtmlResponse(string htmlContent, DateTime? referenceDate = null)
    {
        var events = new List<EconomicEvent>();

        try
        {
            var doc = new HtmlDocument();
            doc.LoadHtml(htmlContent);

            var allRows = doc.DocumentNode.SelectNodes("//tr") ?? new HtmlNodeCollection(null);
            _logger?.LogDebug("Found {Count} total <tr> rows in HTML", allRows.Count);

            DateTime? currentDate = referenceDate;
            int dateHeadersFound = 0;
            int eventRowsFound = 0;
            int eventsParsed = 0;

            foreach (var row in allRows)
            {
                // Check if it's a date header row
                var theDay = row.SelectSingleNode(".//td[contains(@class, 'theDay')]");
                if (theDay != null)
                {
                    dateHeadersFound++;
                    var theDayId = theDay.GetAttributeValue("id", "");
                    if (!string.IsNullOrEmpty(theDayId) && theDayId.StartsWith("theDay"))
                    {
                        try
                        {
                            var timestampStr = theDayId.Replace("theDay", "");
                            if (long.TryParse(timestampStr, out var timestamp))
                            {
                                // Check if timestamp is in milliseconds
                                if (timestamp > 1000000000000)
                                {
                                    timestamp /= 1000;
                                }
                                currentDate = DateTimeOffset.FromUnixTimeSeconds(timestamp).DateTime;
                                _logger?.LogDebug("Found date header: {Date}", currentDate);
                            }
                        }
                        catch
                        {
                            // Try parsing from text
                            var dayText = theDay.InnerText.Trim();
                            if (DateTime.TryParse(dayText, out var parsedDate))
                            {
                                currentDate = parsedDate;
                            }
                        }
                    }
                    continue;
                }

                // Parse event rows
                var rowId = row.GetAttributeValue("id", "");
                if (!string.IsNullOrEmpty(rowId) && rowId.Contains("eventRowId"))
                {
                    eventRowsFound++;
                    var dateForEvent = currentDate ?? referenceDate;
                    if (dateForEvent.HasValue)
                    {
                        _logger?.LogDebug("Parsing event row {RowId} with date: {Date}", rowId, dateForEvent.Value.Date);
                    }

                    var evt = ParseHtmlEventRow(row, dateForEvent);
                    if (evt != null)
                    {
                        eventsParsed++;
                        if (evt.Impact == "Holiday")
                        {
                            _logger?.LogDebug("Parsed Holiday event: {Event} on {DateTime}", evt.Event, evt.DateTime);
                        }
                        events.Add(evt);
                    }
                }
            }

            var holidaysParsed = events.Count(e => e.Impact == "Holiday");
            _logger?.LogInformation(
                "Parsed {Count} events from HTML (found {DateHeaders} date headers, {EventRows} event rows, {Parsed} successfully parsed, {Holidays} holidays)",
                events.Count, dateHeadersFound, eventRowsFound, eventsParsed, holidaysParsed);
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Error parsing HTML response");
        }

        return events;
    }

    private EconomicEvent? ParseHtmlEventRow(HtmlNode row, DateTime? referenceDate)
    {
        try
        {
            var cells = row.SelectNodes(".//td | .//th") ?? new HtmlNodeCollection(null);
            if (cells.Count < 3)
            {
                return null;
            }

            var eventData = new Dictionary<string, string>();

            // 1. DATE/HEURE - Extract from data-event-datetime
            var datetimeAttr = row.GetAttributeValue("data-event-datetime", "");
            if (!string.IsNullOrEmpty(datetimeAttr))
            {
                if (DateTime.TryParseExact(datetimeAttr, "yyyy/MM/dd HH:mm:ss", null, System.Globalization.DateTimeStyles.None, out var eventTime) ||
                    DateTime.TryParseExact(datetimeAttr, "yyyy-MM-dd HH:mm:ss", null, System.Globalization.DateTimeStyles.None, out eventTime))
                {
                    eventData["timestamp"] = new DateTimeOffset(eventTime).ToUnixTimeSeconds().ToString();
                }
                else
                {
                    eventData["date"] = datetimeAttr;
                }
            }

            // 2. HEURE - Extract from time cell
            if (!eventData.ContainsKey("timestamp") && !eventData.ContainsKey("date"))
            {
                var timeCell = row.SelectSingleNode(".//td[contains(@class, 'time')]");
                if (timeCell != null)
                {
                    var timeText = timeCell.InnerText.Trim();
                    if (!string.IsNullOrEmpty(timeText) && timeText != "All Day")
                    {
                        eventData["time"] = timeText;
                    }
                }
            }

            // 3. CURRENCY - Extract from flagCur cell
            var flagCell = row.SelectSingleNode(".//td[contains(@class, 'flagCur')]");
            if (flagCell != null)
            {
                var flagText = flagCell.InnerText.Trim();
                var currencyMatch = Regex.Match(flagText, @"\b([A-Z]{3,4})\b");
                if (currencyMatch.Success)
                {
                    eventData["currency"] = currencyMatch.Groups[1].Value;
                }

                // 4. COUNTRY - Extract from title of span
                var countrySpan = flagCell.SelectSingleNode(".//span[@title]");
                if (countrySpan != null)
                {
                    var countryName = countrySpan.GetAttributeValue("title", "");
                    if (!string.IsNullOrEmpty(countryName))
                    {
                        eventData["country"] = countryName;
                    }
                }
            }

            // 5. IMPACT - Extract from sentiment cell
            var sentimentCell = row.SelectSingleNode(".//td[contains(@class, 'sentiment')]");
            if (sentimentCell != null)
            {
                var sentimentText = sentimentCell.InnerText.Trim();
                var sentimentSpans = sentimentCell.SelectNodes(".//span");
                foreach (var span in sentimentSpans ?? new HtmlNodeCollection(null))
                {
                    var spanText = span.InnerText.Trim();
                    if (spanText.Contains("Holiday", StringComparison.OrdinalIgnoreCase))
                    {
                        sentimentText = "Holiday";
                        break;
                    }
                }

                if (sentimentText.Contains("Holiday", StringComparison.OrdinalIgnoreCase))
                {
                    eventData["impact"] = "Holiday";
                }
                else
                {
                    var impactAttr = sentimentCell.GetAttributeValue("data-img_key", "");
                    if (!string.IsNullOrEmpty(impactAttr))
                    {
                        if (impactAttr.Contains("bull3") || impactAttr.Contains("3"))
                        {
                            eventData["impact"] = "High";
                        }
                        else if (impactAttr.Contains("bull2") || impactAttr.Contains("2"))
                        {
                            eventData["impact"] = "Medium";
                        }
                        else if (impactAttr.Contains("bull1") || impactAttr.Contains("1"))
                        {
                            eventData["impact"] = "Low";
                        }
                    }
                }
            }

            // 6. EVENT NAME - Extract from event cell
            var eventCell = row.SelectSingleNode(".//td[contains(@class, 'event')]");
            if (eventCell != null)
            {
                var eventLink = eventCell.SelectSingleNode(".//a");
                if (eventLink != null)
                {
                    eventData["title"] = eventLink.InnerText.Trim();
                }
                else
                {
                    var eventText = eventCell.InnerText.Trim();
                    if (!string.IsNullOrEmpty(eventText))
                    {
                        eventData["title"] = eventText;
                    }
                }
            }

            // Check for Holiday keywords in event name
            if (!eventData.ContainsKey("impact") && eventData.ContainsKey("title"))
            {
                var eventName = eventData["title"].ToLowerInvariant();
                var holidayKeywords = new[] { "holiday", "christmas", "new year", "thanksgiving", "easter", "independence day" };
                if (holidayKeywords.Any(keyword => eventName.Contains(keyword)))
                {
                    eventData["impact"] = "Holiday";
                }
            }

            // 7. ACTUAL - Extract from act cell
            var actualCell = row.SelectSingleNode(".//td[contains(@class, 'act')] | .//td[contains(@id, 'eventActual')]");
            if (actualCell != null)
            {
                var actualText = actualCell.InnerText.Trim();
                if (!string.IsNullOrEmpty(actualText) && actualText != "&nbsp;")
                {
                    eventData["actual"] = actualText;
                }
            }

            // 8. FORECAST - Extract from fore cell
            var forecastCell = row.SelectSingleNode(".//td[contains(@class, 'fore')] | .//td[contains(@id, 'eventForecast')]");
            if (forecastCell != null)
            {
                var forecastText = forecastCell.InnerText.Trim();
                if (!string.IsNullOrEmpty(forecastText) && forecastText != "&nbsp;")
                {
                    eventData["forecast"] = forecastText;
                }
            }

            // 9. PREVIOUS - Extract from prev cell
            var previousCell = row.SelectSingleNode(".//td[contains(@class, 'prev')] | .//td[contains(@id, 'eventPrevious')]");
            if (previousCell != null)
            {
                var previousText = previousCell.InnerText.Trim();
                if (!string.IsNullOrEmpty(previousText) && previousText != "&nbsp;")
                {
                    eventData["previous"] = previousText;
                }
            }

            // Transform to EconomicEvent
            if (eventData.ContainsKey("title"))
            {
                return TransformEvent(eventData, referenceDate);
            }
        }
        catch (Exception ex)
        {
            _logger?.LogDebug(ex, "Error parsing HTML row");
        }

        return null;
    }

    private EconomicEvent? TransformEvent(Dictionary<string, string> eventData, DateTime? referenceDate)
    {
        try
        {
            var eventName = eventData.GetValueOrDefault("title", eventData.GetValueOrDefault("event", eventData.GetValueOrDefault("name", "")));
            if (string.IsNullOrEmpty(eventName))
            {
                return null;
            }

            // DateTime
            DateTime? eventTime = null;

            if (eventData.TryGetValue("timestamp", out var timestampStr) && long.TryParse(timestampStr, out var timestamp))
            {
                if (timestamp > 1000000000000)
                {
                    timestamp /= 1000;
                }
                eventTime = DateTimeOffset.FromUnixTimeSeconds(timestamp).DateTime;
            }
            else if (eventData.TryGetValue("date", out var dateStr))
            {
                if (DateTime.TryParse(dateStr, out var parsedDate))
                {
                    eventTime = parsedDate;
                }
            }

            // Combine date and time if needed
            if (eventTime.HasValue && eventTime.Value.Hour == 0 && eventTime.Value.Minute == 0 && eventData.TryGetValue("time", out var timeStr))
            {
                if (TimeSpan.TryParse(timeStr, out var timeSpan))
                {
                    eventTime = eventTime.Value.Date + timeSpan;
                }
            }
            else if (!eventTime.HasValue && eventData.TryGetValue("time", out var timeStr2) && referenceDate.HasValue)
            {
                if (TimeSpan.TryParse(timeStr2, out var timeSpan2))
                {
                    eventTime = referenceDate.Value.Date + timeSpan2;
                }
            }

            // Use reference date if no time found
            if (!eventTime.HasValue)
            {
                eventTime = referenceDate?.Date.AddHours(12) ?? DateTime.Now;
            }

            // Country
            var countryId = eventData.GetValueOrDefault("countryId", eventData.GetValueOrDefault("country_id", eventData.GetValueOrDefault("country", "")));
            var country = GetCountryName(countryId);

            // Currency
            var currency = eventData.GetValueOrDefault("currency", eventData.GetValueOrDefault("code", ""));
            if (string.IsNullOrEmpty(currency) && int.TryParse(countryId, out var countryIdInt))
            {
                currency = GetCurrencyFromCountry(countryIdInt);
            }

            // Impact
            var impactValue = eventData.GetValueOrDefault("impact", eventData.GetValueOrDefault("importance", eventData.GetValueOrDefault("priority", "")));
            
            // Check for Holiday keywords
            if (string.IsNullOrEmpty(impactValue) || (!impactValue.Equals("Holiday", StringComparison.OrdinalIgnoreCase) && 
                !new[] { "high", "medium", "low" }.Contains(impactValue.ToLowerInvariant())))
            {
                var eventNameLower = eventName.ToLowerInvariant();
                var holidayKeywords = new[] { "holiday", "christmas", "new year", "thanksgiving", "easter", "independence day" };
                if (holidayKeywords.Any(keyword => eventNameLower.Contains(keyword)))
                {
                    impactValue = "Holiday";
                }
            }

            var impact = ParseImpact(impactValue);

            // Actual/Forecast/Previous
            var actual = eventData.GetValueOrDefault("actual", "N/A");
            var forecast = eventData.GetValueOrDefault("forecast", "N/A");
            var previous = eventData.GetValueOrDefault("previous", "N/A");

            return new EconomicEvent
            {
                DateTime = eventTime.Value,
                Event = eventName,
                Country = country,
                Impact = impact,
                Currency = currency,
                Actual = actual != "N/A" ? actual : "N/A",
                Forecast = forecast != "N/A" ? forecast : "N/A",
                Previous = previous != "N/A" ? previous : "N/A"
            };
        }
        catch (Exception ex)
        {
            _logger?.LogError(ex, "Error transforming event");
            return null;
        }
    }

    private string GetCountryName(string? countryId)
    {
        if (string.IsNullOrEmpty(countryId))
        {
            return "Unknown";
        }

        if (int.TryParse(countryId, out var id))
        {
            return CountryMap.GetValueOrDefault(id, $"Country_{id}");
        }

        return countryId;
    }

    private string GetCurrencyFromCountry(int countryId)
    {
        var currencyMap = new Dictionary<int, string>
        {
            [25] = "USD", [32] = "EUR", [6] = "AUD", [37] = "JPY",
            [72] = "EUR", [22] = "GBP", [17] = "CAD", [39] = "CHF",
            [14] = "CNY", [10] = "NZD", [35] = "SEK", [43] = "NOK",
            [56] = "EUR", [36] = "KRW", [110] = "INR", [11] = "BRL",
            [26] = "EUR", [12] = "RUB", [4] = "ZAR", [5] = "MXN"
        };

        return currencyMap.GetValueOrDefault(countryId, "");
    }

    private string ParseImpact(string? impactValue)
    {
        if (string.IsNullOrEmpty(impactValue))
        {
            return "Medium";
        }

        var impactLower = impactValue.ToLowerInvariant();
        if (ImpactMapString.TryGetValue(impactLower, out var mappedImpact))
        {
            return impactValue.Equals("Holiday", StringComparison.OrdinalIgnoreCase) ? "Holiday" : mappedImpact;
        }

        if (int.TryParse(impactValue, out var impactInt) && ImpactMap.TryGetValue(impactInt, out var mappedInt))
        {
            return mappedInt;
        }

        if (impactLower.Contains("holiday"))
        {
            return "Holiday";
        }
        else if (impactLower.Contains("high") || impactLower == "3")
        {
            return "High";
        }
        else if (impactLower.Contains("medium") || impactLower == "2")
        {
            return "Medium";
        }
        else if (impactLower.Contains("low") || impactLower == "1")
        {
            return "Low";
        }

        return "Medium";
    }

    private EconomicEvent? TransformEvent(Dictionary<string, JsonElement> eventData, DateTime? referenceDate)
    {
        var dict = new Dictionary<string, string>();
        foreach (var kvp in eventData)
        {
            dict[kvp.Key] = kvp.Value.ValueKind == JsonValueKind.String 
                ? kvp.Value.GetString() ?? "" 
                : kvp.Value.GetRawText();
        }
        return TransformEvent(dict, referenceDate);
    }

    public async Task<List<EconomicEvent>> ScrapeSingleDayAsync(DateTime targetDate)
    {
        _logger?.LogInformation("Scraping Investing.com for {Date}", targetDate.Date);

        var jsonDoc = await MakeApiRequestAsync(targetDate, targetDate);
        if (jsonDoc == null)
        {
            _logger?.LogWarning("No data received for {Date}", targetDate.Date);
            return new List<EconomicEvent>();
        }

        var events = ParseJsonResponse(jsonDoc, targetDate);
        _logger?.LogInformation("Scraped {Count} events from Investing.com for {Date}", events.Count, targetDate.Date);
        
        jsonDoc.Dispose();
        return events;
    }

    public async Task<List<EconomicEvent>> ScrapeDateRangeAsync(DateTime startDate, DateTime endDate)
    {
        _logger?.LogInformation("Scraping Investing.com from {StartDate} to {EndDate}", startDate.Date, endDate.Date);

        var allEvents = new List<EconomicEvent>();

        // Important holidays to scrape separately
        var importantHolidays = new List<DateTime>();
        for (int year = startDate.Year; year <= endDate.Year; year++)
        {
            var christmas = new DateTime(year, 12, 25);
            if (startDate <= christmas && christmas <= endDate)
            {
                importantHolidays.Add(christmas);
            }

            var newYear = new DateTime(year, 1, 1);
            if (startDate <= newYear && newYear <= endDate)
            {
                importantHolidays.Add(newYear);
            }
        }

        _logger?.LogInformation("Found {Count} important holiday dates in range to scrape separately", importantHolidays.Count);

        // Scrape in chunks of 30 days
        const int chunkDays = 30;
        var currentStart = startDate;
        while (currentStart <= endDate)
        {
            var currentEnd = currentStart.AddDays(chunkDays - 1);
            if (currentEnd > endDate)
            {
                currentEnd = endDate;
            }

            _logger?.LogInformation("Scraping chunk: {StartDate} to {EndDate}", currentStart.Date, currentEnd.Date);

            var jsonDoc = await MakeApiRequestAsync(currentStart, currentEnd);
            if (jsonDoc != null)
            {
                var events = ParseJsonResponse(jsonDoc, currentStart);
                allEvents.AddRange(events);
                jsonDoc.Dispose();

                // Delay between chunks
                if (currentEnd < endDate)
                {
                    var delay = TimeSpan.FromSeconds(_random.Next(1, 4));
                    await Task.Delay(delay);
                }
            }
            else
            {
                _logger?.LogWarning("No data received for chunk {StartDate} to {EndDate}", currentStart.Date, currentEnd.Date);
            }

            currentStart = currentEnd.AddDays(1);
        }

        // Scrape important holidays separately
        var holidayEvents = new List<EconomicEvent>();
        foreach (var holidayDate in importantHolidays)
        {
            _logger?.LogInformation("Scraping holiday date: {Date}", holidayDate.Date);
            try
            {
                var events = await ScrapeSingleDayAsync(holidayDate);
                holidayEvents.AddRange(events);
                await Task.Delay(TimeSpan.FromSeconds(_random.Next(1, 3)));
            }
            catch (Exception ex)
            {
                _logger?.LogWarning(ex, "Failed to scrape holiday date {Date}", holidayDate.Date);
            }
        }

        if (holidayEvents.Any())
        {
            _logger?.LogInformation("Scraped {Count} additional events from holiday dates", holidayEvents.Count);
            allEvents.AddRange(holidayEvents);
        }

        _logger?.LogInformation("Scraped {Count} total events from Investing.com", allEvents.Count);
        return allEvents;
    }

    public void Dispose()
    {
        _httpClient?.Dispose();
    }
}

