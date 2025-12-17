using Microsoft.Extensions.Logging;
using JTrading.NewsManager.Configuration;
using JTrading.NewsManager.Domain.Models;

namespace JTrading.NewsManager.Services;

public class SymbolMapper
{
    private readonly ILogger<SymbolMapper>? _logger;
    private readonly Dictionary<string, List<string>> _autoMapping;
    private readonly Dictionary<string, List<string>> _customOverrides;

    public SymbolMapper(AppConfig config, ILogger<SymbolMapper>? logger = null)
    {
        _logger = logger;
        _autoMapping = config.SymbolMapping?.AutoMapping ?? LoadDefaultAutoMapping();
        _customOverrides = config.SymbolMapping?.CustomOverrides ?? new Dictionary<string, List<string>>();

        _logger?.LogInformation(
            "Loaded {AutoMappingCount} auto mappings and {CustomOverridesCount} custom overrides",
            _autoMapping.Count,
            _customOverrides.Count
        );
    }

    public List<string> GetAffectedPairs(string currency)
    {
        // First check custom overrides
        if (_customOverrides.TryGetValue(currency, out var customPairs))
        {
            _logger?.LogDebug("Using custom override for {Currency}: {Pairs}", currency, string.Join(", ", customPairs));
            return new List<string>(customPairs);
        }

        // Then check auto mapping
        if (_autoMapping.TryGetValue(currency, out var autoPairs))
        {
            _logger?.LogDebug("Using auto mapping for {Currency}: {Pairs}", currency, string.Join(", ", autoPairs));
            return new List<string>(autoPairs);
        }

        // If no mapping found, return empty list
        _logger?.LogWarning("No mapping found for currency: {Currency}", currency);
        return new List<string>();
    }

    public List<EconomicEvent> MapEventsToPairs(List<EconomicEvent> events)
    {
        var mappedEvents = new List<EconomicEvent>();

        foreach (var evt in events)
        {
            var currency = evt.Currency;
            var affectedPairs = GetAffectedPairs(currency);

            var mappedEvent = new EconomicEvent(evt)
            {
                AffectedPairs = affectedPairs.Any() ? string.Join(", ", affectedPairs) : "N/A"
            };

            mappedEvents.Add(mappedEvent);
        }

        _logger?.LogInformation("Mapped {Count} events with trading pairs", mappedEvents.Count);
        return mappedEvents;
    }

    public void AddCustomMapping(string currency, List<string> pairs)
    {
        _customOverrides[currency] = new List<string>(pairs);
        _logger?.LogInformation("Added custom mapping for {Currency}: {Pairs}", currency, string.Join(", ", pairs));
    }

    public void RemoveCustomMapping(string currency)
    {
        if (_customOverrides.Remove(currency))
        {
            _logger?.LogInformation("Removed custom mapping for {Currency}", currency);
        }
        else
        {
            _logger?.LogWarning("No custom mapping found for {Currency}", currency);
        }
    }

    public List<string> GetAvailableCurrencies()
    {
        var currencies = new HashSet<string>(_autoMapping.Keys);
        currencies.UnionWith(_customOverrides.Keys);
        return currencies.OrderBy(c => c).ToList();
    }

    public Dictionary<string, List<string>> GetAllMappings()
    {
        var completeMapping = new Dictionary<string, List<string>>(_autoMapping);
        foreach (var kvp in _customOverrides)
        {
            completeMapping[kvp.Key] = kvp.Value;
        }
        return completeMapping;
    }

    private static Dictionary<string, List<string>> LoadDefaultAutoMapping()
    {
        return new Dictionary<string, List<string>>
        {
            ["USD"] = new List<string> { "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "NZDUSD", "USDCAD" },
            ["EUR"] = new List<string> { "EURUSD", "EURGBP", "EURJPY", "EURCHF", "EURAUD" },
            ["GBP"] = new List<string> { "GBPUSD", "EURGBP", "GBPJPY", "GBPCHF", "GBPAUD" },
            ["JPY"] = new List<string> { "USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "NZDJPY" },
            ["CHF"] = new List<string> { "USDCHF", "EURCHF", "GBPCHF", "CHFJPY" },
            ["AUD"] = new List<string> { "AUDUSD", "EURAUD", "GBPAUD", "AUDJPY", "AUDNZD" },
            ["NZD"] = new List<string> { "NZDUSD", "NZDJPY", "AUDNZD" },
            ["CAD"] = new List<string> { "USDCAD", "CADJPY" }
        };
    }
}

