using CsvHelper.Configuration;

namespace JTrading.NewsManager.Domain.Models;

public class EconomicEvent
{
    public DateTime DateTime { get; set; }
    public string Event { get; set; } = string.Empty;
    public string Country { get; set; } = string.Empty;
    public string Impact { get; set; } = string.Empty;
    public string Currency { get; set; } = string.Empty;
    public string Actual { get; set; } = "N/A";
    public string Forecast { get; set; } = "N/A";
    public string Previous { get; set; } = "N/A";
    public string AffectedPairs { get; set; } = "N/A";

    public EconomicEvent()
    {
    }

    public EconomicEvent(EconomicEvent other)
    {
        DateTime = other.DateTime;
        Event = other.Event;
        Country = other.Country;
        Impact = other.Impact;
        Currency = other.Currency;
        Actual = other.Actual;
        Forecast = other.Forecast;
        Previous = other.Previous;
        AffectedPairs = other.AffectedPairs;
    }
}

public sealed class EconomicEventMap : ClassMap<EconomicEvent>
{
    public EconomicEventMap()
    {
        Map(m => m.DateTime).Name("DateTime").TypeConverterOption.Format("yyyy-MM-dd HH:mm:ss");
        Map(m => m.Event).Name("Event");
        Map(m => m.Country).Name("Country");
        Map(m => m.Impact).Name("Impact");
        Map(m => m.Currency).Name("Currency");
        Map(m => m.Actual).Name("Actual");
        Map(m => m.Forecast).Name("Forecast");
        Map(m => m.Previous).Name("Previous");
        Map(m => m.AffectedPairs).Name("AffectedPairs");
    }
}


